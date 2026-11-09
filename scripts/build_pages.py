"""Builds one page per country (remote-jobs-india.html and so on) and sitemap.xml.

Each country page is a copy of index.html with its own title, description and
heading, and with the current jobs written into the page itself, so search
engines can read the jobs without running any script. Change the design in
index.html only; these pages follow it on the next refresh.
"""
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://switchremote.world/"
MAX_STATIC = 60   # jobs written into each page

# place, file name, "in ..." wording
PAGES = [
    ("Indonesia", "remote-jobs-indonesia.html", "in Indonesia"),
    ("Vietnam", "remote-jobs-vietnam.html", "in Vietnam"),
    ("Malaysia", "remote-jobs-malaysia.html", "in Malaysia"),
    ("Philippines", "remote-jobs-philippines.html", "in the Philippines"),
    ("Thailand", "remote-jobs-thailand.html", "in Thailand"),
    ("India", "remote-jobs-india.html", "in India"),
    ("Worldwide", "remote-jobs-worldwide.html", "open worldwide"),
]


def in_place(job, place):
    c = job.get("countries", [])
    if place == "Worldwide":
        return "Worldwide" in c
    return place in c or "Worldwide" in c or "Asia" in c


def place_name(x):
    return {"Worldwide": "Anywhere in the World", "Asia": "Asia-Pacific"}.get(x, x)


def card(j):
    tags = "".join(f'<span class="tag">{escape(place_name(c))}</span>' for c in j.get("countries", []))
    rel = "noopener" if j.get("source") == "Remote OK" else "noopener noreferrer nofollow"
    return (
        '<article class="job">'
        f'<div class="av">{escape((j.get("company") or "?").strip()[:1].upper())}</div>'
        '<div class="body">'
        f'<div class="top"><h2>{escape(j["title"])}</h2></div>'
        f'<p class="company">{escape(j.get("company", ""))}</p>'
        f'<div class="tags"><span class="tag"><i class="sw"></i>Remote</span>{tags}'
        f'<span class="tag">{escape(j.get("source", ""))}</span></div>'
        f'<div class="actions"><a class="apply" href="{escape(j["url"], quote=True)}" target="_blank" rel="{rel}">Apply now</a></div>'
        '</div></article>')


def swap(html, pattern, new):
    """Replace exactly one match, or stop: a silent miss would publish a wrong page."""
    out, n = re.subn(pattern, lambda m: new, html, count=1, flags=re.S)
    if n != 1:
        raise ValueError("index.html no longer contains: " + pattern)
    return out


def build(template, jobs, place, name, where):
    url = SITE + name
    if place == "Worldwide":
        title = "Remote jobs for freshers, open worldwide | Switchremote"
        h1 = "Remote jobs for freshers, open worldwide"
        desc = ("Work-from-home jobs that freshers can apply for from anywhere in the world, collected "
                "from company career pages and trusted job feeds. Free, no signup, apply on the employer's own page.")
        sub = ("These remote jobs are open to applicants anywhere in the world. We collect them from company "
               "career pages and trusted job feeds, so you apply directly on the employer's own page. "
               "No signup and no fees, ever.")
    else:
        title = f"Remote jobs for freshers {where} | Switchremote"
        h1 = f"Remote jobs for freshers {where}"
        desc = (f"Work-from-home jobs that freshers {where} can apply for, including remote jobs open worldwide. "
                "Collected from company career pages and trusted job feeds. Free, no signup.")
        sub = (f"Work-from-home jobs that freshers {where} can apply for, including remote jobs open worldwide. "
               "We collect them from company career pages and trusted job feeds, so you apply directly on the "
               "employer's own page. No signup and no fees, ever.")
    rows = [j for j in jobs if in_place(j, place)][:MAX_STATIC]
    crumbs = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Switchremote", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": h1, "item": url}]})
    e = lambda s: escape(s, quote=True)
    h = template
    h = swap(h, r"<title>.*?</title>", f"<title>{escape(title)}</title>")
    h = swap(h, r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(desc)}">')
    h = swap(h, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">')
    h = swap(h, r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(title)}">')
    h = swap(h, r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(desc)}">')
    h = swap(h, r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">')
    h = swap(h, r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{e(h1)}">')
    h = swap(h, r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{e(desc)}">')
    # The WebSite block belongs to the homepage only; country pages get a breadcrumb instead
    h = swap(h, r'<script type="application/ld\+json">\{"@context":"https://schema.org","@type":"WebSite".*?</script>',
             f'<script type="application/ld+json">{crumbs}</script>')
    h = swap(h, r"<h1>.*?</h1>", f"<h1>{escape(h1)}</h1>")
    h = swap(h, r'<p class="sub">.*?</p>', f'<p class="sub">{escape(sub)}</p>')
    h = swap(h, r'<main id="list"></main>', '<main id="list">' + "".join(card(j) for j in rows) + "</main>")
    h = swap(h, r'<script src="app.js"></script>',
             f'<script>window.SR_PLACE={json.dumps(place)};</script>\n<script src="app.js"></script>')
    (ROOT / name).write_text(h, encoding="utf-8")
    return len(rows)


def write_sitemap():
    path = ROOT / "sitemap.xml"
    old = dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", path.read_text())) if path.exists() else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(SITE, today, "daily", "1.0")]
    urls += [(SITE + name, today, "daily", "0.8") for _, name, _ in PAGES]
    urls += [(SITE + "scam-check.html", old.get(SITE + "scam-check.html", today), "monthly", "0.6"),
             (SITE + "legal.html", old.get(SITE + "legal.html", today), "monthly", "0.4")]
    body = "".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{mod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>\n"
        for loc, mod, freq, pri in urls)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def main():
    template = (ROOT / "index.html").read_text(encoding="utf-8")
    jobs = json.loads((ROOT / "data" / "jobs.json").read_text()).get("jobs", [])
    for place, name, where in PAGES:
        print(f"{name}: {build(template, jobs, place, name, where)} jobs")
    write_sitemap()
    print("sitemap.xml written")


if __name__ == "__main__":
    main()
