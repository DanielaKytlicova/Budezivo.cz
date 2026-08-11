# GDPR minimum pro pilot

Tento dokument je praktický provozní postup pro pilot. Nenahrazuje právní
revizi advokátem nebo pověřencem pro ochranu osobních údajů.

## Proč to řešíme před pilotem

Před pilotem musí být jasné:

- kam může člověk poslat žádost o osobní údaje,
- kdo žádost převezme a zapíše,
- jak se ověří identita žadatele,
- jak se provede export,
- kdy a jak se provede výmaz/anonymizace,
- co se nesmí mazat automaticky bez posouzení,
- jaký je retenční postup.

Oficiální východiska:

- ÚOOÚ uvádí práva subjektu údajů včetně přístupu, opravy, výmazu, omezení,
  přenositelnosti a námitky: https://uoou.gov.cz/verejnost/zakladni-prirucka-k-ochrane-udaju
- ÚOOÚ uvádí, že správce má na žádost reagovat bez zbytečného odkladu a
  nejpozději do jednoho měsíce; lhůtu lze ve složitějších případech prodloužit:
  https://uoou.gov.cz/poradna/poradna-gdpr/prava-subjektu-udaju
- Evropská komise připomíná, že právo na výmaz není absolutní, pokud existuje
  zákonná povinnost data uchovat: https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/dealing-requests-individuals/do-we-always-have-delete-personal-data-if-person-asks_en

## Role v pilotu

- Instituce je obvykle správcem osobních údajů u rezervací, škol a kontaktů,
  které používá pro své programy.
- Budeživo.cz je technický poskytovatel platformy a pro tato data obvykle
  vystupuje jako zpracovatel.
- Budeživo.cz může být samostatným správcem u vlastních provozních údajů,
  podpory, bezpečnosti účtů, fakturace a obchodní komunikace.

Pokud žádost směřuje k údajům konkrétní instituce, musí být instituce do
vyřízení zapojena.

## Příjem žádosti

**Kde přijímáme žádosti:**

- e-mail: `gdpr@budezivo.cz`
- datová schránka: `e2u63pp`

**Co zapsat do interní evidence:**

- datum přijetí,
- kanál přijetí,
- jméno/e-mail žadatele,
- typ žádosti: přístup/export, oprava, výmaz/anonymizace, omezení, námitka,
- dotčená instituce, pokud je známá,
- kdo žádost převzal,
- termín odpovědi: nejpozději 1 měsíc od přijetí,
- stav: přijato, čeká na ověření identity, čeká na instituci, vyřízeno,
  odmítnuto/částečně vyřízeno.

## Ověření identity

Před exportem nebo výmazem nesmí stačit pouze volný e-mail bez kontextu.

Minimální ověření:

- pokud je žadatel přihlášený uživatel instituce, požádat ho, aby žádost potvrdil
  z přihlášeného účtu nebo z e-mailu vedeného u účtu,
- pokud jde o pedagoga/objednatele rezervace, ověřit e-mail proti rezervaci a
  případně si vyžádat doplňující údaje k rezervaci, například instituci, program,
  datum nebo školu,
- pokud si nejsme jistí, neexportovat a nemazat; požádat o doplnění údajů.

## Export údajů

Pro přihlášeného administrátora/správce existuje endpoint:

```text
GET /api/gdpr/export
```

Vrací ZIP s JSON a PDF. JSON je strojově čitelný formát, PDF je čitelný přehled.

**Manuální postup v aplikaci:**

1. Přihlásit se do admin účtu dotčené instituce.
2. Otevřít `Nastavení`.
3. Otevřít `GDPR a správa dat`.
4. Spustit export osobních údajů.
5. ZIP předat pouze ověřenému žadateli nebo správci instituce.

**Co neposílat:**

- DB URL,
- tokeny,
- API klíče,
- interní logy obsahující technické identifikátory mimo rozsah žádosti.

## Výmaz a anonymizace

Výmaz není automaticky totéž co smazání všech řádků z databáze. V pilotu se
preferuje anonymizace tam, kde je potřeba zachovat historické statistiky,
auditní stopu nebo provozní návaznost.

V aplikaci existuje endpoint:

```text
POST /api/gdpr/anonymize
```

Vyžaduje potvrzení:

```json
{"confirmation": "SMAZAT"}
```

**Důležité omezení:**

- jediného administrátora instituce nelze anonymizovat bez vytvoření náhradního
  administrátora,
- účetní/fakturační údaje mohou mít zákonné retenční lhůty,
- školy a kontakty používané institucí pro budoucí komunikaci se neposuzují
  automaticky jako údaje jednoho přihlášeného uživatele.

## Retence

V nastavení instituce existuje volba retenčního režimu pro rezervace:

- `never` – automatická anonymizace vypnutá,
- `1year`,
- `2years`,
- `3years`,
- `5years`.

Automatický job běží denně a anonymizuje staré rezervační PII pouze tehdy, když
má instituce zapnuté `anonymize`.

Před pilotem ponechat automatickou anonymizaci vypnutou, pokud instituce výslovně
neodsouhlasila retenční nastavení.

## Minimální checklist před pilotem

- [ ] Veřejná stránka `/gdpr` neobsahuje placeholder adresu.
- [ ] Je uveden funkční kontakt `gdpr@budezivo.cz`.
- [ ] Je uvedena datová schránka `e2u63pp`.
- [ ] Interně je jasné, kdo žádosti kontroluje každý pracovní den.
- [ ] Je jasné, že odpověď má být nejpozději do 1 měsíce.
- [ ] Export přes `Nastavení → GDPR a správa dat` je dostupný adminovi/správci.
- [ ] Výmaz/anonymizace se nespouští bez ověření identity.
- [ ] Destruktivní testy výmazu se před izolovanou testovací DB nespouštějí.

## Stav ověření

✅ Ověřitelné automaticky:

- veřejná stránka neobsahuje `[Adresa]`, `[PSČ]`, `[Město]`,
- frontend build projde,
- dokument runbooku existuje.

⚠️ Nutná manuální kontrola:

- že `gdpr@budezivo.cz` reálně přijímá zprávy,
- že datová schránka `e2u63pp` je správná a obsluhovaná,
- že někdo žádosti pravidelně kontroluje,
- že instituce souhlasí s rolí správce/zpracovatel pro pilot.

❌ Odloženo do izolované testovací DB:

- reálný test anonymizace,
- destruktivní test výmazu,
- větší end-to-end test export + anonymizace nad testovacími daty.
