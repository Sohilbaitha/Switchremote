"""One-off: for each company, open the candidate official careers page(s) and check
1) it loads, 2) it is on the company's own website, 3) whether it mentions the hiring board we read."""
import json, re, urllib.request, urllib.error, concurrent.futures as cf
from urllib.parse import urlparse
cand = json.load(open("scan/official.json"))
links = json.load(open("data/company_links.json"))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en"}
def fetch(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=45)
        return r.status, r.geturl(), r.read(600000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, u, ""
    except Exception as e:
        return "ERR " + type(e).__name__, u, ""
def check(name):
    board = links[name]["careers"]
    slug = board.rstrip("/").split("/")[-1].lower()
    out = []
    for u in cand[name]:
        st, final, html = fetch(u)
        host = urlparse(final).netloc
        mentions = bool(html) and slug in html.lower()
        m=re.search(r"<title[^>]*>(.*?)</title>",html,re.S|re.I); t=(m.group(1).strip()[:70] if m else "")
        hits=sorted(set(re.findall(r"https?://[a-z0-9.-]*(?:greenhouse|lever|ashbyhq|workable|smartrecruiters|breezy|careers-page)[a-z0-9./_-]*",html.lower())))[:4]
        out.append(f"{st} | {u} -> {final} | board '{slug}' mentioned: {mentions} | title: {t} | ats: {hits}")
    return name, board, out
with cf.ThreadPoolExecutor(10) as ex:
    for name, board, out in ex.map(check, sorted(cand)):
        print(f"== {name} (board {board})")
        for o in out: print("   " + o)
