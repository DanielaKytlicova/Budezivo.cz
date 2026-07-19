# Pravidla práce v repozitáři Bude živo

Tato pravidla platí stejně pro ChatGPT, Codex, Emergent i ruční úpravy.

## Rozsah změn

- Dělej malé, tematicky související změny. Nemíchej opravu funkce s plošným refaktoringem nebo formátováním.
- Zachovej existující architekturu a názvosloví v okolním kódu. Větší přesuny nejprve popiš v plánu práce.
- Neupravuj přihlášení, platby, OAuth, produkční konfiguraci ani databázová data bez výslovného zadání.
- Neukládej do repozitáře klientská tajemství, API klíče, tokeny, hesla ani obsah produkčních proměnných prostředí.

## Frontend

- Používej Node 20 a Yarn 1.22.22. Závislosti instaluj pomocí `yarn install --frozen-lockfile`.
- JavaScript a JSX kontroluj příkazem `yarn lint`. Automatické opravy spouštěj jen na souborech v rozsahu úkolu.
- Prettier používej pouze na cíleně měněné soubory: `yarn format:file <soubor...>` a `yarn format:check:file <soubor...>`.
- Stávající frontend není plošně přeformátovaný. Nespouštěj Prettier nad celým `src` bez samostatně schváleného úkolu.
- Komponenty pojmenovávej v PascalCase, hooky s prefixem `use` a běžné funkce či proměnné v camelCase.
- Opakované volání API a doménovou logiku neduplikuj v komponentách; využij existující služby, kontexty a hooky.

## Backend

- Dodržuj styl okolního Python kódu a čtyřmezerové odsazení.
- Změny databázového schématu dělej verzovanou migrací. Neprováděj destruktivní změny dat bez výslovného souhlasu.
- U endpointů zachovej kontrolu oprávnění, validaci vstupů a bezpečné logování bez citlivých údajů.

## Ověření a předání

- Před předáním spusť nejmenší relevantní sadu kontrol a uveď, co přesně proběhlo a co nebylo možné ověřit.
- U změn frontendu spusť lint, cílenou kontrolu Prettieru a produkční build, pokud tomu nebrání prostředí.
- Nevytvářej commit ani push, pokud je uživatel výslovně neschválil. Do commitu nezahrnuj nesouvisející lokální změny.

