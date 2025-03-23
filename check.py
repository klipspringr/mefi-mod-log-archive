import hashlib
from pathlib import Path
import re
from urllib.request import urlopen

import bs4
import dateparser


MOD_LOG_URL = "https://www.metafilter.com/recent-mod-actions.cfm"

HTML_BASEDIR = Path(__file__).parent / "blog" / "content" / "posts"

HTML_TEMPLATE = """+++
title = "{title}"
date = "{timestamp}"
tags = ["{site}", "{mod}", "{kind}"]

[params]
    url = "{url}"
+++

{text}
"""


def fetch_mod_actions():
    html = urlopen(MOD_LOG_URL).read()
    # html = open("temp.html").readlines()

    soup = bs4.BeautifulSoup(html, "lxml")

    for action in soup.find_all("div", {"class": "copy comment"}):
        byline = action.find("div", {"class": "postbyline"}).contents

        mod = byline[1].text
        url = byline[3]["href"]
        timestamp = dateparser.parse(f"{byline[2]} {byline[3].text}")

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

        text = action.decode_contents().strip()

        # workaround for unclosed tags
        text = text.split('<div class="copy comment">')[0]

        post = HTML_TEMPLATE.format(
            title=title,
            timestamp=timestamp.isoformat(),
            site=site,
            mod=mod,
            kind=kind,
            url=url,
            text=text,
        )

        hash = hashlib.md5(str(url).encode()).hexdigest()
        path = HTML_BASEDIR / f"{site}-{hash}.html"

        with open(path, "w") as f:
            f.write(post)


if __name__ == "__main__":
    fetch_mod_actions()
