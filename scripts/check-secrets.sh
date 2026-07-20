#!/usr/bin/env bash
set -euo pipefail

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "Gitleaks is required for the local secret scan." >&2
  echo "Install it with: brew install gitleaks" >&2
  exit 2
fi

gitleaks dir --redact --no-banner "$(git rev-parse --show-toplevel)"
