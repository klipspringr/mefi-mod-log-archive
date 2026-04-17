#!/usr/bin/python
import hashlib
import os
import re
from datetime import datetime, time, timezone
from pathlib import Path
from curl_cffi import requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

import bs4
import dateparser

MOD_LOG_URL = "https://www.metafilter.com/recent-mod-actions.cfm"

HTML_BASEDIR = Path(__file__).parent.parent / "blog" / "content" / "posts"

HTML_TEMPLATE = """+++
title = "{title}"
date = "{timestamp}"

kinds = ["{kind}"]
subsites = ["{site}"]
mods = ["{mod}"]

[params]
url = "{url}"
+++

{text}
"""


def fetch(url: str, interface: str | None, impersonate="chrome") -> str | None:
    try:
        print(
            f"Fetch {url} on {interface if interface else 'any interface'} as {impersonate}",
        )

        # use curl_cffi to appease the Cloudflare gods, for now
        response = requests.get(url, interface=interface, impersonate=impersonate)
        return response.text
    except RequestException as x:
        now_utc = datetime.now(timezone.utc).time()
        in_silent_window = time(10, 14) <= now_utc <= time(10, 26)

        # fail silently:
        # - around 10:15 UTC, when the site is flaky every day
        # - on Cloudflare errors which are (probably) transient
        if in_silent_window or (isinstance(x, HTTPError) and 520 <= x.code <= 530):
            print(x)
            print("Failing silently")
            return None

        raise


def get_actions(html: str) -> list[bs4.element.Tag]:
    soup = bs4.BeautifulSoup(html, "lxml")

    actions = soup.find_all("div", {"class": "copy comment"})

    if len(actions) == 0:
        raise ValueError("No mod actions found, is something wrong?")

    print(f"Found {len(actions)} mod actions")

    # a post can be deleted with one reason, restored, then deleted again
    # reverse the array, so the newer deletion overwrites the older one
    actions.reverse()

    return actions


def process_action(action: bs4.element.Tag):
    byline = action.find("div", {"class": "postbyline"}).contents

    mod = byline[1].text
    url = byline[3]["href"]
    timestamp = dateparser.parse(
        f"{byline[2]} {byline[3].text}",
        settings={
            "TIMEZONE": "America/Los_Angeles",  # Mefi server is Pacific Time
            "RETURN_AS_TIMEZONE_AWARE": True,
            # mod log timestamps don't include year, so we need to specify that dateparser should assume ambiguous dates are from last year
            "PREFER_DATES_FROM": "past",
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

    # remove Cloudflare email protection links, as they contain a hash which changes on every check
    # note ? for non-greediness
    text = re.sub(
        '<a href="/cdn-cgi/l/email-protection#.+?">.+?</a>',
        "[email protected]",
        text,
    )

    post = HTML_TEMPLATE.format(
        title=title,
        timestamp=timestamp,
        site=site,
        mod=mod,
        kind=kind,
        url=url,
        text=text,
    )

    filename = f"{site}-{hash}.html"
    with open(HTML_BASEDIR / filename, "w") as f:
        f.write(post)
        print(f"Wrote {filename} ({title})")


def main():
    HTML_BASEDIR.mkdir(exist_ok=True)

    interface = os.getenv("INTERFACE", None)

    html = fetch(MOD_LOG_URL, interface=interface)

    if html is None:
        return

    for action in get_actions(html):
        process_action(action)


if __name__ == "__main__":
    main()
