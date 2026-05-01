from curl_cffi import requests

for url in [
    "https://www.metafilter.com",
    "https://www.metafilter.com/recent-mod-actions.cfm",
]:
    response = requests.get(url, impersonate="chrome")
    response.raise_for_status()
    print(url, response.status_code)
