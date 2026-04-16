#!/bin/bash
set -euo pipefail

exec 9>"$HOME/.mefi-mod-log-archive.lock"
flock -n 9 || { echo "Previous run in progress, exiting" >&2; exit 1; }

cd "$(dirname "$0")"

if [ -n "$(git status --porcelain)" ]; then
    echo "Working tree dirty, exiting" >&2
    git status >&2
    exit 1
fi

# we don't want to do anything other than fast-forward
git fetch
git pull --ff-only --no-progress

"$HOME/.local/bin/uv" run ./check.py

status_output=$(git status --porcelain ../blog/content/posts)
if [ -n "$status_output" ]; then
    git add ../blog/content/posts
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    git push
else
    echo "No changes to blog posts"
fi
