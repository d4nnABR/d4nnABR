#!/usr/bin/env bash
# Regenerate the cards and the snake with the local gh login, commit only if something changed, push.
set -euo pipefail
cd "$(dirname "$0")"
GH_TOKEN=$(gh auth token) python3 generate.py
git add card-*.svg snake-*.svg
if git diff --cached --quiet; then
  echo "no changes"
else
  git commit -m "chore: refresh stats and snake"
  git push
fi
