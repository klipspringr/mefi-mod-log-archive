#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes in working tree, exiting" >&2
    exit 1
fi

git pull --quiet

uv run ./check.py

if [ -n "$(git status --porcelain ../blog/content/posts)" ]; then
    git add ../blog/content/posts
    
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    git push --quiet
else
    echo "No changes to blog posts"
fi
