# Ověření interního CRM – 11. 10. 2026

## Implementace

Větev `codex/admin-leads-crm`, PR #258. Backend a UI jsou ve dvou oddělených
commitech `a929eafa` a `992fafa6`. Nesouvisející lokální úprava `backend/scheduler.py`
není součástí změny ani nasazení.

## Automatické a prohlížečové kontroly

- 41 cílených backendových testů prošlo: CRM, rotace JWT, core/role isolation,
  public booking guards/transaction lock/CORS a program booking options.
- Všech 10 CRM integračních testů prošlo také na PostgreSQL ve vlastních
  dočasných schématech; bez čtení produkčních záznamů.
- Migrace ověřena dvakrát v jedné vrácené PostgreSQL transakci: 7 RLS tabulek,
  čtyři výchozí cíle, opakovaný upgrade bez chyby.
- Frontend: Node 20 + Yarn 1.22.22, lint bez chyb (109 existujících varování),
  cílená kontrola Prettieru a produkční build úspěšné. Instalované package engines
  vyžadují Node 24, proto byl pro požadovaný Node 20 použit YARN_IGNORE_ENGINES.
- Chrome nad lokálním produkčním buildem a skutečným CRM routerem: přihlášení,
  42 institucí, poznámka po reloadu, filtr 4 připojených, Moje leady, pipeline,
  vytvoření spolupracovníka superadminem. Rozměry 1440, 820 a 390 px bez
  horizontálního přetečení; desktop a mobil vizuálně zkontrolovány.
- GitHub Gitleaks a Vercel build prošly.

Lokální prohlížečová fixture vracela HTML také pro nepřítomný externí skript
Vercel insights. Tato známá chyba fixture byla při vyhodnocení oddělena od CRM;
nelze ji vydávat za test analytiky. Otevření hostovaného preview v uživatelově
Chrome zablokovalo bezpečnostní upozornění. Nebylo obejito.

## Izolovaný staging

Railway environment `crm-staging`, samostatný PostgreSQL a služba `crm-api`.
Produkční integrační tajemství se do něj nekopírovala.
Backend: https://crm-api-crm-staging.up.railway.app
Frontend: https://budezivo-cz-git-codex-admin-l-ee0518-danielakytlicovas-projects.vercel.app/admin/leady
Proměnná REACT_APP_BACKEND_URL je na Vercelu omezena na tuto preview větev.

Po úplném Alembic upgrade a importu prošlo:

- 7 core databázových a 10 role-isolation kontrol původních regresních skriptů;
- skutečné HTTP přihlášení superadmina i institucionálního admina, `/auth/me`,
  seznam programů a rezervací;
- anonymní přístup odmítnut, institucionální účet odmítnut CRM;
- interní login, všechna data, zákaz přístupu interního JWT do tenant API;
- povolená editace přiděleného leadu a zákaz nepřidělené editace;
- uložená poznámka a kontakt, správný autor auditu, aktivita a filtry;
- neveřejný export, zákaz exportu spolupracovníkovi, no-store;
- jednorázovost obnovovacího tokenu, okamžité odvolání po deaktivaci a odhlášení.

Staging odkryl historickou neúplnost původních migrací: `onboarding_completed`
a osm existujících modelových tabulek. Pro regresní fixture byly doplněny pouze
v testovací databázi pod verzí `crm_fixture_20261011`. Produkční schéma se tímto
krokem neměnilo. Původní seed také obsahoval e-maily na `.test` odmítané EmailStr
a NULL anglické názvy programů; HTTP fixture používá platné syntetické hodnoty.
Tato zjištění nejsou změnou CRM a doporučuje se samostatně sjednotit historický
baseline. Syntetické CRM záznamy jsou po testu archivované, účty jsou jen stagingové.

## Kontrola importu

Zdroj: 42 institucí, úplných 7 D1 overrides, bez stránkování či zkrácení.
Opakované načtení D1 před produkční přípravou potvrdilo stejných 7 hodnot.
SHA-256 sloučeného vstupního snapshotu:
`7d230731e779740974b9b9f6b9bee3ae3f0f4b01271917e29d34f2ca53869f38`.

| Kontrola | Očekáváno / ověřeno na stagingu |
|---|---:|
| Instituce | 42 |
| Připojené | 4 |
| Platící | 0 |
| Interní poznámky | 5 |
| Vyplněný kontakt včetně pozice | 42 |
| Kontakt navázán / probíhá jednání | 2 |
| Neobchodní / pouze katalog | 7 |
| Odmítli | 4 |
| Připojeno – aktivně používá | 4 |
| Připraveno k oslovení | 16 |
| Rozhodnutí odloženo | 1 |
| Výzkum / ověřit | 8 |

Porovnána všechna normalizovaná pole, ne pouze součty. BZ-0001 (Praha), BZ-0024
(Liberec) a BZ-0026 (Liberec) odpovídají zdroji. Druhý import vložil 0 řádků a
potvrdil shodu. Zdrojové kontakty, poznámky ani hesla nejsou v repozitáři.

## Produkce a rollback

Produkční krok se provádí až po výše uvedených kontrolách. Výsledek nasazení a
produkčního importu bude doplněn po dokončení. Rollback aplikace vrací předchozí
commit `14d9a34d5ac7072c9558664f998e91b73f9badf8`; CRM tabulky a audit se nemažou.
Původní Lead Map zůstává beze změny. Podrobný postup je v README.md.
