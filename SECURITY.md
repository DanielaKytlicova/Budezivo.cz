# Security checks

## Secret scanning

Every pull request and push to `main` is scanned by Gitleaks in GitHub Actions.
The scan blocks changes containing known API key, token, password, or private-key
patterns.

To run the same protection locally on macOS:

```bash
brew install gitleaks
./scripts/check-secrets.sh
```

The optional pre-commit hook can be enabled for a local clone with:

```bash
git config core.hooksPath .githooks
```

Do not add broad allowlists when a scan fails. A false positive should be
reviewed and suppressed as narrowly as possible, with an explanation in the
pull request.
