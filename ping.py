#!/usr/bin/python
from urllib.request import Request, urlopen

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

for url in [
    "https://www.metafilter.com",
    "https://www.metafilter.com/recent-mod-actions.cfm",
]:
    response = urlopen(Request(url, headers=HEADERS))
    print(url, response.getcode())
