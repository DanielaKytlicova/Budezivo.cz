/**
 * Steps for the Program editor guided tour.
 * Order = display order. Tabs auto-switch via ProgramTour's onTabChange callback.
 *
 * Note: targetTestId must exist as `data-testid` somewhere on the page —
 * if missing, the spotlight is hidden and the card centers itself.
 */
export const PROGRAM_TOUR_STEPS = [
  // ── Detail tab ──
  {
    tab: 'detail',
    targetTestId: 'program-tab-detail',
    title: 'Vítejte v editoru programu',
    body:
      'Provedu vás čtyřmi částmi:\n\n' +
      '1) Detail — co program je\n' +
      '2) Nastavení — kdy se koná\n' +
      '3) Kolize — co s ním nesmí běžet souběžně\n' +
      '4) Zpětná vazba — jak ji vybírat\n\n' +
      'Ukázku můžete kdykoli zavřít a později spustit znovu tlačítkem „Spustit ukázku".',
    placement: 'bottom',
  },
  {
    tab: 'detail',
    targetTestId: 'program-name-cs',
    title: 'Název programu',
    body:
      'Hlavní název, který uvidí učitelé při výběru programu na rezervační stránce. Pište stručně a srozumitelně — např. „Procházka galerií pro MŠ".',
  },
  {
    tab: 'detail',
    targetTestId: 'program-description-cs',
    title: 'Popis programu',
    body:
      'Krátký odstavec (2–4 věty), který popíše obsah a co si účastníci odnesou. Tento text se zobrazí na rezervační stránce a v potvrzovacím e-mailu.',
  },
  {
    tab: 'detail',
    targetTestId: 'target-group-ms_3_6',
    title: 'Cílové skupiny',
    body:
      'Vyberte všechny věkové kategorie, pro které je program vhodný. Můžete zaškrtnout více najednou (např. MŠ + I. stupeň). Slouží také pro filtrování v katalogu „Programy pro školy".',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-duration',
    title: 'Doba trvání',
    body:
      'V minutách. Systém podle této hodnoty automaticky vypočítá konec rezervovaného slotu a hlídá kolize s navazujícími programy.',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-max-capacity',
    title: 'Maximální kapacita',
    body:
      'Kolik účastníků se vejde do jedné skupiny. Při překročení se rezervace automaticky odmítne nebo přesune na hlídání volného termínu (waitlist).',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-pricing-info',
    title: 'Cena pro účastníky',
    body:
      'Volný text, např. „30,- Kč / dítě, pedagog zdarma" nebo „zdarma". Zobrazuje se na rezervační stránce vedle názvu programu i v e-mailovém potvrzení.',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-photo-card',
    title: 'Fotografie programu',
    body:
      'Volitelná hlavní fotka — zobrazí se v záhlaví rezervační stránky a zvyšuje konverzi až o desítky procent. (Funkce může být omezena vaším tarifem.)',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-is-published',
    title: 'Publikace',
    body:
      'Pokud je vypnuto, program je viditelný jen pro váš tým — školy ho nemohou rezervovat. Hodí se pro koncepty nebo sezónní pauzu.',
    placement: 'top',
  },
  {
    tab: 'detail',
    targetTestId: 'program-is-in-catalog',
    title: 'Veřejný katalog',
    body:
      'Volitelně se program objeví v katalogu „Programy pro školy" na adrese /programy-pro-skoly. Učitelé vás tam najdou i bez znalosti přímého odkazu.',
    placement: 'top',
  },

  // ── Settings tab (časy & dny) ──
  {
    tab: 'settings',
    targetTestId: 'program-tab-settings',
    title: 'Záložka Nastavení',
    body:
      'Tady určíte, kdy se program reálně koná: jaké dny v týdnu, v jakou hodinu a po jakou dobu (od–do).',
    placement: 'bottom',
  },
  {
    tab: 'settings',
    targetTestId: 'program-day-monday',
    title: 'Dny v týdnu',
    body:
      'Zaškrtněte dny, ve kterých program běží. Pro každý zaškrtnutý den pak níže přidáte konkrétní časové bloky (např. 9:00–10:30).',
    placement: 'bottom',
  },
  {
    tab: 'settings',
    targetTestId: 'program-add-time-block',
    title: 'Časové bloky',
    body:
      'Přidejte jeden nebo více intervalů (např. 9:00–10:30 a 11:00–12:30). Systém automaticky rozseká delší bloky podle doby trvání programu, takže se učitelům nabídne každý dostupný slot.',
    placement: 'top',
  },
  {
    tab: 'settings',
    targetTestId: 'program-start-date',
    title: 'Sezóna',
    body:
      'Volitelně omezte, kdy se program nabízí (např. jen školní rok). Mimo toto období bude rezervační stránka prázdná, ale program zůstane v editoru.',
    placement: 'top',
  },
  {
    tab: 'settings',
    targetTestId: 'program-min-days-before',
    title: 'Minimální/maximální předstih',
    body:
      'Bránice proti rezervaci „na zítra" (min) a oknu na příliš vzdálená data (max). Doporučujeme min 7, max 180 dní.',
    placement: 'top',
  },

  // ── Collision tab ──
  {
    tab: 'collision',
    targetTestId: 'program-tab-collision',
    title: 'Záložka Kolize',
    body:
      'Některé programy se nemohou konat souběžně — sdílejí lektora, místnost nebo exponáty. Tady určíte pravidla.',
    placement: 'bottom',
  },

  // ── Feedback tab ──
  {
    tab: 'feedback',
    targetTestId: 'program-tab-feedback',
    title: 'Záložka Zpětná vazba',
    body:
      'Po dokončení programu může systém automaticky odeslat dotazník. Můžete použít výchozí (hvězdičky + doporučení) nebo přidat vlastní otázky.\n\nTímto ukázku ukončíme — držíme palce s prvním programem!',
    placement: 'bottom',
  },
];

/** Per-field tooltip texts (for the small `(i)` icons next to labels). */
export const PROGRAM_FIELD_HELP = {
  name_cs:
    'Hlavní viditelný název. Učitelé ho vidí při výběru programu — pište stručně.',
  description_cs:
    'Krátký popis (2–4 věty) zobrazený na rezervační stránce a v potvrzovacím e-mailu.',
  target_groups:
    'Pro koho je program vhodný. Lze zaškrtnout více skupin — využije se i v katalogu pro filtrování.',
  duration:
    'Délka jednoho průběhu programu v minutách. Systém z toho odvodí konec slotu a hlídá kolize.',
  max_capacity:
    'Maximální počet účastníků v jedné skupině. Při překročení se rezervace odmítne nebo dá na waitlist.',
  min_capacity:
    'Pod tímto počtem se program konat nemusí (informativní — školy uvidí poznámku).',
  pricing_info:
    'Volný text, např. „30 Kč / dítě, pedagog zdarma" nebo „Zdarma". Zobrazí se na rezervační stránce.',
  photo:
    'Hlavní fotka programu. Volitelná, ale výrazně zvyšuje míru rezervací. Maximum 5 MB.',
  requires_approval:
    'Pokud zapnuto, rezervace nejdou rovnou „potvrzeno", ale čekají na vaše schválení.',
  is_published:
    'Pokud vypnuto, program je viditelný jen pro váš tým. Hodí se pro koncepty.',
  is_in_catalog:
    'Pokud zapnuto, program se objeví v centrálním katalogu na /programy-pro-skoly.',
  email_notification:
    'Pošleme vám e-mail při každé nové rezervaci. Vypnete-li, najdete je vždy v záložce Rezervace.',
  status:
    'Aktivní = plně v provozu. Koncept = ladíte, není vidět veřejně. Archivováno = ukončeno.',
  days:
    'Dny v týdnu, ve kterých program běží. Pro každý den pak přidáte časové bloky.',
  time_blocks:
    'Časová okna (např. 9:00–10:30). Delší okno se automaticky rozdělí na sloty podle doby trvání programu.',
  date_range:
    'Volitelně omezte sezónu. Mimo toto období program nebude rezervovatelný.',
  min_days_before:
    'Kolik dní předem se nejdříve dá rezervovat. Bránice proti „na zítra" rezervacím. Doporučujeme 7.',
  max_days_before:
    'Jak daleko do budoucna lze rezervovat. Doporučujeme 180 (cca půl roku).',
  preparation_time:
    'Doba na přípravu před programem. Systém ji počítá při kontrole kolizí.',
  cleanup_time:
    'Doba na úklid po programu. Mezi dvěma navazujícími rezervacemi musí být alespoň tato pauza.',
};
