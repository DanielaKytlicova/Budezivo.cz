# Interní CRM /admin/leady

## Architektura a izolace

React používá stávající AdminLayout, skutečné logo, Inter a UI komponenty. Mapa
používá nainstalovaný Leaflet a veřejné OSM dlaždice, bez mapového klíče.
Backend `/api/leads` je jediný přístup k CRM; klient nevolá Supabase REST.

Tabulka `users` má povinnou vazbu na instituci a historický CHECK institucionálních
rolí. Interní spolupracovníci proto používají `lead_accounts` bez tenantové vazby.
Toto rozhodnutí nezavádí jinou kryptografii: sdílí bcrypt, JWT klíče/rotaci,
15minutovou platnost tokenu a hashování náhodných obnovovacích tokenů platformy.
JWT má `account_type=leads`, který existující `get_current_user` odmítá.
Superadmin používá běžné přihlášení; CRM ověřuje jeho aktuální záznam v `users`,
aktivitu a existující `SUPERADMIN_EMAILS`. Impersonace nemá CRM přístup.

Interní relace trvá nejvýše 8 hodin, při obnově rotuje náhodný token. Každé API
volání ověřuje relaci a aktivní účet v databázi. Deaktivace, reset hesla a
odhlášení relace odvolávají. Tokeny jsou v sessionStorage konkrétního panelu,
nikoli v URL. CRM bearer má přednost před případným institucionálním cookie.
Přihlášení omezuje stávající SlowAPI (5 pokusů/min/IP). Nasazení s více workery
vyžaduje sdílené úložiště limiteru, stejně jako existující autentizace.

Všichni spolupracovníci čtou všechny leady, kontakty, aktivity a historii.
Úpravy/aktivity dovoluje backend jen aktuálně přiřazenému aktivnímu pracovníkovi.
Superadmin spravuje tým, přiřazení, archivaci, cíle a CSV export. Změny leadů drží
řádkový zámek; verze brání přepsání souběžné editace. Audit vzniká ve stejné
transakci, zachovává jednotlivá pole i staré/nové hodnoty a neobsahuje hesla.
Heslo má minimálně 12 znaků a nejvýše 72 UTF-8 bajtů (bcrypt).

RLS je zapnuté na všech sedmi nových tabulkách, bez veřejných politik. `PUBLIC`,
`anon` a `authenticated` nemají oprávnění. Přístup je pouze důvěryhodným backendovým
DB účtem (vlastník/BYPASSRLS) a serverovými kontrolami. CRM odpovědi mají no-store;
WAF a uvicorn access log nesmějí vypisovat těla ani vyhledávané CRM hodnoty.

## Schéma a migrace

`1a2b3c4d5e6f_internal_leads_crm.py` navazuje na `0f9e8d7c6b5a`.
Vytváří `lead_accounts`, `lead_sessions`, `leads`, `lead_contacts`,
`lead_activities`, `lead_audit`, `lead_goals`. Nemění stávající tabulky, rezervace,
platby, přihlášení institucí ani startupové ALTER TABLE. Čtyři cíle jsou v DB.

Aplikovat běžným postupem z backendu: `alembic upgrade head`.
Nejsou potřeba nové produkční proměnné; používá se DATABASE_URL a JWT_SECRET.

## Inventář a import původní mapy

Zdrojový Site: `appgprj_6aabcdc883608191a36d7863031c0dd9`, verze 3,
zdrojový commit `cee7ad709c0c5d2bf4033c0f04413279e6fb4176`.
Základ `app/institutions.json` má 42 záznamů. D1 binding `DB`, tabulka
`institution_overrides`, má v exportu z 11. 10. 2026 sedm záznamů.

Zachována jsou všechna původní pole (včetně activity, relationship, variant FREE,
kontaktních údajů a přesnosti polohy), 12 funnel stavů, filtry, šest skupin
pipeline, nabídka programů, poznámky a výpočty připojených/platících institucí.
Původní základ a override zůstávají navíc v neveřejném `legacy_snapshot`.
D1 neobsahuje dřívější historii jednotlivých editací; nelze ji zpětně vytvořit.
Audit začíná importem; původní updated_at/updated_by zůstávají ve snapshotu.

Export pořizujte přes Sites read_database_overview a read_database_table_rows.
Použijte přesné vrácené názvy, pokračujte pouze přes next_offset. Výsledný JSON:
`{"rows":[...],"has_more":false,"model_projection":{"truncated":false,
"truncated_values":0,"omitted_columns":0,"omitted_rows":0,"next_offset":null}}`.
Po stránkování spojte všechny řádky; has_more=false platí až po úplném exportu.
Exporty s kontakty a poznámkami nikdy necommitujte.

```sh
PYTHONPATH=backend python backend/scripts/import_leads.py \
  --seed /private/path/institutions.json \
  --overrides /private/path/overrides.json \
  --report /private/path/dry-run-report.json
# Po validaci a ověření cílové DATABASE_URL:
PYTHONPATH=backend python backend/scripts/import_leads.py \
  --seed /private/path/institutions.json \
  --overrides /private/path/overrides.json \
  --report /private/path/import-report.json --apply
```

Import odmítá neúplný/krácený export, duplicity, osiřelé overrides a neplatná pole.
Prázdný override je skutečná uživatelská změna, nepřeskakuje se. Čtyři aliasy
kontakt/pozice/další krok/program URL zachovávají původní null-coalescing.
Opakovaný shodný import je no-op. Změněný zdroj nebo novější CRM úpravy se nikdy
nepřepíší automaticky. Celá dávka je atomická, importéry serializuje advisory lock.
Report porovná veškeré normalizované hodnoty, počty stavů, poznámky a kontakty,
a kontrolní BZ-0001 (Praha), BZ-0024/BZ-0026 (Liberec), bez obsahu kontaktů.

## Cíle

Připojené = tři stavy začínající „Připojeno“. Platící = přesně „Připojeno – platící“.
Klastr omezuje totožný výpočet. Programy = součet `catalog_programs` u připojených.
Import předvyplní ověřený počet jen z přesného celého čísla. Odhady jako „4+“ nebo
„desítky“ zůstávají v `programs`; pro cíl se svévolně nepřevádějí na přesný počet.
Archivované záznamy jsou ze všech cílů vyloučené. Výchozí termín 31. 1. 2027.

## Rollback

Vraťte backend/frontend na předchozí ověřený commit. Nové CRM tabulky, RLS a data
ponechte. Downgrade migrace úmyslně nemaže tabulky ani audit; opětovný upgrade
je idempotentní. Původní Site nebyl odstraněn ani upraven a zůstává zdrojem pro
kontrolu. Po zahájení práce v CRM už starý Site není úplnou zálohou nových změn;
před návratem vytvořte neveřejný DB backup/export.

## Ověření

Integrační testy: `PYTHONPATH=backend python -m pytest backend/tests/test_leads_crm.py`.
Lokální testovací prostředí potřebuje navíc aiosqlite; produkční závislosti se nemění.
Volitelné `LEADS_TEST_POSTGRES` spustí stejné testy ve vlastních náhodných schématech,
bez čtení produkčních dat, s odstraněním těchto testovacích schémat po skončení.
Nikdy tuto proměnnou neukládejte do repozitáře.

Konkrétní výsledky, publikované adresy a migrační stav jsou v předávacím reportu.
