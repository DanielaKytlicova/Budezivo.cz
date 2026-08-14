# Code freeze policy pro pilot zari 2026

Od **28. 8. 2026** plati pro `main` code freeze pred ostrym pilotem Budezivo.cz.

Cil neni zastavit praci uplne. Cil je prestat pridavat zbytecne riziko tesne pred pilotem a poustet jen zmeny, ktere chrani stabilitu, bezpecnost nebo schopnost pilot vubec spustit.

## Co po 28. 8. smi do main

- Opravy blockeru, ktere brani prihlaseni, rezervaci, akci, mailingu nebo sprave pilotnich dat.
- Bezpecnostni opravy, zejmena pristupy, tajemstvi, role, tenant isolation a produkcni konfigurace.
- Migrace nutne pro opravu produkcni chyby, ale jen s jasnym rollbackem a smoke testem.
- Male UX opravy, pouze pokud odstranovaji realne mateni v pilotnim toku a maji nizke riziko.
- Dokumentace, checklisty a runbooky.

## Co po 28. 8. nesmi do main

- Nove funkce, ktere nejsou nezbytne pro pilot.
- Vetsi refaktory, framework upgrady nebo zmeny build systemu.
- Kosmeticke upravy bez vazby na pilotni pruchod.
- Experimentalni integrace, nove AI/prospecting workflow nebo kreativni tooling.
- Zmeny databaze bez predchoziho overeni v izolovane test DB.

## Povinne pro kazdy PR behem freeze

Kazdy PR musi mit:

- jasny duvod, proc je potreba pred pilotem,
- maly rozsah zmen,
- popis rollbacku nebo alespon navratove cesty,
- konkretni smoke test,
- informaci, jestli se meni databaze, env promenne, role nebo externi sluzby.

## Smoke test podle typu zmeny

### Backend nebo migrace

- Railway deploy dobehne uspesne.
- `https://api.budezivo.cz/health` odpovi OK.
- Pokud jde o DB zmenu, overit Alembic a kriticke tabulky/sloupce.

### Frontend

- Admin stranka se nacte po refreshi.
- Dotcena zalozka se otevre bez bile obrazovky.
- Hlavni dotceny tok projde rucne.

### Rezervace a akce

- Verejna rezervace projde az po potvrzeni.
- Admin vidi rezervaci.
- Akce jde ulozit vcetne terminu a uzaverky, pokud je zmena relevantni.

### Mailing

- Testovaci e-mail se doruci.
- Pokud se meni kampane, zkontrolovat i obsah odkazu na programy/terminy.
- Resend webhook/deliverability zmeny se overuji proti testovacimu nebo bezpecnemu scenari.

### Role a pristupy

- Admin zustane prihlaseny po refreshi.
- Pokladni vidi jen potrebne casti.
- Teacher auth nehlasi nahodne chyby.

## Databazove pravidlo

Jakmile jde o mazani, seedovani nebo vetsi end-to-end testy s daty, musi se pouzit izolovana testovaci Supabase databaze. Produkcni DB se nepouziva jako testovaci hriste.

## Odlozene veci

Veci, ktere nejsou blockerem pilotu, se presouvaji do faze **Okurkova sezona** nebo **Behem pilotu** v Notionu. Typicky:

- drobne UX polish opravy,
- dalsi rozsireni validaci mimo hlavni pilotni tok,
- kreativni/AI tooling,
- vetsi modernizace zavislosti,
- enterprise hardening typu 2FA, pokud neni explicitne potreba pro pilot.

## Rozhodovaci pravidlo

Pred merge si polozit jednu otazku:

> Snizuje tato zmena riziko pilotu vic, nez ho muze zvysit?

Pokud odpoved neni jasne ano, zmena patri az po pilotu nebo do okurkove sezony.
