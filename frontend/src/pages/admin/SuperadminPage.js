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
  FileText, Clock, ArrowLeft, Eye, Settings2
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
  const [selectedInst, setSelectedInst] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState('all');

  // Plan change modal
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planForm, setPlanForm] = useState({ plan: 'free', plan_status: 'active', activated_by: 'admin', billing_note: '' });
  const [saving, setSaving] = useState(false);

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
            onPlanChange={() => {
              setPlanForm({ plan: selectedInst.plan, plan_status: selectedInst.plan_status, activated_by: 'admin', billing_note: selectedInst.billing_note || '' });
              setShowPlanModal(true);
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
      </div>
    </AdminLayout>
  );
};

/* ---- Institution detail component ---- */
const InstitutionDetail = ({ inst, onPlanChange }) => (
  <div className="space-y-4">
    {/* Header */}
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-bold text-slate-900">{inst.name}</h2>
        <p className="text-sm text-slate-500">{inst.email} {inst.website && `| ${inst.website}`}</p>
      </div>
      <Button onClick={onPlanChange} data-testid="change-plan-btn">
        <Settings2 className="w-4 h-4 mr-1" /> Změnit plán
      </Button>
    </div>

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

export default SuperadminPage;
