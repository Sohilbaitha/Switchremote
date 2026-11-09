import csv
import html
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "jobs.json"
SOURCES = ROOT / "sources.json"
HEADERS = {"User-Agent": "SwitchremoteBot/1.0"}
MAX_AGE_DAYS = 14
# A job that is still on the company's own careers board is still open, so it may stay longer
COMPANY_MAX_AGE_DAYS = 30
MAX_JOBS = 500

COUNTRIES = {
    "Indonesia": ["indonesia", "jakarta", "surabaya", "bandung", "bali"],
    "Vietnam": ["vietnam", "viet nam", "hanoi", "ho chi minh", "saigon", "da nang"],
    "Malaysia": ["malaysia", "kuala lumpur", "penang", "johor"],
    "Philippines": ["philippines", "manila", "cebu", "makati"],
    "Thailand": ["thailand", "bangkok", "chiang mai"],
    "India": ["india", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad",
              "pune", "chennai", "gurgaon", "gurugram", "noida"],
}
GLOBAL = ["worldwide", "anywhere", "global"]
# Asia-only jobs get their own honest label instead of "Anywhere in the World"
ASIA = ["apac", "asia", "asia pacific", "asia-pacific", "southeast asia", "south east asia"]
FRESHER = ["fresher", "freshers", "entry level", "entry-level", "junior", "intern",
           "internship", "trainee", "graduate", "fresh graduate", "fresh graduates",
           "no experience", "no prior experience", "0-1 year", "0-1 years",
           "0-2 years", "less than 1 year", "apprentice"]
ROLES = ["customer support", "customer service", "customer success", "support specialist",
         "support agent", "support representative", "chat support", "live chat",
         "data entry", "virtual assistant", "content writer", "content moderator",
         "social media", "appointment setter", "sales development", "community moderator",
         "transcription", "back office", "order processing", "associate"]
SENIOR = ["senior", "sr", "lead", "manager", "director", "principal", "head", "staff", "vp",
          "architect", "chief", "executive", "expert", "ii", "iii", "mid-level", "experienced"]
# Roles that need a licence or past experience, so they are not fresher jobs
# (kept only when the title itself says junior/intern/trainee)
EXPERIENCED = ["consultant", "counsel", "attorney", "lawyer", "accountant", "bookkeeper",
               "controller", "auditor", "drafter", "nurse", "physician", "pharmacist",
               "therapist", "supervisor"]
# Seniority labels that job feeds attach to a job
LEVEL_HIGH = ["senior", "mid", "mid-level", "midweight", "manager", "director", "executive",
              "lead", "principal"]
LEVEL_OK = ["entry", "entry-level", "junior", "intern", "internship", "graduate", "trainee", "any"]
TECH = ["engineer", "developer", "devops", "sre", "scientist", "analyst", "architect",
        "programmer", "security", "data engineer", "machine learning", "backend", "frontend",
        "full stack", "fullstack", "software"]
BAD = ["registration fee", "security deposit", "pay a fee", "processing fee", "investment required"]


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**HEADERS, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def has(text, words):
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def clean(text):
    return re.sub(r"<[^>]+>", " ", html.unescape(text or ""))[:4000]


def countries_for(location):
    t = (location or "").lower()
    found = [c for c, w in COUNTRIES.items() if has(t, w)]
    if not found and has(t, GLOBAL):
        found = ["Worldwide"]
    if not found and has(t, ASIA):
        found = ["Asia"]
    return found


def title_ok(title):
    """Fresher board rule for titles: no senior roles, no experience-only roles,
    and technical roles only when the title itself says junior/intern/trainee."""
    t = (title or "").lower()
    if has(t, SENIOR):
        return False
    if (has(t, TECH) or has(t, EXPERIENCED)) and not has(t, FRESHER):
        return False
    return True


def level_ok(level):
    """Drop a job when the feed itself marks it mid-level or above."""
    lv = (level or "").lower()
    return not (has(lv, LEVEL_HIGH) and not has(lv, LEVEL_OK))


def parse_date(value):
    if isinstance(value, str) and value.strip().isdigit():
        value = float(value)
    if isinstance(value, (int, float)):
        if value > 1e11:
            value /= 1000
        return datetime.fromtimestamp(value, timezone.utc)
    s = str(value).strip().replace("Z", "+00:00").replace(" UTC", "+00:00")
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def min_years(text):
    """Smallest 'N years' number asked for in the text, or None."""
    found = re.findall(r"(\d{1,2})\s*(?:\+|-|to|\u2013)?\s*(?:\d{1,2})?\s*\+?\s*(?:years|yrs)\b", text.lower())
    return min(int(n) for n in found) if found else None


# ---------- safety rules ----------
# Apply links that real employers almost never use: chat apps, link shorteners, forms, personal email
BAD_LINK = re.compile(
    r"(wa\.me|whatsapp\.com|(^|[/.])t\.me/|telegram\.(me|org)|bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|"
    r"is\.gd|shorturl\.at|forms\.gle|docs\.google\.com/forms|linktr\.ee|"
    r"mailto:[^ ]*@(gmail|yahoo|hotmail|outlook|ymail|rediffmail)\.)", re.I)
# Phrases that only show up in scams (asking for money, task scams, money mules, chat-app hiring)
SCAM = re.compile(
    r"\b((registration|processing|training|joining|application|onboarding) (fee|charge)s?|"
    r"(security|refundable) deposit|starter kit|pay to (apply|join)|advance payment|"
    r"money transfer agent|payment processing agent|reshipp?ing|package forwarding|"
    r"(like|rate|review) (videos|posts|products|hotels) (and|to) earn|prepaid task|"
    r"(contact|message|text|dm|chat with) (us |me |the recruiter )?(on|via) (whatsapp|telegram)|"
    r"telegram (id|handle|username)|unlimited (income|earning)|earn (rs\.?|inr|₹|\$) ?\d[\d,]* (per|a) day)\b", re.I)
# Recruitment / staffing agencies: allowed, but at most 2 jobs each so one agency cannot flood the board
AGENCY = re.compile(r"staff|recruit|agency|outsourc|manpower|placement|talent|hire|hiring|consultan", re.I)
AGENCY_MAX = 2
FEEDS = {"Remotive", "Jobicy", "Himalayas", "Remote OK"}
MIN_TEXT = 300   # feed jobs with almost no description are dropped


def bad_link(*links):
    return any(l and BAD_LINK.search(l) for l in links)


def make(title, company, location, url, posted, source, text, need_remote=False, logo="", check="",
         level="", expires=None):
    try:
        text = (text or "")[:4000]
        if not (title and url and url.startswith("http")):
            return None
        if bad_link(url, check):
            return None
        if source in FEEDS and len(text.strip()) < MIN_TEXT:
            return None
        if need_remote and "remote" not in (location + " " + title).lower():
            return None
        body = (title + " " + text).lower()
        if not title_ok(title) or not level_ok(level) or has(body, BAD) or SCAM.search(body):
            return None
        years = min_years(text)
        if years is not None and years >= 2:
            return None
        countries = countries_for(location)
        if not countries:
            return None
        return {
            "title": title.strip(),
            "company": (company or "Company").strip(),
            "countries": countries,
            "url": url,
            "posted": parse_date(posted).isoformat(),
            "source": source,
            **({"logo": logo} if isinstance(logo, str) and logo.startswith("https://") else {}),
            **({"expires": parse_date(expires).isoformat()} if expires else {}),
        }
    except Exception:
        return None


# ---------- job feeds ----------

def remotive():
    for j in get("https://remotive.com/api/remote-jobs")["jobs"]:
        yield make(j["title"], j["company_name"], j.get("candidate_required_location", ""),
                   j["url"], j["publication_date"], "Remotive",
                   clean(j.get("description")) + " " + j.get("category", ""),
                   logo=j.get("company_logo") or "")


def jobicy():
    seen = set()
    # All remote jobs, then Asia-Pacific and each of our countries as separate calls.
    # Jobicy fair use: keep Jobicy as the source, link to the Jobicy job page, poll at most hourly.
    batch = get("https://jobicy.com/api/v2/remote-jobs?count=100")["jobs"]
    for geo in ("apac", "india", "philippines", "indonesia", "vietnam", "malaysia", "thailand"):
        try:
            batch += get(f"https://jobicy.com/api/v2/remote-jobs?count=50&geo={geo}").get("jobs") or []
        except Exception as e:
            print(f"Jobicy {geo} skipped:", e)
    for j in batch:
        if j.get("id") in seen:
            continue
        seen.add(j.get("id"))
        geo = j.get("jobGeo", "")
        geo = " ".join(geo) if isinstance(geo, list) else geo
        level = j.get("jobLevel", "")
        level = " ".join(level) if isinstance(level, list) else level
        yield make(j["jobTitle"], j["companyName"], geo, j["url"], j["pubDate"], "Jobicy",
                   clean(j.get("jobDescription")) + " " + level,
                   logo=j.get("companyLogo") or "", level=level)


# Himalayas API terms: use applicationLink unchanged for Apply, show Himalayas as the source,
# show the jobs only on our own site (never in feeds or on other platforms), remove expired jobs.
HIMALAYAS = "https://himalayas.app/jobs/api"
HIMALAYAS_PLACES = ["Indonesia", "Vietnam", "Malaysia", "Philippines", "Thailand", "India"]


def himalayas_get(url):
    # A free Himalayas API key is optional. Add it as the GitHub secret HIMALAYAS_API_KEY if we get rate limited.
    key = os.environ.get("HIMALAYAS_API_KEY", "").strip()
    return get(url, {"Authorization": "Bearer " + key} if key else None)


def himalayas_job(j):
    places = [p.get("name", "") if isinstance(p, dict) else str(p)
              for p in (j.get("locationRestrictions") or [])]
    loc = " ".join(places) if places else "Worldwide"
    level = j.get("seniority") or []
    level = " ".join(level) if isinstance(level, list) else str(level)
    return make(j["title"], j["companyName"], loc,
                j.get("applicationLink") or j.get("guid"), j.get("pubDate"), "Himalayas",
                clean(j.get("description") or j.get("excerpt")) + " " + level,
                logo=j.get("companyLogo") or "", level=level, expires=j.get("expiryDate"))


def himalayas():
    """Newest jobs on Himalayas (5 pages of 20)."""
    cursor = None
    for page in range(5):
        if page and not cursor:
            url = f"{HIMALAYAS}?limit=20&offset={page * 20}"   # older paging, if no cursor is sent
        else:
            url = f"{HIMALAYAS}?limit=20" + ("&cursor=" + urllib.parse.quote(str(cursor)) if cursor else "")
        d = himalayas_get(url)
        for j in d.get("jobs") or []:
            yield himalayas_job(j)
        cursor = d.get("nextCursor")


def himalayas_search():
    """Entry-level jobs for each of our countries, plus entry-level jobs open worldwide."""
    queries = [("country=" + urllib.parse.quote(c)) for c in HIMALAYAS_PLACES] + ["worldwide=true"]
    worked = 0
    for q in queries:
        for page in (1, 2):
            try:
                d = himalayas_get(f"{HIMALAYAS}/search?{q}&seniority=Entry-level&sort=recent&page={page}")
            except Exception as e:
                print(f"Himalayas search {q} page {page} skipped:", e)
                break
            worked += 1
            rows = d.get("jobs") or []
            for j in rows:
                yield himalayas_job(j)
            if not rows:
                break
    if not worked:
        raise RuntimeError("no Himalayas search call worked")


def himalayas_closed(url):
    """True only when Himalayas itself says the job is closed or gone."""
    m = re.search(r"himalayas\.app/companies/([^/?#]+)/jobs/([^/?#]+)", url or "")
    if not m:
        return False
    try:
        himalayas_get(f"{HIMALAYAS}/companies/{m.group(1)}/jobs/{m.group(2)}")
        return False
    except urllib.error.HTTPError as e:
        return e.code in (404, 410)
    except Exception:
        return False


def remoteok():
    # Remote OK terms: credit Remote OK and link to the job's Remote OK page (followed link).
    # We do not use the Remote OK logo.
    for j in get("https://remoteok.com/api"):
        if not isinstance(j, dict) or not j.get("position"):
            continue
        yield make(j["position"], j.get("company", ""), j.get("location") or "Worldwide",
                   j.get("url"), j.get("date"), "Remote OK",
                   clean(j.get("description")) + " " + " ".join(j.get("tags") or []),
                   check=j.get("apply_url") or "")


# ---------- company career pages ----------

# Proper display names for companies whose careers link uses a short code
NAMES = {"automatticcareers": "Automattic", "wikimedia": "Wikimedia Foundation",
         "mozilla": "Mozilla", "supabase": "Supabase", "posthog": "PostHog",
         "gohighlevel": "HighLevel", "sprinto": "Sprinto", "gleanwork": "Glean",
         "elevenlabs": "ElevenLabs", "deel": "Deel", "zapier": "Zapier",
         "gitlab": "GitLab", "branch": "Branch International",
         "remotecom": "Remote", "invisibletech": "Invisible Technologies",
         "pricelabs": "PriceLabs", "canonical": "Canonical"}


def nice(slug, fallback=None):
    return NAMES.get(slug.lower()) or fallback or slug.replace("-", " ").title()


def greenhouse(slug):
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")["jobs"]:
        yield make(j["title"], nice(slug, j.get("company_name")),
                   (j.get("location") or {}).get("name", ""), j["absolute_url"],
                   j.get("first_published") or j["updated_at"], "Company site",
                   clean(j.get("content")), need_remote=True)


def lever(slug):
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        loc = (j.get("categories") or {}).get("location", "") or ""
        if j.get("workplaceType") == "remote":
            loc += " remote"
        yield make(j["text"], nice(slug), loc, j["hostedUrl"], j["createdAt"], "Company site",
                   j.get("descriptionPlain", ""), need_remote=True)


def ashby(slug):
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")["jobs"]:
        places = [j.get("location") or ""]
        for s in j.get("secondaryLocations") or []:
            places.append(s.get("location", "") if isinstance(s, dict) else str(s))
        loc = " ".join(places) + (" remote" if j.get("isRemote") else "")
        yield make(j["title"], nice(slug), loc,
                   j.get("jobUrl") or j.get("applyUrl"), j.get("publishedAt"), "Company site",
                   j.get("descriptionPlain") or clean(j.get("descriptionHtml")), need_remote=True)


def workable(slug):
    d = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        if j.get("telecommuting"):
            loc += " remote"
        yield make(j["title"], nice(slug, d.get("name")), loc, j.get("url") or j.get("shortlink"),
                   j.get("published_on") or j.get("created_at"), "Company site",
                   clean(j.get("description")), need_remote=True)


def recruitee(slug):
    for j in get(f"https://{slug}.recruitee.com/api/offers/").get("offers", []):
        loc = " ".join(x for x in [j.get("location"), j.get("city"), j.get("country")] if x)
        if j.get("remote"):
            loc += " remote"
        yield make(j["title"], j.get("company_name") or slug, loc, j.get("careers_url"),
                   j.get("published_at") or j.get("created_at"), "Company site",
                   clean(j.get("description")), need_remote=True)


# ---------- employer jobs from the Google Form sheet ----------

EMPLOYER_MAX_AGE_DAYS = 30
FORM_COUNTRIES = {"worldwide": "Worldwide", "indonesia": "Indonesia", "vietnam": "Vietnam",
                  "malaysia": "Malaysia", "philippines": "Philippines",
                  "thailand": "Thailand", "india": "India", "philipines": "Philippines"}


def get_text(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8-sig")


def sheet_date(value):
    """Form timestamps look like 5/11/2026 18:20:15. If day/month is unclear, use now."""
    now = datetime.now(timezone.utc)
    try:
        date_part, _, time_part = value.strip().partition(" ")
        a, b, year = [int(x) for x in date_part.split("/")]
        if a > 12:
            day, month = a, b
        elif b > 12:
            month, day = a, b
        else:
            return now
        h, m, sec = ([int(x) for x in time_part.split(":")] + [0, 0, 0])[:3]
        d = datetime(year, month, day, h, m, sec, tzinfo=timezone.utc)
        return min(d, now)
    except Exception:
        return now


def employer_sheet(url):
    cutoff = datetime.now(timezone.utc) - timedelta(days=EMPLOYER_MAX_AGE_DAYS)
    rows = list(csv.reader(io.StringIO(get_text(url))))
    for row in rows[1:]:
        row = [c.strip() for c in row] + [""] * 5
        stamp, company, title, country, link = row[:5]
        place = FORM_COUNTRIES.get(country.lower().replace(" ", ""))
        if link and not link.startswith("http") and "." in link and " " not in link:
            link = "https://" + link
        if not (company and title and place and link.startswith("http")):
            continue
        posted = sheet_date(stamp)
        if posted < cutoff:
            continue
        yield {"title": title, "company": company, "countries": [place], "url": link,
               "posted": posted.isoformat(), "source": "Employer"}


READERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
           "workable": workable, "recruitee": recruitee}


def detect(link):
    u = urllib.parse.urlparse(link.strip())
    host = u.netloc.lower()
    parts = [p for p in u.path.split("/") if p]
    first = parts[0] if parts else ""
    if "greenhouse.io" in host and first and first != "embed":
        return "greenhouse", first
    if host.endswith("lever.co") and first:
        return "lever", first
    if host.endswith("ashbyhq.com") and first:
        return "ashby", first
    if host.endswith("workable.com") and first:
        return "workable", first
    if host.endswith(".recruitee.com"):
        return "recruitee", host.split(".")[0]
    return None, None


def main():
    cfg = json.loads(SOURCES.read_text())
    tasks = [("Remotive", remotive), ("Jobicy", jobicy), ("Himalayas", himalayas),
             ("Himalayas entry-level search", himalayas_search), ("Remote OK", remoteok)]
    for link in cfg.get("companies", []):
        kind, slug = detect(link)
        if kind:
            tasks.append((f"{kind}:{slug}".lower(), lambda k=kind, s=slug: READERS[k](s)))
        else:
            print("UNKNOWN careers link (skipped):", link)

    found = {}
    succeeded = 0
    boards_ok = set()   # company boards that answered this time
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    company_cutoff = now - timedelta(days=COMPANY_MAX_AGE_DAYS)

    def fresh(job):
        limit = company_cutoff if job.get("source") == "Company site" else cutoff
        return parse_date(job["posted"]) >= limit

    def board_of(job):
        if job.get("board"):
            return job["board"]
        kind, slug = detect(job.get("url", ""))
        return f"{kind}:{slug}".lower() if kind else None

    for name, task in tasks:
        kept = 0
        is_board = ":" in name
        try:
            for job in task():
                if job and fresh(job):
                    if is_board:
                        job["board"] = name
                    found[job["url"]] = job
                    kept += 1
            succeeded += 1
            if is_board:
                boards_ok.add(name)
            print(f"OK    {name}: {kept} matching jobs")
        except Exception as e:
            print(f"FAIL  {name}: {e}")

    if cfg.get("sheet"):
        kept = 0
        try:
            for job in employer_sheet(cfg["sheet"]):
                found[job["url"]] = job
                kept += 1
            succeeded += 1
            print(f"OK    employer form: {kept} approved jobs")
        except Exception as e:
            print(f"FAIL  employer form: {e}")

    # Keep jobs from earlier refreshes until they are MAX_AGE_DAYS old.
    # Feeds only return their newest jobs, so without this good jobs vanish after a few hours.
    # Employer jobs are not carried over: they always follow the Sheet.
    # Company jobs are not carried over when their board answered: if the job is no longer
    # on the company's own board, it is closed.
    carried = closed = checks = 0
    if OUT.exists():
        try:
            for job in json.loads(OUT.read_text()).get("jobs", []):
                if job.get("source") == "Employer" or job.get("url") in found or not fresh(job):
                    continue
                if job.get("source") == "Company site":
                    board = board_of(job)
                    # Gone from a board that answered, or no way to re-check it after 14 days
                    if board in boards_ok or (board is None and parse_date(job["posted"]) < cutoff):
                        closed += 1
                        continue
                # Himalayas tells us when a job has closed, so ask before keeping an old one
                if job.get("source") == "Himalayas" and checks < 40:
                    checks += 1
                    if himalayas_closed(job.get("url")):
                        closed += 1
                        continue
                found[job["url"]] = job
                carried += 1
        except Exception as e:
            print("Could not read old jobs:", e)
    print(f"Kept {carried} jobs from earlier refreshes, removed {closed} that have closed")

    # Final safety pass on everything, including jobs kept from earlier refreshes
    blocked = [b.lower() for b in cfg.get("blocked_companies", []) if b.strip()]
    clean_jobs, per_agency, dropped = [], {}, 0
    # The same job often comes from two sources. Keep one copy, preferring the employer's own post
    # or the company's own career page over a job feed.
    rank = {"Employer": 0, "Company site": 1}
    seen_jobs = set()
    ordered = sorted(found.values(), key=lambda j: j["posted"], reverse=True)
    ordered.sort(key=lambda j: rank.get(j.get("source"), 2))
    keep = []
    for job in ordered:
        key = (re.sub(r"\W+", " ", job.get("company", "").lower()).strip(),
               re.sub(r"\W+", " ", job.get("title", "").lower()).strip())
        if key in seen_jobs:
            dropped += 1
            continue
        seen_jobs.add(key)
        keep.append(job)
    for job in sorted(keep, key=lambda j: j["posted"], reverse=True):
        name = job.get("company", "").lower()
        if any(b in name for b in blocked) or bad_link(job.get("url")):
            dropped += 1
            continue
        # Past the closing date the source gave us
        if job.get("expires") and parse_date(job["expires"]) < now:
            dropped += 1
            continue
        # Title rules also apply to jobs kept from earlier refreshes
        if job.get("source") != "Employer" and not title_ok(job.get("title")):
            dropped += 1
            continue
        if job.get("source") != "Employer" and AGENCY.search(name):
            per_agency[name] = per_agency.get(name, 0) + 1
            if per_agency[name] > AGENCY_MAX:
                dropped += 1
                continue
        clean_jobs.append(job)
    print(f"Safety pass removed {dropped} jobs")

    jobs = clean_jobs[:MAX_JOBS]
    if (succeeded == 0 or not jobs) and OUT.exists():
        print("No sources worked or nothing matched, keeping the old file.")
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"updated": datetime.now(timezone.utc).isoformat(), "jobs": jobs}, ensure_ascii=False))
    print(len(jobs), "jobs saved")


main()
