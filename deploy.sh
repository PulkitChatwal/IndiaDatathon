#!/bin/bash
# Rebuild the site and publish the site/ folder to GitHub Pages (the gh-pages branch).
# Usage: ./deploy.sh      Commit your changes on main first.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
if [ -n "$(git status --porcelain)" ]; then
  echo "There are uncommitted changes. Commit them first, then run ./deploy.sh again." >&2
  exit 1
fi
git push origin main
git push origin "$(git subtree split --prefix site main)":refs/heads/gh-pages --force
echo "Published. It can take a minute or two to appear at https://pulkitchatwal.github.io/IndiaDatathon/"
