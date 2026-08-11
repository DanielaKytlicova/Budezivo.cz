# Izolované regresní testovací prostředí

Tento postup slouží k ověření, že testy, cleanup a seed skripty poběží proti
oddělené testovací databázi, ne proti produkci.

## Co musí platit

- Testovací databáze je samostatný Supabase projekt nebo jinak izolovaná DB.
- Testovací DB URL se ukládá pouze lokálně jako `TEST_DATABASE_URL`.
- Produkční `DATABASE_URL` se pro ad-hoc testovací skripty nepoužívá.
- Skripty se spouštějí s `APP_ENV=test`.
- Skutečné mazání přes `pilot_cleanup.py` se spouští jen s `--execute` a jen po
  kontrole dry-run výstupu.

## Lokální ověření baseline

V terminálu v kořeni repozitáře:

```bash
cd /Users/vanilka/Projects/Budezivo.cz/backend
APP_ENV=test TEST_DATABASE_URL='postgresql://...' python3 scripts/regression_baseline.py
```

Správný výsledek:

- JSON report má `"status": "ok"`,
- `alembic_version_present` je `true`,
- `required_tables_present` je `true`,
- `required_columns_present` je `true`,
- `write_probe_rolled_back` je `true`.

Chybný výsledek:

- `"status": "attention_required"`,
- některý z required checks je `false`,
- report vypíše `missing_tables` nebo `missing_columns`.

Výstup nikdy neobsahuje DB heslo ani connection string.

## Negativní bezpečnostní kontrola

Bez env proměnných:

```bash
cd /Users/vanilka/Projects/Budezivo.cz/backend
python3 scripts/regression_baseline.py
```

Správný výsledek:

```text
requires APP_ENV=test
```

Pokud by se skript spustil bez `APP_ENV=test`, kontrola selhala.

## Doporučený předpilotní pořádek

1. Vytvořit izolovanou testovací DB.
2. Nastavit lokálně `APP_ENV=test` a `TEST_DATABASE_URL`.
3. Spustit `alembic upgrade head` proti testovací DB.
4. Spustit `scripts/regression_baseline.py`.
5. Spustit `scripts/seed_test_muzeum_bookable.py`.
6. Spustit `scripts/pilot_cleanup.py` nejdřív bez `--execute`.
7. Až po kontrole dry-run výstupu případně spustit cleanup s `--execute`.

## Co poslat ke kontrole

Pošli pouze:

- celý JSON výstup `scripts/regression_baseline.py`,
- případně chybovou hlášku,
- nikdy neposílej hodnotu `TEST_DATABASE_URL`, heslo ani tokeny.
