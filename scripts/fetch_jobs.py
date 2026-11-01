import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "jobs.json"
SOURCES = ROOT / "sources.json"
HEADERS = {"User-Agent": "SwitchremoteBot/1.0"}
MAX_AGE_DAYS = 3
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
GLOBAL = ["worldwide", "anywhere", "global", "apac", "asia", "southeast asia"]
FRESHER = ["fresher", "freshers", "entry level", "entry-level", "junior", "intern",
           "internship", "trainee", "graduate", "fresh graduate", "fresh graduates",
           "no experience", "no prior experience", "0-1 year", "0-1 years",
           "0-2 years", "less than 1 year", "apprentice"]
SENIOR = ["senior", "sr", "lead", "manager", "director", "principal", "head", "staff", "vp"]
BAD = ["registration fee", "security deposit", "pay a fee", "processing fee", "investment required"]


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def has(text, words):
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def clean(text):
    return re.sub(r"<[^>]+>", " ", html.unescape(text or ""))[:1500]


def countries_for(location):
    t = (location or "").lower()
    found = [c for c, w in COUNTRIES.items() if has(t, w)]
    if not found and has(t, GLOBAL):
        found = ["Worldwide"]
    return found


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


def make(title, company, location, url, posted, source, text, need_remote=False):
    try:
        text = (text or "")[:1500]
        if not (title and url and url.startswith("http")):
            return None
        if need_remote and "remote" not in (location + " " + title).lower():
            return None
        body = (title + " " + text).lower()
        if has(title.lower(), SENIOR) or has(body, BAD) or not has(body, FRESHER):
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
        }
    except Exception:
        return None


# ---------- job feeds ----------

def remotive():
    for j in get("https://remotive.com/api/remote-jobs")["jobs"]:
        yield make(j["title"], j["company_name"], j.get("candidate_required_location", ""),
                   j["url"], j["publication_date"], "Remotive",
                   clean(j.get("description")) + " " + j.get("category", ""))


def jobicy():
    for j in get("https://jobicy.com/api/v2/remote-jobs?count=100")["jobs"]:
        geo = j.get("jobGeo", "")
        geo = " ".join(geo) if isinstance(geo, list) else geo
        level = j.get("jobLevel", "")
        level = " ".join(level) if isinstance(level, list) else level
        yield make(j["jobTitle"], j["companyName"], geo, j["url"], j["pubDate"], "Jobicy",
                   clean(j.get("jobDescription")) + " " + level)


def himalayas():
    for offset in (0, 20, 40):
        for j in get(f"https://himalayas.app/jobs/api?limit=20&offset={offset}")["jobs"]:
            places = j.get("locationRestrictions") or []
            loc = " ".join(places) if places else "Worldwide"
            level = " ".join(j.get("seniority") or [])
            yield make(j["title"], j["companyName"], loc,
                       j.get("applicationLink") or j.get("guid"), j.get("pubDate"), "Himalayas",
                       clean(j.get("description") or j.get("excerpt")) + " " + level)


# ---------- company career pages ----------

def greenhouse(slug):
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")["jobs"]:
        yield make(j["title"], j.get("company_name") or slug,
                   (j.get("location") or {}).get("name", ""), j["absolute_url"],
                   j.get("first_published") or j["updated_at"], "Company site",
                   clean(j.get("content")), need_remote=True)


def lever(slug):
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        loc = (j.get("categories") or {}).get("location", "") or ""
        if j.get("workplaceType") == "remote":
            loc += " remote"
        yield make(j["text"], slug, loc, j["hostedUrl"], j["createdAt"], "Company site",
                   j.get("descriptionPlain", ""), need_remote=True)


def ashby(slug):
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")["jobs"]:
        places = [j.get("location") or ""]
        for s in j.get("secondaryLocations") or []:
            places.append(s.get("location", "") if isinstance(s, dict) else str(s))
        loc = " ".join(places) + (" remote" if j.get("isRemote") else "")
        yield make(j["title"], slug.replace("-", " ").title(), loc,
                   j.get("jobUrl") or j.get("applyUrl"), j.get("publishedAt"), "Company site",
                   j.get("descriptionPlain") or clean(j.get("descriptionHtml")), need_remote=True)


def workable(slug):
    d = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        if j.get("telecommuting"):
            loc += " remote"
        yield make(j["title"], d.get("name") or slug, loc, j.get("url") or j.get("shortlink"),
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
    tasks = [("Remotive", remotive), ("Jobicy", jobicy), ("Himalayas", himalayas)]
    for link in cfg.get("companies", []):
        kind, slug = detect(link)
        if kind:
            tasks.append((f"{kind}:{slug}", lambda k=kind, s=slug: READERS[k](s)))
        else:
            print("UNKNOWN careers link (skipped):", link)

    found = {}
    succeeded = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    for name, task in tasks:
        kept = 0
        try:
            for job in task():
                if job and parse_date(job["posted"]) >= cutoff:
                    found[job["url"]] = job
                    kept += 1
            succeeded += 1
            print(f"OK    {name}: {kept} matching jobs")
        except Exception as e:
            print(f"FAIL  {name}: {e}")

    jobs = sorted(found.values(), key=lambda j: j["posted"], reverse=True)[:MAX_JOBS]
    if succeeded == 0 and OUT.exists():
        print("All sources failed, keeping the old file.")
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"updated": datetime.now(timezone.utc).isoformat(), "jobs": jobs}, ensure_ascii=False))
    print(len(jobs), "jobs saved")


main()
