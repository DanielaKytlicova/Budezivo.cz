import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { Header, BudezivoLogo } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../components/ui/accordion';
import { Check, X, Mail, RefreshCw, Table2, Copy, Eye, Calendar, Bell, Settings, Users, UserCheck, BarChart3, FileText, Clock, TrendingUp, Shield, Zap, Quote, Building2, Palette, BookOpen, Sprout, Music, School as SchoolIcon, ArrowRight, CalendarCheck2, MailCheck, CheckCircle2, CalendarDays, UserPlus, Smile, AlertTriangle, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// --- Social proof config ---

const INSTITUTION_TYPES = [
  { key: 'museum',           label: 'Muzea',             icon: Building2 },
  { key: 'gallery',          label: 'Galerie',           icon: Palette },
  { key: 'library',          label: 'Knihovny',          icon: BookOpen },
  { key: 'botanical_garden', label: 'Botanické zahrady', icon: Sprout },
  { key: 'cultural_center',  label: 'Kulturní centra',   icon: Music },
  { key: 'school',           label: 'Školy',             icon: SchoolIcon },
];

// Real references will replace these once institutions opt-in.
const TESTIMONIALS = [
  {
    quote: "Budeživo nám ušetřilo hodiny týdně nad e-maily a tabulkami. Učitelky si rezervují programy samy, my jen potvrzujeme. Konec zmatků.",
    author: "Lektorský tým",
    role:   "Muzeum středních Čech",
    initials: "LT",
  },
  {
    quote: "Konečně jeden nástroj pro rezervace, kolizní kontrolu i reporty. Přechod z Google tabulek trval méně než týden.",
    author: "Vedoucí vzdělávacího programu",
    role:   "Galerie v regionu",
    initials: "VP",
  },
];

// Numeric count-up component for trust stats.
const StatCard = ({ value, suffix = '', label, color }) => {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const target = Number(value) || 0;
    if (target === 0) { setDisplay(0); return; }
    const duration = 900;
    const start = performance.now();
    let raf;
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return (
    <div className="text-center">
      <div className={`text-4xl md:text-5xl font-bold ${color || 'text-slate-900'} tabular-nums`}>
        {display.toLocaleString('cs-CZ')}{suffix}
      </div>
      <div className="text-xs md:text-sm text-slate-500 mt-1.5 uppercase tracking-wider">
        {label}
      </div>
    </div>
  );
};

export const HomePage = () => {
  const { t } = useTranslation();
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [showDemoDialog, setShowDemoDialog] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [demoFormData, setDemoFormData] = useState({
    name: '',
    institution: '',
    email: '',
    availability: '',
  });
  const [stats, setStats] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/stats`).then(r => setStats(r.data)).catch(() => setStats(null));
  }, []);

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      await axios.post(`${API}/public/contact`, {
        ...demoFormData,
        source: 'Demo formulář - Homepage'
      });
      toast.success('Děkujeme! Brzy vás budeme kontaktovat.');
      setShowDemoDialog(false);
      setDemoFormData({ name: '', institution: '', email: '', availability: '' });
    } catch (error) {
      console.error('Contact form error:', error);
      toast.error('Nepodařilo se odeslat. Zkuste to prosím znovu.');
    } finally {
      setSubmitting(false);
    }
  };

  const pricingTiers = ['free', 'start', 'pro', 'pro_plus'];

  // Pain points data
  // Pain → Solution comparison (before/after with Budeživo)
  const painComparison = [
    {
      bad:  { icon: Mail,          text: 'Desítky e-mailů pro potvrzení jedné rezervace' },
      good: { icon: MailCheck,     text: 'Automatické potvrzení obratem, žádný e-mail' },
    },
    {
      bad:  { icon: RefreshCw,     text: 'Ruční potvrzování každé rezervace zvlášť' },
      good: { icon: CheckCircle2,  text: 'Pravidla nastavíte jednou, systém pracuje sám' },
    },
    {
      bad:  { icon: Table2,        text: 'Nepřehledné Excel tabulky, které jsou vždy zastaralé' },
      good: { icon: CalendarDays,  text: 'Přehledný kalendář vždy aktuální v reálném čase' },
    },
    {
      bad:  { icon: Copy,          text: 'Duplicitní objednávky a kolize termínů' },
      good: { icon: Shield,        text: 'Systém hlídá obsazenost, duplicity jsou nemožné' },
    },
    {
      bad:  { icon: Clock,         text: 'Školy čekají na odpověď, volají a píšou znovu' },
      good: { icon: UserPlus,      text: 'Škola rezervuje sama bez registrace, za 2 minuty' },
    },
  ];

  // Benefits data
  const employeeBenefits = [
    { icon: Clock,       title: 'Méně rutinní administrativy', description: 'Rezervace a potvrzení probíhají bez vašeho zásahu' },
    { icon: UserCheck,   title: 'Úspora hodin týdně',          description: 'Průměrně 3 hodiny administrativy méně každý týden' },
    { icon: CheckCircle2,title: 'Méně chyb a nedorozumění',    description: 'Pravidla hlídá systém, ne člověk' },
    { icon: Smile,       title: 'Klidnější pracovní den',      description: 'Žádné urgentní e-maily, žádné telefonáty' },
  ];

  const managementBenefits = [
    { icon: BarChart3,   title: 'Statistiky a přehledy',          description: 'Kolik skupin, odkud, kdy — exportovatelné reporty' },
    { icon: FileText,    title: 'Podklady pro zřizovatele',       description: 'Reporty připravené pro výroční zprávy a dotace' },
    { icon: TrendingUp,  title: 'Lepší plánování kapacit',        description: 'Vidíte vytíženost dopředu a můžete reagovat' },
    { icon: Shield,      title: 'Transparentní evidence rezervací', description: 'Každá rezervace dohledatelná, nic se neztratí' },
  ];

  // How it works steps (4-step timeline)
  const howItWorks = [
    {
      step: 1,
      icon: CalendarDays,
      title: 'Nastavíte instituci',
      description: 'Prostory, kapacity a provozní dobu za 15 minut',
    },
    {
      step: 2,
      icon: UserCheck,
      title: 'Škola si vybere',
      description: 'Jednoduchý formulář, výběr termínu bez registrace',
    },
    {
      step: 3,
      icon: CheckCircle2,
      title: 'Potvrzení automaticky',
      description: 'Obě strany obdrží e-mail, termín se zapíše do kalendáře',
    },
    {
      step: 4,
      icon: BarChart3,
      title: 'Přehled po ruce',
      description: 'Kalendář a statistiky kdykoli, odkudkoli',
    },
  ];

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
                      <Label htmlFor="demo_availability">Kdy máte obecně čas?</Label>
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
                      disabled={submitting}
                      data-testid="demo-submit-button"
                      className="w-full bg-[#C4AB86] text-white hover:bg-[#b39975] disabled:opacity-50"
                    >
                      {submitting ? 'Odesílám...' : 'Odeslat žádost'}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Section — only rendered once we have meaningful real data
          (gated by backend `show_stats`, currently ≥5 non-deleted institutions).
          Testimonials block is kept disabled until real opt-in references land. */}
      {stats?.show_stats && (
      <section className="py-16 bg-white border-b border-slate-100" id="social-proof" data-testid="social-proof-section">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          {/* Stats bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8 mb-12" data-testid="trust-stats">
              <StatCard
                value={stats.institutions}
                suffix="+"
                label="kulturních institucí"
                color="text-[#4A6FA5]"
              />
              <StatCard
                value={stats.programs + stats.events}
                suffix="+"
                label="programů a akcí"
                color="text-[#4A6FA5]"
              />
              <StatCard
                value={stats.reservations}
                suffix="+"
                label="zpracovaných rezervací"
                color="text-[#4A6FA5]"
              />
              <StatCard
                value={stats.satisfaction}
                suffix="%"
                label="úspěšnost doručení"
                color="text-[#C4AB86]"
              />
            </div>

          {/* Institution types */}
          <div className="text-center mb-10">
            <p className="text-sm font-semibold tracking-wider uppercase text-slate-500 mb-5">
              Důvěřují nám
            </p>
            <div className="flex flex-wrap justify-center gap-3 md:gap-4">
              {INSTITUTION_TYPES.map((t) => {
                const count = stats?.institution_types?.[t.key] || 0;
                return (
                  <div
                    key={t.key}
                    className="group flex items-center gap-2 px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-[#4A6FA5] hover:shadow-sm transition-all"
                    data-testid={`type-chip-${t.key}`}
                  >
                    <t.icon className="w-4 h-4 text-slate-500 group-hover:text-[#4A6FA5]" />
                    <span className="text-sm font-medium text-slate-700">{t.label}</span>
                    {count > 0 && (
                      <span className="text-xs font-mono text-slate-400 ml-1">{count}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/*
            Testimonials are intentionally disabled until we have real, written
            consent from customer institutions. Placeholder TESTIMONIALS array
            is kept in this file — once references are collected, set the flag
            SHOW_TESTIMONIALS below (or better: drive it from a CMS field).
          */}
          {false && TESTIMONIALS.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12 max-w-5xl mx-auto">
              {TESTIMONIALS.map((t, i) => (
                <Card
                  key={i}
                  className="p-6 md:p-8 border border-slate-200 bg-gradient-to-br from-white to-slate-50 relative"
                  data-testid={`testimonial-${i}`}
                >
                  <Quote className="w-8 h-8 text-[#C4AB86] opacity-40 absolute top-5 right-5" />
                  <p className="text-base md:text-lg text-slate-700 leading-relaxed mb-5 italic">
                    „{t.quote}"
                  </p>
                  <div className="flex items-center gap-3 pt-4 border-t border-slate-100">
                    <div className="w-10 h-10 rounded-full bg-[#4A6FA5]/10 flex items-center justify-center text-[#4A6FA5] font-semibold">
                      {t.initials}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-slate-800">{t.author}</div>
                      <div className="text-xs text-slate-500">{t.role}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>
      )}

      {/* Pain Points Section - "Znáte tuto realitu?" */}
      <section className="py-20 bg-[#F8F9FA]" id="problemy">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-[#2B3E50] text-center mb-14">
            Znáte tuto realitu?
          </h2>

          {/* Column headers */}
          <div className="grid grid-cols-1 md:grid-cols-[1fr_40px_1fr] gap-4 md:gap-6 max-w-5xl mx-auto mb-6 px-1">
            <div className="flex items-center gap-2 text-sm font-semibold tracking-wider uppercase text-[#D94A4A]">
              <span className="w-2 h-2 rounded-full bg-[#D94A4A]"></span>
              Bez systému
            </div>
            <div></div>
            <div className="flex items-center gap-2 text-sm font-semibold tracking-wider uppercase text-[#4A6FA5]">
              <span className="w-2 h-2 rounded-full bg-[#4A6FA5]"></span>
              S Budeživo
            </div>
          </div>

          {/* Comparison rows */}
          <div className="space-y-4 max-w-5xl mx-auto">
            {painComparison.map((row, idx) => {
              const BadIcon = row.bad.icon;
              const GoodIcon = row.good.icon;
              return (
                <div
                  key={idx}
                  className="grid grid-cols-1 md:grid-cols-[1fr_40px_1fr] items-center gap-4 md:gap-6"
                  data-testid={`pain-comparison-row-${idx}`}
                >
                  {/* Bad card */}
                  <div className="flex items-center gap-4 bg-[#FCECEB] border border-[#F5D5D2] rounded-2xl p-5 hover:shadow-sm transition-shadow">
                    <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                      <BadIcon className="w-5 h-5 text-[#D94A4A]" strokeWidth={2} />
                    </div>
                    <p className="text-[#2B3E50] font-medium leading-snug">{row.bad.text}</p>
                  </div>

                  {/* Arrow */}
                  <div className="hidden md:flex items-center justify-center">
                    <ArrowRight className="w-5 h-5 text-[#B8C4D6]" strokeWidth={2} />
                  </div>

                  {/* Good card */}
                  <div className="flex items-center gap-4 bg-[#EEF2F9] border border-[#D9E1F0] rounded-2xl p-5 hover:shadow-sm transition-shadow">
                    <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                      <GoodIcon className="w-5 h-5 text-[#4A6FA5]" strokeWidth={2} />
                    </div>
                    <p className="text-[#2B3E50] font-medium leading-snug">{row.good.text}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section - "Jak to funguje?" 4-step timeline */}
      <section className="py-20 bg-[#F1F4FA]" id="jak-to-funguje">
        <div className="max-w-7xl mx-auto px-6 md:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-[#2B3E50] text-center mb-16">
            Jak to funguje?
          </h2>

          <div className="relative max-w-5xl mx-auto">
            {/* Horizontal connecting line (desktop only) */}
            <div
              className="hidden md:block absolute top-10 left-[12.5%] right-[12.5%] h-px bg-[#CBD4E4]"
              aria-hidden="true"
            ></div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-6 relative">
              {howItWorks.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div
                    key={idx}
                    className="flex flex-col items-center text-center"
                    data-testid={`how-it-works-${idx}`}
                  >
                    {/* Circle with icon + step badge */}
                    <div className="relative mb-6">
                      <div className="w-20 h-20 bg-[#4A6FA5] rounded-full flex items-center justify-center shadow-md">
                        <Icon className="w-8 h-8 text-white" strokeWidth={2} />
                      </div>
                      <div className="absolute -top-1 -right-1 w-7 h-7 bg-[#C4AB86] rounded-full flex items-center justify-center shadow-sm ring-4 ring-[#F1F4FA]">
                        <span className="text-xs font-bold text-white">{item.step}</span>
                      </div>
                    </div>

                    <h3 className="text-lg font-semibold text-[#2B3E50] mb-3">{item.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed max-w-[220px]">{item.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section — "Vše na jednom místě." with dashboard preview */}
      <section className="py-20 md:py-24 bg-[#2B3E50] relative overflow-hidden" id="funkce">
        {/* subtle grid backdrop */}
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
        <div className="relative max-w-7xl mx-auto px-6 md:px-8">
          <h2 className="text-3xl md:text-5xl font-bold text-white text-center mb-4">
            Vše na jednom místě.
          </h2>
          <p className="text-base md:text-lg text-white/70 text-center mb-12 md:mb-16 max-w-2xl mx-auto">
            Rezervační systém navržený speciálně pro kulturní instituce
          </p>

          <DashboardPreview />

          {/* Feature pills below */}
          <div className="mt-12 md:mt-14 flex flex-wrap justify-center gap-3" data-testid="feature-pills">
            {[
              { icon: Bell,       label: 'Automatická potvrzení' },
              { icon: UserCheck,  label: 'Bez registrace pro školy' },
              { icon: BarChart3,  label: 'Statistiky pro vedení' },
              { icon: Settings,   label: 'Správa kapacit' },
              { icon: Zap,        label: 'Online platby' },
              { icon: Users,      label: 'Týmové role' },
            ].map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/[0.04] border border-white/10 backdrop-blur-sm hover:bg-white/[0.08] transition"
                  data-testid={`feature-pill-${i}`}
                >
                  <Icon className="w-4 h-4 text-[#C4AB86]" strokeWidth={2} />
                  <span className="text-sm font-medium text-white/90">{f.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Benefits Section - Split layout: Úleva pro zaměstnance / Přínos pro vedení */}
      <section className="bg-white">
        <div className="grid grid-cols-1 md:grid-cols-2">
          {/* Employee Benefits (light side) */}
          <div className="py-20 px-6 md:px-12 lg:px-20 bg-white">
            <div className="max-w-xl md:ml-auto md:pr-8">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase text-[#C4AB86] mb-3">Pro zaměstnance</p>
              <h3 className="text-3xl md:text-4xl font-bold text-[#2B3E50] mb-10">Úleva pro zaměstnance</h3>

              <div className="divide-y divide-gray-100">
                {employeeBenefits.map((benefit, idx) => {
                  const Icon = benefit.icon;
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-4 py-5"
                      data-testid={`employee-benefit-${idx}`}
                    >
                      <div className="w-10 h-10 bg-[#F1F3F8] rounded-lg flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-[#4A6FA5]" strokeWidth={2} />
                      </div>
                      <div>
                        <h4 className="text-base font-semibold text-[#2B3E50] mb-1">{benefit.title}</h4>
                        <p className="text-sm text-gray-500 leading-relaxed">{benefit.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Management Benefits (dark side) */}
          <div className="py-20 px-6 md:px-12 lg:px-20 bg-[#2B3E50]">
            <div className="max-w-xl md:mr-auto md:pl-8">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase text-[#C4AB86] mb-3">Pro vedení</p>
              <h3 className="text-3xl md:text-4xl font-bold text-white mb-10">Přínos pro vedení</h3>

              <div className="divide-y divide-white/10">
                {managementBenefits.map((benefit, idx) => {
                  const Icon = benefit.icon;
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-4 py-5"
                      data-testid={`management-benefit-${idx}`}
                    >
                      <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-[#C4AB86]" strokeWidth={2} />
                      </div>
                      <div>
                        <h4 className="text-base font-semibold text-white mb-1">{benefit.title}</h4>
                        <p className="text-sm text-white/60 leading-relaxed">{benefit.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Demo / CTA Section — dark navy with primary CTAs + customer-view demo card */}
      <section className="py-20 md:py-24 bg-[#2B3E50] relative overflow-hidden">
        {/* subtle gradient accent */}
        <div
          aria-hidden="true"
          className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full opacity-[0.18] pointer-events-none"
          style={{ background: 'radial-gradient(circle, #C4AB86 0%, transparent 60%)' }}
        />
        <div className="relative max-w-5xl mx-auto px-6 md:px-8">
          {/* Headline */}
          <div className="text-center mb-12">
            <p className="text-xs font-semibold tracking-[0.25em] uppercase text-[#C4AB86] mb-4" data-testid="cta-eyebrow">
              Připraveni začít?
            </p>
            <h2 className="text-3xl md:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
              Nastavení za 15 minut.
            </h2>
            <p className="text-base md:text-lg text-white/70 max-w-xl mx-auto">
              Přidejte svou instituci, nastavte prostory a začněte přijímat rezervace ještě dnes.
            </p>
          </div>

          {/* Primary CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16" data-testid="cta-buttons">
            <Link to="/register" data-testid="cta-register">
              <Button size="lg" className="h-12 px-8 bg-[#C4AB86] hover:bg-[#b39975] text-white rounded-lg font-semibold">
                Zaregistrovat instituci
              </Button>
            </Link>
            <a href="#contact" data-testid="cta-online-demo">
              <Button size="lg" variant="outline" className="h-12 px-8 bg-transparent border-white/30 text-white hover:bg-white/10 hover:text-white rounded-lg font-semibold">
                Domluvit online ukázku
              </Button>
            </a>
          </div>

          {/* Divider with caption */}
          <div className="flex items-center gap-4 mb-8">
            <div className="flex-1 h-px bg-white/10" />
            <p className="text-xs text-white/60 inline-flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-[#C4AB86]" />
              Podívejte se, jak to uvidí váš zákazník
            </p>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          {/* Customer-view demo card (glass) */}
          <div
            className="rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-sm p-6 md:p-8"
            data-testid="customer-view-card"
          >
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] items-center gap-6">
              {/* Left: text + checks */}
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-[#C4AB86]/10 border border-[#C4AB86]/30 flex items-center justify-center flex-shrink-0">
                    <UserCheck className="w-5 h-5 text-[#C4AB86]" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold tracking-[0.2em] uppercase text-[#C4AB86]">Pohled vašeho zákazníka</p>
                    <h3 className="text-lg md:text-xl font-bold text-white">Jak jednoduché to bude pro učitele?</h3>
                  </div>
                </div>
                <p className="text-sm text-white/70 leading-relaxed mb-4 max-w-xl">
                  Vyzkoušejte si celý proces rezervace na vlastní kůži — přesně tak, jak ho uvidí učitel. Bez registrace, za 2 minuty.
                </p>
                <ul className="space-y-2">
                  {[
                    'Žádná registrace ani přihlášení',
                    'Výběr programu, termínu a odeslání',
                    'Ukázkové potvrzení e-mailem',
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-2.5 text-sm text-white/85">
                      <Check className="w-4 h-4 text-[#C4AB86] flex-shrink-0" strokeWidth={2.5} />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Right: action */}
              <div className="flex flex-col items-stretch md:items-end gap-2">
                <Link to="/booking/demo" target="_blank" rel="noreferrer" data-testid="try-booking-demo">
                  <Button size="lg" className="h-12 px-6 w-full md:w-auto bg-[#C4AB86] hover:bg-[#b39975] text-white rounded-lg font-semibold shadow-lg shadow-[#C4AB86]/20">
                    <Play className="w-4 h-4 mr-2" /> Spustit ukázku rezervace
                  </Button>
                </Link>
                <p className="text-[11px] text-white/50 text-center md:text-right">Otevře se v novém okně · Pouze demo data</p>
              </div>
            </div>
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

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricingTiers.map((tier) => {
              const isPro = tier === 'pro';

              const prices = {
                free: { monthly: 0, yearly: 0 },
                start: { monthly: 490, yearly: 4900 },
                pro: { monthly: 990, yearly: 9900 },
                pro_plus: { monthly: 1990, yearly: 19900 }
              };

              const accentColors = {
                free: '#64748B',
                start: '#3B82F6',
                pro: '#F59E0B',
                pro_plus: '#8B5CF6',
              };

              const price = prices[tier][billingCycle];
              const tierFeatures = t(`pricing.${tier}.features`);
              const tierLimitations = t(`pricing.${tier}.limitations`);
              const tierHighlight = t(`pricing.${tier}.highlight`);
              const tierInherits = t(`pricing.${tier}.inherits`);

              return (
                <Card
                  key={tier}
                  data-testid={`pricing-tier-${tier}`}
                  className={`p-6 bg-white rounded-2xl relative border flex flex-col ${
                    isPro ? 'border-amber-400 border-2 shadow-lg' : 'border-gray-200'
                  }`}
                >
                  {isPro && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className="bg-amber-400 text-slate-900 text-xs font-semibold px-4 py-1 rounded-full whitespace-nowrap">
                        Doporučeno
                      </span>
                    </div>
                  )}
                  <h3 className="text-xl font-bold text-[#2B3E50] mb-2">{t(`pricing.${tier}.name`)}</h3>
                  <div className="mb-5">
                    {tier === 'free' ? (
                      <>
                        <span className="text-3xl font-bold text-[#2B3E50]">0 Kč</span>
                        <span className="text-gray-500 text-sm block mt-1">navždy</span>
                      </>
                    ) : (
                      <>
                        <span className="text-3xl font-bold text-[#2B3E50]">{price.toLocaleString('cs-CZ')} Kč</span>
                        <span className="text-gray-500 text-sm block mt-1">
                          {billingCycle === 'monthly' ? '/ měsíčně' : '/ ročně'}
                        </span>
                      </>
                    )}
                  </div>

                  {/* Features */}
                  <ul className="space-y-2.5 mb-4 flex-1">
                    {tierInherits && typeof tierInherits === 'string' && !tierInherits.includes('pricing.') && (
                      <li className="text-xs font-semibold text-slate-500 uppercase tracking-wide pb-1">{tierInherits}</li>
                    )}
                    {Array.isArray(tierFeatures) && tierFeatures.map((feature, idx) => (
                      <li key={idx} className="flex items-start">
                        <Check className="w-4 h-4 mr-2 flex-shrink-0 mt-0.5" style={{ color: accentColors[tier] || '#4A6FA5' }} />
                        <span className="text-sm text-gray-700">{feature}</span>
                      </li>
                    ))}
                    {/* Limitations with X icon */}
                    {Array.isArray(tierLimitations) && tierLimitations.map((limitation, idx) => (
                      <li key={`lim-${idx}`} className="flex items-start">
                        <X className="w-4 h-4 text-red-400 mr-2 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-400">{limitation}</span>
                      </li>
                    ))}
                  </ul>

                  {/* Highlight */}
                  {tierHighlight && typeof tierHighlight === 'string' && (
                    <p className="text-xs text-gray-500 italic mb-4 border-t border-gray-100 pt-3">
                      {tierHighlight}
                    </p>
                  )}

                  <Link to="/register" data-testid={`pricing-cta-${tier}`} className="mt-auto">
                    <Button
                      className={`w-full rounded-lg ${
                        isPro
                          ? 'bg-amber-400 text-slate-900 hover:bg-amber-500'
                          : 'border-2 border-[#4A6FA5] text-[#4A6FA5] bg-white hover:bg-[#4A6FA5]/5'
                      }`}
                      variant={isPro ? 'default' : 'outline'}
                    >
                      {t(`pricing.${tier}.cta`)}
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
            <Dialog open={showDemoDialog} onOpenChange={setShowDemoDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" className="border-2 border-[#4A6FA5] text-[#4A6FA5] rounded-lg px-8 h-12">
                  Nezávazná konzultace
                </Button>
              </DialogTrigger>
            </Dialog>
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

// ────────────────────────────────────────────────────────────────────────
// DashboardPreview — stylized illustration of the admin dashboard for
// the "Vše na jednom místě" section. No real data, purely visual.
// ────────────────────────────────────────────────────────────────────────
const DashboardPreview = () => {
  const sidebarItems = [
    { label: 'Přehled',      active: true },
    { label: 'Programy' },
    { label: 'Rezervace' },
    { label: 'Události' },
    { label: 'Školy' },
    { label: 'Mailingy' },
    { label: 'Zpětná vazba' },
    { label: 'Dostupnost' },
    { label: 'Statistiky' },
    { label: 'Tým' },
    { label: 'Můj profil' },
    { label: 'Nastavení' },
  ];

  const stats = [
    { label: 'Dnešní rezervace',    value: '3',     icon: Calendar,  bg: 'bg-[#EEF2F9]', tint: 'text-[#4A6FA5]' },
    { label: 'Nadcházející skupiny',value: '8',     icon: Users,     bg: 'bg-[#FFF6E0]', tint: 'text-[#C4AB86]' },
    { label: 'Vytížení kapacity',   value: '74%',   icon: BarChart3, bg: 'bg-[#E8F5E9]', tint: 'text-[#84A98C]' },
    { label: 'Limit rezervací',     value: '24/50', icon: Clock,     bg: 'bg-[#FCECEB]', tint: 'text-[#D94A4A]' },
  ];

  // Calendar mock: rows = time slots, cols = weekdays
  const days = ['PO 28', 'ÚT 29', 'ST 30', 'ČT 1', 'PÁ 2', 'SO 3', 'NE 4'];
  const todayCol = 2; // Wed
  const slots = ['8:00', '9:00', '10:00', '11:00', '13:00'];
  // Bookings at [rowIdx][colIdx] => { title, sub, tone: 'primary'|'deep'|null }
  const bookings = {
    '1-0': { title: 'ZŠ Palacká',       sub: '9:00 · 25 žáků',   tone: 'primary' },
    '1-1': { title: 'Gymnázium Praha',  sub: '9:00 · 30 žáků',   tone: 'primary' },
    '1-2': { title: 'ZŠ Botanická',     sub: '9:30 · 22 žáků',   tone: 'primary' },
    '1-4': { title: 'ZŠ Mendlova',      sub: '9:00 · 28 žáků',   tone: 'primary' },
    '2-1': { title: 'Gymnázium Praha',  sub: '10:00 pokračování', tone: 'deep' },
    '2-3': { title: 'VOŠ Brno',         sub: '10:00 · 18 žáků',  tone: 'primary' },
    '3-0': { title: 'ZŠ Náměstí',       sub: '11:00 · 24 žáků',  tone: 'primary' },
    '3-2': { title: 'ZŠ Líšeň',         sub: '11:30 · 20 žáků',  tone: 'primary' },
    '3-4': { title: 'ZŠ Mendlova',      sub: '11:00 pokračování', tone: 'deep' },
    '4-1': { title: 'SPŠ Technická',    sub: '13:00 · 16 žáků',  tone: 'primary' },
    '4-3': { title: 'ZŠ Kohoutovice',   sub: '13:30 · 26 žáků',  tone: 'primary' },
  };

  return (
    <div
      className="relative mx-auto max-w-5xl rounded-2xl bg-white shadow-2xl shadow-black/40 ring-1 ring-black/5 overflow-hidden"
      data-testid="dashboard-preview"
    >
      <div className="grid grid-cols-[200px_1fr]">
        {/* Sidebar */}
        <aside className="bg-white border-r border-slate-100 p-4 hidden md:block">
          <div className="mb-6 px-2">
            <BudezivoLogo showText={true} />
          </div>
          <nav className="space-y-0.5">
            {sidebarItems.map((it, i) => (
              <div
                key={i}
                className={`px-3 py-2 rounded-lg text-sm transition ${
                  it.active ? 'bg-[#2B3E50] text-white font-semibold' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {it.label}
              </div>
            ))}
          </nav>
        </aside>

        {/* Main */}
        <div className="p-5 md:p-6 bg-[#FAFBFC]">
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-lg md:text-xl font-bold text-[#2B3E50]">Vítejte zpět</h3>
              <p className="text-xs text-slate-500 mt-0.5">Muzeum města Brna</p>
            </div>
            <div className="relative w-9 h-9 rounded-full bg-white border border-slate-200 flex items-center justify-center">
              <Bell className="w-4 h-4 text-slate-500" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#D94A4A]" />
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            {stats.map((s, i) => {
              const Icon = s.icon;
              return (
                <div key={i} className="p-3 rounded-xl bg-white border border-slate-100 flex items-start justify-between">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500">{s.label}</p>
                    <p className="text-xl md:text-2xl font-bold text-[#2B3E50] mt-1">{s.value}</p>
                  </div>
                  <div className={`w-7 h-7 rounded-md ${s.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-3.5 h-3.5 ${s.tint}`} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Calendar header */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-[#2B3E50]">Nadcházející rezervace</p>
            <div className="flex items-center gap-1.5">
              <button className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-white border border-slate-200 text-slate-600">Dnes</button>
              <span className="text-[11px] text-slate-500">Duben 2026</span>
              <button className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-[#2B3E50] text-white">Kalendář</button>
            </div>
          </div>

          {/* Calendar grid */}
          <div className="rounded-lg bg-white border border-slate-100 overflow-hidden">
            {/* Days header */}
            <div className="grid grid-cols-[44px_repeat(7,minmax(0,1fr))] text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
              <div />
              {days.map((d, i) => {
                const [w, n] = d.split(' ');
                return (
                  <div key={i} className="px-2 py-2 text-center">
                    <div>{w}</div>
                    <div className={`text-sm font-bold mt-0.5 ${i === todayCol ? 'text-white bg-[#4A6FA5] rounded-full w-7 h-7 mx-auto flex items-center justify-center' : 'text-[#2B3E50]'}`}>{n}</div>
                  </div>
                );
              })}
            </div>

            {/* Time rows */}
            {slots.map((slot, ri) => (
              <div key={ri} className="grid grid-cols-[44px_repeat(7,minmax(0,1fr))] border-b border-slate-50 last:border-b-0 min-h-[58px]">
                <div className="text-[10px] text-slate-400 px-2 py-2 border-r border-slate-100">{slot}</div>
                {days.map((_, ci) => {
                  const b = bookings[`${ri}-${ci}`];
                  return (
                    <div key={ci} className="border-r border-slate-50 last:border-r-0 p-1">
                      {b && (
                        <div
                          className={`rounded-md px-1.5 py-1 ${b.tone === 'deep' ? 'bg-[#C4AB86] text-white' : 'bg-[#FBE099] text-[#5C4A1F]'}`}
                        >
                          <p className="text-[10px] font-semibold leading-tight truncate">{b.title}</p>
                          <p className="text-[9px] opacity-80 leading-tight truncate">{b.sub}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

