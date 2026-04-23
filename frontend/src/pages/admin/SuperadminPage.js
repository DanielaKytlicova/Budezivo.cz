import React, { useState, useEffect, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Building2, Users, BookOpen, Calendar, Mail, BarChart3, Loader2,
  Search, ChevronRight, Crown, Shield, AlertTriangle, Check, X,
  FileText, Clock, ArrowLeft, Eye, Settings2, Trash2, BarChart2,
  UserCog, AtSign, History, Flag, ToggleLeft, ToggleRight, Image as ImageIcon
} from 'lucide-react';
import { API } from '../../config/api';

const PLAN_BADGE = {
  free: 'bg-slate-100 text-slate-700',
  start: 'bg-blue-100 text-blue-700',
  pro: 'bg-amber-100 text-amber-800',
  pro_plus: 'bg-purple-100 text-purple-800',
};

const STATUS_BADGE = {
  active: 'bg-green-100 text-green-700',
  pending: 'bg-yellow-100 text-yellow-800',
  inactive: 'bg-slate-100 text-slate-500',
  expired: 'bg-red-100 text-red-700',
  cancelled: 'bg-red-100 text-red-600',
};

export const SuperadminPage = () => {
  const { user } = useContext(AuthContext);
  const [view, setView] = useState('overview'); // overview | institutions | detail | billing
  const [overview, setOverview] = useState(null);
  const [institutions, setInstitutions] = useState([]);
  const [billingOrders, setBillingOrders] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [auditLog, setAuditLog] = useState(null);
  const [featureFlags, setFeatureFlags] = useState(null);
  const [selectedInst, setSelectedInst] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState('all');

  // Plan change modal
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planForm, setPlanForm] = useState({ plan: 'free', plan_status: 'active', activated_by: 'admin', billing_note: '' });
  const [saving, setSaving] = useState(false);

  // Delete institution modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteForm, setDeleteForm] = useState({ confirmation_name: '', reason: '' });
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { loadOverview(); loadInstitutions(); }, []);

  const loadOverview = async () => {
    try {
      const res = await axios.get(`${API}/superadmin/overview`, { withCredentials: true });
      setOverview(res.data);
    } catch { /* silent */ }
  };

  const loadInstitutions = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/superadmin/institutions`, { withCredentials: true });
      setInstitutions(res.data.institutions || []);
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
    finally { setLoading(false); }
  };

  const loadDetail = async (id) => {
    try {
      const res = await axios.get(`${API}/superadmin/institutions/${id}`, { withCredentials: true });
      setSelectedInst(res.data);
      setView('detail');
    } catch { toast.error('Nepodařilo se načíst detail'); }
  };

  const loadBilling = async () => {
    try {
      const res = await axios.get(`${API}/superadmin/billing-orders`, { withCredentials: true });
      setBillingOrders(res.data.orders || []);
      setView('billing');
    } catch { toast.error('Chyba při načítání objednávek'); }
  };

  const loadAnalytics = async () => {
    try {
      const res = await axios.get(`${API}/superadmin/usage-analytics`, { withCredentials: true });
      setAnalytics(res.data);
      setView('analytics');
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při načítání analytiky'); }
  };

  const loadAuditLog = async () => {
    try {
      const res = await axios.get(`${API}/superadmin/audit-log?per_page=100`, { withCredentials: true });
      setAuditLog(res.data);
      setView('audit');
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při načítání historie'); }
  };

  const loadFeatureFlags = async () => {
    try {
      // Ensure we have the full institutions list to let admin choose
      let insts = institutions;
      if (!insts || insts.length === 0) {
        const r = await axios.get(`${API}/superadmin/institutions?per_page=200`, { withCredentials: true });
        insts = r.data.institutions || [];
        setInstitutions(insts);
      }
      const res = await axios.get(`${API}/superadmin/feature-flags`, { withCredentials: true });
      setFeatureFlags(res.data);
      setView('features');
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při načítání feature flagů'); }
  };

  const saveFeatureFlag = async (flagKey, patch) => {
    try {
      await axios.put(`${API}/superadmin/feature-flags/${flagKey}`, patch, { withCredentials: true });
      toast.success('Feature flag uložen');
      loadFeatureFlags();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
  };

  const runExpirationJob = async () => {
    if (!window.confirm('Spustit expirační úlohu nyní? Instituce s expirovaným plánem budou přepnuty do stavu expired.')) return;
    try {
      await axios.post(`${API}/superadmin/run-expiration-job`, {}, { withCredentials: true });
      toast.success('Expirační úloha spuštěna');
      loadInstitutions();
      loadOverview();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
  };

  const handlePlanChange = async () => {
    if (!selectedInst) return;
    setSaving(true);
    try {
      await axios.put(`${API}/superadmin/institutions/${selectedInst.id}/plan`, planForm, { withCredentials: true });
      toast.success('Plán změněn');
      setShowPlanModal(false);
      await loadDetail(selectedInst.id);
      loadInstitutions();
      loadOverview();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
    finally { setSaving(false); }
  };

  const confirmOrder = async (orderId) => {
    try {
      await axios.post(`${API}/superadmin/billing-orders/${orderId}/confirm`, {}, { withCredentials: true });
      toast.success('Objednávka potvrzena, plán aktivován');
      loadBilling();
      loadOverview();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
  };

  const cancelOrder = async (orderId) => {
    if (!window.confirm('Zrušit objednávku?')) return;
    try {
      await axios.post(`${API}/superadmin/billing-orders/${orderId}/cancel`, {}, { withCredentials: true });
      toast.success('Objednávka zrušena');
      loadBilling();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
  };

  const handleDeleteInstitution = async () => {
    if (!selectedInst) return;
    setDeleting(true);
    try {
      await axios.delete(`${API}/superadmin/institutions/${selectedInst.id}`, {
        data: deleteForm,
        withCredentials: true,
      });
      toast.success('Instituce byla smazána');
      setShowDeleteModal(false);
      setDeleteForm({ confirmation_name: '', reason: '' });
      setSelectedInst(null);
      setView('institutions');
      loadInstitutions();
      loadOverview();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při mazání'); }
    finally { setDeleting(false); }
  };

  const filtered = institutions.filter(i => {
    if (planFilter !== 'all' && i.plan !== planFilter) return false;
    if (search && !i.name?.toLowerCase().includes(search.toLowerCase()) && !i.email?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {view !== 'overview' && view !== 'institutions' && (
              <Button variant="ghost" size="sm" onClick={() => { setView('institutions'); setSelectedInst(null); }}>
                <ArrowLeft className="w-4 h-4" />
              </Button>
            )}
            <Shield className="w-6 h-6 text-purple-600" />
            <h1 className="text-2xl font-bold text-slate-900" data-testid="superadmin-title">Superadmin</h1>
          </div>
          <div className="flex gap-2">
            <Button variant={view === 'overview' || view === 'institutions' ? 'default' : 'outline'} size="sm"
              onClick={() => setView('institutions')} data-testid="tab-institutions">
              <Building2 className="w-4 h-4 mr-1" /> Instituce
            </Button>
            <Button variant={view === 'billing' ? 'default' : 'outline'} size="sm"
              onClick={loadBilling} data-testid="tab-billing">
              <FileText className="w-4 h-4 mr-1" /> Objednávky
            </Button>
            <Button variant={view === 'analytics' ? 'default' : 'outline'} size="sm"
              onClick={loadAnalytics} data-testid="tab-analytics">
              <BarChart2 className="w-4 h-4 mr-1" /> Usage
            </Button>
            <Button variant={view === 'audit' ? 'default' : 'outline'} size="sm"
              onClick={loadAuditLog} data-testid="tab-audit">
              <History className="w-4 h-4 mr-1" /> Historie
            </Button>
            <Button variant={view === 'features' ? 'default' : 'outline'} size="sm"
              onClick={loadFeatureFlags} data-testid="tab-features">
              <Flag className="w-4 h-4 mr-1" /> Feature flagy
            </Button>
            <Button variant="outline" size="sm" onClick={runExpirationJob} data-testid="run-expiration-btn" title="Spustit expiraci plánů nyní">
              <Clock className="w-4 h-4 mr-1" /> Expirace
            </Button>
          </div>
        </div>

        {/* Overview cards */}
        {overview && (view === 'overview' || view === 'institutions') && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="p-4 text-center">
              <div className="text-2xl font-bold">{overview.total_institutions}</div>
              <div className="text-xs text-slate-500">Institucí</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-2xl font-bold">{overview.total_reservations}</div>
              <div className="text-xs text-slate-500">Rezervací</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-2xl font-bold">{overview.total_programs}</div>
              <div className="text-xs text-slate-500">Programů</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-2xl font-bold text-amber-600">{overview.pending_billing_orders}</div>
              <div className="text-xs text-slate-500">Čeká na platbu</div>
            </Card>
            {/* Plan distribution */}
            {Object.entries(overview.plan_distribution).map(([plan, count]) => (
              <Card key={plan} className="p-3 flex items-center justify-between">
                <Badge className={PLAN_BADGE[plan] || ''}>{plan === 'pro_plus' ? 'PRO+' : plan.toUpperCase()}</Badge>
                <span className="text-lg font-bold">{count}</span>
              </Card>
            ))}
          </div>
        )}

        {/* Institutions list */}
        {(view === 'overview' || view === 'institutions') && (
          <div className="space-y-3">
            <div className="flex gap-2 items-center">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Hledat instituci..." className="pl-9" data-testid="search-institutions" />
              </div>
              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny plány</SelectItem>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="start">Start</SelectItem>
                  <SelectItem value="pro">PRO</SelectItem>
                  <SelectItem value="pro_plus">PRO+</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {loading ? (
              <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : (
              <div className="space-y-2">
                {filtered.map(inst => (
                  <Card key={inst.id} className="p-3 hover:shadow-md transition-shadow cursor-pointer" onClick={() => loadDetail(inst.id)} data-testid={`inst-row-${inst.id}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-semibold text-slate-900 truncate">{inst.name}</span>
                          <Badge className={PLAN_BADGE[inst.plan] || ''}>{inst.plan_label}</Badge>
                          <Badge className={STATUS_BADGE[inst.plan_status] || ''}>{inst.plan_status}</Badge>
                        </div>
                        <div className="flex gap-4 text-xs text-slate-500">
                          <span>{inst.programs_count} programů</span>
                          <span>{inst.reservations_count} rezervací</span>
                          <span>{inst.users_count} uživatelů</span>
                          {inst.plan_activated_by && <span>Aktivoval: {inst.plan_activated_by}</span>}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                    </div>
                  </Card>
                ))}
                {filtered.length === 0 && <p className="text-center text-slate-500 py-8">Žádné instituce</p>}
              </div>
            )}
          </div>
        )}

        {/* Institution detail */}
        {view === 'detail' && selectedInst && (
          <InstitutionDetail
            inst={selectedInst}
            canDelete={String(selectedInst.id) !== String(user?.institution_id)}
            onPlanChange={() => {
              setPlanForm({ plan: selectedInst.plan, plan_status: selectedInst.plan_status, activated_by: 'admin', billing_note: selectedInst.billing_note || '' });
              setShowPlanModal(true);
            }}
            onDelete={() => {
              setDeleteForm({ confirmation_name: '', reason: '' });
              setShowDeleteModal(true);
            }}
          />
        )}

        {/* Billing orders */}
        {view === 'billing' && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Objednávky plánů</h2>
            {billingOrders.length === 0 ? (
              <p className="text-slate-500 text-center py-8">Žádné objednávky</p>
            ) : billingOrders.map(o => (
              <Card key={o.id} className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{o.institution_name}</span>
                      <Badge className={PLAN_BADGE[o.requested_plan] || ''}>{o.requested_plan_label}</Badge>
                      <Badge className={o.status === 'paid' ? 'bg-green-100 text-green-700' : o.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-slate-100 text-slate-500'}>
                        {o.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {o.amount ? `${(o.amount / 100).toLocaleString('cs-CZ')} ${o.currency}` : ''} | {o.provider} | {new Date(o.created_at).toLocaleDateString('cs-CZ')}
                    </div>
                  </div>
                  {o.status === 'pending' && (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => confirmOrder(o.id)} data-testid={`confirm-order-${o.id}`}>
                        <Check className="w-3 h-3 mr-1" /> Potvrdit
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => cancelOrder(o.id)}>
                        <X className="w-3 h-3 mr-1" /> Zrušit
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Platform usage analytics */}
        {view === 'analytics' && (
          <div className="space-y-4" data-testid="analytics-view">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <BarChart2 className="w-5 h-5" /> Platform Usage Analytics
            </h2>

            {!analytics ? (
              <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : (
              <>
                <Card className="p-4">
                  <h3 className="font-semibold text-slate-800 mb-3">Využití dle plánu</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {analytics.by_plan.map(p => (
                      <div key={p.plan} className="p-3 bg-slate-50 rounded">
                        <Badge className={PLAN_BADGE[p.plan] || ''}>{p.plan_label}</Badge>
                        <div className="mt-2 text-2xl font-bold">{p.total_usage.toLocaleString('cs-CZ')}</div>
                        <div className="text-xs text-slate-500">{p.active_institutions} aktivních institucí</div>
                      </div>
                    ))}
                    {analytics.by_plan.length === 0 && <p className="text-slate-500 col-span-4 text-center py-4">Zatím žádná data</p>}
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="font-semibold text-slate-800 mb-3">Využití dle funkce</h3>
                  <div className="space-y-1">
                    {analytics.by_feature.map(f => (
                      <div key={f.feature_key} className="grid grid-cols-12 gap-2 items-center text-sm py-1.5 border-b last:border-0" data-testid={`feature-row-${f.feature_key}`}>
                        <div className="col-span-5">
                          <div className="font-medium text-slate-800">{f.feature_label}</div>
                          <div className="text-xs text-slate-400">{f.feature_key}</div>
                        </div>
                        <div className="col-span-2">
                          {f.min_plan_label && <Badge className={PLAN_BADGE[f.min_plan] || ''}>{f.min_plan_label}</Badge>}
                        </div>
                        <div className="col-span-2 text-slate-600">{f.total_usage.toLocaleString('cs-CZ')}x</div>
                        <div className="col-span-3 flex items-center gap-2">
                          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${Math.min(100, f.adoption_rate)}%` }} />
                          </div>
                          <span className="text-xs text-slate-500 w-12 text-right">{f.adoption_rate}%</span>
                        </div>
                      </div>
                    ))}
                    {analytics.by_feature.length === 0 && <p className="text-slate-500 text-center py-4">Zatím žádné využití funkcí nebylo zaznamenáno</p>}
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="font-semibold text-slate-800 mb-3">Nejaktivnější instituce</h3>
                  <div className="space-y-1">
                    {analytics.top_institutions.map((inst, idx) => (
                      <div key={inst.institution_id} className="flex items-center justify-between py-1.5 border-b last:border-0 text-sm">
                        <div className="flex items-center gap-3">
                          <span className="text-slate-400 font-mono w-5 text-right">{idx + 1}.</span>
                          <span className="font-medium text-slate-800">{inst.institution_name}</span>
                          <Badge className={PLAN_BADGE[inst.plan] || ''}>{inst.plan_label}</Badge>
                        </div>
                        <span className="font-mono text-slate-600">{inst.total_usage.toLocaleString('cs-CZ')}x</span>
                      </div>
                    ))}
                    {analytics.top_institutions.length === 0 && <p className="text-slate-500 text-center py-4">Žádná data</p>}
                  </div>
                </Card>
              </>
            )}
          </div>
        )}

        {/* Platform-wide superadmin audit log */}
        {view === 'audit' && (
          <div className="space-y-4" data-testid="audit-view">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <History className="w-5 h-5" /> Historie změn superadmina
            </h2>
            <p className="text-xs text-slate-500">Všechny superadmin zásahy napříč platformou (změny plánů, mazání institucí, objednávky, expirace). Akce běžného admina ve vlastní instituci zde nejsou — ty jsou v Audit Logu dané instituce.</p>

            {!auditLog ? (
              <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : (
              <Card className="p-4">
                {auditLog.items.length === 0 ? (
                  <p className="text-slate-500 text-center py-6">Zatím žádné superadmin zásahy nebyly zaznamenány.</p>
                ) : (
                  <>
                    <div className="text-xs text-slate-500 mb-2">Celkem {auditLog.total} záznamů{auditLog.items.length < auditLog.total ? ` (zobrazeno ${auditLog.items.length})` : ''}</div>
                    <div className="grid grid-cols-12 gap-2 pb-2 text-[10px] uppercase tracking-wider text-slate-400 border-b">
                      <div className="col-span-3">Čas</div>
                      <div className="col-span-2">Akce</div>
                      <div className="col-span-3">Instituce</div>
                      <div className="col-span-4">Detaily</div>
                    </div>
                    {auditLog.items.map(e => <AuditEntryRow key={e.id} entry={e} />)}
                  </>
                )}
              </Card>
            )}
          </div>
        )}

        {/* Feature Flags (pilot modules) */}
        {view === 'features' && (
          <div className="space-y-4" data-testid="features-view">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Flag className="w-5 h-5" /> Feature flagy (pilotní moduly)
            </h2>
            <p className="text-xs text-slate-500">
              Pilotní funkce, které nejsou součástí cenových plánů. Pokud je flag <strong>globálně zapnutý</strong>,
              mají k němu přístup všechny instituce. Jinak rozhoduje whitelist níže.
            </p>

            {!featureFlags ? (
              <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : featureFlags.length === 0 ? (
              <Card className="p-6 text-center text-slate-500">Žádné pilot feature flagy zatím nejsou definovány.</Card>
            ) : (
              featureFlags.map(flag => (
                <FeatureFlagCard
                  key={flag.key}
                  flag={flag}
                  institutions={institutions}
                  onSave={(patch) => saveFeatureFlag(flag.key, patch)}
                />
              ))
            )}
          </div>
        )}



        {/* Plan change modal */}
        {showPlanModal && selectedInst && (
          <Dialog open onOpenChange={() => setShowPlanModal(false)}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Změnit plán: {selectedInst.name}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Plán</Label>
                  <Select value={planForm.plan} onValueChange={v => setPlanForm(p => ({ ...p, plan: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="free">Free</SelectItem>
                      <SelectItem value="start">Start</SelectItem>
                      <SelectItem value="pro">PRO</SelectItem>
                      <SelectItem value="pro_plus">PRO+</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Status</Label>
                  <Select value={planForm.plan_status} onValueChange={v => setPlanForm(p => ({ ...p, plan_status: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Aktivoval</Label>
                  <Select value={planForm.activated_by} onValueChange={v => setPlanForm(p => ({ ...p, activated_by: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin (manuální)</SelectItem>
                      <SelectItem value="payment">Platba</SelectItem>
                      <SelectItem value="migration">Migrace</SelectItem>
                      <SelectItem value="system">Systém</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Interní poznámka</Label>
                  <Textarea value={planForm.billing_note} onChange={e => setPlanForm(p => ({ ...p, billing_note: e.target.value }))} rows={2} placeholder="Poznámka pro interní účely..." />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowPlanModal(false)}>Zrušit</Button>
                <Button onClick={handlePlanChange} disabled={saving} data-testid="save-plan-change">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Check className="w-4 h-4 mr-1" />}
                  Uložit
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Delete institution modal */}
        {showDeleteModal && selectedInst && (
          <Dialog open onOpenChange={() => setShowDeleteModal(false)}>
            <DialogContent className="max-w-md" data-testid="delete-inst-modal">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" /> Smazat instituci
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  <p className="font-semibold mb-1">Nevratná operace</p>
                  <p>
                    Instituce <strong>{selectedInst.name}</strong> a všichni její uživatelé ({selectedInst.stats?.users || 0}) budou deaktivováni.
                    Data zůstanou v databázi pro audit, ale nebudou dostupná v aplikaci.
                  </p>
                </div>
                <div>
                  <Label>Pro potvrzení napište přesný název instituce:</Label>
                  <div className="mt-1 text-xs text-slate-500 font-mono select-all mb-1">{selectedInst.name}</div>
                  <Input
                    value={deleteForm.confirmation_name}
                    onChange={e => setDeleteForm(f => ({ ...f, confirmation_name: e.target.value }))}
                    placeholder="Zadejte název..."
                    data-testid="delete-confirm-name"
                    autoFocus
                  />
                </div>
                <div>
                  <Label>Důvod (nepovinné)</Label>
                  <Textarea
                    value={deleteForm.reason}
                    onChange={e => setDeleteForm(f => ({ ...f, reason: e.target.value }))}
                    rows={2}
                    placeholder="Např. duplikát, požadavek uživatele, ukončení smlouvy..."
                    data-testid="delete-reason"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDeleteModal(false)} data-testid="delete-cancel-btn">
                  Zrušit
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDeleteInstitution}
                  disabled={deleting || deleteForm.confirmation_name.trim() !== (selectedInst.name || '').trim()}
                  data-testid="delete-confirm-btn"
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Trash2 className="w-4 h-4 mr-1" />}
                  Trvale smazat
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </AdminLayout>
  );
};

/* ---- Institution detail component ---- */
const AUDIT_ACTION_LABEL = {
  plan_change: 'Změna plánu',
  institution_delete: 'Smazání instituce',
  billing_confirm: 'Potvrzení objednávky',
  billing_cancel: 'Zrušení objednávky',
  run_expiration_job: 'Spuštění expirační úlohy',
  impersonation_start: 'Zahájení impersonace',
  impersonation_end: 'Ukončení impersonace',
  setup_move_to_platform: 'Přesun superadmina do Platform instituce',
};

const AUDIT_ACTION_COLOR = {
  plan_change: 'bg-blue-100 text-blue-700',
  institution_delete: 'bg-red-100 text-red-700',
  billing_confirm: 'bg-emerald-100 text-emerald-700',
  billing_cancel: 'bg-amber-100 text-amber-700',
  run_expiration_job: 'bg-slate-100 text-slate-700',
  impersonation_start: 'bg-orange-100 text-orange-700',
  impersonation_end: 'bg-orange-50 text-orange-600',
  setup_move_to_platform: 'bg-purple-100 text-purple-700',
};

const FEATURE_FLAG_LABELS = {
  events_module: {
    label: 'Události & přihlášky',
    icon: Calendar,
    description: 'Správa jednorázových akcí a přihlášek s QR platbou.',
  },
  program_photos: {
    label: 'Fotografie programů',
    icon: ImageIcon,
    description: 'Umožňuje nahrát hlavní fotografii programu zobrazenou na veřejné rezervační stránce.',
  },
};

const FeatureFlagCard = ({ flag, institutions, onSave }) => {
  const meta = FEATURE_FLAG_LABELS[flag.key] || { label: flag.key, icon: Flag, description: flag.description };
  const Icon = meta.icon;

  const allowedSet = new Set(flag.allowed_institution_ids || []);
  const [pendingAllowed, setPendingAllowed] = useState(allowedSet);
  const [search, setSearch] = useState('');
  const [dirty, setDirty] = useState(false);

  React.useEffect(() => {
    setPendingAllowed(new Set(flag.allowed_institution_ids || []));
    setDirty(false);
  }, [flag]);

  const toggleInst = (id) => {
    const next = new Set(pendingAllowed);
    if (next.has(id)) next.delete(id); else next.add(id);
    setPendingAllowed(next);
    setDirty(true);
  };

  const toggleGlobal = () => {
    onSave({ enabled: !flag.enabled });
  };

  const saveWhitelist = () => {
    const before = allowedSet;
    const after = pendingAllowed;
    const toAdd = [...after].filter(id => !before.has(id));
    const toRemove = [...before].filter(id => !after.has(id));
    onSave({ add_institution_ids: toAdd, remove_institution_ids: toRemove });
  };

  const filtered = (institutions || []).filter(i => {
    if (!search) return true;
    return (i.name || '').toLowerCase().includes(search.toLowerCase()) ||
           (i.email || '').toLowerCase().includes(search.toLowerCase());
  });

  return (
    <Card className="p-5" data-testid={`feature-card-${flag.key}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${flag.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-900">{meta.label}</h3>
            <p className="text-xs font-mono text-slate-400">{flag.key}</p>
            {meta.description && <p className="text-sm text-slate-600 mt-1">{meta.description}</p>}
          </div>
        </div>
        <button
          type="button"
          onClick={toggleGlobal}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors shrink-0 ${
            flag.enabled
              ? 'bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700'
              : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
          }`}
          data-testid={`feature-global-toggle-${flag.key}`}
          title={flag.enabled
            ? 'Globálně zapnuto — mají všichni. Klikněte pro vypnutí (přepnutí na whitelist)'
            : 'Vypnuto — používá whitelist. Klikněte pro globální zapnutí'}
        >
          {flag.enabled ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
          {flag.enabled ? 'Globálně ZAPNUTO' : 'Whitelist režim'}
        </button>
      </div>

      <div className={`mt-4 p-3 rounded-md border ${flag.enabled ? 'bg-slate-50 border-slate-200 opacity-70' : 'bg-white border-slate-300'}`}>
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-semibold text-slate-700">
            Whitelist institucí ({pendingAllowed.size} / {institutions?.length || 0})
          </p>
          {dirty && (
            <Button
              size="sm"
              onClick={saveWhitelist}
              className="h-7 text-xs"
              data-testid={`feature-save-${flag.key}`}
            >
              <Check className="w-3 h-3 mr-1" /> Uložit změny
            </Button>
          )}
        </div>
        {flag.enabled && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mb-2">
            Flag je globálně zapnutý — whitelist se nyní nepoužívá, ale změny zde se uloží a aktivují po vypnutí globálu.
          </p>
        )}
        <Input
          placeholder="Hledat instituci..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="mb-2 h-8 text-sm"
          data-testid={`feature-search-${flag.key}`}
        />
        <div className="max-h-64 overflow-y-auto divide-y divide-slate-100 border rounded">
          {filtered.length === 0 ? (
            <p className="text-xs text-slate-400 p-3 text-center">Žádné výsledky</p>
          ) : filtered.map(inst => {
            const on = pendingAllowed.has(inst.id);
            return (
              <label
                key={inst.id}
                className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 cursor-pointer"
                data-testid={`feature-inst-${flag.key}-${inst.id}`}
              >
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => toggleInst(inst.id)}
                  className="w-4 h-4 accent-emerald-600"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800 truncate">{inst.name}</div>
                  <div className="text-xs text-slate-400 truncate">{inst.email}</div>
                </div>
                {inst.plan_label && <Badge className={PLAN_BADGE[inst.plan] || ''}>{inst.plan_label}</Badge>}
              </label>
            );
          })}
        </div>
      </div>
    </Card>
  );
};

const AuditEntryRow = ({ entry, showInstitution = true }) => {
  const label = AUDIT_ACTION_LABEL[entry.action] || entry.action;
  const color = AUDIT_ACTION_COLOR[entry.action] || 'bg-slate-100 text-slate-700';
  const d = entry.details || {};
  return (
    <div className="grid grid-cols-12 gap-2 items-start py-2 border-b last:border-0 text-sm" data-testid={`audit-row-${entry.id}`}>
      <div className="col-span-3 text-xs text-slate-500 font-mono">
        {entry.created_at ? new Date(entry.created_at).toLocaleString('cs-CZ') : '—'}
      </div>
      <div className="col-span-2">
        <Badge className={color}>{label}</Badge>
      </div>
      {showInstitution && (
        <div className="col-span-3 text-slate-700 truncate" title={entry.institution_name || ''}>
          {entry.institution_name || entry.institution_id?.slice(0, 8)}
        </div>
      )}
      <div className={showInstitution ? "col-span-4 text-xs text-slate-600" : "col-span-7 text-xs text-slate-600"}>
        <div className="truncate" title={entry.user_email}>
          <AtSign className="w-3 h-3 inline -mt-0.5 text-slate-400" /> {entry.user_email}
        </div>
        {entry.action === 'plan_change' && (
          <div className="text-slate-500">
            {d.from_plan}/{d.from_status} → <span className="font-medium">{d.to_plan}/{d.to_status}</span>
            {d.activated_by && <> · aktivoval: <span className="font-mono">{d.activated_by}</span></>}
          </div>
        )}
        {entry.action === 'institution_delete' && (
          <div className="text-slate-500">
            {d.institution_name}{d.reason && ` · důvod: ${d.reason}`}
          </div>
        )}
        {(entry.action === 'billing_confirm' || entry.action === 'billing_cancel') && d.requested_plan && (
          <div className="text-slate-500">Plán: <span className="font-mono">{d.requested_plan}</span></div>
        )}
        {entry.action === 'impersonation_start' && (
          <div className="text-slate-500">
            Cíl: <span className="font-mono">{d.target_email}</span> ({d.target_role})
            {d.reason && <> · důvod: <span className="italic">{d.reason}</span></>}
          </div>
        )}
        {entry.action === 'impersonation_end' && d.impersonated_email && (
          <div className="text-slate-500">
            Ukončeno pro: <span className="font-mono">{d.impersonated_email}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const ROLE_LABELS = {
  admin: 'Admin',
  spravce: 'Správce',
  edukator: 'Edukátor',
  lektor: 'Lektor',
  pokladni: 'Pokladní',
  viewer: 'Pozorovatel',
};

const ROLE_BADGE = {
  admin: 'bg-red-100 text-red-700',
  spravce: 'bg-purple-100 text-purple-700',
  edukator: 'bg-blue-100 text-blue-700',
  lektor: 'bg-emerald-100 text-emerald-700',
  pokladni: 'bg-amber-100 text-amber-700',
  viewer: 'bg-slate-100 text-slate-600',
};

const InstitutionDetail = ({ inst, onPlanChange, onDelete, canDelete }) => {
  const [usersOpen, setUsersOpen] = React.useState(false);
  const { startImpersonation, user: me } = useContext(AuthContext);
  const [impBusyId, setImpBusyId] = useState(null);
  const owner = inst.owner;
  const users = inst.users || [];

  const doImpersonate = async (u) => {
    const reason = window.prompt(
      `Zahájit impersonaci uživatele ${u.email}?\n\nBudete na 30 minut vystupovat jako tento uživatel.\nAkce je zaznamenána v audit logu.\n\nDůvod (nepovinné):`,
      ''
    );
    if (reason === null) return; // cancelled
    setImpBusyId(u.id);
    try {
      await startImpersonation(u.id, reason || '');
      toast.success(`Impersonace aktivní jako ${u.email}`);
      // Navigate to the institution dashboard so the session-inheritance takes effect
      setTimeout(() => window.location.assign('/admin'), 500);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Impersonaci se nepodařilo zahájit');
    } finally {
      setImpBusyId(null);
    }
  };

  return (
  <div className="space-y-4">
    {/* Header */}
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-bold text-slate-900">{inst.name}</h2>
        <p className="text-sm text-slate-500">{inst.email} {inst.website && `| ${inst.website}`}</p>
      </div>
      <div className="flex gap-2">
        <Button onClick={onPlanChange} data-testid="change-plan-btn">
          <Settings2 className="w-4 h-4 mr-1" /> Změnit plán
        </Button>
        {canDelete && (
          <Button variant="destructive" onClick={onDelete} data-testid="delete-inst-btn">
            <Trash2 className="w-4 h-4 mr-1" /> Smazat
          </Button>
        )}
      </div>
    </div>

    {/* Owner / zřizovatel */}
    <Card className="p-4" data-testid="owner-card">
      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <UserCog className="w-4 h-4" /> Zřizovatel / administrátor účtu
      </h3>
      {owner ? (
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-700 flex items-center justify-center font-semibold text-lg shrink-0">
            {(owner.first_name || owner.email || '?').charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
            <div>
              <div className="text-xs text-slate-500">Jméno a příjmení</div>
              <div className="font-medium text-slate-900" data-testid="owner-name">
                {owner.name || <span className="italic text-slate-400">(neuvedeno)</span>}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Registrační e-mail</div>
              <div className="font-medium text-slate-900 flex items-center gap-1" data-testid="owner-email">
                <AtSign className="w-3 h-3 text-slate-400" /> {owner.email}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Role</div>
              <Badge className={ROLE_BADGE[owner.role] || 'bg-slate-100'}>
                {ROLE_LABELS[owner.role] || owner.role}
              </Badge>
            </div>
            <div>
              <div className="text-xs text-slate-500">Registrace</div>
              <div className="text-slate-700">{owner.created_at ? new Date(owner.created_at).toLocaleDateString('cs-CZ') : '—'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Poslední přihlášení</div>
              <div className="text-slate-700">{owner.last_login_at ? new Date(owner.last_login_at).toLocaleString('cs-CZ') : '—'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Status</div>
              <Badge className={owner.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}>
                {owner.status}
              </Badge>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">Nenalezen žádný admin uživatel pro tuto instituci.</p>
      )}
    </Card>

    {/* Plan info */}
    <Card className="p-4">
      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <Crown className="w-4 h-4" /> Plán
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div><span className="text-slate-500">Plán:</span> <Badge className={PLAN_BADGE[inst.plan]}>{inst.plan_label}</Badge></div>
        <div><span className="text-slate-500">Status:</span> <Badge className={STATUS_BADGE[inst.plan_status]}>{inst.plan_status}</Badge></div>
        <div><span className="text-slate-500">Aktivoval:</span> {inst.plan_activated_by || '—'}</div>
        <div><span className="text-slate-500">Aktivováno:</span> {inst.plan_activated_at ? new Date(inst.plan_activated_at).toLocaleDateString('cs-CZ') : '—'}</div>
        {inst.plan_expires_at && <div><span className="text-slate-500">Vyprší:</span> {new Date(inst.plan_expires_at).toLocaleDateString('cs-CZ')}</div>}
        {inst.billing_note && <div className="col-span-2"><span className="text-slate-500">Poznámka:</span> {inst.billing_note}</div>}
      </div>
    </Card>

    {/* Stats */}
    <Card className="p-4">
      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <BarChart3 className="w-4 h-4" /> Statistiky
      </h3>
      <div className="grid grid-cols-3 md:grid-cols-7 gap-3">
        {Object.entries({
          Programy: inst.stats.programs,
          Rezervace: inst.stats.reservations,
          Uživatelé: inst.stats.users,
          Události: inst.stats.events,
          Přihlášky: inst.stats.applications,
          Mailingy: inst.stats.mailings,
          Waitlist: inst.stats.waitlist_entries,
        }).map(([label, val]) => (
          <div key={label} className="text-center p-2 bg-slate-50 rounded">
            <div className="text-xl font-bold text-slate-900">{val}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>
    </Card>

    {/* Users list (read-only sub-panel) */}
    <Card className="p-4" data-testid="users-card">
      <button
        type="button"
        onClick={() => setUsersOpen(o => !o)}
        className="w-full flex items-center justify-between hover:opacity-80"
        data-testid="toggle-users-panel"
      >
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <Users className="w-4 h-4" /> Uživatelé instituce
          <span className="text-xs font-normal text-slate-500 ml-1">({users.length})</span>
          <span className="text-[10px] font-mono uppercase text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded ml-2">pouze čtení</span>
        </h3>
        <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${usersOpen ? 'rotate-90' : ''}`} />
      </button>

      {usersOpen && (
        <div className="mt-4 overflow-x-auto">
          {users.length === 0 ? (
            <p className="text-sm text-slate-500 py-2">Žádní uživatelé.</p>
          ) : (
            <table className="w-full text-sm" data-testid="users-table">
              <thead>
                <tr className="text-left border-b text-xs uppercase text-slate-500">
                  <th className="py-2 pr-3">Jméno</th>
                  <th className="py-2 pr-3">E-mail</th>
                  <th className="py-2 pr-3">Role</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Registrace</th>
                  <th className="py-2 pr-3">Poslední přihlášení</th>
                  <th className="py-2 text-right">Akce</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const isSelf = me?.id === u.id;
                  const isAnotherSuperadmin = ['demo@budezivo.cz', 'admin@budezivo.cz'].includes(u.email);
                  const cantImpersonate = isSelf || isAnotherSuperadmin || u.status !== 'active';
                  return (
                  <tr key={u.id} className="border-b last:border-0 hover:bg-slate-50" data-testid={`user-row-${u.id}`}>
                    <td className="py-2 pr-3">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center text-xs font-semibold">
                          {(u.first_name || u.email || '?').charAt(0).toUpperCase()}
                        </div>
                        <span className="text-slate-800">{u.name || <span className="italic text-slate-400">—</span>}</span>
                      </div>
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs text-slate-700">{u.email}</td>
                    <td className="py-2 pr-3">
                      <Badge className={ROLE_BADGE[u.role] || 'bg-slate-100'}>
                        {ROLE_LABELS[u.role] || u.role}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3">
                      <Badge className={u.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}>
                        {u.status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-xs text-slate-500">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString('cs-CZ') : '—'}
                    </td>
                    <td className="py-2 pr-3 text-xs text-slate-500">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleString('cs-CZ') : '—'}
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => doImpersonate(u)}
                        disabled={cantImpersonate || impBusyId === u.id}
                        title={
                          isSelf ? 'Nelze impersonovat sám sebe' :
                          isAnotherSuperadmin ? 'Nelze impersonovat jiného superadmina' :
                          u.status !== 'active' ? 'Uživatel není aktivní' :
                          'Zahájit impersonaci (30 min)'
                        }
                        className="h-7 text-xs"
                        data-testid={`impersonate-btn-${u.id}`}
                      >
                        {impBusyId === u.id
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : <UserCog className="w-3 h-3 mr-1" />}
                        Impersonovat
                      </Button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Card>

    {/* Usage metrics */}
    {inst.usage_metrics?.length > 0 && (
      <Card className="p-4">
        <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <Eye className="w-4 h-4" /> Feature usage
        </h3>
        <div className="space-y-1">
          {inst.usage_metrics.map(m => (
            <div key={m.feature_key} className="flex items-center justify-between py-1 border-b last:border-0 text-sm">
              <span className="text-slate-700">{m.feature_key}</span>
              <div className="flex items-center gap-3 text-slate-500 text-xs">
                <span>{m.usage_count}x</span>
                {m.last_used_at && <span>Naposledy: {new Date(m.last_used_at).toLocaleDateString('cs-CZ')}</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    )}

    {/* Superadmin audit log for this institution */}
    {inst.audit_log?.length > 0 && (
      <Card className="p-4" data-testid="institution-audit-card">
        <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <History className="w-4 h-4" /> Historie zásahů superadmina
          <span className="text-xs font-normal text-slate-500 ml-1">({inst.audit_log.length})</span>
        </h3>
        <div className="grid grid-cols-12 gap-2 pb-2 text-[10px] uppercase tracking-wider text-slate-400 border-b">
          <div className="col-span-3">Čas</div>
          <div className="col-span-2">Akce</div>
          <div className="col-span-7">Detaily</div>
        </div>
        {inst.audit_log.map(e => <AuditEntryRow key={e.id} entry={e} showInstitution={false} />)}
      </Card>
    )}

    {/* Billing orders */}
    {inst.billing_orders?.length > 0 && (
      <Card className="p-4">
        <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4" /> Objednávky
        </h3>
        <div className="space-y-1">
          {inst.billing_orders.map(o => (
            <div key={o.id} className="flex items-center justify-between py-1.5 border-b last:border-0 text-sm">
              <div className="flex items-center gap-2">
                <Badge className={PLAN_BADGE[o.requested_plan] || ''}>{o.requested_plan}</Badge>
                <Badge className={o.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-800'}>{o.status}</Badge>
              </div>
              <span className="text-xs text-slate-500">{new Date(o.created_at).toLocaleDateString('cs-CZ')}</span>
            </div>
          ))}
        </div>
      </Card>
    )}
  </div>
  );
};

export default SuperadminPage;
