import hashlib
from pathlib import Path
import re
from urllib.error import ContentTooShortError, HTTPError, URLError
from urllib.request import urlopen

import bs4
import dateparser


MOD_LOG_URL = "https://www.metafilter.com/recent-mod-actions.cfm"

HTML_BASEDIR = Path(__file__).parent / "blog" / "content" / "posts"

HTML_TEMPLATE = """+++
title = "{title}"
date = "{timestamp}"
tags = ["{kind}", "{site}", "{mod}"]
categories = ["{year}", "{month}"]

[params]
url = "{url}"
site = "{site}"
hash = "{hash}"
+++

{text}
"""


def fetch_mod_actions():
    HTML_BASEDIR.mkdir(exist_ok=True)

    try:
        html = urlopen(MOD_LOG_URL).read()
    except (HTTPError, ContentTooShortError):
        raise
    except URLError as x:
        print("Encountered URLError, failing silently.")
        print(x)
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
        )

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

        post = HTML_TEMPLATE.format(
            title=title,
            timestamp=timestamp.isoformat(),
            year=timestamp.year,
            month=timestamp.strftime("%Y %B"),
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
