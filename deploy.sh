#!/bin/bash
# Rebuild the site and publish it. GitHub Pages serves the main branch, so publishing = pushing main.
# Usage: ./deploy.sh      Commit your changes first.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
if [ -n "$(git status --porcelain)" ]; then
  echo "There are uncommitted changes (the rebuild may have updated site/). Commit them, then run ./deploy.sh again." >&2
  exit 1
fi
git push origin main
echo "Published. It can take a minute or two to appear at https://pulkitchatwal.github.io/IndiaDatathon/"
