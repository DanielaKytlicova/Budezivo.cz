import React, { useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../components/ui/accordion';
import { Check, Mail, Calendar, Users, BarChart, CheckCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';

export const HomePage = () => {
  const { t } = useTranslation();
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [showDemoDialog, setShowDemoDialog] = useState(false);
  const [demoFormData, setDemoFormData] = useState({
    name: '',
    institution: '',
    email: '',
    availability: '',
  });

  const pricingTiers = ['free', 'basic', 'standard', 'premium'];

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    // Mock submission - in production, send to backend
    toast.success('Děkujeme! Brzy vás budeme kontaktovat.');
    setShowDemoDialog(false);
    setDemoFormData({ name: '', institution: '', email: '', availability: '' });
  };

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />

      {/* Hero Section */}
      <section className="py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-12 items-center">
            <div className="md:col-span-7">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 leading-tight mb-6">
                {t('hero.title')}
              </h1>
              <p className="text-lg leading-relaxed text-slate-600 mb-8">
                {t('hero.subtitle')}
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/register" data-testid="hero-cta-trial">
                  <Button size="lg" className="bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90 h-12 px-8 shadow-sm">
                    {t('hero.cta_trial')}
                  </Button>
                </Link>
                <Dialog open={showDemoDialog} onOpenChange={setShowDemoDialog}>
                  <DialogTrigger asChild>
                    <Button size="lg" variant="outline" className="h-12 px-8" data-testid="hero-cta-demo">
                      {t('hero.cta_demo')}
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle>{t('hero.cta_demo')}</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleDemoSubmit} className="space-y-4" data-testid="demo-request-form">
                      <div>
                        <Label htmlFor="demo_name">Jméno</Label>
                        <Input
                          id="demo_name"
                          data-testid="demo-name-input"
                          value={demoFormData.name}
                          onChange={(e) => setDemoFormData({ ...demoFormData, name: e.target.value })}
                          required
                          className="mt-2"
                        />
                      </div>
                      <div>
                        <Label htmlFor="demo_institution">Název instituce</Label>
                        <Input
                          id="demo_institution"
                          data-testid="demo-institution-input"
                          value={demoFormData.institution}
                          onChange={(e) => setDemoFormData({ ...demoFormData, institution: e.target.value })}
                          required
                          className="mt-2"
                        />
                      </div>
                      <div>
                        <Label htmlFor="demo_email">E-mail</Label>
                        <Input
                          id="demo_email"
                          type="email"
                          data-testid="demo-email-input"
                          value={demoFormData.email}
                          onChange={(e) => setDemoFormData({ ...demoFormData, email: e.target.value })}
                          required
                          className="mt-2"
                        />
                      </div>
                      <div>
                        <Label htmlFor="demo_availability">Kdy máte obecně čas? (např. středy dopoledne, pátky dopoledne)</Label>
                        <Textarea
                          id="demo_availability"
                          data-testid="demo-availability-input"
                          value={demoFormData.availability}
                          onChange={(e) => setDemoFormData({ ...demoFormData, availability: e.target.value })}
                          required
                          className="mt-2"
                          placeholder="Např: Středy 9:00-12:00, Pátky 10:00-14:00"
                        />
                      </div>
                      <Button
                        type="submit"
                        data-testid="demo-submit-button"
                        className="w-full bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90"
                      >
                        Odeslat žádost
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
            <div className="md:col-span-5">
              <div className="relative">
                <img
                  src="https://images.unsplash.com/photo-1625358775317-a4f33370c520"
                  alt="Museum gallery"
                  className="rounded-lg shadow-md w-full h-auto"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 text-center mb-12">
            {t('problem.title')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {['point1', 'point2', 'point3', 'point4', 'point5'].map((point, idx) => (
              <Card key={idx} className="p-6">
                <p className="text-sm text-slate-700 leading-relaxed">{t(`problem.${point}`)}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 text-center mb-12">
            {t('solution.title')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: Mail, key: 'feature1' },
              { icon: Calendar, key: 'feature2' },
              { icon: CheckCircle, key: 'feature3' },
              { icon: Users, key: 'feature4' },
              { icon: BarChart, key: 'feature5' },
            ].map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <Card key={idx} className="p-6 text-center hover:shadow-md transition-shadow duration-200">
                  <div className="w-12 h-12 bg-[#84A98C] rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <p className="text-base text-slate-700 leading-relaxed">{t(`solution.${feature.key}`)}</p>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Demo Booking Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 mb-4">
              Vyzkoušejte si rezervační systém
            </h2>
            <p className="text-lg text-slate-600">
              Projděte si ukázkový proces rezervace jako učitel nebo vedoucí skupiny
            </p>
          </div>
          <div className="flex justify-center">
            <Link to="/booking/demo" data-testid="try-booking-demo">
              <Button size="lg" className="bg-[#84A98C] text-white hover:bg-[#84A98C]/90 h-12 px-8 shadow-sm">
                Vyzkoušet rezervační formulář
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-16 md:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 text-center mb-8">
            {t('pricing.title')}
          </h2>

          <div className="flex justify-center mb-12">
            <div className="inline-flex rounded-md border border-border p-1 bg-muted">
              <button
                data-testid="billing-monthly"
                className={`px-6 py-2 rounded text-sm font-medium transition-colors ${
                  billingCycle === 'monthly' ? 'bg-white shadow-sm' : 'text-muted-foreground'
                }`}
                onClick={() => setBillingCycle('monthly')}
              >
                {t('pricing.monthly')}
              </button>
              <button
                data-testid="billing-yearly"
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

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {pricingTiers.map((tier) => {
              const isBasic = tier === 'basic';
              const price = billingCycle === 'monthly' ? t(`pricing.${tier}.price`) : t(`pricing.${tier}.priceYearly`) || t(`pricing.${tier}.price`);
              const features = t(`pricing.${tier}.features`);

              return (
                <Card
                  key={tier}
                  data-testid={`pricing-tier-${tier}`}
                  className={`p-6 relative ${
                    isBasic ? 'border-[#E9C46A] border-2 shadow-lg' : ''
                  }`}
                >
                  {isBasic && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className="bg-[#E9C46A] text-slate-900 text-xs font-semibold px-3 py-1 rounded-full">
                        {t(`pricing.${tier}.description`)}
                      </span>
                    </div>
                  )}
                  <h3 className="text-2xl font-semibold text-slate-900 mb-2">{t(`pricing.${tier}.name`)}</h3>
                  {tier !== 'free' && !isBasic && (
                    <p className="text-sm text-muted-foreground mb-4">{t(`pricing.${tier}.description`)}</p>
                  )}
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-slate-900">{price}</span>
                    <span className="text-muted-foreground ml-2">
                      {tier === 'free' ? '' : billingCycle === 'monthly' ? t('pricing.perMonth') : t('pricing.perYear')}
                    </span>
                  </div>
                  <ul className="space-y-3 mb-6">
                    {Array.isArray(features) && features.map((feature, idx) => (
                      <li key={idx} className="flex items-start">
                        <Check className="w-5 h-5 text-[#84A98C] mr-2 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-slate-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to="/register" data-testid={`pricing-cta-${tier}`}>
                    <Button
                      className={`w-full ${
                        isBasic
                          ? 'bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90'
                          : 'bg-slate-800 text-white hover:bg-slate-700'
                      }`}
                    >
                      {t(`pricing.${tier}.cta`)}
                    </Button>
                  </Link>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16">
        <div className="max-w-3xl mx-auto px-4 md:px-8">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 text-center mb-12">
            {t('faq.title')}
          </h2>
          <Accordion type="single" collapsible className="w-full">
            {['q1', 'q2', 'q3', 'q4'].map((q, idx) => (
              <AccordionItem key={idx} value={`item-${idx}`}>
                <AccordionTrigger className="text-left font-medium">{t(`faq.${q}`)}</AccordionTrigger>
                <AccordionContent className="text-slate-600 leading-relaxed">
                  {t(`faq.a${idx + 1}`)}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      <Footer />
    </div>
  );
};
