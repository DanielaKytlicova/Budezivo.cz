import React, { useState, useMemo, useEffect, useCallback } from 'react';
import axios from 'axios';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  Search, Plus, Mail, Phone, User, Calendar, ShieldCheck, ShieldX,
  X, Edit2, Save, Tag, Filter, Download, ChevronRight, Loader2, AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../../config/api';

const CONTACT_TYPES = [
  { value: 'skola', label: 'Škola' },
  { value: 'pedagog', label: 'Pedagog' },
  { value: 'rodic', label: 'Rodič' },
  { value: 'verejnost', label: 'Veřejnost' },
  { value: 'odborna_verejnost', label: 'Odborná veřejnost' },
  { value: 'jine', label: 'Jiný' },
];

const CONTACT_SOURCES = [
  { value: 'skolni_rezervace', label: 'Školní rezervace' },
  { value: 'jednorazova_akce', label: 'Jednorázová akce' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'kurz', label: 'Kurz' },
  { value: 'primestsky_tabor', label: 'Příměstský tábor' },
  { value: 'baby_herna', label: 'Baby herna' },
  { value: 'rucne', label: 'Ručně přidáno' },
];

function typeLabel(value) {
  return CONTACT_TYPES.find(t => t.value === value)?.label || value;
}
function sourceLabel(value) {
  return CONTACT_SOURCES.find(s => s.value === value)?.label || value;
}
function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('cs-CZ');
  } catch { return iso; }
}

function ConsentBadge({ consent }) {
  if (consent === true) {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 gap-1">
        <ShieldCheck className="w-3 h-3" /> Souhlas
      </Badge>
    );
  }
  if (consent === false) {
    return (
      <Badge variant="outline" className="gap-1 text-rose-600 border-rose-200">
        <ShieldX className="w-3 h-3" /> Bez souhlasu
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1 text-slate-500">
      <ShieldX className="w-3 h-3" /> Neznámé
    </Badge>
  );
}

const ContactsPage = () => {
  const [contacts, setContacts] = useState([]);
  const [stats, setStats] = useState({ total: 0, with_consent: 0, schools: 0, public: 0 });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [consentFilter, setConsentFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(null);
  const [showAdd, setShowAdd] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (typeFilter !== 'all') params.set('type', typeFilter);
      if (sourceFilter !== 'all') params.set('source', sourceFilter);
      if (consentFilter !== 'all') params.set('consent', consentFilter);
      if (searchQuery.trim()) params.set('search', searchQuery.trim());
      const [list, st] = await Promise.all([
        axios.get(`${API}/contacts?${params.toString()}`),
        axios.get(`${API}/contacts/stats`),
      ]);
      setContacts(list.data || []);
      setStats(st.data || stats);
    } catch (err) {
      toast.error('Nepodařilo se načíst kontakty');
      console.error(err);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeFilter, sourceFilter, consentFilter, searchQuery]);

  useEffect(() => {
    // Debounce search input slightly
    const t = setTimeout(fetchAll, 250);
    return () => clearTimeout(t);
  }, [fetchAll]);

  const handleExportCsv = async () => {
    try {
      const params = new URLSearchParams();
      if (typeFilter !== 'all') params.set('type', typeFilter);
      if (sourceFilter !== 'all') params.set('source', sourceFilter);
      if (consentFilter !== 'all') params.set('consent', consentFilter);
      if (searchQuery.trim()) params.set('search', searchQuery.trim());
      const res = await axios.get(`${API}/contacts/export.csv?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'kontakty.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Export se nepodařil');
    }
  };

  const handleSaveContact = async (payload, contactId) => {
    try {
      if (contactId) {
        await axios.patch(`${API}/contacts/${contactId}`, payload);
        toast.success('Kontakt aktualizován');
      } else {
        await axios.post(`${API}/contacts`, payload);
        toast.success('Kontakt přidán');
        setShowAdd(false);
      }
      await fetchAll();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Uložení selhalo';
      toast.error(msg);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-4 md:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Kontakty</h1>
            <p className="text-sm text-slate-500 mt-1">
              Centrální přehled kontaktů z rezervací a přihlášek na akce.
              Slouží jako základ pro cílený mailing.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleExportCsv} data-testid="contacts-export-btn">
              <Download className="w-4 h-4 mr-2" /> Export CSV
            </Button>
            <Button
              className="bg-slate-800 text-white hover:bg-slate-700"
              onClick={() => setShowAdd(true)}
              data-testid="contacts-add-btn"
            >
              <Plus className="w-4 h-4 mr-2" /> Přidat kontakt
            </Button>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Celkem kontaktů</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-total">{stats.total}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">S marketing. souhlasem</p>
            <p className="text-2xl font-semibold text-emerald-700 mt-1" data-testid="stat-consent">{stats.with_consent}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Pedagogové / Školy</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-schools">{stats.schools}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Veřejnost / Rodiče</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-public">{stats.public}</p>
          </Card>
        </div>

        {/* Filters */}
        <Card className="p-3 md:p-4">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Hledat podle jména, e-mailu, telefonu, školy..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="contacts-search"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[170px]" data-testid="filter-type">
                  <Filter className="w-3.5 h-3.5 mr-1.5" /><SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny typy</SelectItem>
                  {CONTACT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={sourceFilter} onValueChange={setSourceFilter}>
                <SelectTrigger className="w-[180px]" data-testid="filter-source">
                  <Tag className="w-3.5 h-3.5 mr-1.5" /><SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny zdroje</SelectItem>
                  {CONTACT_SOURCES.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={consentFilter} onValueChange={setConsentFilter}>
                <SelectTrigger className="w-[180px]" data-testid="filter-consent">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1.5" /><SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny souhlasy</SelectItem>
                  <SelectItem value="yes">Pouze se souhlasem</SelectItem>
                  <SelectItem value="no">Bez souhlasu</SelectItem>
                  <SelectItem value="unknown">Neznámý</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-2.5" data-testid="contacts-result-count">
            Zobrazeno {contacts.length} z {stats.total}
          </p>
        </Card>

        {/* Table */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="contacts-table">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Jméno</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">E-mail / telefon</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Typ</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Zdroj</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Marketing</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Poslední aktivita</th>
                  <th className="px-4 py-3 text-right font-semibold text-slate-600"></th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin inline mr-2" /> Načítám…
                  </td></tr>
                )}
                {!loading && contacts.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-12" data-testid="contacts-empty">
                    <AlertCircle className="w-8 h-8 text-slate-300 inline mb-2" />
                    <p className="text-slate-400">Žádné kontakty neodpovídají vašim filtrům.</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Kontakty se automaticky tvoří z nových rezervací a přihlášek na akce od dnešního dne.
                    </p>
                  </td></tr>
                )}
                {contacts.map(c => (
                  <tr key={c.id} onClick={() => setSelectedId(c.id)}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                    data-testid={`contact-row-${c.id}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">
                        {c.first_name || ''} {c.last_name || ''}
                        {!c.first_name && !c.last_name && <span className="text-slate-400 italic">(bez jména)</span>}
                      </div>
                      {c.school_name && <div className="text-xs text-slate-500 mt-0.5">{c.school_name}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-700">{c.email}</div>
                      {c.phone && <div className="text-xs text-slate-500 mt-0.5">{c.phone}</div>}
                    </td>
                    <td className="px-4 py-3"><Badge variant="outline" className="font-normal">{typeLabel(c.type)}</Badge></td>
                    <td className="px-4 py-3 text-slate-600 text-xs">{sourceLabel(c.primary_source) || '—'}</td>
                    <td className="px-4 py-3"><ConsentBadge consent={c.marketing_consent} /></td>
                    <td className="px-4 py-3 text-slate-600 text-xs">{formatDate(c.last_activity_at)}</td>
                    <td className="px-4 py-3 text-right"><ChevronRight className="w-4 h-4 text-slate-400 inline" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {selectedId && (
        <ContactDetailPanel
          contactId={selectedId}
          onClose={() => setSelectedId(null)}
          onSave={handleSaveContact}
          onDelete={async () => { await fetchAll(); setSelectedId(null); }}
        />
      )}
      {showAdd && (
        <AddContactDialog
          onClose={() => setShowAdd(false)}
          onSave={(payload) => handleSaveContact(payload, null)}
        />
      )}
    </AdminLayout>
  );
};

function ContactDetailPanel({ contactId, onClose, onSave, onDelete }) {
  const [contact, setContact] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editingNote, setEditingNote] = useState(false);
  const [note, setNote] = useState('');
  const [type, setType] = useState('jine');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API}/contacts/${contactId}`);
        if (cancelled) return;
        setContact(res.data);
        setNote(res.data.note || '');
        setType(res.data.type || 'jine');
      } catch {
        toast.error('Nepodařilo se načíst detail');
        onClose();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [contactId, onClose]);

  const handleSaveNote = async () => {
    await onSave({ note, type }, contactId);
    setEditingNote(false);
    setContact(c => ({ ...c, note, type }));
  };
  const handleTypeChange = async (v) => {
    setType(v);
    await onSave({ type: v }, contactId);
    setContact(c => ({ ...c, type: v }));
  };
  const handleConsentToggle = async () => {
    const next = contact.marketing_consent ? false : true;
    await onSave({ marketing_consent: next }, contactId);
    setContact(c => ({ ...c, marketing_consent: next }));
  };
  const handleDelete = async () => {
    if (!window.confirm('Opravdu smazat tento kontakt? Akce je nevratná.')) return;
    try {
      await axios.delete(`${API}/contacts/${contactId}`);
      toast.success('Kontakt smazán');
      onDelete();
    } catch {
      toast.error('Smazání selhalo');
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} data-testid="contact-detail-backdrop" />
      <div className="fixed top-0 right-0 bottom-0 w-full sm:max-w-md bg-white shadow-2xl z-50 overflow-y-auto" data-testid="contact-detail-panel">
        <div className="sticky top-0 bg-white border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Detail kontaktu</h2>
            {contact?.id && <p className="text-xs text-slate-500 mt-0.5">ID: {contact.id.slice(0, 8)}…</p>}
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 transition-colors" data-testid="contact-detail-close">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {loading && <div className="p-8 text-center"><Loader2 className="w-6 h-6 animate-spin text-slate-400 mx-auto" /></div>}
        {contact && (
          <div className="p-5 space-y-6">
            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Identita</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-slate-400" />
                  <span className="font-medium text-slate-900">
                    {contact.first_name || ''} {contact.last_name || ''}
                    {!contact.first_name && !contact.last_name && <em className="text-slate-400">(bez jména)</em>}
                  </span>
                </div>
                {contact.school_name && <div className="text-slate-600 pl-6">{contact.school_name}</div>}
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Kontaktní údaje</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-slate-400" />
                  <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline">{contact.email}</a>
                </div>
                {contact.phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-slate-400" />
                    <a href={`tel:${contact.phone}`} className="text-slate-700">{contact.phone}</a>
                  </div>
                )}
              </div>
            </section>

            <section className="grid grid-cols-2 gap-3">
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Typ</h3>
                <Select value={type} onValueChange={handleTypeChange}>
                  <SelectTrigger data-testid="detail-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CONTACT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Marketing</h3>
                <button
                  type="button"
                  onClick={handleConsentToggle}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  data-testid="detail-consent-toggle"
                  title="Klikněte pro přepnutí souhlasu"
                >
                  <ConsentBadge consent={contact.marketing_consent} />
                </button>
                {!contact.marketing_consent && (
                  <p className="mt-1 text-xs text-slate-500">Kliknutím obnovíte odběr této instituce.</p>
                )}
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Poznámka</h3>
                {!editingNote ? (
                  <button onClick={() => setEditingNote(true)} className="text-xs text-blue-600 hover:underline flex items-center gap-1" data-testid="detail-note-edit">
                    <Edit2 className="w-3 h-3" /> Upravit
                  </button>
                ) : (
                  <button onClick={handleSaveNote} className="text-xs text-emerald-600 hover:underline flex items-center gap-1" data-testid="detail-note-save">
                    <Save className="w-3 h-3" /> Uložit
                  </button>
                )}
              </div>
              {editingNote ? (
                <textarea value={note} onChange={e => setNote(e.target.value)} className="w-full p-2 border border-slate-200 rounded text-sm min-h-[80px]" data-testid="detail-note-textarea" />
              ) : (
                <p className="text-sm text-slate-700 italic">
                  {contact.note || <span className="text-slate-400 not-italic">Bez poznámky</span>}
                </p>
              )}
            </section>

            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Historie vazeb ({contact.links?.length || 0})
              </h3>
              {(!contact.links || contact.links.length === 0) ? (
                <p className="text-xs text-slate-400">Žádné vazby. Nové vazby se přidají automaticky při příští rezervaci nebo přihlášce.</p>
              ) : (
                <ol className="space-y-3" data-testid="detail-links-list">
                  {contact.links.map(l => (
                    <li key={l.id} className="flex items-start gap-3 text-sm border-l-2 border-slate-200 pl-3">
                      <Calendar className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="font-medium text-slate-900">{l.label || '—'}</div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {formatDate(l.linked_at)} · {sourceLabel(l.source_type)}
                          {l.status && <> · <span className="font-medium">{l.status}</span></>}
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            <section className="pt-3 border-t border-slate-100 text-xs text-slate-400 space-y-0.5">
              <p>Vytvořeno: {formatDate(contact.created_at)}</p>
              <p>Poslední aktivita: {formatDate(contact.last_activity_at)}</p>
              <button
                onClick={handleDelete}
                className="text-rose-600 hover:underline mt-3"
                data-testid="contact-delete-btn"
              >
                Smazat kontakt
              </button>
            </section>
          </div>
        )}
      </div>
    </>
  );
}

function AddContactDialog({ onClose, onSave }) {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    type: 'pedagog', school_name: '', marketing_consent: false, note: '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email.trim()) {
      toast.error('E-mail je povinný');
      return;
    }
    setSaving(true);
    await onSave(form);
    setSaving(false);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-6 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Přidat kontakt</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded">
              <X className="w-4 h-4" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Jméno" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} data-testid="add-first-name" />
              <Input placeholder="Příjmení" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} data-testid="add-last-name" />
            </div>
            <Input type="email" placeholder="E-mail *" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required data-testid="add-email" />
            <Input placeholder="Telefon" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} data-testid="add-phone" />
            <Input placeholder="Škola (volitelné)" value={form.school_name} onChange={e => setForm({ ...form, school_name: e.target.value })} data-testid="add-school" />
            <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
              <SelectTrigger data-testid="add-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONTACT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <textarea placeholder="Poznámka" value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} className="w-full p-2 border rounded text-sm min-h-[60px]" data-testid="add-note" />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.marketing_consent} onChange={e => setForm({ ...form, marketing_consent: e.target.checked })} data-testid="add-consent" />
              Marketingový souhlas (kontakt může být zařazen do propagačních kampaní)
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Zrušit</Button>
              <Button type="submit" disabled={saving} className="bg-slate-800 text-white" data-testid="add-submit">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Přidat'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}

export default ContactsPage;
