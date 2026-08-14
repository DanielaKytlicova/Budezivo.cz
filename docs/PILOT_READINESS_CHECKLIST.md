# Pilot readiness checklist

Tento checklist shrnuje kontroly pred ostrym pilotem Budezivo.cz. Slouzi jako provozni seznam veci, ktere maji byt pred pilotem hotove, overene nebo vedome odlozene.

## Stav k pilotu

Legenda:

- ✅ OVĚŘENO: proslo realnym testem nebo produkcnim overenim.
- ⚠️ PRAVDĚPODOBNĚ SPRÁVNĚ: technicky opraveno, ale jeste potrebuje uzivatelske overeni.
- ❌ NEOVĚŘENO / CHYBA: nesmi se brat jako hotove.
- 🕒 ODLOŽENO: neni pilotni blokator, vratit se k tomu pozdeji.

## Povinne pred ostrym pilotem

- ✅ Railway backend bezi a deploy po merge probiha uspesne.
- ✅ Produkcni databazove migrace maji jeden Alembic head a backend startuje bez chyby `Multiple head revisions`.
- ✅ Supabase databazove heslo bylo zrotovano po odstraneni stareho seed credentialu.
- ✅ JWT rotace probehla a stare odkazy/sessions byly overeny.
- ✅ Resend API klic byl zrotovan, stary klic byl smazan a testovaci kampan se odeslala.
- ✅ SPF, DKIM a DMARC pro `budezivo.cz` v Gmail detailu zpravy ukazuji `PASS`.
- ✅ Admin prihlaseni, odhlaseni, obnova session a zapomenute heslo byly overeny.
- ✅ Teacher auth `/teacher/auth/me` uz nehlasi nahodne auth chyby.
- ✅ Pokladni role vidi jen potrebne casti: prehled a rezervace.
- ✅ Verejny kalendarovy/ICS odkaz zustal funkcni po JWT rotaci.
- ✅ Vytvareni udalosti a uzaverek prihlasovani funguje po migraci.
- ✅ Vytvareni mailoveho konceptu i testovaci/ostra kampan funguji.
- ✅ Rezervace byly overeny jako funkcni pro pilotni scenar.
- ✅ Izolovana testovaci databaze umi projit migrace od nuly: `regression_baseline.py` vratil `status: ok`.
- ✅ Zakladni testovaci data se umi nasadit do izolovane test DB: `regression_core_seed.py` vratil `status: ok`.
- ✅ Core smoke test nad izolovanou test DB vratil `status: ok`.
- ✅ Role/tenant isolation smoke test nad izolovanou test DB vratil `status: ok`.

## UI a uzivatelske overeni

- ✅ Validacni hlasky povinnych poli byly sjednoceny na cerveny ramecek pole a cerveny text pod polem.
- ✅ Browserove bubliny s oranzovym vykricnikem se u upravenych formularu nepouzivaji.
- ✅ Verejne formulare: kontakt, katalogovy dotaz, verejne akce a pozvanky maji sjednocene chyby.
- ✅ Admin formulare: profil, tym, programy, akce, mailing wizard, nastaveni a zpetna vazba maji sjednocene chyby.
- ✅ Dobrovolna pole se zbytecne nevaliduji.
- ✅ Tlacitka, ktera vyzaduji predchozi vyber nebo nahrany soubor, mohou zustat disabled misto zobrazovani validacni chyby.

## Pred pilotem jeste rucne projit

- [ ] Supabase pred ostrym pilotem prepnout na Pro plan, ponechat Spend Cap a zapnout/overit zalohy.
- [ ] Po prechodu na Pro zkontrolovat, ze produkcni projekt zustal stejny a Railway `DATABASE_URL` nebylo omylem zmeneno.
- [ ] Udelat posledni produkcni smoke test: `/health`, admin login, program, rezervace, akce, mailing, feedback.
- [ ] Vytvorit jednu realnou pilotni rezervaci a jednu testovaci udalost, pak zkontrolovat, ze se daji bezpecne spravovat.
- [ ] Pred hromadnym oslovenim skol odeslat jednu testovaci kampan na Gmail a jeden dalsi externi mailbox.
- [ ] Zkontrolovat, ze v Resendu nejsou stare aktivni API klice.

## Odlozeno na okurkovou sezonu

- 🕒 Inline validace vyberu casoveho bloku ve verejne rezervaci.
  Rezervace jako takova funguje spravne, proto to neni pilotni blokator. Chybu lze zlepsit pozdeji jako UX detail.

- 🕒 Dalsi rozsireni validacniho systemu na mene kriticke okrajove formulare.
  Pred pilotem staci pokryt hlavni tok: registrace/prihlaseni, programy, akce, rezervace, mailing, nastaveni a zpetna vazba.

## Pravidlo pro testovaci databazi

Pilotni UI a funkcni opravy muzeme delat dal bez testovaci databaze. Jakmile ale pujde o mazani, seedovani nebo vetsi end-to-end testy s daty, musi se pouzit izolovana testovaci Supabase databaze, ne produkce.
