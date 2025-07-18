#!/bin/bash
set -e
# shellcheck disable=1091
. .env/bin/activate
python ./check.py
git add blog/content/posts
if ! git diff-index --quiet HEAD; then
    git -c "user.name=mefi-activity-automated" -c "user.email=mefi-activity-automated" commit -m "Recent mod actions updated"
    git push
fi