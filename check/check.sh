#!/bin/bash
set -euo pipefail

exec 9>"$HOME/.mefi-mod-log-archive.lock"
flock -n 9 || { echo "Previous run in progress, exiting" >&2; exit 1; }

cd "$(dirname "$0")"

if [ -n "$(git status --porcelain)" ]; then
    git status >&2
    echo "Working tree dirty, exiting" >&2
    exit 1
fi

# fast-forward only
# git outputs progress stuff to stderr, so redirect to stdout and check exit code
if ! git pull --ff-only 2>&1; then
    echo "Failed to pull, exiting" >&2
    exit 1
fi

"$HOME/.local/bin/uv" run ./check.py

if [ -n "$(git status --porcelain ../blog/content/posts)" ]; then
    git add ../blog/content/posts
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    if ! git push 2>&1; then
        echo "Failed to push, exiting" >&2
        exit 1
    fi
else
    echo "No changes to blog posts"
fi
