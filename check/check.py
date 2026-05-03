import copy
import enum
import hashlib
import re
import sys
from datetime import datetime, time
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import bs4
import dateparser
from bs4.element import PageElement, Tag
from curl_cffi import requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

MOD_LOG_URL = "https://www.metafilter.com/recent-mod-actions.cfm"

MEFI_TIMEZONE = "America/Los_Angeles"

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

{content}
"""


class Kind(enum.Enum):
    DELETED_POST = "Deleted post"
    MOD_NOTE = "Mod note"


def fetch(url: str) -> str:
    try:
        print(f"Fetch {url}")

        # use curl_cffi to appease the Cloudflare gods, for now
        response = requests.get(url, impersonate="chrome")
        response.raise_for_status()
        return response.text
    except RequestException as x:
        # exit silently:
        # - around 3:15 PST/PDT, when the site is flaky every day
        # - on Cloudflare errors which are (probably) transient

        server_time = datetime.now(ZoneInfo(MEFI_TIMEZONE)).time()
        in_silent_window = time(3, 14) <= server_time <= time(3, 26)
        is_cloudflare_error = isinstance(x, HTTPError) and 520 <= x.code <= 530

        if in_silent_window or is_cloudflare_error:
            print(x)
            print("Failing silently")
            sys.exit(0)

        raise


def get_actions(html: str) -> list[Tag]:
    soup = bs4.BeautifulSoup(html, "lxml")

    actions = soup.select("div.comment.copy")

    # process actions in reverse chronological order
    actions.reverse()

    if len(actions) == 0:
        raise ValueError("No mod actions found, is something wrong?")

    print(f"Found {len(actions)} mod actions")

    return actions


def get_kind(byline: list[PageElement]) -> Kind:
    first_node_text = byline[0].get_text().strip().lower()
    if first_node_text.startswith("deleted"):
        return Kind.DELETED_POST
    elif first_node_text.startswith("mod comment"):
        return Kind.MOD_NOTE
    else:
        raise ValueError(f'Unexpected action kind "{first_node_text}"')


def get_mod(byline: list[PageElement]) -> str:
    mod = byline[1].get_text()
    if not mod:
        raise ValueError("No mod found in byline")
    return mod


def get_url(byline: list[PageElement]) -> str:
    link = byline[3]
    if not isinstance(link, Tag) or link.name != "a":
        raise ValueError("No link found in byline")
    url = str(link["href"])
    if not url:
        raise ValueError("No URL found in byline")
    return url


def get_timestamp(byline: list[PageElement]) -> datetime:
    timestamp_str = f"{byline[2].get_text()} {byline[3].get_text()}"

    timestamp = dateparser.parse(
        timestamp_str,
        settings={
            "TIMEZONE": MEFI_TIMEZONE,
            "RETURN_AS_TIMEZONE_AWARE": True,
            # mod log timestamps don't include year, so we need to tell dateparser that dates are in the past
            "PREFER_DATES_FROM": "past",
        },
    )

    if not timestamp:
        raise ValueError(f'Invalid timestamp "{timestamp_str}"')

    return timestamp


# get the content of the mod action as a string, with some cleanup
# keep the action byline. its now removed in the Hugo HTML template, but (a) it's useful in RSS and (b) useful for consistency/posterity
def get_content(action: Tag) -> str:
    content = action.decode_contents().strip()

    # work around unclosed tags
    content = content.split('<div class="copy comment">', 1)[0].strip()

    # remove Cloudflare email protection links, as they contain a hash which changes on every check
    # note ? for non-greediness
    content = re.sub(
        '<a href="/cdn-cgi/l/email-protection#.+?">.+?</a>',
        "[email protected]",
        content,
    )

    return content


def get_deletion_title(site: str, action: Tag) -> str:
    post_link = action.find("a")
    if not post_link:
        raise ValueError("No post link found in action")

    post_title = post_link.get_text().strip().replace('"', '\\"')

    return f"Deleted {site} post '{post_title}'"


def get_note_title(byline: list[PageElement]) -> str:
    post_title = byline[5].get_text().strip().replace('"', '\\"')
    return f"Mod note on '{post_title}'"


# key post deletions on site, post id, and hash of content
# the same post can be deleted multiple times, potentially with the same timestamp (minute precision) and same mod
# we want a separate blog post if the deletion reason or post title is changed
def get_deletion_key(site: str, path: str, action: Tag) -> str:
    post_id = path.split("/")[1]
    if not post_id.isnumeric():
        raise ValueError(f'Invalid path "{path}"')

    action_copy = copy.copy(action)
    byline = action_copy.find("div", class_="postbyline")
    if not byline:
        raise ValueError("No byline found in deleted post action")
    byline.decompose()
    content_without_byline = get_content(action_copy)

    content_hash = hashlib.md5(content_without_byline.encode()).hexdigest()[:8]

    return f"{site}-post-{post_id}-{content_hash}"


# key mod notes on site and comment id
def get_note_key(site: str, comment_id: str) -> str:
    if not comment_id.isnumeric():
        raise ValueError(f'Invalid comment id "{comment_id}"')

    return f"{site}-note-{comment_id}"


def write_post(key: str, post: str):
    with open(HTML_BASEDIR / f"{key}.html", "w") as f:
        f.write(post)


def process_action(action: Tag):
    byline_tag = action.find("div", class_="postbyline")
    if not byline_tag:
        raise ValueError("No byline found in action")

    byline = byline_tag.contents

    kind = get_kind(byline)

    mod = get_mod(byline)

    url = get_url(byline)
    url_parsed = urlsplit(url)
    site = url_parsed.netloc.split(".")[0]
    if site == "www" or site == "metafilter":
        site = "mefi"

    timestamp = get_timestamp(byline)

    content = get_content(action)

    if kind == Kind.DELETED_POST:
        title = get_deletion_title(site, action)
        key = get_deletion_key(site, url_parsed.path, action)
    elif kind == Kind.MOD_NOTE:
        title = get_note_title(byline)
        key = get_note_key(site, url_parsed.fragment)
    else:
        raise ValueError(f'Unexpected kind "{kind}"')

    post = HTML_TEMPLATE.format(
        title=title,
        timestamp=timestamp.isoformat(),
        site=site,
        mod=mod,
        kind=kind.value,
        url=url,
        content=content,
    )

    print(f"{key}: {title}")
    write_post(key, post)


def main():
    HTML_BASEDIR.mkdir(exist_ok=True)

    html = fetch(MOD_LOG_URL)

    for action in get_actions(html):
        process_action(action)


if __name__ == "__main__":
    main()
