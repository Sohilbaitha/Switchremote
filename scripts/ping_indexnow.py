"""Tell Bing (and other IndexNow search engines) which pages changed.

IndexNow is a free, open way to notify search engines. The key below is public on purpose:
the same key sits in a text file on the site, which proves the ping comes from the site owner.
"""
import json
import re
import urllib.request

HOST = "switchremote.world"
KEY = "c822d02a8cafe8e9a8d98aa83a5c0b54"

urls = re.findall(r"<loc>(.*?)</loc>", open("sitemap.xml", encoding="utf-8").read())
body = json.dumps({
    "host": HOST,
    "key": KEY,
    "keyLocation": f"https://{HOST}/{KEY}.txt",
    "urlList": urls,
}).encode()
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow", data=body,
    headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=20) as r:
    print("IndexNow:", r.status, len(urls), "pages sent")
