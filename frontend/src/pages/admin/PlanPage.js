import React, { useState, useEffect, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { AuthContext } from '../../context/AuthContext';
import { Check, Crown, Lock, ArrowRight, Loader2, AlertTriangle, Info, Mail } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';

const PLAN_COLORS = {
  free: { bg: 'bg-slate-50', border: 'border-slate-200', badge: 'bg-slate-100 text-slate-700', accent: '#64748B' },
  start: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-blue-100 text-blue-700', accent: '#3B82F6' },
  pro: { bg: 'bg-amber-50', border: 'border-amber-300', badge: 'bg-amber-100 text-amber-800', accent: '#F59E0B' },
  pro_plus: { bg: 'bg-purple-50', border: 'border-purple-300', badge: 'bg-purple-100 text-purple-800', accent: '#8B5CF6' },
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
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
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

  const handleSelectPlan = (planKey) => {
    if (planKey === 'free') return;
    if (planKey === currentPlan?.plan && currentPlan?.plan_status === 'active') return;
    setSelectedPlan(planKey);
    setShowRequestModal(true);
  };

  const handleRequestPlan = async () => {
    if (!selectedPlan) return;
    setRequesting(true);
    try {
      const res = await axios.post(`${API}/plan/request`, { target_plan: selectedPlan }, { withCredentials: true });
      toast.success(res.data.message);
      setShowRequestModal(false);
      // Refresh status
      const statusRes = await axios.get(`${API}/plan/status`, { withCredentials: true });
      setCurrentPlan(statusRes.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při odesílání žádosti'); }
    finally { setRequesting(false); }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      </AdminLayout>
    );
  }

  const isPlanActive = (planKey) => currentPlan?.plan === planKey && currentPlan?.plan_status === 'active';
  const isPlanPending = (planKey) => currentPlan?.plan === planKey && currentPlan?.plan_status === 'pending';
  const isCurrentOrLower = (planKey) => {
    const order = ['free', 'start', 'pro', 'pro_plus'];
    return order.indexOf(planKey) <= order.indexOf(currentPlan?.plan || 'free');
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900" data-testid="plan-page-title">Plány a fakturace</h1>
          <p className="text-slate-500 mt-1">
            Aktuální plán: <strong>{currentPlan?.plan_label || 'Free'}</strong>
            {currentPlan?.plan_status === 'pending' && (
              <Badge className="ml-2 bg-yellow-100 text-yellow-800">Čeká na platbu</Badge>
            )}
            {currentPlan?.plan_status === 'active' && currentPlan?.plan !== 'free' && (
              <Badge className="ml-2 bg-green-100 text-green-700">Aktivní</Badge>
            )}
          </p>
        </div>

        {/* Pending payment notice */}
        {currentPlan?.plan_status === 'pending' && (
          <Card className="p-4 bg-yellow-50 border-yellow-300">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-yellow-800">Čeká na potvrzení platby</h3>
                <p className="text-sm text-yellow-700 mt-1">
                  Váš plán {currentPlan?.plan_label} čeká na potvrzení platby. 
                  Uhraďte prosím fakturu nebo kontaktujte tým Budeživo pro aktivaci.
                </p>
                <div className="flex gap-2 mt-3">
                  <Button size="sm" variant="outline" className="border-yellow-400 text-yellow-800 hover:bg-yellow-100" onClick={() => window.open('mailto:info@budezivo.cz?subject=Aktivace plánu ' + currentPlan?.plan_label)}>
                    <Mail className="w-4 h-4 mr-1" /> Kontaktovat nás
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Billing toggle */}
        <div className="flex justify-center">
          <div className="inline-flex rounded-lg border p-1 bg-slate-100">
            <button className={`px-6 py-2 rounded-md text-sm font-medium transition ${billingCycle === 'monthly' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
              onClick={() => setBillingCycle('monthly')} data-testid="plan-billing-monthly">
              Měsíčně
            </button>
            <button className={`px-6 py-2 rounded-md text-sm font-medium transition ${billingCycle === 'yearly' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
              onClick={() => setBillingCycle('yearly')} data-testid="plan-billing-yearly">
              Ročně <span className="ml-1 text-xs text-green-600">-17%</span>
            </button>
          </div>
        </div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map(p => {
            const colors = PLAN_COLORS[p.key] || PLAN_COLORS.free;
            const prices = PLAN_PRICES[p.key] || { monthly: 0, yearly: 0 };
            const price = billingCycle === 'monthly' ? prices.monthly : prices.yearly;
            const isActive = isPlanActive(p.key);
            const isPending = isPlanPending(p.key);
            const isRecommended = p.key === 'pro';

            return (
              <Card key={p.key} className={`p-5 relative ${colors.border} border-2 ${isActive ? 'ring-2 ring-offset-2 ring-green-400' : ''} ${isRecommended && !isActive ? 'shadow-lg' : ''}`} data-testid={`plan-card-${p.key}`}>
                {isRecommended && !isActive && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-amber-400 text-slate-900 font-semibold">Doporučeno</Badge>
                  </div>
                )}
                {isActive && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-green-500 text-white font-semibold">Aktivní</Badge>
                  </div>
                )}

                <div className="mb-4">
                  <h3 className="text-xl font-bold text-slate-900">{p.label}</h3>
                  <div className="mt-2">
                    {price === 0 ? (
                      <span className="text-3xl font-bold text-slate-900">Zdarma</span>
                    ) : (
                      <>
                        <span className="text-3xl font-bold text-slate-900">{price.toLocaleString('cs-CZ')}</span>
                        <span className="text-slate-500 ml-1">{billingCycle === 'monthly' ? 'Kč/měs.' : 'Kč/rok'}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Limits */}
                <div className="text-sm text-slate-600 mb-3 space-y-1">
                  <div>Programů: <strong>{p.limits.programs_limit === -1 ? 'Neomezeně' : p.limits.programs_limit}</strong></div>
                  <div>Rezervací/měs.: <strong>{p.limits.bookings_monthly_limit === -1 ? 'Neomezeně' : p.limits.bookings_monthly_limit}</strong></div>
                </div>

                {/* Features */}
                <ul className="space-y-1.5 mb-4">
                  {p.features.slice(0, 6).map(f => (
                    <li key={f.key} className="flex items-start gap-1.5 text-sm">
                      <Check className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                      <span>{f.label}</span>
                    </li>
                  ))}
                  {p.features.length > 6 && (
                    <li className="text-xs text-slate-500 ml-5">+ {p.features.length - 6} dalších</li>
                  )}
                  {p.features.length === 0 && (
                    <li className="text-sm text-slate-500">Základní funkce</li>
                  )}
                </ul>

                {/* Action button */}
                {p.key === 'free' ? (
                  <Button variant="outline" className="w-full" disabled>
                    {isActive ? 'Aktuální plán' : 'Základní'}
                  </Button>
                ) : isActive ? (
                  <Button variant="outline" className="w-full border-green-300 text-green-700" disabled>
                    <Check className="w-4 h-4 mr-1" /> Aktivní
                  </Button>
                ) : isPending ? (
                  <Button variant="outline" className="w-full border-yellow-300 text-yellow-700" disabled>
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" /> Čeká na platbu
                  </Button>
                ) : (
                  <Button className="w-full" style={{ backgroundColor: colors.accent }}
                    onClick={() => handleSelectPlan(p.key)} data-testid={`select-plan-${p.key}`}>
                    <Crown className="w-4 h-4 mr-1" />
                    {isCurrentOrLower(p.key) ? 'Přepnout' : 'Vybrat'}
                  </Button>
                )}
              </Card>
            );
          })}
        </div>

        {/* Info box */}
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-start gap-2">
            <Info className="w-5 h-5 text-blue-500 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium">Jak funguje aktivace?</p>
              <p className="mt-1">Po výběru plánu vám zašleme fakturu. Po uhrazení bude plán aktivován do 24 hodin. 
              Pro okamžitou aktivaci nás kontaktujte na <strong>info@budezivo.cz</strong>.</p>
            </div>
          </div>
        </Card>

        {/* Request plan modal */}
        {showRequestModal && selectedPlan && (
          <Dialog open onOpenChange={() => setShowRequestModal(false)}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Objednat plán {PLAN_COLORS[selectedPlan] ? '' : ''}{(plans.find(p => p.key === selectedPlan))?.label}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="text-sm space-y-2">
                    <div className="flex justify-between">
                      <span>Plán:</span>
                      <strong>{(plans.find(p => p.key === selectedPlan))?.label}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Cena:</span>
                      <strong>{(PLAN_PRICES[selectedPlan]?.[billingCycle] || 0).toLocaleString('cs-CZ')} Kč / {billingCycle === 'monthly' ? 'měsíc' : 'rok'}</strong>
                    </div>
                  </div>
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                  <AlertTriangle className="w-4 h-4 inline mr-1" />
                  Po potvrzení vám bude zaslána faktura. Plán bude aktivován po přijetí platby.
                </div>
              </div>
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setShowRequestModal(false)}>Zrušit</Button>
                <Button onClick={handleRequestPlan} disabled={requesting} data-testid="confirm-plan-request-btn">
                  {requesting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <ArrowRight className="w-4 h-4 mr-1" />}
                  Objednat
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
