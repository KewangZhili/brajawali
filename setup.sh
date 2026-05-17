#!/usr/bin/env bash
# One-shot installer for the v2 NLP layer (indic-nlp-library + scikit-learn).
# Creates a local venv inside the skill directory so it doesn't touch system python.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

echo "==> Creating venv at $HERE/.venv"
python3 -m venv .venv

echo "==> Installing dependencies"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet indic-nlp-library scikit-learn numpy

echo "==> Smoke-test"
.venv/bin/python lib/translate_v2.py "মই তোমাক ভাল পাওঁ"

cat <<'EOF'

✓ Setup complete.

Use:
    ./translate "মই তোমাক ভাল পাওঁ"
or:
    .venv/bin/python lib/translate_v2.py "<text>"

Run tests:
    .venv/bin/python lib/test_translate_v2.py
EOF
