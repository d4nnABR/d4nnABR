#!/usr/bin/env bash
# Regenerate the cards and the snake with the local gh login, commit if something changed, then push.
set -euo pipefail
cd "$(dirname "$0")"
GH_TOKEN=$(gh auth token) python3 generate.py
git add card-*.svg snake-*.svg
if git diff --cached --quiet; then
  echo "no changes to commit"
else
  git commit -m "chore: refresh stats and snake"
fi
# Push even when nothing new was committed, so earlier local commits are never left behind.
git -c credential.helper= -c credential.helper="!$(command -v gh) auth git-credential" push
