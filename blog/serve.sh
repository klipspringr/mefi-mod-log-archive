#!/bin/bash
cd "$(dirname "$0")" || exit
hugo mod verify
mkdir -p assets/data
hugo list published > assets/data/published-content.csv
rm -rf public
hugo build
npx -y pagefind@v1.5.2 --site public --glob "posts/**/*.html"
hugo server --bind=0.0.0.0
