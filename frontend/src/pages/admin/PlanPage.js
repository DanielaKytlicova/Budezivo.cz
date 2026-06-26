import React, { useState, useEffect, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { AuthContext } from '../../context/AuthContext';
import { Check, Crown, Lock, ArrowRight, ArrowUp, ArrowDown, Loader2, AlertTriangle, Info, Mail, X, Minus } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';

const PLAN_STYLE = {
  free:     { accent: '#64748B', bg: 'bg-slate-50',  border: 'border-slate-200', badge: 'bg-slate-100 text-slate-700' },
  start:    { accent: '#3B82F6', bg: 'bg-blue-50',   border: 'border-blue-300',  badge: 'bg-blue-100 text-blue-700' },
  pro:      { accent: '#F59E0B', bg: 'bg-amber-50',  border: 'border-amber-300', badge: 'bg-amber-100 text-amber-800' },
  pro_plus: { accent: '#8B5CF6', bg: 'bg-purple-50', border: 'border-purple-300',badge: 'bg-purple-100 text-purple-800' },
};

const PLAN_PRICES = {
  free: { monthly: 0, yearly: 0 },
  start: { monthly: 490, yearly: 4900 },
  pro: { monthly: 990, yearly: 9900 },
  pro_plus: { monthly: 1990, yearly: 19900 },
};

export const PlanPage = () => {
  const { user } = useContext(AuthContext);
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState('monthly');

  // Switch modal
  const [switchTarget, setSwitchTarget] = useState(null);
  const [diff, setDiff] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [statusRes, plansRes] = await Promise.all([
          axios.get(`${API}/plan/status`, { withCredentials: true }),
          axios.get(`${API}/plan/plans`, { withCredentials: true }),
        ]);
        setCurrentPlan(statusRes.data);
        setPlans(plansRes.data.plans || []);
      } catch { toast.error('Nepodařilo se načíst plány'); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const openSwitchModal = async (targetKey) => {
    if (!currentPlan) return;
    if (targetKey === currentPlan.plan && currentPlan.plan_status === 'active') return;

    setSwitchTarget(targetKey);
    setDiffLoading(true);
    try {
      const res = await axios.get(`${API}/plan/diff?from_plan=${currentPlan.plan}&to_plan=${targetKey}`, { withCredentials: true });
      setDiff(res.data);
    } catch { setDiff(null); }
    finally { setDiffLoading(false); }
  };

  const handleConfirmSwitch = async () => {
    if (!switchTarget) return;
    setRequesting(true);
    try {
      if (switchTarget === 'free') {
        // Downgrade to free is immediate and free of charge (no invoice).
        const res = await axios.put(`${API}/plan/downgrade`, {}, { withCredentials: true });
        toast.success(res.data.message || 'Plán změněn na Free');
      } else {
        const res = await axios.post(`${API}/plan/request`, { target_plan: switchTarget }, { withCredentials: true });
        toast.success(res.data.message);
      }
      setSwitchTarget(null);
      setDiff(null);
      const statusRes = await axios.get(`${API}/plan/status`, { withCredentials: true });
      setCurrentPlan(statusRes.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba'); }
    finally { setRequesting(false); }
  };

  if (loading) return <AdminLayout><div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div></AdminLayout>;

  const isActive = (k) => currentPlan?.plan === k && currentPlan?.plan_status === 'active';
  const isPending = (k) => currentPlan?.plan === k && currentPlan?.plan_status === 'pending';
  const targetPlanData = plans.find(p => p.key === switchTarget);

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900" data-testid="plan-page-title">Plány a fakturace</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-slate-500">Aktuální plán:</span>
            <Badge className={PLAN_STYLE[currentPlan?.plan]?.badge || ''}>{currentPlan?.plan_label}</Badge>
            {currentPlan?.plan_status === 'pending' && <Badge className="bg-yellow-100 text-yellow-800">Čeká na platbu</Badge>}
            {currentPlan?.plan_status === 'active' && currentPlan?.plan !== 'free' && <Badge className="bg-green-100 text-green-700">Aktivní</Badge>}
          </div>
        </div>

        {/* Pending notice */}
        {currentPlan?.plan_status === 'pending' && (
          <Card className="p-4 bg-yellow-50 border-yellow-300">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-yellow-800">Čeká na potvrzení platby</p>
                <p className="text-sm text-yellow-700 mt-1">Plán {currentPlan?.plan_label} bude aktivován po uhrazení faktury.</p>
                <Button size="sm" variant="outline" className="mt-2 border-yellow-400 text-yellow-800" onClick={() => window.open('mailto:info@budezivo.cz?subject=Aktivace plánu ' + currentPlan?.plan_label)}>
                  <Mail className="w-4 h-4 mr-1" /> Kontaktovat nás
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Billing toggle */}
        <div className="flex justify-center">
          <div className="inline-flex rounded-lg border p-1 bg-slate-100">
            <button className={`px-6 py-2 rounded-md text-sm font-medium transition ${billingCycle === 'monthly' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
              onClick={() => setBillingCycle('monthly')} data-testid="plan-billing-monthly">Měsíčně</button>
            <button className={`px-6 py-2 rounded-md text-sm font-medium transition ${billingCycle === 'yearly' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
              onClick={() => setBillingCycle('yearly')} data-testid="plan-billing-yearly">Ročně <span className="ml-1 text-xs text-green-600">-17%</span></button>
          </div>
        </div>

        {/* Plan cards — hierarchical, no duplication */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map(p => {
            const style = PLAN_STYLE[p.key] || PLAN_STYLE.start;
            const prices = PLAN_PRICES[p.key] || { monthly: 0, yearly: 0 };
            const price = billingCycle === 'monthly' ? prices.monthly : prices.yearly;
            const active = isActive(p.key);
            const pending = isPending(p.key);
            const isRecommended = p.key === 'pro';

            return (
              <Card key={p.key} className={`p-5 relative ${style.border} border-2 ${active ? 'ring-2 ring-offset-2 ring-green-400' : ''}`} data-testid={`plan-card-${p.key}`}>
                {isRecommended && !active && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2"><Badge className="bg-amber-400 text-slate-900 font-semibold">Doporučeno</Badge></div>
                )}
                {active && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2"><Badge className="bg-green-500 text-white font-semibold">Aktivní</Badge></div>
                )}

                <h3 className="text-xl font-bold text-slate-900">{p.label}</h3>
                <div className="mt-2 mb-3">
                  <span className="text-3xl font-bold text-slate-900">{price.toLocaleString('cs-CZ')}</span>
                  <span className="text-slate-500 ml-1 text-sm">{billingCycle === 'monthly' ? 'Kč/měs.' : 'Kč/rok'}</span>
                </div>

                {/* Limits */}
                <div className="text-xs text-slate-500 mb-3 space-y-0.5">
                  <div>Programů: <strong>{p.limits.programs_limit === -1 ? 'Neomezeně' : p.limits.programs_limit}</strong></div>
                  <div>Rezervací/měs.: <strong>{p.limits.bookings_monthly_limit === -1 ? 'Neomezeně' : p.limits.bookings_monthly_limit}</strong></div>
                </div>

                {/* Hierarchical features — delta only */}
                {p.inherits_from_label && (
                  <p className="text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wide">Vše z {p.inherits_from_label} +</p>
                )}
                <ul className="space-y-1 mb-4">
                  {p.own_features.map(f => (
                    <li key={f.key} className="flex items-start gap-1.5 text-sm">
                      <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: style.accent }} />
                      <span>{f.label}</span>
                    </li>
                  ))}
                  {p.key === 'free' && p.own_features.length === 0 && (
                    <>
                      <li className="flex items-start gap-1.5 text-sm">
                        <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: style.accent }} />
                        <span>Základní rezervační systém</span>
                      </li>
                      <li className="flex items-start gap-1.5 text-sm">
                        <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: style.accent }} />
                        <span>Správa programů (do limitu)</span>
                      </li>
                      <li className="flex items-start gap-1.5 text-sm">
                        <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: style.accent }} />
                        <span>Kalendář dostupnosti</span>
                      </li>
                      <li className="text-xs text-slate-400 pt-1">Ideální pro vyzkoušení zdarma, bez závazku.</li>
                    </>
                  )}
                </ul>

                {/* Action */}
                {active ? (
                  <Button variant="outline" className="w-full border-green-300 text-green-700" disabled><Check className="w-4 h-4 mr-1" /> Aktivní</Button>
                ) : pending ? (
                  <Button variant="outline" className="w-full border-yellow-300 text-yellow-700" disabled><Loader2 className="w-4 h-4 mr-1 animate-spin" /> Čeká na platbu</Button>
                ) : (
                  <Button className="w-full text-white" style={{ backgroundColor: style.accent }} onClick={() => openSwitchModal(p.key)} data-testid={`select-plan-${p.key}`}>
                    {p.key === 'free'
                      ? <><ArrowDown className="w-4 h-4 mr-1" /> Přejít na Free</>
                      : <><Crown className="w-4 h-4 mr-1" /> Vybrat plán</>}
                  </Button>
                )}
              </Card>
            );
          })}
        </div>

        {/* Info */}
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-start gap-2 text-sm text-blue-800">
            <Info className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">Jak funguje aktivace?</p>
              <p className="mt-1">Po výběru plánu vám zašleme fakturu. Po uhrazení bude plán aktivován do 24 hodin. Pro okamžitou aktivaci kontaktujte <strong>info@budezivo.cz</strong>.</p>
            </div>
          </div>
        </Card>

        {/* ===== Switch modal (delta view) ===== */}
        {switchTarget && (
          <Dialog open onOpenChange={() => { setSwitchTarget(null); setDiff(null); }}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>
                  {diff?.is_upgrade ? 'Upgrade' : 'Změna'} na {targetPlanData?.label}
                </DialogTitle>
              </DialogHeader>

              {diffLoading ? (
                <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin" /></div>
              ) : diff ? (
                <div className="space-y-4 py-2">
                  {/* Price */}
                  <div className="bg-slate-50 rounded-lg p-3 text-sm flex justify-between">
                    <span>Cena:</span>
                    <strong>{(PLAN_PRICES[switchTarget]?.[billingCycle] || 0).toLocaleString('cs-CZ')} Kč / {billingCycle === 'monthly' ? 'měsíc' : 'rok'}</strong>
                  </div>

                  {/* Gained */}
                  {diff.gained.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-green-700 mb-1.5 flex items-center gap-1">
                        <ArrowUp className="w-4 h-4" /> Získáte navíc:
                      </p>
                      <ul className="space-y-1">
                        {diff.gained.map(f => (
                          <li key={f.key} className="flex items-center gap-2 text-sm text-green-800 bg-green-50 rounded px-2 py-1">
                            <Check className="w-4 h-4 text-green-500 shrink-0" /> {f.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Lost */}
                  {diff.lost.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-red-700 mb-1.5 flex items-center gap-1">
                        <ArrowDown className="w-4 h-4" /> Přijdete o:
                      </p>
                      <ul className="space-y-1">
                        {diff.lost.map(f => (
                          <li key={f.key} className="flex items-center gap-2 text-sm text-red-800 bg-red-50 rounded px-2 py-1">
                            <Minus className="w-4 h-4 text-red-400 shrink-0" /> {f.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Payment / downgrade note */}
                  {switchTarget === 'free' ? (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-700">
                      <Info className="w-4 h-4 inline mr-1 text-slate-500" />
                      Přechod na Free je okamžitý a zdarma. O placené funkce výše přijdete ihned po potvrzení.
                    </div>
                  ) : (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                      <AlertTriangle className="w-4 h-4 inline mr-1" />
                      Po potvrzení vám bude zaslána faktura. Plán bude aktivován po přijetí platby.
                    </div>
                  )}
                </div>
              ) : null}

              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => { setSwitchTarget(null); setDiff(null); }}>Zrušit</Button>
                <Button onClick={handleConfirmSwitch} disabled={requesting || diffLoading} data-testid="confirm-plan-request-btn">
                  {requesting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <ArrowRight className="w-4 h-4 mr-1" />}
                  {switchTarget === 'free' ? 'Potvrdit přechod' : 'Objednat'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </AdminLayout>
  );
};

export default PlanPage;
