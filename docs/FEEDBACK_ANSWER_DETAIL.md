# Detail odpovědí na zpětnou vazbu

## Chování

- V přehledu má každý vyplněný dotazník tlačítko **Zobrazit odpovědi**. Detail
  obsahuje školu, program, datum návštěvy a vyplnění, hodnocení, doporučení,
  celý komentář a vlastní otázky instituce i programu. Dlouhý detail lze posouvat.
- Tabulka označuje **Obsahuje komentář**. Prázdná odpověď je Nezodpovězeno,
  boolean false je Ne, nikoli prázdná hodnota. Text je vykreslen jako text, ne HTML.
- Souhrny rozlišují **Vyplněné dotazníky**, **Odeslané výzvy** a **Různé programy
  s odpovědí**. Více dotazníků k jednomu programu zvyšuje pouze první počet.
- Detail vyžaduje stávající oprávnění admin/edukátor a institucionální rozsah
  zpětné vazby i rezervace. Cizí program nesmí poskytnout znění otázek.

## Historie otázek

Nový nullable sloupec `feedbacks.questions_snapshot` uchovává ID, přesné znění,
typ, povinnost a zdroj otázek. Poprvé se uloží při otevření veřejného formuláře,
ještě před jeho zobrazením. Další otevření a odeslání používá tutéž verzi, i když
mezitím administrátor otázku změní nebo deaktivuje. Platná je také prázdná sada.
GET a POST zamykají řádek zpětné vazby v transakci. Znovu odeslaný formulář se
nepřepisuje. POST odmítá ID otázek, která do této sady nepatří.

Staré vyplněné dotazníky zůstávají beze změny, snapshot se jim zpětně nevymýšlí.
Detail upozorní, že znění je současné a mohlo se změnit. Pokud otázka již není
dohledatelná, zobrazí uloženou odpověď i ID s označením chybějícího znění.
Nově přidané otázky nejsou u historických dotazníků vydávány za nezodpovězené.

Formulář otevřený ještě před nasazením může při odeslání dostat 409 s pokynem
k obnovení stránky; bez uloženého znění se odpověď nespojí s domnělou verzí otázky.

## Nasazení a rollback

1. Před spuštěním nové verze backendu aplikovat běžnou Alembic migraci
   `2b3c4d5e6f70` navazující na `1a2b3c4d5e6f`. V historii zůstává jediný head.
2. Migrace pouze přidává nullable JSON sloupec; nemaže ani nepřepisuje data,
   nemění role, RLS ani Supabase Data API oprávnění a nevytváří nové tabulky.
3. Nasadit backend i frontend. Přes starý backend není nový detail kompletní.
4. Při návratu aplikace zachovat sloupec i snapshoty; downgrade je záměrně
   nedestruktivní a opakovaný upgrade idempotentní. Starý kód ochranu verzí
   nezná: pokud by během rollbacku pokračovalo vyplňování a úpravy otázek,
   nezaručuje shodu znění. Preferovat dopřednou opravu, případně během návratu
   pozastavit tento tok samostatně schváleným provozním postupem.

## Ověření

- 16 backend testů: historie, prázdná sada, legacy/missing otázky, tenantové
  podmínky a role, opakované odeslání, reálný SQLite roundtrip snapshotu/odpovědí
  i předchozí regresní testy agregací statistik.
- 6 frontend testů: celý komentář a otázky, false/prázdné odpovědi, bezpečné
  vykreslení textu, legacy upozornění, chyba a opakování načtení, ochrana před
  opožděnou odpovědí předchozího detailu, zavřený dialog bez API požadavku;
  starý backend není vydáván za prázdný dotazník.
- Node 20.20.2, Yarn 1.22.22: cílený Prettier, lint (0 chyb, 109 stávajících
  upozornění), produkční build. Existující závislosti, beze změny lockfile.
  Kvůli rozdílu mezi AGENTS (Node 20) a package.json (Node 24) použito
  `YARN_IGNORE_ENGINES=1`, stejně jako u předchozí opravy.
- Jediný Alembic head a offline PostgreSQL SQL migrace ověřeny.
- Nebyl proveden souběhový integrační test na živém PostgreSQL, produkční migrace
  ani živý end-to-end. Nebyly odeslány e-maily ani měněna produkční data.

Po nasazení: otevřít starší odpověď s komentářem; na testovacím formuláři ověřit
otázky instituce/programu a Ne; změnit znění až po otevření formuláře a ověřit,
že detail po odeslání obsahuje původní znění. Nepoužívat skutečné adresáty pro test.
