import React, { useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../components/ui/accordion';
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';
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

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    toast.success('Děkujeme! Brzy vás budeme kontaktovat.');
    setShowDemoDialog(false);
    setDemoFormData({ name: '', institution: '', email: '', availability: '' });
  };

  const pricingTiers = ['free', 'basic', 'standard', 'premium'];

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Header />

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-[#4A6FA5] via-[#5979ad] to-[#6889bb] text-white py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <div className="max-w-3xl">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6">
              Méně administrativy. Více prostoru pro kreativitu.
            </h1>
            <p className="text-lg md:text-xl text-white/90 leading-relaxed mb-8">
              Spravujte rezervace školních a skupinových programů přehledně, bez e-mailového chaosu a tabulek.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/register" data-testid="hero-cta-trial">
                <Button size="lg" className="bg-[#C4AB86] text-white hover:bg-[#b39975] h-12 px-8 rounded-lg shadow-none">
                  Vyzkoušet zdarma
                </Button>
              </Link>
              <Dialog open={showDemoDialog} onOpenChange={setShowDemoDialog}>
                <DialogTrigger asChild>
                  <Button size="lg" variant="outline" className="h-12 px-8 rounded-lg border-2 border-white text-white hover:bg-white/10" data-testid="hero-cta-demo">
                    Domluvit online ukázku
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Domluvit online ukázku</DialogTitle>
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
                      className="w-full bg-[#C4AB86] text-white hover:bg-[#b39975]"
                    >
                      Odeslat žádost
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Booking Section */}
      <section className="py-16 bg-white" id="funkce">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-[#2B3E50] mb-4">
              Vyzkoušejte si rezervační systém
            </h2>
            <p className="text-lg text-gray-600">
              Projděte si ukázkový proces rezervace jako učitel nebo vedoucí skupiny
            </p>
          </div>
          <div className="flex justify-center">
            <Link to="/booking/demo" data-testid="try-booking-demo">
              <Button size="lg" className="bg-[#C4AB86] text-white hover:bg-[#b39975] h-12 px-8 rounded-lg">
                Vyzkoušet rezervační formulář
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-[#F8F9FA]">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-[#2B3E50] text-center mb-4">
            Jednoduché a transparentní tarify
          </h2>

          <div className="flex justify-center mb-12">
            <div className="inline-flex rounded-full bg-white border border-gray-200 p-1">
              <button
                data-testid="billing-monthly"
                className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                  billingCycle === 'monthly' ? 'bg-[#4A6FA5] text-white' : 'text-gray-700'
                }`}
                onClick={() => setBillingCycle('monthly')}
              >
                Měsíčně
              </button>
              <button
                data-testid="billing-yearly"
                className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                  billingCycle === 'yearly' ? 'bg-[#4A6FA5] text-white' : 'text-gray-700'
                }`}
                onClick={() => setBillingCycle('yearly')}
              >
                Ročně <span className="text-xs">(ušetříte 20%)</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {pricingTiers.map((tier) => {
              const isBasic = tier === 'basic';
              
              // Pevně definované ceny
              const prices = {
                free: { monthly: 0, yearly: 0 },
                basic: { monthly: 990, yearly: 9900 },
                standard: { monthly: 1990, yearly: 19900 },
                premium: { monthly: 3990, yearly: 39900 }
              };
              
              const price = prices[tier][billingCycle];
              const features = t(`pricing.${tier}.features`);

              return (
                <Card
                  key={tier}
                  data-testid={`pricing-tier-${tier}`}
                  className={`p-6 bg-white rounded-2xl relative border ${
                    isBasic ? 'border-[#C4AB86] border-2' : 'border-gray-200'
                  }`}
                >
                  {isBasic && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className="bg-[#C4AB86] text-white text-xs font-semibold px-4 py-1 rounded-full">
                        Nejčastější volba
                      </span>
                    </div>
                  )}
                  <h3 className="text-2xl font-bold text-[#2B3E50] mb-2">{t(`pricing.${tier}.name`)}</h3>
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-[#2B3E50]">{price} Kč</span>
                    {tier !== 'free' && (
                      <span className="text-gray-500 text-sm block mt-1">
                        {billingCycle === 'monthly' ? 'měsíčně' : 'ročně'}
                      </span>
                    )}
                    {tier === 'free' && (
                      <span className="text-gray-500 text-sm block mt-1">navždy</span>
                    )}
                  </div>
                  <ul className="space-y-3 mb-6">
                    {Array.isArray(features) && features.map((feature, idx) => (
                      <li key={idx} className="flex items-start">
                        <Check className="w-5 h-5 text-[#4A6FA5] mr-2 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to="/register" data-testid={`pricing-cta-${tier}`}>
                    <Button
                      className={`w-full rounded-lg ${
                        isBasic
                          ? 'bg-[#C4AB86] text-white hover:bg-[#b39975]'
                          : 'border-2 border-[#4A6FA5] text-[#4A6FA5] bg-white hover:bg-[#4A6FA5]/5'
                      }`}
                      variant={isBasic ? 'default' : 'outline'}
                    >
                      Začít zdarma
                    </Button>
                  </Link>
                </Card>
              );
            })}
          </div>

          <div className="flex justify-center gap-4 mt-8">
            <Link to="/register">
              <Button className="bg-[#C4AB86] text-white hover:bg-[#b39975] rounded-lg px-8 h-12">
                Začít zdarma
              </Button>
            </Link>
            <Button variant="outline" className="border-2 border-[#4A6FA5] text-[#4A6FA5] rounded-lg px-8 h-12">
              Nezávazná konzultace
            </Button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-br from-[#4A6FA5] via-[#5979ad] to-[#6889bb] text-white py-20">
        <div className="max-w-4xl mx-auto px-6 md:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Dopřejte svému týmu více času na skutečnou práci.
          </h2>
          <p className="text-lg text-white/90 mb-8">
            Vyzkoušejte systém zdarma po dobu 30 dnů. Žádná platební karta není potřeba.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register">
              <Button size="lg" className="bg-[#C4AB86] text-white hover:bg-[#b39975] h-12 px-8 rounded-lg">
                Vyzkoušet zdarma
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="h-12 px-8 rounded-lg border-2 border-white text-white hover:bg-white/10">
              Domluvit online ukázku
            </Button>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 bg-white">
        <div className="max-w-3xl mx-auto px-6 md:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-[#2B3E50] text-center mb-12">
            {t('faq.title')}
          </h2>
          <Accordion type="single" collapsible className="w-full">
            {['q1', 'q2', 'q3', 'q4'].map((q, idx) => (
              <AccordionItem key={idx} value={`item-${idx}`}>
                <AccordionTrigger className="text-left font-semibold text-[#2B3E50]">
                  {t(`faq.${q}`)}
                </AccordionTrigger>
                <AccordionContent className="text-gray-600 leading-relaxed">
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
