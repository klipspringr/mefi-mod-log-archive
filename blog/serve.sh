#!/bin/bash
cd "$(dirname "$0")" || exit
mkdir -p assets/data
hugo mod verify
hugo list published > assets/data/published-content.csv
rm -rf public
hugo build
npx -y pagefind@v1.5.0 --site public
hugo server --bind=0.0.0.0
