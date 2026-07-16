/**
 * "Synchronizace kalendáře" dialog for the Rezervace page.
 *
 * Two clearly separated concerns (backend enforces both independently):
 *   1. Reservation EXPORT into an external calendar
 *      - admin/spravce  → whole-institution scope ("Synchronizace rezervací instituce")
 *      - educator/lecturer/production → only their assigned reservations
 *   2. ICS subscription feed (revocable link) + one-time download
 *
 * Personal calendar CONNECT (Google/Outlook) is shared with the Lektorský
 * profil; connecting here connects the same personal account.
 */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import {
  CalendarDays, RefreshCw, Unlink, ExternalLink, Link2, Copy, Trash2,
  Rss, Info, Building2, User as UserIcon,
} from 'lucide-react';
import { API } from '../../config/api';
import { PROVIDERS, listFeedTokens, createFeedToken, revokeFeedToken, copyToClipboard } from './calendarUtils';

const formatApiError = (err, fallback) => {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (detail) return status ? `${detail} (${status})` : detail;
  return fallback;
};

export const ReservationSyncDialog = ({ open, onClose, user, token }) => {
  const headers = { Authorization: `Bearer ${token}` };
  const isManager = ['admin', 'spravce'].includes(user?.role);

  const [google, setGoogle] = useState({ connected: false, configured: false });
  const [outlook, setOutlook] = useState({ connected: false });
  const [syncing, setSyncing] = useState(null);
  const [feeds, setFeeds] = useState([]);
  const [freshUrl, setFreshUrl] = useState(null);
  const [feedLoading, setFeedLoading] = useState(false);

  const fetchGoogle = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/google-calendar/status`, { headers });
      setGoogle(res.data);
    } catch (err) {
      if (err?.response?.status !== 403) console.error('google status');
    }
  }, [token]);

  const fetchOutlook = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/microsoft-calendar/status`, { headers });
      setOutlook(res.data);
    } catch (err) {
      if (err?.response?.status !== 403) console.error('outlook status');
    }
  }, [token]);

  const fetchFeeds = useCallback(async () => {
    try { setFeeds(await listFeedTokens(token)); } catch { /* ignore */ }
  }, [token]);

  useEffect(() => {
    if (!open) return;
    fetchGoogle();
    fetchOutlook();
    fetchFeeds();
  }, [open, fetchGoogle, fetchOutlook, fetchFeeds]);

  // Refresh when an OAuth popup reports success.
  useEffect(() => {
    const handler = (event) => {
      if (event.data?.type === 'google_connected') { toast.success('Google kalendář připojen'); fetchGoogle(); }
      else if (event.data?.type === 'outlook_connected') { toast.success('Outlook kalendář připojen'); fetchOutlook(); }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [fetchGoogle, fetchOutlook]);

  const connect = async (provider) => {
    const base = provider === 'google' ? 'google-calendar' : 'microsoft-calendar';
    try {
      const res = await axios.get(`${API}/${base}/connect`, { headers });
      if (res.data.auth_url) window.open(res.data.auth_url, `${provider}_auth`, 'width=500,height=700');
    } catch (err) {
      toast.error(formatApiError(err, 'Nepodařilo se zahájit připojení'));
    }
  };

  const setExport = async (provider, value) => {
    const base = provider === 'google' ? 'google-calendar' : 'microsoft-calendar';
    const setter = provider === 'google' ? setGoogle : setOutlook;
    const prev = provider === 'google' ? google : outlook;
    setter((s) => ({ ...s, export_enabled: value }));
    try {
      // Google auto-syncs only when auto_sync_enabled; turn it on with export.
      const body = provider === 'google'
        ? { export_enabled: value, auto_sync_enabled: value || prev.import_enabled }
        : { export_enabled: value };
      await axios.put(`${API}/${base}/settings`, body, { headers });
      toast.success(value ? 'Export rezervací zapnut' : 'Export rezervací vypnut');
    } catch (err) {
      setter(prev);
      if (err?.response?.status === 409 || err?.response?.status === 403) {
        setter((s) => ({ ...s, needs_reconnect: true }));
        toast.error('Pro export je potřeba znovu připojit účet (chybí oprávnění k zápisu do kalendáře).');
      } else {
        toast.error(formatApiError(err, 'Nepodařilo se uložit nastavení'));
      }
    }
  };

  const runSync = async (provider) => {
    const base = provider === 'google' ? 'google-calendar' : 'microsoft-calendar';
    setSyncing(provider);
    try {
      const res = await axios.post(`${API}/${base}/sync`, {}, { headers });
      toast.success(res.data.message || 'Synchronizováno');
      provider === 'google' ? fetchGoogle() : fetchOutlook();
    } catch (err) {
      toast.error(formatApiError(err, 'Synchronizace selhala'));
    } finally {
      setSyncing(null);
    }
  };

  const generateFeed = async () => {
    setFeedLoading(true);
    try {
      const feedType = isManager ? 'institution' : 'lecturer';
      const entityId = isManager ? user?.institution_id : user?.id;
      const data = await createFeedToken(feedType, entityId, token);
      setFreshUrl(data.url);
      toast.success('Nový odkaz vygenerován. Předchozí přestal platit.');
      fetchFeeds();
    } catch (err) {
      toast.error(formatApiError(err, 'Nepodařilo se vygenerovat odkaz'));
    } finally {
      setFeedLoading(false);
    }
  };

  const revoke = async (id) => {
    try {
      await revokeFeedToken(id, token);
      setFreshUrl(null);
      toast.success('Odkaz byl zneplatněn');
      fetchFeeds();
    } catch (err) {
      toast.error(formatApiError(err, 'Nepodařilo se zneplatnit odkaz'));
    }
  };

  const ProviderExportRow = ({ provider, status }) => {
    const meta = PROVIDERS[provider];
    const scopeInstitution = status.export_scope === 'institution';
    return (
      <div className="rounded-lg border border-slate-200 p-3" data-testid={`sync-provider-${provider}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${status.connected ? meta.ring : 'bg-gray-100'}`}>
              <CalendarDays className={`w-4.5 h-4.5 ${status.connected ? meta.accent : 'text-gray-400'}`} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">{meta.label}</p>
              <p className="text-xs text-gray-500">
                {status.connected
                  ? `Připojeno${status.last_sync_at ? ' · ' + new Date(status.last_sync_at).toLocaleString('cs-CZ') : ''}`
                  : (status.configured === false ? 'Modul není nakonfigurován' : 'Nepřipojeno')}
              </p>
            </div>
          </div>
          {status.connected ? (
            <div className="flex items-center gap-1.5">
              <Button variant="outline" size="sm" onClick={() => runSync(provider)} disabled={syncing === provider} data-testid={`sync-now-${provider}`}>
                <RefreshCw className={`w-4 h-4 ${syncing === provider ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          ) : (
            <Button
              size="sm"
              onClick={() => connect(provider)}
              disabled={provider === 'google' && status.configured === false}
              data-testid={`connect-${provider}`}
              className="bg-slate-800 hover:bg-slate-900 text-white"
            >
              <ExternalLink className="w-4 h-4 mr-1" />
              {meta.connectLabel}
            </Button>
          )}
        </div>

        {status.connected && (
          <div className="mt-3 pt-3 border-t flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-800 flex items-center gap-1.5">
                {scopeInstitution ? <Building2 className="w-3.5 h-3.5" /> : <UserIcon className="w-3.5 h-3.5" />}
                {scopeInstitution ? 'Exportovat rezervace celé instituce' : 'Exportovat mé přiřazené rezervace'}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {scopeInstitution
                  ? 'Všechny rezervace instituce se zapíší do tohoto kalendáře.'
                  : 'Do kalendáře se zapíší jen rezervace, ke kterým jste přiřazeni.'}
              </p>
              {status.needs_reconnect && (
                <p className="text-xs text-amber-700 mt-1">Pro export je potřeba účet znovu připojit (oprávnění k zápisu).</p>
              )}
            </div>
            <Switch
              checked={!!status.export_enabled}
              onCheckedChange={(v) => setExport(provider, v)}
              data-testid={`export-toggle-${provider}`}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose?.(); }}>
      <DialogContent className="sm:max-w-lg max-h-[85dvh] overflow-y-auto" aria-describedby={undefined} data-testid="reservation-sync-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarDays className="w-5 h-5 text-[#4A6FA5]" />
            Synchronizace kalendáře
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-1">
          {/* Reservation export */}
          <section className="space-y-2">
            <h3 className="text-sm font-semibold text-slate-900">
              {isManager ? 'Synchronizace rezervací instituce' : 'Export mých rezervací'}
            </h3>
            <p className="text-xs text-gray-500">
              {isManager
                ? 'Zapíše rezervace do připojeného Google nebo Outlook kalendáře. Administrativní funkce za celý účet.'
                : 'Zapíše vaše přiřazené rezervace do vašeho připojeného kalendáře.'}
            </p>
            <ProviderExportRow provider="google" status={google} />
            <ProviderExportRow provider="outlook" status={outlook} />
          </section>

          {/* ICS subscription feed */}
          <section className="space-y-2 pt-1 border-t">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
              <Rss className="w-4 h-4 text-[#C4AB86]" />
              Odkaz pro odběr (ICS)
            </h3>
            <p className="text-xs text-gray-500">
              Alternativa bez přihlašování — vložte odkaz do libovolného kalendáře (Google, Apple, Outlook…). Odkaz je tajný; kdokoli s ním uvidí termíny.
            </p>

            {freshUrl && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-2.5" data-testid="fresh-feed-url">
                <p className="text-xs font-medium text-emerald-800 mb-1">Váš nový odkaz (zkopírujte hned, zobrazí se jen teď):</p>
                <div className="flex items-center gap-1.5">
                  <code className="flex-1 text-[11px] bg-white border rounded px-2 py-1 truncate">{freshUrl}</code>
                  <Button size="sm" variant="outline" onClick={() => copyToClipboard(freshUrl)} data-testid="copy-feed-url">
                    <Copy className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={generateFeed} disabled={feedLoading} data-testid="generate-feed-btn">
                <Link2 className="w-4 h-4 mr-1.5" />
                {feeds.length > 0 ? 'Vygenerovat nový odkaz' : 'Vytvořit odkaz pro odběr'}
              </Button>
            </div>

            {feeds.length > 0 && (
              <div className="space-y-1.5" data-testid="feed-token-list">
                {feeds.map((f) => (
                  <div key={f.id} className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2" data-testid={`feed-token-${f.id}`}>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-700 truncate flex items-center gap-1.5">
                        <span>{f.feed_type === 'institution' ? 'Rezervace instituce' : f.feed_type === 'lecturer' ? 'Moje rezervace' : 'Program'}</span>
                        <Badge variant="outline" className="text-[10px]">aktivní</Badge>
                      </div>
                      <p className="text-[11px] text-gray-400">
                        Vytvořeno {f.created_at ? new Date(f.created_at).toLocaleDateString('cs-CZ') : '—'}
                        {f.last_used_at && ` · naposledy použit ${new Date(f.last_used_at).toLocaleDateString('cs-CZ')}`}
                      </p>
                    </div>
                    <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50 h-8 w-8 p-0" onClick={() => revoke(f.id)} data-testid={`revoke-feed-${f.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <p className="text-[11px] text-gray-400 flex items-start gap-1">
              <Info className="w-3 h-3 mt-0.5 shrink-0" />
              Vygenerování nového odkazu okamžitě zneplatní ten předchozí.
            </p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ReservationSyncDialog;
