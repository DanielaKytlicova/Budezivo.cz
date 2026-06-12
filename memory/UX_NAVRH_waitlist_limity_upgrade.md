# UX návrh — Waitlist událostí, Využití tarifů, Upgrade výzvy
_Stav k 12. 6. 2026. Základní verze všech tří už NASAZENA a otestována; níže je návrh na vylepšení v dalších iteracích._

## 1) Waitlist událostí

**Už hotovo (live):**
- Plný termín = oranžový štítek „Plný – čekací listina" (zůstává klikatelný).
- Před odesláním: oranžová informační karta + tlačítko „Přihlásit na čekací listinu".
- Success: „Jste na čekací listině" bez platby/QR.
- Admin: badge „Čekací listina" + „Posunout z čekací listiny".

**Návrh na další iteraci (P1-P2):**
- **Pozice ve frontě:** zobrazit účastníkovi „Jste 3. v pořadí". Backend: `position = count(waitlist applications created before me)`.
- **Automatická notifikace při uvolnění:** při zrušení/zamítnutí obsazující přihlášky e-mailem oslovit 1. čekatele s časově omezeným odkazem „Máte 24 h na potvrzení". (Reuse `services/email_service` + nová `event_waitlist_promote` šablona.)
- **Admin „1-klik promote":** při posunu z waitlistu volitelně rovnou vygenerovat QR/platbu a odeslat potvrzení.
- **Kapacita v reálném čase:** na veřejné stránce „Zbývá 2 z 20 míst" + progress bar; po naplnění plynulý přechod na waitlist UI.

## 2) Zobrazení využití tarifních limitů

**Už hotovo (live):**
- `PlanUsageBanner` na dashboardu (programy + rezervace/měsíc), barevné metry (zelená/jantarová/červená), skryto pro PRO+/unlimited.

**Návrh na další iteraci (P2):**
- **Mini-indikátor v sidebaru:** kompaktní „2/3 programy" u položky Programy + „38/50 rezervací" — stálá viditelnost bez nutnosti jít na dashboard.
- **Detail na stránce Tarify (`/admin/plan`):** plný rozpad využití per limit + historie (sparkline rezervací/měsíc) → buduje hodnotu před upgradem.
- **Reset info:** „Měsíční limit se obnoví 1. 7." u rezervací.

## 3) Upgrade výzvy při dosažení limitů

**Už hotovo (live):**
- Banner při ≥80 % (jantarový) a ≥100 % (červený) + CTA „Vylepšit tarif" → `/admin/plan`.

**Návrh na další iteraci (P1 — konverze):**
- **Kontextová výzva v místě akce:** při pokusu vytvořit 4. program na Free se nad formulářem objeví nenásilný banner „Na Free máte 3 programy. Start = 10 programů" + „Zobrazit tarify" (NEblokovat — soft limit dle rozhodnutí).
- **Cílená hodnota místo obecného CTA:** text dle nejbližšího limitu („Odemkněte neomezené rezervace") místo generického „Vylepšit".
- **Časově omezená pobídka:** po prvním dosažení limitu jednorázový e-mail/banner s drobnou slevou na první měsíc → zvýší konverzi pilotních zákazníků.
- **Telemetrie:** logovat zobrazení banneru a klik na CTA (UsageMetric `upgrade_prompt_view` / `_click`) pro měření konverzního trychtýře.

## Pozn. k hard enforcement
Architektura je připravená: `get_plan_quota_usage` vrací `enforced:false`. Po pilotu stačí přidat guard `if usage.over_limit and ENFORCE: raise 402/403` do `create_program` / booking create + chytit to na FE elegantním modalem místo tvrdé chyby.
