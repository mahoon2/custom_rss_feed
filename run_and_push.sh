#!/usr/bin/env bash
set -euo pipefail

VENV_PATH=".venv/bin/activate"

if [[ -f "$VENV_PATH" ]]; then
  source "$VENV_PATH"
else
  echo "Virtual environment not found at $VENV_PATH. Please create it before running this script." >&2
  exit 1
fi

echo "Running scraper..."
if ! python main.py; then
  echo "main.py failed; aborting feed update." >&2
  exit 1
fi

echo "Staging CNSfeed.xml..."
git add CNSfeed.xml

if git diff --cached --quiet; then
  echo "No changes detected in CNSfeed.xml; nothing to commit."
  exit 0
fi

TIMESTAMP="$(date -u +%Y-%m-%d)"
git commit -m "Update feed: $TIMESTAMP"

echo "Pushing to GitHub..."
git push origin main

echo "Feed update complete."
