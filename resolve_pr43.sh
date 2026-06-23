#!/usr/bin/env bash
###############################################################################
# resolve_pr43.sh — Trvale vyřeší konflikty PR #43 (security -> main).
# Kompatibilní s macOS bash 3.2 (NEpoužívá `mapfile`).
#
# PROČ: Emergent preview pod nemá git remote, takže merge + push musí proběhnout
# v LOKÁLNÍM klonu. Konflikty jsou jen v artefaktech/testech (žádný runtime kód).
#
# POUŽITÍ (v lokálním klonu):
#   git checkout security && git pull origin security
#   bash resolve_pr43.sh
#   git push origin security
###############################################################################
set -eu

# Cesty mimo verzování (artefakty + testy + ad-hoc QA skripty).
IGNORED_PATHS="test_reports memory test_result.md .emergent/summary.txt backend/tests backend_test.py backend/scripts/collision_deep_test.py backend/scripts/download_all_exports.py backend/scripts/full_system_test.py test_theme_fix.py"

echo "==> 1/4  Zajišťuji .gitignore…"
for entry in "test_reports/" "memory/" "test_result.md" ".emergent/summary.txt" "backend/tests/" "backend_test.py" "backend/scripts/collision_deep_test.py" "backend/scripts/download_all_exports.py" "backend/scripts/full_system_test.py" "/test_theme_fix.py" "/test_*.py"; do
  grep -qxF "$entry" .gitignore 2>/dev/null || echo "$entry" >> .gitignore
done
git rm -r --cached --ignore-unmatch $IGNORED_PATHS >/dev/null 2>&1 || true
git add .gitignore
git commit -m "chore: stop tracking test/artifact files (PR #43)" >/dev/null 2>&1 || true

echo "==> 2/4  Merge main do security…"
git fetch origin main
git merge origin/main --no-edit || true   # konflikty vyřešíme níže

echo "==> 3/4  Řeším konflikty (mažu artefakty/testy, produkční kód = security)…"
git diff --name-only --diff-filter=U | while IFS= read -r f; do
  case "$f" in
    test_reports/*|memory/*|test_result.md|.emergent/summary.txt|backend/tests/*|backend_test.py|backend/scripts/collision_deep_test.py|backend/scripts/download_all_exports.py|backend/scripts/full_system_test.py|test_*.py)
      git rm -f --ignore-unmatch -- "$f" >/dev/null 2>&1 || true
      echo "    delete: $f"
      ;;
    *)
      git checkout --ours -- "$f" 2>/dev/null && git add -- "$f" && echo "    keep(security): $f"
      ;;
  esac
done

echo "==> 4/4  Kontrola…"
REMAIN=$(git diff --name-only --diff-filter=U || true)
if [ -z "$REMAIN" ]; then
  git commit --no-edit >/dev/null 2>&1 || true
  echo "    ŽÁDNÉ konflikty. ✅  Spusť:  git push origin security"
else
  echo "    !! Ručně dořeš:"; echo "$REMAIN" | sed 's/^/      - /'
fi
