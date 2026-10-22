import json, re, html, sys, time
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 45
BLOCKED = {"pratham international"}

COUNTRIES = {
    "India": ["india", "bengaluru", "bangalore", "mumbai",
              "delhi", "hyderabad", "chennai", "pune", "noida",
              "gurgaon", "gurugram"],
    "Indonesia": ["indonesia", "jakarta", "surabaya", "bandung",
                  "yogyakarta", "bali"],
    "Philippines": ["philippines", "manila", "cebu", "davao"],
    "Vietnam": ["vietnam", "viet nam", "ho chi minh", "hanoi"],
    "Malaysia": ["malaysia", "kuala lumpur", "penang"],
    "Thailand": ["thailand", "bangkok", "chiang mai"],
}
COUNTRY_RX = {
    c: re.compile(r"\b(" + "|".join(re.escape(a) for a in al) + r")\b")
    for c, al in COUNTRIES.items()
}
ALL6 = list(COUNTRIES)

WORLD = re.compile(
    r"\b(worldwide|world wide|anywhere|global|globally|"
    r"all countries|work from anywhere)\b")
REGION = re.compile(
    r"\b(apac|asia|asia pacific|asia-pacific|"
    r"southeast asia|south east asia)\b")
RESTRICT = re.compile(
    r"\b(us|usa|u\.s\.|united states|canada|uk|united kingdom|"
    r"europe|emea|eu|latam|latin america|americas|"
    r"north america|australia|new zealand)\b")
REMOTE_LOC = re.compile(
    r"\b(remote|work from home|wfh|anywhere|worldwide|distributed)\b")
REMOTE_DESC = re.compile(
    r"(fully remote|100% remote|remote[- ](first|position|role|work|job)"
    r"|work from home|work-from-home)")
HYBRID = re.compile(
    r"\b(on[- ]?site|hybrid|in[- ]office|office[- ]based)\b")
SENIOR = re.compile(
    r"\b(senior|sr|principal|director|manager|head of|"
    r"vice president|vp|team lead|tech lead|lead engineer|"
    r"lead developer|staff engineer|architect|chief|expert)\b")
EXP = [
    re.compile(r"\b(?:[2-9]|1\d)\s*\+?\s*(?:(?:-|–|to)\s*\d+\s*)?"
               r"years?\b[^.]{0,40}\bexperience"),
    re.compile(r"\bexperience\b[^.]{0,30}\b(?:[2-9]|1\d)\s*\+?\s*"
               r"years?\b"),
    re.compile(r"\b(?:minimum|min\.?|at least)\s+(?:of\s+)?"
               r"(?:[2-9]|1\d)\s*\+?\s*years?"),
]
ENTRY_TITLE = re.compile(
    r"\b(intern|internship|entry[- ]level|graduate|"
    r"fresh graduate|new grad|trainee|junior)\b")
ENTRY_DESC = re.compile(
    r"\b(intern|internship|entry[- ]level|fresh graduate|"
    r"new grad|recent graduate|trainee|junior|"
    r"no experience required|no prior experience|"
    r"0[-–]1 years?|0 years of experience)\b")
FRIENDLY = re.compile(
    r"\b(customer support|customer service|customer care|"
    r"customer success|support agent|support representative|"
    r"support associate|helpdesk|help desk|technical support|"
    r"it support|associate|assistant|coordinator|representative|"
    r"data entry|annotator|annotation|content moderator|"
    r"moderator|sales development|sdr|bdr|virtual assistant|"
    r"social media|content writer|copywriter)\b")


def clean(v):
    if isinstance(v, list):
        return ", ".join(map(str, v))
    return html.unescape(str(v or ""))


def plain(v):
    text = re.sub(r"<[^>]*>", " ", clean(v))
    return re.sub(r"\s+", " ", text).strip().lower()


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Switchremote/1.0 "
                              "(+https://sohilbaitha.github.io/Switchremote/)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(3 * (i + 1))
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def parse_date(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            if value > 10**12:
                value /= 1000
            return datetime.fromtimestamp(value, timezone.utc)
        s = str(value).strip()
        if s.isdigit():
            return parse_date(int(s))
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def valid_url(url, hosts):
    p = urlparse(clean(url))
    return bool(p.scheme == "https" and p.hostname and any(
        p.hostname == h or p.hostname.endswith("." + h)
        for h in hosts
    ))


def resolve_countries(location):
    loc = clean(location).lower()
    found = [c for c, rx in COUNTRY_RX.items() if rx.search(loc)]
    if found:
        return found, "country"
    if RESTRICT.search(loc):
        return [], ""
    if WORLD.search(loc):
        return ALL6[:], "worldwide"
    if REGION.search(loc):
        return ALL6[:], "region"
    return [], ""


def consider(r):
    title = clean(r.get("title")).strip()
    tl = title.lower()
    loc = clean(r.get("location"))
    desc = plain(r.get("desc"))

    if not title or not r.get("url") or not r.get("id"):
        return False, "missing data", None

    if clean(r.get("company")).lower() in BLOCKED:
        return False, "blocked company", None

    countries, scope = resolve_countries(loc)
    allowed = r.get("eligible_countries")
    if allowed:
        countries = [c for c in countries if c in allowed]
    if not countries:
        return False, "country/location", None

    if not r.get("remote_verified"):
        if not (REMOTE_LOC.search(tl + " " + loc.lower())
                or REMOTE_DESC.search(desc)):
            return False, "remote not confirmed", None

    if HYBRID.search(tl + " " + loc.lower()):
        return False, "onsite/hybrid", None

    if SENIOR.search(tl) or r.get("level") == "senior":
        return False, "experienced title", None

    text = tl + " " + desc
    if any(rx.search(text) for rx in EXP):
        return False, "experience requirement", None

    if r.get("entry_required", True):
        if not (r.get("level") == "entry"
                or ENTRY_TITLE.search(tl)
                or ENTRY_DESC.search(desc)
                or FRIENDLY.search(tl)):
            return False, "not clearly entry-level", None

    d = parse_date(r.get("posted"))
    if not (d and NOW - timedelta(days=MAX_AGE_DAYS) <= d
            <= NOW + timedelta(days=1)):
        return False, "missing/old posting date", None

    job = {
        "id": clean(r["id"]),
        "title": title,
        "company": clean(r.get("company")),
        "url": clean(r["url"]),
        "location": loc,
        "category": clean(r.get("category")),
        "type": "Remote",
        "salary": clean(r.get("salary")),
        "logo": clean(r.get("logo")),
        "source": r["source"],
        "description": desc[:1500],
        "postedAt": d.isoformat(),
        "countries": countries,
        "scope": scope,
    }
    return True, "accepted", job
