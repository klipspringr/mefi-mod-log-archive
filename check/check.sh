#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# shellcheck disable=1091
. .env/bin/activate

if ! git diff-index --quiet HEAD; then
    echo "Uncommitted changes in working tree, exiting"
    exit 1
fi

git pull 2>&1

python ./check.py

git add ../blog/content/posts

if ! git diff-index --quiet HEAD; then
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    git push 2>&1
else
    echo "No changes to blog posts"
fi
