#!/usr/bin/python
from curl_cffi import requests

for url in [
    "https://www.metafilter.com",
    "https://www.metafilter.com/recent-mod-actions.cfm",
]:
    code = requests.get(url, impersonate="chrome").status_code
    if code != 200:
        raise f"{url} returned HTTP {code}"
    print(url, code)
