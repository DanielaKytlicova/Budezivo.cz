import React, { useRef, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  BellRing,
  CalendarCheck2,
  CalendarDays,
  Check,
  ChevronDown,
  Clock3,
  ContactRound,
  Database,
  FileText,
  Mail,
  Megaphone,
  ShieldCheck,
  Smile,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  Settings2,
} from 'lucide-react';
import { Header } from '../../components/layout/Header';
import './HomePageRedesign.css';

const LOGO_WHITE = 'https://budezivo-redesign.kytlicova-vanilie.chatgpt.site/logo-budezivo-white.svg';
const FOUNDER_IMAGE = 'https://budezivo-redesign.kytlicova-vanilie.chatgpt.site/daniela-kytlicova.png';

const steps = [
  {
    number: '01',
    icon: CalendarDays,
    title: 'Vytvoříte program',
    text: 'Popis, kapacitu a pravidla nastavíte jen jednou.',
  },
  {
    number: '02',
    icon: Settings2,
    title: 'Zpřístupníte termíny',
    text: 'Systém hlídá dostupnost, kapacity i případné kolize.',
  },
  {
    number: '03',
    icon: UserCheck,
    title: 'Škola si rezervuje',
    text: 'Jednoduše online, bez registrace a čekání na potvrzení.',
  },
  {
    number: '04',
    icon: Sparkles,
    title: 'A může být živo',
    text: 'Tým má jasno a může se věnovat programu i návštěvníkům.',
  },
];

const employeeBenefits = [
  {
    icon: Clock3,
    title: 'Méně rutinní administrativy',
    text: 'Rezervace a potvrzení probíhají bez vašeho zásahu.',
  },
  {
    icon: UserCheck,
    title: 'Úspora hodin týdně',
    text: 'Méně přepisování, dohledávání a odpovídání na stejné dotazy.',
  },
  {
    icon: ShieldCheck,
    title: 'Méně chyb a nedorozumění',
    text: 'Kapacity, kolize a pravidla hlídá systém, ne člověk.',
  },
  {
    icon: Smile,
    title: 'Klidnější pracovní den',
    text: 'Žádné urgentní e-maily kvůli informaci, která už je v systému.',
  },
];

const leadershipBenefits = [
  {
    icon: BarChart3,
    title: 'Statistiky a přehledy',
    text: 'Kolik skupin přišlo, odkud a kdy, bez ručního sčítání.',
  },
  {
    icon: FileText,
    title: 'Podklady pro zřizovatele',
    text: 'Data pro výroční zprávy a dotace připravená k exportu.',
  },
  {
    icon: TrendingUp,
    title: 'Lepší plánování kapacit',
    text: 'Vytíženost programů i týmu vidíte s předstihem.',
  },
  {
    icon: Database,
    title: 'Transparentní evidence rezervací',
    text: 'Každá rezervace je dohledatelná a nic se neztratí.',
  },
];

const capabilities = [
  {
    number: '01',
    icon: BellRing,
    eyebrow: 'KOMUNIKACE',
    title: 'Potvrzení i připomenutí odejdou sama',
    text: 'Po rezervaci, změně i před návštěvou dostane pedagog správnou zprávu bez dalšího hlídání.',
  },
  {
    number: '02',
    icon: CalendarCheck2,
    eyebrow: 'PROVOZ',
    title: 'Kolize zachytí dřív, než vzniknou',
    text: 'Systém kontroluje termíny, kapacity, místnosti i dostupnost lektorů.',
  },
  {
    number: '03',
    icon: ShieldCheck,
    eyebrow: 'ROLE A GDPR',
    title: 'Každý vidí jen to, co potřebuje',
    text: 'Správce, lektor, produkce i pokladna mají vlastní oprávnění a pouze nezbytné údaje.',
  },
  {
    number: '04',
    icon: BarChart3,
    eyebrow: 'DATA V REÁLNÉM ČASE',
    title: 'Statistiky bez ručního sčítání',
    text: 'Návštěvnost, vytíženost i původ skupin se průběžně zapisují a jsou připravené k exportu.',
  },
  {
    number: '05',
    icon: ContactRound,
    eyebrow: 'KONTAKTY NA ŠKOLY',
    title: 'Kontakty zůstávají přehledně pohromadě',
    text: 'Školy, pedagogové, štítky i historie komunikace jsou připravené pro další práci.',
  },
  {
    number: '06',
    icon: Megaphone,
    eyebrow: 'PROPAGAČNÍ KAMPANĚ',
    title: 'Nový program rozešlete na pár kliknutí',
    text: 'Bez úmorného posílání po dvaceti adresách. Rozesílku řídí systém a hlídá její doručení.',
  },
];

const plans = [
  {
    name: 'Zdarma',
    price: '0 Kč',
    note: 'navždy',
    items: [
      'Max. 50 rezervací měsíčně',
      'Až 3 aktivní programy',
      'Základní přehled rezervací',
      'E-mailová podpora',
    ],
  },
  {
    name: 'Start',
    price: '490 Kč',
    annualPrice: '4 900 Kč',
    note: '/ měsíčně',
    items: [
      'Až 200 rezervací měsíčně',
      'Až 10 aktivních programů',
      'Kalendář dostupnosti',
      'Vlastní branding a formuláře',
      'E-mailové šablony',
    ],
  },
  {
    name: 'PRO',
    price: '990 Kč',
    annualPrice: '9 900 Kč',
    note: '/ měsíčně',
    popular: true,
    items: [
      'Vše ze Start',
      'Paralelní programy',
      'Pokročilé statistiky a exporty',
      'Mailing na školy',
      'Náhradníci a kolizní systém',
    ],
  },
  {
    name: 'PRO+',
    price: '1 990 Kč',
    annualPrice: '19 900 Kč',
    note: '/ měsíčně',
    items: [
      'Vše z PRO',
      'Události včetně online plateb',
      'Neomezené rezervace',
      'API přístup',
      'Outlook a Google synchronizace',
    ],
  },
];

const faqItems = [
  {
    question: 'Pro koho je Budeživo určené?',
    answer: 'Pro muzea, galerie, knihovny a další kulturní nebo vzdělávací instituce, které organizují programy pro školy, skupiny či veřejnost a potřebují sjednotit rezervace, termíny a práci týmu.',
  },
  {
    question: 'Musí si návštěvník nebo pedagog zakládat účet?',
    answer: 'Ne. Veřejnou rezervaci může vyplnit přímo přes rezervační stránku instituce. Účty slouží pracovníkům instituce pro správu programů, rezervací a interního provozu.',
  },
  {
    question: 'Můžeme si systém nejdřív vyzkoušet?',
    answer: 'Ano. Můžete si projít ukázkovou rezervaci pohledem návštěvníka a následně domluvit online ukázku nebo pilotní nastavení pro svou instituci.',
  },
  {
    question: 'Mohou mít členové týmu rozdílná oprávnění?',
    answer: 'Ano. Správci, lektoři, produkce i pokladna mohou pracovat s rozdílnými rolemi, aby každý viděl a upravoval jen to, co ke své práci potřebuje.',
  },
  {
    question: 'Je propojení s Google Kalendářem nebo Outlookem povinné?',
    answer: 'Není. Kalendáře lze připojit pro úsporu času, ale Budeživo funguje i samostatně. Propojení můžete později odpojit.',
  },
  {
    question: 'Podporuje Budeživo také online platby?',
    answer: 'Ano, u vybraných událostí lze využít online platby přes platební bránu Comgate. Konkrétní možnosti závisí na zvoleném tarifu a nastavení instituce.',
  },
  {
    question: 'Jak funguje měsíční a roční předplatné?',
    answer: 'U placených tarifů si můžete zvolit měsíční platbu nebo zvýhodněnou roční variantu. Při roční platbě odpovídá cena deseti měsíčním platbám, tedy dvěma měsícům zdarma.',
  },
  {
    question: 'Kde najdu podmínky zpracování osobních údajů?',
    answer: 'Odkaz na ochranu osobních údajů, obchodní podmínky, reklamace i platební podmínky najdete v zápatí každé stránky.',
  },
];

function ProductPreview() {
  return (
    <div className="product-preview" aria-label="Ukázka prostředí Budeživo">
      <div className="preview-shell">
        <aside>
          <img src={LOGO_WHITE} alt="" />
          <div className="preview-nav">
            <b>▦ <span>Přehled</span></b>
            <span>▣ <i>Programy</i></span>
            <span>▤ <i>Rezervace</i></span>
            <span className="active">▦ <i>Akce</i></span>
            <span>✉ <i>Propagace</i></span>
            <span>⌄ <i>Správa</i></span>
            <span>⌁ <i>Statistiky</i></span>
            <span>⚙ <i>Nastavení</i></span>
          </div>
          <div className="preview-user">
            <b>Oblastní galerie</b>
            <span>Daniela Kytlicová</span>
            <small>Správce</small>
          </div>
        </aside>
        <div className="preview-content">
          <header>
            <div>
              <small>PONDĚLÍ, 20. ČERVENCE</small>
              <h3>Dobré ráno, Danielo</h3>
            </div>
            <button>+ Nová událost</button>
          </header>
          <div className="preview-stats">
            <article>
              <small>Dnešní návštěvy</small>
              <strong>84</strong>
              <span>↑ 12 % tento měsíc</span>
            </article>
            <article>
              <small>Rezervace tento týden</small>
              <strong>27</strong>
              <span>z 36 dostupných</span>
            </article>
            <article>
              <small>Nejbližší program</small>
              <strong>09:30</strong>
              <span>Kde se vzalo muzeum?</span>
            </article>
          </div>
          <div className="preview-lower">
            <section>
              <div className="preview-heading">
                <b>Dnešní program</b>
                <span>Celý kalendář →</span>
              </div>
              {[
                ['09:30', 'Kde se vzalo muzeum?', 'ZŠ Kaplického · 24 dětí'],
                ['11:00', 'Obraz jako příběh', 'ZŠ Husova · 18 dětí'],
                ['13:30', 'Ateliér všemi smysly', 'MŠ Sluníčko · 16 dětí'],
              ].map((event, index) => (
                <div className="preview-event" key={event[0]}>
                  <time>{event[0]}</time>
                  <i className={`bar bar-${index}`} />
                  <p>
                    <b>{event[1]}</b>
                    <span>{event[2]}</span>
                  </p>
                  <em>{index === 2 ? 'čeká' : 'potvrzeno'}</em>
                </div>
              ))}
            </section>
            <section className="occupancy">
              <b>Obsazenost programů</b>
              <div className="preview-ring">
                <strong>75<small>%</small></strong>
              </div>
              <span>27 z 36 termínů</span>
            </section>
          </div>
        </div>
      </div>
      <div className="float-card reservation">
        <CalendarDays />
        <p><b>Nová rezervace</b><span>ZŠ Lesní · 26 osob</span></p>
        <Check />
      </div>
      <div className="float-card time-back">
        <span>◷</span>
        <p><b>3 hodiny týdně</b><small>zpět pro váš tým</small></p>
      </div>
    </div>
  );
}

function SiteFooter({ onPricing }) {
  const isHome = window.location.pathname === '/';
  const sectionHref = (id) => `${isHome ? '' : '/'}#${id}`;

  return (
    <footer className="site-footer">
      <div className="footer-main">
        <div className="footer-about">
          <a className="brand" href="/">
            <img src={LOGO_WHITE} alt="Budeživo.cz" />
          </a>
          <p>Rezervační systém pro muzea, galerie a knihovny, který zjednodušuje správu školních a skupinových programů.</p>
          <address>
            <strong>Provozovatel</strong>
            <span>Daniela Kytlicová</span>
            <span>IČO: 07407971</span>
            <span>Mlýnská 538</span>
            <a href="mailto:info@budezivo.cz">info@budezivo.cz</a>
          </address>
        </div>
        <div className="footer-column">
          <h3>Budeživo</h3>
          <a href={sectionHref('o-projektu')}>O projektu</a>
          <a href={sectionHref('moznosti')}>Co systém umí</a>
          <a href={sectionHref('cenik-nabidky')} onClick={isHome && onPricing ? onPricing : undefined}>Tarify</a>
          <a href="/kontakt">Kontakt</a>
          <a href="/faq">Často kladené otázky</a>
        </div>
        <div className="footer-column">
          <h3>Účet</h3>
          <a href="/login">Přihlášení</a>
          <a href="https://www.budezivo.cz/register">Registrace</a>
        </div>
        <div className="footer-column">
          <h3>Právní</h3>
          <a href="https://www.budezivo.cz/obchodni-podminky">Obchodní podmínky</a>
          <a href="https://www.budezivo.cz/gdpr">Ochrana osobních údajů</a>
          <a href="https://www.budezivo.cz/reklamace">Reklamace a storno</a>
          <a href="https://www.budezivo.cz/platebni-podminky">Platební podmínky</a>
        </div>
      </div>
      <div className="footer-bottom">
        <div className="payments">
          <span>AKCEPTUJEME ONLINE PLATBY PŘES</span>
          <div>
            <a className="pay comgate" href="https://www.comgate.cz/cz/platebni-brana" target="_blank" rel="noreferrer">◖ <b>comgate</b></a>
            <span className="pay visa">VISA</span>
            <span className="pay mastercard" aria-label="Mastercard"><i /><i /></span>
          </div>
        </div>
        <small>© 2026 Budeživo.cz. Všechna práva vyhrazena.</small>
      </div>
    </footer>
  );
}

export const HomePage = () => {
  const [pricingOpen, setPricingOpen] = useState(() => window.location.hash === '#cenik-nabidky');
  const [annual, setAnnual] = useState(false);
  const pricingPanelRef = useRef(null);

  const scrollToPricing = () => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        pricingPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  };

  const openPricing = (event) => {
    event?.preventDefault();
    setPricingOpen(true);
    window.history.replaceState(null, '', '#cenik-nabidky');
    scrollToPricing();
  };

  const togglePricing = () => {
    if (pricingOpen) {
      setPricingOpen(false);
      window.history.replaceState(null, '', '#cena');
      return;
    }
    openPricing();
  };

  return (
    <>
      <Header />
      <main className="homepage-v21 homepage">
        <section className="hero photo-hero" id="top">
          <div className="hero-copy">
            <div className="eyebrow"><Sparkles size={15} /> Bude živo · pro kulturní instituce</div>
            <h1>Méně administrativy.<br />Více prostoru pro <em>kreativitu.</em></h1>
            <p className="lead">Online rezervace programů, termíny, dostupnost lektorů i komunikace se školami přehledně na jednom místě.</p>
            <div className="hero-actions">
              <a className="button beige" href="https://www.budezivo.cz/booking/demo">Vyzkoušet demo rezervaci <ArrowRight size={18} /></a>
              <a className="outline-button" href="/kontakt">Domluvit online ukázku</a>
            </div>
            <div className="trust">
              <span><Check /> Bez instalace</span>
              <span><Check /> Česká podpora</span>
              <span><Check /> GDPR a bezpečná data</span>
            </div>
          </div>
        </section>

        <section className="price reveal" id="cena">
          <div className="price-intro">
            <span>CENA, KTERÁ DÁVÁ SMYSL</span>
            <h2>Začněte jednoduše. Rozšiřujte až ve chvíli, kdy systém opravdu šetří čas.</h2>
            <p>Úvodní stránka ukazuje celý tarifní rámec. Detail cen si může instituce rozbalit až tehdy, když ho potřebuje.</p>
            <button type="button" className="button" onClick={togglePricing}>{pricingOpen ? 'Skrýt tarify' : 'Zobrazit tarify'} <ChevronDown size={18} /></button>
          </div>
          {pricingOpen && (
            <div className="pricing-panel" id="cenik-nabidky" ref={pricingPanelRef}>
              <div className="billing-toggle" aria-label="Přepínač měsíčního a ročního předplatného">
                <button className={!annual ? 'active' : ''} type="button" onClick={() => setAnnual(false)}>Měsíčně</button>
                <button className={annual ? 'active' : ''} type="button" onClick={() => setAnnual(true)}>Ročně <span>2 měsíce zdarma</span></button>
              </div>
              <div className="plans">
                {plans.map((plan) => (
                  <article key={plan.name} className={plan.popular ? 'plan popular' : 'plan'}>
                    {plan.popular && <div className="badge">Nejčastější volba</div>}
                    <h3>{plan.name}</h3>
                    <p className="plan-price">{annual && plan.annualPrice ? plan.annualPrice : plan.price}<small>{annual && plan.annualPrice ? ' / ročně' : plan.note}</small></p>
                    <ul>
                      {plan.items.map((item) => <li key={item}><Check size={17} /> {item}</li>)}
                    </ul>
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="how" id="jak">
          <div className="sectionhead light">
            <span>OD NABÍDKY K NÁVŠTĚVĚ</span>
            <h2>Čtyři jednoduché kroky.<br />A může být živo.</h2>
          </div>
          <div className="journey-steps">
            {steps.map(({ number, icon: Icon, title, text }) => (
              <article key={number}>
                <div className="journey-icon"><Icon aria-hidden="true" /><b>{number}</b></div>
                <div><h3>{title}</h3><p>{text}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section className="benefits" aria-labelledby="benefits-title">
          <div className="benefits-heading">
            <span>JEDEN SYSTÉM, DVA DRUHY ÚLEVY</span>
            <h2 id="benefits-title">Méně provozní zátěže.<br />Více jistoty pro celou instituci.</h2>
            <p>Budeživo pomáhá lidem, kteří programy každý den zajišťují, i vedení, které potřebuje spolehlivá data pro rozhodování.</p>
          </div>
          <div className="benefits-split">
            <div className="benefit-side employee-side">
              <span>PRO TÝM</span>
              <h3>Úleva pro zaměstnance</h3>
              <div className="benefit-list">
                {employeeBenefits.map(({ icon: Icon, title, text }) => (
                  <article key={title}><div className="benefit-icon"><Icon aria-hidden="true" /></div><div><h4>{title}</h4><p>{text}</p></div></article>
                ))}
              </div>
            </div>
            <div className="benefit-side leadership-side">
              <span>PRO VEDENÍ</span>
              <h3>Přínos pro vedení</h3>
              <div className="benefit-list">
                {leadershipBenefits.map(({ icon: Icon, title, text }) => (
                  <article key={title}><div className="benefit-icon"><Icon aria-hidden="true" /></div><div><h4>{title}</h4><p>{text}</p></div></article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="brand-statement" id="funkce">
          <div>
            <span>VÍCE NEŽ REZERVAČNÍ SYSTÉM</span>
            <h2>Není to jen další software. Je to klidnější provoz pro instituce, které chtějí mít plnější programy a méně chaosu okolo nich.</h2>
          </div>
        </section>

        <section className="capabilities" id="moznosti">
          <div className="capabilities-heading">
            <div>
              <span>CO SYSTÉM OHLÍDÁ</span>
              <h2>Co za vás Budeživo <em>ohlídá a vyřídí.</em></h2>
            </div>
            <p>Od rezervace školy přes interní role až po mailing a vyhodnocení. Bez přeskakování mezi tabulkami, kalendářem a e-mailovou schránkou.</p>
          </div>
          <div className="capabilities-path">
            {capabilities.map(({ number, icon: Icon, eyebrow, title, text }) => (
              <article className="capability-step" key={number}>
                <div className="capability-icon"><Icon aria-hidden="true" /><i /></div>
                <div className="capability-copy">
                  <b>{number}</b>
                  <span>{eyebrow}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="capabilities-note">
            <Sparkles aria-hidden="true" />
            <p><strong>Systém nevymýšlí nový provoz.</strong> Pomáhá dostat ten stávající do podoby, kterou tým zvládne udržet i ve špičce.</p>
          </div>
        </section>

        <section className="origin" id="o-projektu">
          <div className="origin-kicker">
            <span>VZNIKLO PŘÍMO V PRAXI</span>
            <div className="founder-photo">
              <img src={FOUNDER_IMAGE} alt="Daniela Kytlicová, zakladatelka Budeživo" />
              <div className="years"><strong>7+</strong><small>let praxe<br />v edukaci</small></div>
              <div><strong>MgA. Daniela Kytlicová</strong><small>Zakladatelka Budeživo<br />produktová designérka a edukátorka</small></div>
            </div>
          </div>
          <div className="origin-copy">
            <h2>Navržené někým, kdo zná kulturní provoz zevnitř.</h2>
            <p>Budeživo vzniká z praktické zkušenosti s organizací vzdělávacích programů, komunikací se školami a každodenní administrativou kulturních institucí.</p>
            <p>Není postavené jako obecný rezervační kalendář. Je navržené pro situace, kdy se potkává kapacita, termín, lektor, skupina, kontaktní osoba a potřeba mít všechno dohledatelné.</p>
          </div>
        </section>

        <section className="integrations" aria-labelledby="integration-title">
          <div className="copy">
            <span>PROPOJENÍ, KTERÁ ŠETŘÍ PŘEPISOVÁNÍ</span>
            <h2 id="integration-title">Kalendář už máte. Budeživo s ním umí spolupracovat.</h2>
            <p>Termíny a rezervace se mohou promítat do Google Kalendáře i Outlooku, takže tým nemusí kontrolovat několik míst najednou.</p>
          </div>
          <div className="calendar-visual" aria-hidden="true">
            <div className="calendar-top"><b>Srpen 2026</b><span>Google / Outlook</span></div>
            <div className="calendar-grid">
              {['Po', 'Út', 'St', 'Čt', 'Pá'].map((day) => <strong key={day}>{day}</strong>)}
              {Array.from({ length: 15 }).map((_, index) => <i key={index} className={index === 6 || index === 8 || index === 12 ? 'busy' : ''} />)}
            </div>
          </div>
        </section>

        <section className="product-showcase" aria-label="Ukázka systému">
          <ProductPreview />
        </section>

        <section className="faq-section" id="faq">
          <div className="sectionhead">
            <span>ČASTÉ DOTAZY</span>
            <h2>Co si instituce obvykle potřebuje ujasnit před pilotem?</h2>
          </div>
          <div className="faq-list">
            {faqItems.map((item) => (
              <details key={item.question}>
                <summary>{item.question}<ChevronDown size={20} /></summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="demo-cta">
          <span>CHCETE VIDĚT, JAK BY TO VYPADALO U VÁS?</span>
          <h2>Domluvme krátkou ukázku nad konkrétním provozem vaší instituce.</h2>
          <p>Projít můžeme programy, veřejnou rezervaci, kalendář, role týmu i mailing na školy.</p>
          <a className="button beige" href="/kontakt">Domluvit online ukázku <ArrowRight size={18} /></a>
        </section>

        <SiteFooter onPricing={openPricing} />
      </main>
    </>
  );
};
