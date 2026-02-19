#!/bin/bash
cd "$(dirname "$0")" || exit
mkdir -p assets/data
hugo mod verify
hugo list published > assets/data/published-content.csv
rm -rf public
hugo build
.env/bin/python3 -m pagefind --site public
hugo server --bind=0.0.0.0
