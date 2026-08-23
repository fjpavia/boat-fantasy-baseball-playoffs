#!/usr/bin/env bash
# Publish the dashboard: copy the latest bracket into docs/ and push.
# Run from the repo root after scoring a round.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f data/bracket.json ]; then
  echo "No data/bracket.json yet. Score a round first."
  exit 1
fi

mkdir -p docs/data
cp data/bracket.json docs/data/bracket.json

git add docs/data/bracket.json docs/index.html
if git diff --cached --quiet; then
  echo "Nothing changed since last publish."
  exit 0
fi

git commit -m "Update standings $(date +%Y-%m-%d\ %H:%M)"
git push
echo "Pushed. Live in ~1 minute at your Pages URL."
