import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  BarChart3,
  Bell,
  CalendarCheck2,
  Check,
  ChevronDown,
  Clock,
  FileText,
  Mail,
  MailCheck,
  MousePointerClick,
  RefreshCw,
  Shield,
  Sparkles,
  Users,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { FieldError, FIELD_ERROR_CLASS } from '../../components/ui/field-error';
import { Label } from '../../components/ui/label';
import { Header } from '../../components/layout/Header';
import { Textarea } from '../../components/ui/textarea';
import './HomePageRedesign.css';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const HERO_IMAGE = 'https://budezivo-redesign.kytlicova-vanilie.chatgpt.site/hero-museum.png';
const FOUNDER_IMAGE = 'https://budezivo-redesign.kytlicova-vanilie.chatgpt.site/daniela-kytlicova.png';

const flowSteps = [
  {
    number: '01',
    icon: CalendarCheck2,
    title: 'Škola si vybere termín',
    text: 'Veřejný rezervační odkaz ukáže jen dostupné programy a termíny.',
  },
  {
    number: '02',
    icon: Shield,
    title: 'Systém zkontroluje kolize',
    text: 'Hlídá místnosti, lektory, kapacity i souběhy bez ruční tabulky.',
  },
  {
    number: '03',
    icon: MailCheck,
    title: 'Potvrzení odejde automaticky',
    text: 'Škola dostane jasné instrukce a tým vidí rezervaci v přehledu.',
  },
  {
    number: '04',
    icon: Bell,
    title: 'Připomínky běží samy',
    text: 'E-maily, organizační informace a změny drží jeden konzistentní tón.',
  },
  {
    number: '05',
    icon: Users,
    title: 'Tým má jasno, kdo přijde',
    text: 'Admin, lektor i pokladna vidí jen to, co ke své roli potřebují.',
  },
  {
    number: '06',
    icon: BarChart3,
    title: 'Vyhodnocení je připravené',
    text: 'Statistiky, kontakty a kampaně se dají použít pro další plánování.',
  },
];

const howSteps = [
  {
    icon: MousePointerClick,
    title: 'Publikujete nabídku',
    text: 'Programy, termíny a pravidla vyplníte jednou. Odkaz vložíte na web nebo pošlete školám.',
  },
  {
    icon: CalendarCheck2,
    title: 'Školy rezervují samy',
    text: 'Učitel si vybere program, termín a odešle přihlášku bez registrace.',
  },
  {
    icon: RefreshCw,
    title: 'Bude živo hlídá provoz',
    text: 'Systém kontroluje obsazenost, kolize, kontakty, e-maily a stav rezervací.',
  },
  {
    icon: BarChart3,
    title: 'Vy vidíte výsledek',
    text: 'Tým má kalendář, seznamy, exporty a přehled, co opravdu proběhlo.',
  },
];

const audienceCards = [
  {
    title: 'Muzea a galerie',
    text: 'Vzdělávací programy, komentované prohlídky, dílny a akce pro školy.',
    items: ['termíny a kapacity', 'lektoři a místnosti', 'školní kontakty'],
  },
  {
    title: 'Knihovny a kulturní centra',
    text: 'Opakované programy, čtenářské lekce, workshopy a veřejné akce.',
    items: ['rezervace bez registrace', 'přehled účasti', 'hromadná propagace'],
  },
  {
    title: 'Botanické zahrady a science centra',
    text: 'Sezonní provoz, skupiny, tematické bloky a návštěvy s pevnou kapacitou.',
    items: ['kolizní pravidla', 'kalendář týmu', 'exporty pro vedení'],
  },
];

const benefits = [
  { icon: Clock, title: 'Méně rutiny', text: 'Méně ručního potvrzování a opisování mezi e-maily, tabulkami a kalendářem.' },
  { icon: Shield, title: 'Méně chyb', text: 'Kapacity, kolize a povinná pole hlídá systém, ne paměť jednoho člověka.' },
  { icon: Mail, title: 'Lepší komunikace', text: 'Školy dostávají jasné potvrzení, připomínky a odkazy na správný termín.' },
  { icon: FileText, title: 'Přehled pro vedení', text: 'Data pro vyhodnocení návštěvnosti, vytížení a další plánování máte po ruce.' },
];

const pricing = [
  {
    name: 'Start',
    price: '0 Kč',
    note: 'pro vyzkoušení',
    items: ['veřejný rezervační odkaz', 'základní programy', 'ruční správa rezervací'],
  },
  {
    name: 'Pro',
    price: 'od 690 Kč',
    note: 'měsíčně za instituci',
    featured: true,
    items: ['kolize a kapacity', 'propagace školám', 'role týmu', 'statistiky a exporty'],
  },
  {
    name: 'Individuálně',
    price: 'na míru',
    note: 'pro větší organizace',
    items: ['více institucí', 'specifické procesy', 'pilotní nastavení s podporou'],
  },
];

const faqItems = [
  {
    question: 'Nahradí Bude živo náš web?',
    answer: 'Ne. Bude živo doplní váš web o rezervační a provozní část. Veřejný odkaz vložíte na své stránky nebo ho pošlete školám.',
  },
  {
    question: 'Musí se učitelé registrovat?',
    answer: 'Ne. Veřejná rezervace je navržená tak, aby škola mohla vybrat termín a odeslat přihlášku bez vytváření účtu.',
  },
  {
    question: 'Co když máme vlastní pravidla pro kapacity a lektory?',
    answer: 'Právě proto systém počítá s kapacitami, místnostmi, lektory, uzávěrkami přihlášek a kolizními pravidly.',
  },
  {
    question: 'Dá se začít postupně?',
    answer: 'Ano. Pro pilot stačí nastavit několik programů, ověřit veřejný odkaz a postupně doplnit mailing, exporty a další provozní detaily.',
  },
];

const DemoDialog = ({ children }) => {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [form, setForm] = useState({ name: '', institution: '', email: '', availability: '' });

  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const validate = () => {
    const errors = {};
    if (!form.name.trim()) errors.name = 'Vyplňte jméno.';
    if (!form.institution.trim()) errors.institution = 'Vyplňte název instituce.';
    if (!form.email.trim()) errors.email = 'Vyplňte e-mail.';
    if (!form.availability.trim()) errors.availability = 'Vyplňte, kdy máte obecně čas.';
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      toast.error('Zkontrolujte zvýrazněná pole.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validate()) return;
    setSubmitting(true);

    try {
      await axios.post(`${API}/public/contact`, {
        ...form,
        source: 'Demo formulář - Homepage redesign',
      });
      toast.success('Děkujeme! Brzy vás budeme kontaktovat.');
      setOpen(false);
      setForm({ name: '', institution: '', email: '', availability: '' });
      setFieldErrors({});
    } catch (error) {
      console.error('Contact form error:', error);
      toast.error('Nepodařilo se odeslat. Zkuste to prosím znovu.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="bz-demo-dialog">
        <DialogHeader>
          <DialogTitle>Domluvit online ukázku</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="bz-demo-form">
          <div>
            <Label htmlFor="demo-name">Jméno</Label>
            <Input id="demo-name" value={form.name} onChange={(event) => setField('name', event.target.value)} className={fieldErrors.name ? FIELD_ERROR_CLASS : ''} aria-invalid={Boolean(fieldErrors.name)} />
            <FieldError message={fieldErrors.name} />
          </div>
          <div>
            <Label htmlFor="demo-institution">Název instituce</Label>
            <Input id="demo-institution" value={form.institution} onChange={(event) => setField('institution', event.target.value)} className={fieldErrors.institution ? FIELD_ERROR_CLASS : ''} aria-invalid={Boolean(fieldErrors.institution)} />
            <FieldError message={fieldErrors.institution} />
          </div>
          <div>
            <Label htmlFor="demo-email">E-mail</Label>
            <Input id="demo-email" type="email" value={form.email} onChange={(event) => setField('email', event.target.value)} className={fieldErrors.email ? FIELD_ERROR_CLASS : ''} aria-invalid={Boolean(fieldErrors.email)} />
            <FieldError message={fieldErrors.email} />
          </div>
          <div>
            <Label htmlFor="demo-availability">Kdy se vám hodí ukázka?</Label>
            <Textarea id="demo-availability" rows={4} value={form.availability} onChange={(event) => setField('availability', event.target.value)} className={fieldErrors.availability ? FIELD_ERROR_CLASS : ''} aria-invalid={Boolean(fieldErrors.availability)} />
            <FieldError message={fieldErrors.availability} />
          </div>
          <button type="submit" className="bz-primary-button bz-full-button" disabled={submitting}>
            {submitting ? 'Odesílám...' : 'Odeslat poptávku'}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const ProductPreview = () => (
  <div className="bz-product-preview" aria-label="Ukázka prostředí Bude živo">
    <div className="bz-preview-sidebar">
      <span />
      <span />
      <span />
      <span />
    </div>
    <div className="bz-preview-main">
      <div className="bz-preview-topbar">
        <strong>Rezervace</strong>
        <div>
          <span />
          <span />
        </div>
      </div>
      <div className="bz-preview-grid">
        <div className="bz-preview-card wide">
          <p>Programy tento týden</p>
          <strong>24</strong>
        </div>
        <div className="bz-preview-card">
          <p>Čeká na potvrzení</p>
          <strong>3</strong>
        </div>
        <div className="bz-preview-card green">
          <p>Bez kolize</p>
          <strong>OK</strong>
        </div>
        <div className="bz-preview-calendar">
          <span>PO</span><span>ÚT</span><span>ST</span><span>ČT</span><span>PÁ</span>
          <b className="event one">Seznamte se!</b>
          <b className="event two">Výtvarná dílna</b>
        </div>
      </div>
    </div>
  </div>
);

export const HomePage = () => {
  return (
    <>
      <Header />
      <main className="homepage-redesign">
        <section className="bz-hero" style={{ '--bz-hero-image': `url(${HERO_IMAGE})` }}>
          <div className="bz-hero-media" aria-hidden="true" />
          <div className="bz-hero-overlay" />
          <div className="bz-container bz-hero-content">
            <p className="bz-eyebrow">Rezervační systém pro kulturní instituce</p>
            <h1>Bude živo pomáhá školám najít termín a vašemu týmu udržet klid v provozu.</h1>
            <p className="bz-hero-copy">
              Jeden veřejný odkaz pro rezervace, jeden přehled pro tým a méně ruční administrativy kolem programů, akcí, škol a kampaní.
            </p>
            <div className="bz-hero-actions">
              <DemoDialog>
                <button type="button" className="bz-primary-button">Domluvit online ukázku</button>
              </DemoDialog>
              <a href="/booking/demo" className="bz-secondary-button">Vyzkoušet demo rezervaci</a>
            </div>
            <div className="bz-hero-proof" aria-label="Hlavní přínosy">
              <span><Check size={18} /> Rezervace bez registrace školy</span>
              <span><Check size={18} /> Kolize, kapacity a role týmu</span>
              <span><Check size={18} /> Mailing a přehled výsledků</span>
            </div>
          </div>
        </section>

        <section className="bz-preview-section" aria-label="Náhled systému">
          <div className="bz-container bz-preview-layout">
            <div>
              <p className="bz-eyebrow dark">Místo tabulek a e-mailových vláken</p>
              <h2>Všechno důležité o programu, termínu a škole drží systém pohromadě.</h2>
            </div>
            <ProductPreview />
          </div>
        </section>

        <section id="jak-to-funguje" className="bz-section">
          <div className="bz-container">
            <div className="bz-section-heading">
              <p className="bz-eyebrow dark">Jak to funguje</p>
              <h2>Od zveřejnění programu po potvrzenou rezervaci.</h2>
            </div>
            <div className="bz-how-grid">
              {howSteps.map((step, index) => {
                const Icon = step.icon;
                return (
                  <article className="bz-how-card" key={step.title}>
                    <div className="bz-how-number">{String(index + 1).padStart(2, '0')}</div>
                    <Icon size={28} />
                    <h3>{step.title}</h3>
                    <p>{step.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="funkce" className="bz-section bz-flow-section">
          <div className="bz-container">
            <div className="bz-section-heading centered">
              <p className="bz-eyebrow dark">Co systém umí</p>
              <h2>Od první rezervace po vyhodnocení</h2>
              <p>Bude živo ohlídá a vyřídí provozní kroky, které se jinak ztrácí mezi lidmi, tabulkami a e-maily.</p>
            </div>
            <div className="bz-flow-grid">
              {flowSteps.map((step) => {
                const Icon = step.icon;
                return (
                  <article className="bz-flow-step" key={step.number}>
                    <div className="bz-flow-icon"><Icon size={30} /></div>
                    <span>{step.number}</span>
                    <h3>{step.title}</h3>
                    <p>{step.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="pro-koho" className="bz-section bz-audience-section">
          <div className="bz-container">
            <div className="bz-section-heading">
              <p className="bz-eyebrow dark">Pro koho</p>
              <h2>Pro týmy, které pracují s programy, školami a kapacitou.</h2>
            </div>
            <div className="bz-audience-grid">
              {audienceCards.map((card) => (
                <article className="bz-audience-card" key={card.title}>
                  <h3>{card.title}</h3>
                  <p>{card.text}</p>
                  <ul>
                    {card.items.map((item) => <li key={item}><Check size={17} /> {item}</li>)}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="bz-section bz-benefit-section">
          <div className="bz-container bz-benefit-layout">
            <div>
              <p className="bz-eyebrow dark">Proč teď</p>
              <h2>Pilot má ověřit reálnou úsporu času, ne jen hezké rozhraní.</h2>
              <p>
                Bude živo vzniká z praxe kulturních institucí: školy potřebují rychle rezervovat a tým potřebuje jistotu, že v datech není chaos.
              </p>
            </div>
            <div className="bz-benefit-grid">
              {benefits.map((item) => {
                const Icon = item.icon;
                return (
                  <article key={item.title}>
                    <Icon size={24} />
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="bz-founder-section">
          <div className="bz-container bz-founder-layout">
            <img src={FOUNDER_IMAGE} alt="Daniela Kytlicová, zakladatelka Bude živo" />
            <div>
              <p className="bz-eyebrow dark">Vzniklo z každodenní práce</p>
              <h2>„Cílem není přidat další nástroj. Cílem je ubrat zbytečné ruční kroky.“</h2>
              <p>
                Bude živo stavíme s důrazem na běžný provoz institucí: jasné rezervace, srozumitelné role, bezpečná data a praktické výstupy pro tým i vedení.
              </p>
              <p className="bz-founder-name">Daniela Kytlicová</p>
            </div>
          </div>
        </section>

        <section id="pricing" className="bz-section bz-pricing-section">
          <div className="bz-container">
            <div className="bz-section-heading centered">
              <p className="bz-eyebrow dark">Ceník</p>
              <h2>Začněte jednoduše a rozšiřujte podle provozu.</h2>
            </div>
            <div className="bz-pricing-grid">
              {pricing.map((plan) => (
                <article className={`bz-price-card ${plan.featured ? 'featured' : ''}`} key={plan.name}>
                  {plan.featured && <span className="bz-plan-badge">Doporučeno pro pilot</span>}
                  <h3>{plan.name}</h3>
                  <strong>{plan.price}</strong>
                  <p>{plan.note}</p>
                  <ul>{plan.items.map((item) => <li key={item}><Check size={17} /> {item}</li>)}</ul>
                </article>
              ))}
            </div>
            <div className="bz-pricing-note">
              Platby kartou zajišťuje platební brána <a href="https://www.comgate.cz/cz/platebni-brana" target="_blank" rel="noreferrer">Comgate</a>, pokud se instituce rozhodne placené akce v Bude živo používat.
            </div>
          </div>
        </section>

        <section id="faq" className="bz-section bz-faq-section">
          <div className="bz-container bz-faq-layout">
            <div>
              <p className="bz-eyebrow dark">FAQ</p>
              <h2>Časté otázky před prvním nastavením.</h2>
              <p>Krátké odpovědi pro instituce, které zvažují pilot nebo první provozní test.</p>
            </div>
            <div className="bz-faq-list">
              {faqItems.map((item) => (
                <details key={item.question}>
                  <summary>{item.question}<ChevronDown size={20} /></summary>
                  <p>{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="bz-cta-section">
          <div className="bz-container bz-cta-box">
            <Sparkles size={34} />
            <h2>Připravme první programy tak, aby školy mohly rezervovat bez zbytečného čekání.</h2>
            <p>Online ukázka projde konkrétní provoz vaší instituce: programy, termíny, role, školy a veřejný odkaz.</p>
            <div>
              <DemoDialog>
                <button type="button" className="bz-primary-button light">Domluvit online ukázku</button>
              </DemoDialog>
              <Link to="/register" className="bz-secondary-button light">Vytvořit účet</Link>
            </div>
          </div>
        </section>

        <footer className="bz-footer">
          <div className="bz-container bz-footer-grid">
            <div>
              <div className="bz-footer-brand">Bude živo.cz</div>
              <p>Rezervační a provozní systém pro kulturní instituce, které pracují se školami, programy a týmem.</p>
            </div>
            <div>
              <h3>Produkt</h3>
              <a href="#jak-to-funguje">Jak to funguje</a>
              <a href="#funkce">Co systém umí</a>
              <a href="#pricing">Ceník</a>
            </div>
            <div>
              <h3>Účet</h3>
              <Link to="/login">Přihlášení</Link>
              <Link to="/register">Registrace</Link>
              <Link to="/kontakt">Kontakt</Link>
            </div>
            <div>
              <h3>Právní informace</h3>
              <Link to="/obchodni-podminky">Obchodní podmínky</Link>
              <Link to="/gdpr">Ochrana osobních údajů</Link>
              <Link to="/reklamace">Reklamace</Link>
              <Link to="/platebni-podminky">Platební podmínky</Link>
            </div>
          </div>
          <div className="bz-container bz-footer-bottom">
            <span>© 2026 Bude živo</span>
            <span>Systém pro rezervace, propagaci a vyhodnocení programů.</span>
          </div>
        </footer>
      </main>
    </>
  );
};
