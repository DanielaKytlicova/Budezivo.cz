import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { AuthContext } from '../../context/AuthContext';
import { Check } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const PlanPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (sessionId) {
      checkPaymentStatus(sessionId);
    }
  }, []);

  const checkPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 5;
    
    if (attempts >= maxAttempts) {
      toast.error('Payment status check timeout');
      return;
    }

    try {
      const response = await axios.get(`${API}/payments/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        toast.success(t('common.success') + ' - Payment completed!');
        window.history.replaceState({}, document.title, '/admin/plan');
        return;
      }
      
      if (response.data.status === 'expired') {
        toast.error('Payment session expired');
        return;
      }

      setTimeout(() => checkPaymentStatus(sessionId, attempts + 1), 2000);
    } catch (error) {
      console.error('Error checking payment status:', error);
    }
  };

  const handleUpgrade = async (packageName) => {
    setProcessing(true);

    try {
      const response = await axios.post(`${API}/payments/create-session`, {
        package: packageName,
        billing_cycle: billingCycle,
      });

      window.location.href = response.data.url;
    } catch (error) {
      toast.error(t('common.error'));
      setProcessing(false);
    }
  };

  const plans = [
    {
      name: 'basic',
      price: billingCycle === 'monthly' ? '990' : '9900',
      features: [
        'Up to 200 bookings per month',
        'Unlimited programs',
        'Advanced statistics',
        'Priority email support',
        'Data export',
      ],
    },
    {
      name: 'standard',
      price: billingCycle === 'monthly' ? '1990' : '19900',
      recommended: true,
      features: [
        'Up to 500 bookings per month',
        'Unlimited programs',
        'Advanced statistics and reports',
        'Bulk actions',
        'Multi-user management',
        'Phone support',
      ],
    },
    {
      name: 'premium',
      price: billingCycle === 'monthly' ? '3990' : '39900',
      features: [
        'Unlimited bookings',
        'Unlimited programs',
        'Dedicated account manager',
        'Custom branding',
        'API access',
        'Priority 24/7 support',
      ],
    },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t('plan.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('plan.currentPlan')}: Free</p>
        </div>

        <Card className="p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900 mb-2">{t('plan.usage')}</h2>
            <p className="text-sm text-muted-foreground">{t('plan.bookingsUsed')}: 0 / 50</p>
            <div className="mt-4 w-full bg-muted rounded-full h-2">
              <div className="bg-[#84A98C] h-2 rounded-full" style={{ width: '0%' }}></div>
            </div>
          </div>
        </Card>

        <div className="flex justify-center mb-8">
          <div className="inline-flex rounded-md border border-border p-1 bg-muted">
            <button
              data-testid="plan-billing-monthly"
              className={`px-6 py-2 rounded text-sm font-medium transition-colors ${
                billingCycle === 'monthly' ? 'bg-white shadow-sm' : 'text-muted-foreground'
              }`}
              onClick={() => setBillingCycle('monthly')}
            >
              {t('pricing.monthly')}
            </button>
            <button
              data-testid="plan-billing-yearly"
              className={`px-6 py-2 rounded text-sm font-medium transition-colors ${
                billingCycle === 'yearly' ? 'bg-white shadow-sm' : 'text-muted-foreground'
              }`}
              onClick={() => setBillingCycle('yearly')}
            >
              {t('pricing.yearly')}
              <span className="ml-2 text-xs text-[#84A98C]">{t('pricing.save')}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              data-testid={`plan-card-${plan.name}`}
              className={`p-6 relative ${plan.recommended ? 'border-[#E9C46A] border-2 shadow-lg' : ''}`}
            >
              {plan.recommended && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-[#E9C46A] text-slate-900 text-xs font-semibold px-3 py-1 rounded-full">
                    Nejčastější volba
                  </span>
                </div>
              )}
              <h3 className="text-2xl font-semibold text-slate-900 mb-4">{t(`pricing.${plan.name}.name`)}</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-slate-900">{plan.price}</span>
                <span className="text-muted-foreground ml-2">
                  {billingCycle === 'monthly' ? 'Kč / měsíc' : 'Kč / rok'}
                </span>
              </div>
              <ul className="space-y-3 mb-6">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start">
                    <Check className="w-5 h-5 text-[#84A98C] mr-2 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-slate-700">{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                data-testid={`upgrade-to-${plan.name}`}
                onClick={() => handleUpgrade(plan.name)}
                disabled={processing}
                className={`w-full ${
                  plan.recommended
                    ? 'bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90'
                    : 'bg-slate-800 text-white hover:bg-slate-700'
                }`}
              >
                {processing ? t('common.loading') : t('plan.upgrade')}
              </Button>
            </Card>
          ))}
        </div>
      </div>
    </AdminLayout>
  );
};
