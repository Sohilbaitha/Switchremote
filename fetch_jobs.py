import html
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "jobs.json"
SOURCES = ROOT / "sources.json"
HEADERS = {"User-Agent": "SwitchremoteBot/1.0"}
MAX_AGE_DAYS = 45
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
           "internship", "trainee", "graduate", "no experience", "0-1 year", "0-2 years"]
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
    if isinstance(value, (int, float)):
        if value > 1e11:
            value /= 1000
        return datetime.fromtimestamp(value, timezone.utc)
    d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def make(title, company, location, url, posted, source, text, need_remote=False):
    try:
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


def greenhouse(token):
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")["jobs"]:
        yield make(j["title"], j.get("company_name") or token,
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


def main():
    cfg = json.loads(SOURCES.read_text())
    tasks = [remotive, jobicy]
    tasks += [lambda t=t: greenhouse(t) for t in cfg.get("greenhouse", [])]
    tasks += [lambda s=s: lever(s) for s in cfg.get("lever", [])]

    found = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    for task in tasks:
        try:
            for job in task():
                if job and parse_date(job["posted"]) >= cutoff:
                    found[job["url"]] = job
        except Exception as e:
            print("Source failed:", e)

    jobs = sorted(found.values(), key=lambda j: j["posted"], reverse=True)[:MAX_JOBS]
    if not jobs and OUT.exists():
        print("No jobs found, keeping the old file.")
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"updated": datetime.now(timezone.utc).isoformat(), "jobs": jobs}, ensure_ascii=False))
    print(len(jobs), "jobs saved")


main()
