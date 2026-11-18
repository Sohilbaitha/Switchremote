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
    return {"Worldwide": "Any country", "Asia": "Asia-Pacific"}.get(x, x)


SOURCE_SITES = {"Remotive": "https://remotive.com", "Jobicy": "https://jobicy.com",
                "Himalayas": "https://himalayas.app", "Remote OK": "https://remoteok.com"}


def source_tag(source):
    if source == "Employer":
        return '<span class="tag">Posted by employer</span>'
    site = SOURCE_SITES.get(source)
    if not site:
        return f'<span class="tag">{escape(source)}</span>'
    rel = "noopener" if source == "Remote OK" else "noopener noreferrer"
    return f'<a class="tag tag-src" href="{site}" target="_blank" rel="{rel}">via {escape(source)}</a>'


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
        f'{source_tag(j.get("source", ""))}</div>'
        f'<div class="actions"><a class="apply" href="{escape(j["url"], quote=True)}" target="_blank" rel="{rel}">Apply now</a></div>'
        '</div></article>')


LIST = r'<main id="list">.*?</main>'


def build_home(jobs):
    """The homepage gets the current jobs written in too, so search engines see them without running app.js."""
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    new = swap(html, LIST, '<main id="list">' + "".join(card(j) for j in jobs[:MAX_STATIC]) + "</main>")
    if new != html:
        path.write_text(new, encoding="utf-8")
    return min(len(jobs), MAX_STATIC)


def swap(html, pattern, new):
    """Replace exactly one match, or stop: a silent miss would publish a wrong page."""
    out, n = re.subn(pattern, lambda m: new, html, count=1, flags=re.S)
    if n != 1:
        raise ValueError("index.html no longer contains: " + pattern)
    return out


COUNTRY_WORD = {"Philippines": "the Philippines"}


def country_faq(place, rows):
    """Questions people in this country search for, answered from the jobs listed right now."""
    if place == "Worldwide":
        return []
    c = COUNTRY_WORD.get(place, place)
    local = [j for j in rows if place in j.get("countries", [])]
    anyw = [j for j in rows if "Worldwide" in j.get("countries", []) or "Asia" in j.get("countries", [])]
    picks = (local + [j for j in anyw if j not in local])[:3]
    if picks:
        now = "Right now you can find " + ", ".join(f"{j['title']} at {j.get('company', '')}" for j in picks) + \
              f". The list changes every 6 hours, so check back often."
    else:
        now = "There are no openings for this country at the moment. New jobs come in every 6 hours, so check back soon."
    return [
        (f"Can freshers in {c} get a remote job with no experience?",
         f"Yes. Every job on this page is remote and picked for freshers, such as internships, trainee, graduate and entry-level roles. "
         f"We leave out jobs that ask for two or more years of experience. Some jobs are only for people in {c}, "
         f"and some are open to any country, which you can also apply for from {c}."),
        (f"Which work from home jobs for freshers are open in {c} now?", now),
        (f"Do I need to pay to apply for a remote job in {c}?",
         "No. You apply for free on the company's own page, and you do not need an account on Switchremote. "
         "A real employer will never ask you to pay for a job, training or equipment."),
    ]


def build(template, jobs, place, name, where):
    url = SITE + name
    if place == "Worldwide":
        title = "Remote, work from home jobs for freshers in any country | Switchremote"
        h1 = "Remote jobs for freshers, open to any country"
        desc = ("Work-from-home jobs that freshers can apply for from any country, gathered "
                "from company career pages and trusted remote job boards. Free, no signup, refreshed every 6 hours.")
        sub = "Remote jobs open to freshers in any country. Free, no signup, and you apply on the company's own page."
    else:
        title = f"Remote, work from home jobs for freshers {where} | Switchremote"
        h1 = f"Remote jobs for freshers {where}"
        desc = (f"Work-from-home jobs that freshers {where} can apply for, including remote jobs open to any country. "
                "Gathered from company career pages and trusted remote job boards. Free, no signup.")
        sub = f"Work-from-home jobs that freshers {where} can apply for. Free, no signup, and you apply on the company's own page."
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
    # The homepage FAQ data stays on the homepage; country pages get their own questions
    faq = country_faq(place, rows)
    faq_ld = ""
    if faq:
        faq_ld = '<script type="application/ld+json" id="faq-ld">' + json.dumps({
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
            ensure_ascii=False) + "</script>\n"
    h = swap(h, r'<script type="application/ld\+json" id="faq-ld">.*?</script>\n?', faq_ld)
    if faq:
        # One "Good to know" list: this country's questions first, without repeating the general
        # questions they already answer (is it free, can freshers apply)
        block = "".join(f'\n    <details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q, a in faq)
        h = swap(h, r'<h2 id="faq-h">Good to know</h2>', '<h2 id="faq-h">Good to know</h2>' + block)
        h = swap(h, r'\s*<details><summary>Is Switchremote free\?</summary>.*?</details>', "")
        h = swap(h, r"\s*<details><summary>I'm a fresher with no experience\. Can I apply\?</summary>.*?</details>", "")
    h = swap(h, r"<h1>.*?</h1>", f"<h1>{escape(h1)}</h1>")
    h = swap(h, r'<p class="sub">.*?</p>', f'<p class="sub">{escape(sub)}</p>')
    # Mark this country's chip as the selected one in the plain HTML too
    h = h.replace('<a class="chip on" href="./">', '<a class="chip" href="./">', 1)
    h = h.replace(f'<a class="chip" href="{name}">', f'<a class="chip on" href="{name}" aria-current="page">', 1)
    h = swap(h, LIST, '<main id="list">' + "".join(card(j) for j in rows) + "</main>")
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
    for page, pri in (("post-a-job.html", "0.6"), ("about.html", "0.5"),
                      ("contact.html", "0.4"), ("terms.html", "0.3"), ("privacy.html", "0.3"),
                      ("disclaimer.html", "0.3")):
        if (ROOT / page).exists():
            urls.append((SITE + page, old.get(SITE + page, today), "monthly", pri))
    body = "".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{mod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>\n"
        for loc, mod, freq, pri in urls)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def update_counts():
    """Keep the numbers in "How we pick jobs" in step with sources.json."""
    src = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    nums = {"pages": len(src.get("companies", [])), "approved": len(src.get("approved_companies", []))}
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    new = html
    for key, value in nums.items():
        new = re.sub(r'(<span data-n="%s">)\d+(</span>)' % key, r"\g<1>%d\g<2>" % value, new)
    if new != html:
        path.write_text(new, encoding="utf-8")


def main():
    update_counts()
    template = (ROOT / "index.html").read_text(encoding="utf-8")
    jobs = json.loads((ROOT / "data" / "jobs.json").read_text()).get("jobs", [])
    for place, name, where in PAGES:
        print(f"{name}: {build(template, jobs, place, name, where)} jobs")
    print(f"index.html: {build_home(jobs)} jobs")
    write_sitemap()
    print("sitemap.xml written")


if __name__ == "__main__":
    main()
