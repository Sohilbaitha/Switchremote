"""Builds one page per country (remote-jobs-india.html and so on), one page per
company-site or employer job (remote-job-....html), and sitemap.xml.

Each country page is a copy of index.html with its own title, description and
heading, and with the current jobs written into the page itself, so search
engines can read the jobs without running any script. Change the design in
index.html only; these pages follow it on the next refresh.
"""
import json
import re
from datetime import datetime, timedelta, timezone
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
    ("Internships", "remote-internships.html", ""),
]

INTERN = re.compile(r"\bintern(s|ship|ships)?\b", re.I)


def is_intern(job):
    return bool(INTERN.search(job.get("title", "")) or INTERN.search(job.get("kind") or ""))


def in_place(job, place):
    if place == "Internships":
        return is_intern(job)
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


# ---------- one page per job ----------
# Only jobs from company career pages and employers get their own page and Google Jobs data.
# Jobs from job boards stay on job.html (not indexed): Remotive asks that its jobs are never
# sent to Google Jobs, and Himalayas asks that its jobs are not passed on to other platforms.
OWN_SOURCES = {"Company site", "Employer"}
TARGETS = ["India", "Philippines", "Indonesia", "Vietnam", "Malaysia", "Thailand"]
COUNTRY_CODES = {"India": "IN", "Philippines": "PH", "Indonesia": "ID", "Vietnam": "VN",
                 "Malaysia": "MY", "Thailand": "TH"}
KEEP_DAYS = 14
EMPLOYMENT = {"intern": "INTERN", "full": "FULL_TIME", "part": "PART_TIME", "contract": "CONTRACTOR",
              "temporary": "TEMPORARY", "freelance": "CONTRACTOR"}


def job_id(j):
    """Same short id as jobId() in app.js and job.js."""
    h = 2166136261
    for ch in j["url"]:
        o = ord(ch)
        h ^= o if o < 0x10000 else 0xD800 + ((o - 0x10000) >> 10)   # JS charCodeAt(0) of the character
        h = (h * 16777619) & 0xFFFFFFFF
    n, out = h, ""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


def slug(text):
    t = re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " and ")).strip("-")
    return t[:70].rstrip("-")


def page_name(j):
    if j.get("source") not in OWN_SOURCES:
        return None
    return f"remote-job-{slug(j.get('company', '') + ' ' + short_title(j))}-{job_id(j)}.html"


def title_safe(t):
    """Titles shown in Google: no commas and no long dashes, only " - " and " | "."""
    t = re.sub(r"\s*[\u2013\u2014]\s*", " - ", t)
    t = re.sub(r"\s*,\s*", " - ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def short_title(j):
    """The title without a trailing ", Company name" part, which repeats the company."""
    parts = [p.strip() for p in clean_title(j["title"]).split(",")]
    first = (j.get("company") or "").lower().split(" ")[0]
    if len(parts) > 1 and first and first in parts[-1].lower():
        parts = parts[:-1]
    return ", ".join(parts)


def clean_title(t):
    t = re.sub(r"\s+-\s+", " ", t)                    # "Backend - Intern" reads as "Backend Intern"
    t = re.sub(r"\s*[\u2013\u2014]\s*", " - ", t)       # long dashes become a plain " - "
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def where_text(j):
    c = j.get("countries", [])
    if "Worldwide" in c:
        return "open to any country"
    if "Asia" in c:
        return "open across Asia-Pacific"
    return "in " + ", ".join(c)


def job_ld(j):
    """Google Jobs data, built only from facts in the listing."""
    title = short_title(j)
    where = where_text(j)
    kind = (j.get("kind") or "").strip()
    desc = (f"<p>{escape(j.get('company', ''))} is hiring for {escape(title)}. "
            f"This is a remote {escape(kind.lower() + ' ') if kind else ''}role, {escape(where)}, "
            f"and suited to freshers.</p>")
    if j.get("summary"):
        desc += f"<p>{escape(j['summary'])}</p>"
    desc += "<p>Read the full listing and apply on the company's own careers page.</p>"
    c = j.get("countries", [])
    places = TARGETS if ("Worldwide" in c or "Asia" in c) else [x for x in c if x in COUNTRY_CODES]
    posted = j.get("posted", "")[:10]
    try:
        until = datetime.fromisoformat(j.get("expires") or "")
    except ValueError:
        until = None
    if not until:
        try:
            until = datetime.fromisoformat(j["posted"].replace("Z", "+00:00")) + timedelta(days=KEEP_DAYS)
        except (KeyError, ValueError):
            until = None
    ld = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": title_safe(title),
        "description": desc,
        "datePosted": posted,
        "hiringOrganization": {"@type": "Organization", "name": j.get("company", "")},
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": [{"@type": "Country", "name": x} for x in places],
        "directApply": False,
        "identifier": {"@type": "PropertyValue", "name": "Switchremote", "value": job_id(j)},
    }
    m = re.search(r"domain=([^&]+)", j.get("logo") or "")
    if m:
        ld["hiringOrganization"]["sameAs"] = "https://" + m.group(1)
    if until:
        ld["validThrough"] = until.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    for key, value in EMPLOYMENT.items():
        if key in kind.lower():
            ld["employmentType"] = value
            break
    return ld


def build_job_page(template, j, name):
    title = short_title(j)
    company = j.get("company", "")
    where = where_text(j)
    full = title_safe(f"{title} at {company}") + " - remote job for freshers"
    desc = f"{title} at {company}. Remote work from home job for freshers, {where}. Free to apply on the company's own page, no signup."
    url = SITE + name
    h = template
    h = swap(h, r"<title>.*?</title>", f"<title>{escape(full)} | Switchremote</title>")
    h = swap(h, r'<meta name="robots" content="[^"]*">', '<meta name="robots" content="index, follow, max-image-preview:large">')
    h = swap(h, r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{escape(desc, quote=True)}">')
    h = swap(h, r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{escape(full, quote=True)}">')
    h = swap(h, r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{escape(full, quote=True)}">')
    h = swap(h, r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{escape(desc, quote=True)}">')
    h = swap(h, r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{escape(desc, quote=True)}">')
    h = swap(h, r'<meta property="og:url" content="[^"]*">',
             f'<meta property="og:url" content="{url}">\n<link rel="canonical" href="{url}">\n'
             f'<script type="application/ld+json">{json.dumps(job_ld(j), ensure_ascii=False)}</script>\n'
             '<script type="application/ld+json">' + json.dumps({
                 "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                     {"@type": "ListItem", "position": 1, "name": "Switchremote", "item": SITE},
                     {"@type": "ListItem", "position": 2, "name": title_safe(f"{title} at {company}"), "item": url}]},
                 ensure_ascii=False) + "</script>")
    rel = "noopener noreferrer nofollow"
    static = (f'<a class="jd-back" href="./">All jobs</a>'
              f'<h1>{escape(title)}</h1><p class="jd-co">{escape(company)}</p>'
              f'<p>Remote, {escape(where)}.</p>'
              + (f'<p>{escape(j["summary"])}</p>' if j.get("summary") else "")
              + f'<a class="apply" href="{escape(j["url"], quote=True)}" target="_blank" rel="{rel}">Apply on the company site</a>')
    h = swap(h, r'<p class="status">Loading this job\.\.\.</p>', static)
    h = swap(h, r'<script src="job.js"></script>', f'<script>window.SR_JOB_ID={json.dumps(job_id(j))};</script>\n<script src="job.js"></script>')
    path = ROOT / name
    if not path.exists() or path.read_text(encoding="utf-8") != h:
        path.write_text(h, encoding="utf-8")


def update_llms(jobs):
    """llms.txt lists the current company-site and employer jobs (never job-board jobs)."""
    path = ROOT / "llms.txt"
    text = path.read_text(encoding="utf-8")
    lines = [f"- [{title_safe(short_title(j))} at {j.get('company', '')}]({SITE}{page_name(j)}): "
             f"Remote, {where_text(j)}" for j in jobs if page_name(j)]
    block = ("## Latest jobs from company career pages\n\n" + ("\n".join(lines) if lines else "- None right now") + "\n\n")
    text = re.sub(r"## Latest jobs from company career pages\n\n.*?\n\n(?=## )", "", text, flags=re.S)
    text = text.replace("## Tools\n", block + "## Tools\n", 1)
    path.write_text(text, encoding="utf-8")


# ---------- companies page ----------
# Names shown once even when the approved list has two spellings of the same company
SAME_AS = {"Cengage": "Cengage Group", "Dell": "Dell Technologies", "PhysicsWallah": "Physics Wallah",
           "TCS": "Tata Consultancy Services", "Think Academy US": "Think Academy"}
BOARD_NAMES = {"branch": "Branch International", "gohighlevel": "HighLevel", "contentsquare": "Contentsquare"}


def all_companies():
    cfg = json.loads((ROOT / "sources.json").read_text())
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    names = {norm(a): a for a in cfg.get("approved_companies", [])}
    for url in cfg.get("companies", []):
        slug = url.rstrip("/").split("/")[-1]
        dom = cfg.get("company_sites", {}).get(slug, "")
        root = dom.split(".")[0] if dom else slug
        if not (names.get(norm(slug)) or names.get(norm(root))):
            n = BOARD_NAMES.get(slug, root.title())
            names[norm(n)] = n
    out = {}
    for n in names.values():
        n = SAME_AS.get(n, n)
        out[norm(n)] = n
    return sorted(out.values(), key=lambda x: x.lower())


def build_companies(jobs):
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    live = {}
    for j in jobs:
        live[norm(j.get("company", ""))] = live.get(norm(j.get("company", "")), 0) + 1
    names = all_companies()
    hiring = [n for n in names if live.get(norm(n))]
    # Live jobs whose company spelling differs slightly from the list still count
    for j in jobs:
        c = j.get("company", "")
        if c and not any(norm(c) == norm(n) for n in names) and c not in hiring:
            hiring.append(c)
            names.append(c)
    hiring.sort(key=lambda x: x.lower())
    names = sorted(set(names), key=lambda x: x.lower())
    from urllib.parse import quote
    links = json.loads((ROOT / "data" / "company_links.json").read_text())
    def logo(n):
        dom = links.get(n, {}).get("domain", "")
        first = escape(n[:1].upper())
        # Logos are stored on our own site (logos/<domain>.png); without one we show the first letter
        img = (f'<img src="logos/{dom}.png" alt="" width="28" height="28" loading="lazy" onerror="this.remove()">'
               if dom and (ROOT / "logos" / f"{dom}.png").exists() else "")
        return f'<span class="co-logo" aria-hidden="true">{first}{img}</span>'
    def careers(n):
        u = links.get(n, {}).get("careers", "")
        return u
    hire_html = "".join(
        f'<li><a class="co-card" href="/?q={quote(n)}">{logo(n)}<span class="co-n">{escape(n)}</span>'
        f'<span class="co-c">{live.get(norm(n), 0)} {"job" if live.get(norm(n), 0) == 1 else "jobs"} live</span></a></li>'
        for n in hiring)
    groups = {}
    for n in names:
        k = n[0].upper() if n[0].isalpha() else "#"
        groups.setdefault(k, []).append(n)
    def item(n):
        u = careers(n)
        inner = f'{logo(n)}<span>{escape(n)}</span>'
        if u:
            return (f'<li><a href="{escape(u, quote=True)}" target="_blank" rel="noopener noreferrer nofollow" '
                    f'data-track="company_careers_click" title="{escape(n, quote=True)} careers page">{inner}'
                    f'<span class="co-ext" aria-hidden="true">&#8599;</span></a></li>')
        return f"<li><span class=\"co-plain\">{inner}</span></li>"
    az = "".join(f'<h3 class="co-l">{k}</h3><ul class="co-all">' + "".join(item(n) for n in v) + "</ul>"
                 for k, v in sorted(groups.items()))
    url = SITE + "companies.html"
    title = "Remote Jobs for Freshers by Company | Switchremote"
    desc = (f"{len(names)} companies whose remote jobs for freshers we list on Switchremote, including Canonical, SAP, Paytm "
            "and Canva. See which companies have remote fresher jobs and internships open right now.")
    body = (f'<main class="wrap legal companies">\n  <h1>Companies on Switchremote</h1>\n'
            f'  <p>We list remote jobs for freshers from these {len(names)} companies whenever they have one open. '
            f'Tap a company with live jobs to see them, or tap any company below to open its official careers page.</p>\n'            f'  <p class="meta">Switchremote is not affiliated with, endorsed by or sponsored by any of these companies. '
            f'Company names are shown only to tell you whose jobs we list, and all trademarks belong to their owners.</p>\n'
            f'  <h2>Hiring now</h2>\n  <ul class="co-hire">{hire_html}</ul>\n'
            f'  <h2>All companies A to Z</h2>\n  {az}\n'
            f'  <p class="meta">Want your company here? <a href="post-a-job.html" data-track="post_job_click">Post a remote job for free</a>.</p>\n'
            f'</main>')
    h = (ROOT / "about.html").read_text(encoding="utf-8")
    e = lambda x: escape(x, quote=True)
    h = swap(h, r"<title>.*?</title>", f"<title>{escape(title)}</title>")
    h = swap(h, r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(desc)}">')
    h = swap(h, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">')
    h = swap(h, r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(title)}">')
    h = swap(h, r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{e(title)}">')
    h = swap(h, r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(desc)}">')
    h = swap(h, r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{e(desc)}">')
    h = swap(h, r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">')
    h = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", h, flags=re.S)
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Switchremote", "item": SITE},
        {"@type": "ListItem", "position": 2, "name": "Companies", "item": url}]}
    h = h.replace("</head>", f'<script type="application/ld+json">{json.dumps(crumbs)}</script>\n</head>', 1)
    h = swap(h, r'<main class="wrap legal">.*?</main>', body)
    path = ROOT / "companies.html"
    if not path.exists() or path.read_text(encoding="utf-8") != h:
        path.write_text(h, encoding="utf-8")
    return len(names), len(hiring)


def build_job_pages(jobs):
    """Write a page for each company-site or employer job and delete pages of jobs that left the list."""
    template = (ROOT / "job.html").read_text(encoding="utf-8")
    keep = set()
    for j in jobs:
        name = page_name(j)
        if name:
            build_job_page(template, j, name)
            keep.add(name)
    for old in ROOT.glob("remote-job-*.html"):
        if old.name not in keep:
            old.unlink()
    return keep


def card(j):
    tags = "".join(f'<span class="tag">{escape(place_name(c))}</span>' for c in j.get("countries", []))
    rel = "noopener" if j.get("source") == "Remote OK" else "noopener noreferrer nofollow"
    return (
        '<article class="job">'
        f'<div class="av">{escape((j.get("company") or "?").strip()[:1].upper())}</div>'
        '<div class="body">'
        + (f'<div class="top"><h2><a href="{page_name(j)}">{escape(j["title"])}</a></h2></div>' if page_name(j)
           else f'<div class="top"><h2>{escape(j["title"])}</h2></div>') +
        f'<p class="company">{escape(j.get("company", ""))}</p>'
        f'<div class="tags"><span class="tag"><i class="sw"></i>Remote</span>{tags}'
        f'{source_tag(j.get("source", ""))}</div>'
        f'<div class="actions"><a class="apply" href="{escape(j["url"], quote=True)}" target="_blank" rel="{rel}">Apply now</a></div>'
        '</div></article>')


LIST = r'<main id="list">.*?</main>'


def list_ld(rows, url, name):
    """Tells search engines and AI tools what this page lists and when it last changed."""
    items = []
    for j in rows:
        page = page_name(j)
        items.append({"@type": "ListItem", "position": len(items) + 1,
                      "name": f"{title_safe(short_title(j))} at {j.get('company', '')}",
                      **({"url": SITE + page} if page else {})})
    data = {"@context": "https://schema.org", "@type": "CollectionPage", "name": name, "url": url,
            "dateModified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "isPartOf": {"@type": "WebSite", "name": "Switchremote", "url": SITE},
            "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items}}
    return '<script type="application/ld+json" id="list-ld">' + json.dumps(data, ensure_ascii=False) + "</script>"


def put_list_ld(html, block):
    if 'id="list-ld"' in html:
        return swap(html, r'<script type="application/ld\+json" id="list-ld">.*?</script>', block)
    return html.replace("</head>", block + "\n</head>", 1)


def build_home(jobs):
    """The homepage gets the current jobs written in too, so search engines see them without running app.js."""
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    new = swap(html, LIST, '<main id="list">' + "".join(card(j) for j in jobs[:MAX_STATIC]) + "</main>")
    new = put_list_ld(new, list_ld(jobs[:MAX_STATIC], SITE, "Remote jobs for freshers"))
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
    if place == "Internships":
        picks = rows[:3]
        now = ("Right now you can find " + ", ".join(f"{j['title']} at {j.get('company', '')}" for j in picks) +
               ". The list changes every 6 hours, so check back often.") if picks else \
              "There are no remote internships at the moment. New jobs come in every 6 hours, so check back soon."
        return [
            ("Can students and freshers get a remote internship with no experience?",
             "Yes. Every internship on this page is fully remote and open to students and freshers. Each one shows "
             "which countries it is open to, so check that you can apply from where you live."),
            ("Which work from home internships are open now?", now),
            ("Do I need to pay to apply for a remote internship?",
             "No. You apply for free on the company's own page, and you do not need an account on Switchremote. "
             "A real employer will never ask you to pay for an internship, training or a certificate."),
        ]
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
    if place == "Internships":
        title = "Remote Internships for Freshers - Work From Home | Switchremote"
        h1 = "Remote internships"
        desc = ("Remote and work from home internships for students and freshers in India, the Philippines, Southeast Asia "
                "and worldwide. No experience needed. Free, no signup, updated every 6 hours.")
        sub = "Work-from-home internships for students and freshers. Free, no signup, and you apply on the company's own page."
    elif place == "Worldwide":
        title = "Remote Jobs for Freshers Worldwide - Work From Home | Switchremote"
        h1 = "Remote jobs for freshers, open to any country"
        desc = ("Remote and work from home jobs for freshers in any country. Internships, trainee, graduate and "
                "entry-level roles for people with little or no experience. Free, no signup, updated every 6 hours.")
        sub = "Remote jobs open to freshers in any country. Free, no signup, and you apply on the company's own page."
    else:
        title = f"Remote Jobs for Freshers {where} - Work From Home | Switchremote"
        h1 = f"Remote jobs for freshers {where}"
        desc = (f"Remote and work from home jobs for freshers {where}. Internships, trainee, graduate and entry-level "
                "roles for people with little or no experience. Free, no signup, updated every 6 hours.")
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
    h = swap(h, r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{e(title)}">')
    h = put_list_ld(h, list_ld(rows, url, h1))
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


def write_sitemap(jobs=()):
    path = ROOT / "sitemap.xml"
    old = dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", path.read_text())) if path.exists() else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(SITE, today, "daily", "1.0")]
    urls += [(SITE + name, today, "daily", "0.8") for _, name, _ in PAGES]
    for page, pri in (("post-a-job.html", "0.6"), ("companies.html", "0.6"), ("about.html", "0.5"),
                      ("contact.html", "0.4"), ("terms.html", "0.3"), ("privacy.html", "0.3"),
                      ("disclaimer.html", "0.3")):
        if (ROOT / page).exists():
            urls.append((SITE + page, old.get(SITE + page, today), "monthly", pri))
    for j in jobs:
        name = page_name(j)
        if name:
            urls.append((SITE + name, (j.get("posted") or today)[:10], "weekly", "0.7"))
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
    pages = build_job_pages(jobs)
    update_llms(jobs)
    print(f"job pages: {len(pages)}")
    # app.js links each job to its own page when it has one
    data_path = ROOT / "data" / "jobs.json"
    data = json.loads(data_path.read_text())
    changed = False
    for j in data.get("jobs", []):
        name = page_name(j)
        if j.get("page") != name:
            changed = True
            if name:
                j["page"] = name
            else:
                j.pop("page", None)
    if changed:
        data_path.write_text(json.dumps(data, ensure_ascii=False))
    for place, name, where in PAGES:
        print(f"{name}: {build(template, jobs, place, name, where)} jobs")
    print(f"index.html: {build_home(jobs)} jobs")
    print("companies.html: %d companies, %d hiring now" % build_companies(jobs))
    write_sitemap(jobs)
    print("sitemap.xml written")


if __name__ == "__main__":
    main()
