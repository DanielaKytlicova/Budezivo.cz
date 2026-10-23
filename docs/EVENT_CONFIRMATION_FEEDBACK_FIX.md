# Časy akcí a statistiky zpětné vazby — 23. 10. 2026

## Rozsah

- Jednotné formátování termínu v `Europe/Prague` pro potvrzovací e-mail,
  oba PDF endpointy a upomínku k platbě. Začátek i konec, více dnů a změna času.
- Náhradní PDF ponechá termín i při selhání volitelné části.
- Neplatná/ztracená vazba na termín vrací 409, nenahrazuje se prvním termínem.
  Historické přihlášky bez vazby i bez existujících termínů zobrazí výslovné
  „Termín není evidován…“. Bez důkazu nelze odlišit předzápis od smazaného termínu.
- Mazání termínu s přihláškami je zakázané, kontrola je omezena na instituci.
  Vytvoření přihlášky i mazání zamyká řádek termínu, aby kontrolu neobešel souběh.
- Schvalování přihlášek, kapacity, platby a data termínů se nemění.

## Chyba statistik

Původní dotaz kombinoval `count(Feedback.id)` s `select_from(filtered.subquery())`.
Reference na původní model přidala do FROM také celou tabulku feedbacks. Výsledkem
byl kartézský součin; tentýž problém ovlivňoval průměr i procento doporučení.
Souhrny nyní používají pouze sloupce poddotazu omezeného na instituci a filtry.

- `total_feedbacks`: počet skutečně odevzdaných formulářů (`status=submitted`).
- `sent_requests`: počet rezervací se záznamem úspěšného odeslání výzvy nebo
  připomínky (`email_sent_at` / `reminder_sent_at`). Připomínka nepřičítá další výzvu.
  Jde o evidované odeslání, ne potvrzené doručení; chybějící historické záznamy se
  nevymýšlejí a počet odeslaných se neodvozuje z počtu dokončených rezervací.
- Počet hodnocených programů je samostatný agregát, ne délka seznamu TOP 10.
- Souhrny respektují program a datum rezervace. Filtry stavu/minimálního hodnocení
  filtrují jen seznam; UI to uvádí. Hodnota 0 % se zobrazuje jako 0 %, ne pomlčka.

Regresní fixture 19 odpovědí instituce + 130 dalších řádků reprodukuje původní
mechanismus 19 × 149 = 2831; správný výsledek je 19. Není to ověření živých počtů
Severočeského muzea. Přímé DB připojení nebylo nakonfigurováno, produkce se nečetla
ani neměnila. Po nasazení se počty přepočítají z existujících záznamů.

## Ověření

- 36 unit/regresních testů: reálné SQL dotazy nad izolovanou SQLite DB, tenantová
  izolace, filtry, odeslané vs. vyplněné, 0 %, více než deset programů, obsah HTML,
  textu a vygenerovaného PDF, letní/zimní čas, oba PDF fallbacky, blokace smazání.
- Testy SQL zvedají SQLAlchemy warning o kartézském součinu na chybu.
- Testy PDF vyžadují `backend/requirements-test.txt` (pypdf). Spouštět s testovacím
  JWT_SECRET a bez produkčního DATABASE_URL. Žádné skutečné e-maily.
- Syntetické PDF vyrenderováno Popplerem a vizuálně zkontrolováno.
- Node 20.20.2, Yarn 1.22.22: lint (0 chyb, 109 warnings), cílený Prettier, build.
  Použito `YARN_IGNORE_ENGINES=1`, protože package.json požaduje Node 24, zatímco
  AGENTS.md stanoví Node 20. Závislosti ani lockfile se neměnily.
- Nebyl proveden souběhový integrační test na PostgreSQL ani živý end-to-end test.
  Zámky byly ověřeny kontrolou generovaného PostgreSQL SQL; SQLite je nesimuluje.

## Před commitem / nasazením

Není potřeba migrace ani hromadná oprava dat. Staré odeslané dokumenty/e-maily
se nezmění; PDF nově stažené po nasazení použije opravený čas. Opravné e-maily
nebyly odeslány a vyžadují samostatné schválení.

Zachovány nesouvisející lokální změny AGENTS.md / dokumentace Supabase a původní
část `backend/scheduler.py`, která zahrnuje i zrušené rezervace do automatického
dokončování. Tato původní změna **nepatří do této opravy**. Ze scheduler.py patří
do commitu pouze formátování termínu v `process_event_payment_reminders`.
Nové soubory v backend/tests jsou v tomto repozitáři ignorované; při autorizovaném
commitu je potřeba cílené `git add -f` pouze pro nové testy tohoto úkolu.

Po nasazení ověřit oba termíny jedné akce v novém e-mailu i PDF a porovnat kartu
„Vyplněné zpětné vazby“ se seznamem vyplněných formulářů za stejné období/program.
Nevytvářet skutečné přihlášky ani neposílat opravné zprávy bez souhlasu.
