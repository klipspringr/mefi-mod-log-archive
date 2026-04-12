#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# shellcheck disable=1091
. .env/bin/activate

if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes in working tree, exiting" >&2
    exit 1
fi

git pull --quiet

python ./check.py

git add ../blog/content/posts

if ! git diff-index --quiet HEAD; then
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    git push --quiet
else
    echo "No changes to blog posts"
fi
