#!/usr/bin/python
import hashlib
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request

import bs4
import dateparser

MOD_LOG_URL = "https://www.metafilter.com/recent-mod-actions.cfm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


HTML_BASEDIR = Path(__file__).parent / "blog" / "content" / "posts"

HTML_TEMPLATE = """+++
title = "{title}"
date = "{timestamp}"
tags = ["{kind}", "{site}", "{mod}"]

[params]
url = "{url}"
site = "{site}"
hash = "{hash}"
+++

{text}
"""


# https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/
HTTP_ERRORS_SILENCE = (520, 521, 522, 523, 524, 525, 526, 530)


def fetch_mod_actions():
    HTML_BASEDIR.mkdir(exist_ok=True)

    try:
        html = urlopen(Request(MOD_LOG_URL, headers=HEADERS)).read()
    except (URLError, ConnectionError, HTTPError) as x:
        # fail silently on any URLError or ConnectionError, and on HTTPError if code indicates CloudFlare can't reach origin
        if isinstance(x, HTTPError) and x.code not in HTTP_ERRORS_SILENCE:
            raise
        print(x)
        print("Failing silently")
        return

    soup = bs4.BeautifulSoup(html, "lxml")

    actions = soup.find_all("div", {"class": "copy comment"})
    print(f"Found {len(actions)} mod actions")

    for action in actions:
        byline = action.find("div", {"class": "postbyline"}).contents

        mod = byline[1].text
        url = byline[3]["href"]
        timestamp = dateparser.parse(
            f"{byline[2]} {byline[3].text}",
            settings={
                "TIMEZONE": "America/Los_Angeles",  # mefi server is Pacific Time
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        ).isoformat()

        hash = hashlib.md5(str(url).encode()).hexdigest()

        site = re.search(r"^//(\w+)\.", url).group(1).lower()
        site = "mefi" if site == "www" else site

        byline_start = byline[0].strip().lower()
        if byline_start.startswith("deleted"):
            kind = "Deleted post"
            post_title = action.find("a").text.strip().replace('"', '\\"')
            title = f"Deleted {site} post '{post_title}'"
        elif byline_start.startswith("mod comment"):
            kind = "Mod note"
            post_title = byline[5].text.strip().replace('"', '\\"')
            title = f"Mod note on '{post_title}'"
        else:
            raise ValueError(f'Unexpected action "{byline_start}"')

        # split() to work around unclosed tags
        text = action.decode_contents().strip().split('<div class="copy comment">')[0]

        # remove CloudFlare email protection links, as they contain a hash which changes on every check
        text = re.sub(
            '<a href="/cdn-cgi/l/email-protection#.+">.+</a>',
            "[email protected]",
            text,
        )

        post = HTML_TEMPLATE.format(
            title=title,
            timestamp=timestamp,
            site=site,
            mod=mod,
            kind=kind,
            hash=hash,
            url=url,
            text=text,
        )

        path = HTML_BASEDIR / f"{site}-{hash}.html"
        with open(path, "w") as f:
            f.write(post)


if __name__ == "__main__":
    fetch_mod_actions()
