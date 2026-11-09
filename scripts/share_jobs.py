"""Writes feed.xml (an RSS feed of the newest jobs) after every refresh.

Remotive, Remote OK and Himalayas jobs are never shared outside the site,
because their terms ask us not to pass their jobs on (feeds included).
"""
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "data" / "jobs.json"
FEED = ROOT / "feed.xml"
SITE = "https://switchremote.world/"
NOT_SHARED = {"Remotive", "Remote OK", "Himalayas"}


def job_id(url):
    # Same short id the website uses for shared links (32-bit FNV-1a, base 36)
    h = 2166136261
    for ch in url.encode("utf-16-le").decode("utf-16-le"):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        h, r = divmod(h, 36)
        out = digits[r] + out
        if h == 0:
            return out


def where(job):
    c = job.get("countries", [])
    return "Anywhere in the world" if "Worldwide" in c else ", ".join(c)


def shareable(jobs):
    return [j for j in jobs if j.get("source") not in NOT_SHARED]


def write_feed(jobs):
    items = []
    for j in shareable(jobs)[:50]:
        link = SITE + "?job=" + job_id(j["url"])
        when = datetime.fromisoformat(j["posted"].replace("Z", "+00:00"))
        src = "Posted directly by the employer" if j["source"] == "Employer" else "Source: " + j["source"]
        desc = f"{j['title']} at {j['company']}. Remote, {where(j)}. {src}."
        items.append(
            "<item>"
            f"<title>{escape(j['title'] + ' at ' + j['company'])}</title>"
            f"<link>{escape(link)}</link>"
            f"<guid isPermaLink=\"false\">{escape(job_id(j['url']))}</guid>"
            f"<pubDate>{format_datetime(when)}</pubDate>"
            f"<description>{escape(desc)}</description>"
            "</item>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>'
           "<title>Switchremote: remote jobs for freshers</title>"
           f"<link>{SITE}</link>"
           "<description>New remote jobs for freshers across Asia and the world.</description>"
           "<language>en</language>"
           f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
           + "".join(items) + "</channel></rss>\n")
    FEED.write_text(xml, encoding="utf-8")
    print(f"feed.xml written with {len(items)} jobs")


def main():
    jobs = json.loads(JOBS.read_text()).get("jobs", [])
    write_feed(jobs)


if __name__ == "__main__":
    main()
