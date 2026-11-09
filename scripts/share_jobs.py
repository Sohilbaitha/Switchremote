"""Shares new jobs automatically after every refresh.

1. Writes feed.xml (an RSS feed) that social media tools can read.
2. Posts new jobs to the Switchremote Telegram channel, if the two
   GitHub secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.

Remotive and Remote OK jobs are never shared outside the site,
because their terms ask us not to pass their jobs on.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "data" / "jobs.json"
STATE = ROOT / "data" / "shared.json"
FEED = ROOT / "feed.xml"
SITE = "https://switchremote.world/"
NOT_SHARED = {"Remotive", "Remote OK"}
MAX_POSTS_PER_RUN = 5      # never flood the channel
FIRST_RUN_POSTS = 3        # on the very first run, post only the newest few


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


def telegram(token, chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("ok", False)


def message(j):
    lines = [f"New remote job: {j['title']}", f"Company: {j['company']}", f"Where: {where(j)}"]
    lines.append("Posted directly by the employer" if j["source"] == "Employer" else f"Source: {j['source']}")
    lines += ["", "Details and apply: " + SITE + "?job=" + job_id(j["url"]), "",
              "Free for freshers. A real employer never asks you to pay."]
    return "\n".join(lines)


def post_new(jobs):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        print("Telegram not set up yet, skipping posts")
        return
    first_run = not STATE.exists()
    done = set() if first_run else set(json.loads(STATE.read_text()).get("ids", []))
    fresh = [j for j in shareable(jobs) if job_id(j["url"]) not in done]
    fresh.sort(key=lambda j: j["posted"], reverse=True)
    limit = FIRST_RUN_POSTS if first_run else MAX_POSTS_PER_RUN
    posted = 0
    for j in fresh[:limit]:
        try:
            if telegram(token, chat, message(j)):
                posted += 1
                done.add(job_id(j["url"]))
        except Exception as e:
            print("Telegram post failed:", e)
            break
    if first_run:
        # Do not dump the whole board on the first day; mark the rest as seen
        done.update(job_id(j["url"]) for j in shareable(jobs))
    current = {job_id(j["url"]) for j in jobs}
    STATE.write_text(json.dumps({"ids": sorted(done & current)}, indent=0))
    print(f"Posted {posted} new jobs to Telegram")


def main():
    jobs = json.loads(JOBS.read_text()).get("jobs", [])
    write_feed(jobs)
    post_new(jobs)


if __name__ == "__main__":
    main()
