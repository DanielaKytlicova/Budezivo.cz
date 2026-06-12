#!/usr/bin/env bash
###############################################################################
# resolve_pr43.sh — Bezpečně vyřeší konflikty PR #43 (security -> main).
#
# PROČ tento skript: Emergent preview pod NEMÁ git remote ani GitHub credentials,
# takže agent NEMŮŽE pushnout ani provést 3-way merge s `main`. Tenhle skript
# spustíš v LOKÁLNÍM klonu repa (máš GitHub přístup) a on merge dořeší a pushne.
#
# Co dělá (dle rozhodnutí uživatele):
#   1) test_reports/*, memory/*, .emergent/summary.txt  -> SMAZAT + .gitignore
#   2) backend/tests/*, backend_test.py, backend/scripts/*_test.py -> vzít SECURITY
#   3) Produkční kód -> ponechat (žádný z konfliktů v PR #43 není runtime kód)
#
# POUŽITÍ:
#   git clone <tvuj-repo> && cd <repo>
#   git checkout security && git pull origin security
#   bash resolve_pr43.sh
#   # zkontroluj `git status`, pak:
#   git commit --no-edit && git push origin security
###############################################################################
set -euo pipefail

echo "==> 1/5  Spouštím merge main do security…"
git fetch origin main
git merge origin/main --no-edit || true   # konflikty vyřešíme níže

echo "==> 2/5  Artefakty: smazat + ignorovat (test_reports, memory, summary)…"
git rm -r --ignore-unmatch test_reports memory .emergent/summary.txt >/dev/null 2>&1 || true
for pat in 'test_reports/' 'memory/' '.emergent/summary.txt'; do
  grep -qxF "$pat" .gitignore 2>/dev/null || echo "$pat" >> .gitignore
done
git add .gitignore

echo "==> 3/5  Testovací soubory/skripty: ponechat verzi ze SECURITY (--ours)…"
mapfile -t CONFLICTS < <(git diff --name-only --diff-filter=U || true)
for f in "${CONFLICTS[@]}"; do
  case "$f" in
    backend/tests/*|backend_test.py|backend/scripts/*_test.py|backend/scripts/*full_system*|backend/scripts/*download_all*|backend/scripts/*collision_deep*)
      git checkout --ours -- "$f" && git add -- "$f"
      echo "    keep(security): $f"
      ;;
    test_reports/*|memory/*|.emergent/summary.txt)
      git rm -f --ignore-unmatch -- "$f" >/dev/null 2>&1 || true
      echo "    delete:         $f"
      ;;
  esac
done

echo "==> 4/5  Zbývající (produkční) konflikty k ruční kontrole:"
REMAIN=$(git diff --name-only --diff-filter=U || true)
if [ -z "$REMAIN" ]; then
  echo "    ŽÁDNÉ — vše vyřešeno automaticky. ✅"
else
  echo "    !! Ručně vyřeš tyto soubory (zachovej funkce z main + security):"
  echo "$REMAIN" | sed 's/^/      - /'
  echo "    Po ruční úpravě: git add <soubory>"
fi

echo "==> 5/5  Hotovo. Zkontroluj 'git status', pak:"
echo "    git commit --no-edit && git push origin security"
echo "    -> Na GitHubu PR #43 musí zmizet 'This branch has conflicts that must be resolved'."
