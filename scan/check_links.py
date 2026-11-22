"""One-off: open every careers link and report which ones fail or land somewhere unexpected."""
import json, urllib.request, urllib.error, concurrent.futures as cf
from urllib.parse import urlparse
d = json.load(open("data/company_links.json"))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en"}
def check(item):
    name, v = item
    try:
        r = urllib.request.urlopen(urllib.request.Request(v["careers"], headers=UA), timeout=25)
        return name, r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return name, e.code, v["careers"]
    except Exception as e:
        return name, "ERR " + type(e).__name__, v["careers"]
extra = {"PW alt careers.pw.live": {"careers": "https://careers.pw.live/"}, "PW alt pw.live/careers": {"careers": "https://pw.live/careers"},
         "Uber alt list": {"careers": "https://www.uber.com/us/en/careers/list/"}, "Hello alt": {"careers": "https://helloenglish.com/"}}
d.update(extra)
with cf.ThreadPoolExecutor(12) as ex:
    res = list(ex.map(check, d.items()))
bad = [r for r in res if r[1] != 200]
print("OK", len(res) - len(bad), "of", len(res))
for name, st, url in sorted(res):
    host = urlparse(url).netloc
    flag = "" if st == 200 else "  <-- CHECK"
    print(f"{st} | {name} | {d[name]['careers']} -> {url}{flag}")
