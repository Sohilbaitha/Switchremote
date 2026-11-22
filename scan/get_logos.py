"""One-off: download a small logo for every company domain."""
import json, urllib.request, concurrent.futures as cf, pathlib
d = json.load(open("data/company_links.json"))
out = pathlib.Path("logos"); out.mkdir(exist_ok=True)
def get(dom):
    try:
        r = urllib.request.urlopen(f"https://www.google.com/s2/favicons?domain={dom}&sz=64", timeout=20)
        data = r.read()
        (out / f"{dom}.png").write_bytes(data)
        return dom, len(data)
    except Exception as e:
        return dom, str(e)
doms = sorted({v["domain"] for v in d.values() if v.get("domain")})
with cf.ThreadPoolExecutor(10) as ex:
    for dom, res in ex.map(get, doms):
        print(dom, res)
