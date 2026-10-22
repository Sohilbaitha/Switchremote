
import json
import re
import html
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 30
BLOCKED = {"pratham international"}

COUNTRIES = {
    "India": [
        "india", "bengaluru", "bangalore", "mumbai", "delhi",
        "hyderabad", "chennai", "pune", "noida", "gurgaon", "gurugram"
    ],
    "Indonesia": [
        "indonesia", "jakarta", "surabaya", "bandung", "yogyakarta", "bali"
    ],
    "Philippines": ["philippines", "manila", "cebu", "davao"],
    "Vietnam": ["vietnam", "viet nam", "ho chi minh", "hanoi"],
    "Malaysia": ["malaysia", "kuala lumpur", "penang"],
    "Thailand": ["thailand", "bangkok", "chiang mai"],
}
ALL6 = list(COUNTRIES)
COUNTRY_RX = {
    c: re.compile(
        r"\b(" + "|".join(re.escape(x) for x in names) + r")\b",
        re.I
    )
    for c, names in COUNTRIES.items()
}

WORLD = re.compile(
    r"\b(worldwide|world wide|anywhere|global|globally|"
    r"all countries|work from anywhere)\b", re.I
)
REGION = re.compile(
    r"\b(apac|asia|asia pacific|asia-pacific|"
    r"southeast asia|south east asia)\b", re.I
)
RESTRICT = re.compile(
    r"\b(usa|u\.s\.|united states|canada|uk|united kingdom|"
    r"europe|emea|latam|latin america|americas|"
    r"north america|australia|new zealand)\b", re.I
)
REMOTE_LOC = re.compile(
    r"\b(remote|work from home|wfh|anywhere|worldwide|distributed)\b", re.I
)
REMOTE_DESC = re.compile(
    r"(fully remote|100% remote|remote[- ](first|position|role|work|job)"
    r"|work from home|work-from-home)", re.I
)
HYBRID = re.compile(
    r"\b(on[- ]?site|hybrid|in[- ]office|office[- ]based)\b", re.I
)
SENIOR = re.compile(
    r"\b(senior|sr\.?|principal|director|manager|head of|"
    r"vice president|vp|team lead|tech lead|lead engineer|"
    r"lead developer|staff engineer|architect|chief|expert)\b", re.I
)

EXP = [
    re.compile(
        r"\b(?:[2-9]|1\d)\s*\+?\s*(?:(?:-|–|to)\s*\d+\s*)?"
        r"years?\b[^.]{0,60}\bexperience\b", re.I
    ),
    re.compile(
        r"\bexperience\b[^.]{0,40}\b(?:[2-9]|1\d)\s*\+?\s*years?\b",
        re.I
    ),
    re.compile(
        r"\b(?:minimum|min\.?|at least)\s+(?:of\s+)?"
        r"(?:[2-9]|1\d)\s*\+?\s*years?\b", re.I
    ),
]

ENTRY_TITLE = re.compile(
    r"\b(intern|internship|entry[- ]level|graduate|fresh graduate|"
    r"new grad|trainee|junior)\b", re.I
)
ENTRY_DESC = re.compile(
    r"\b(intern|internship|entry[- ]level|fresh graduate|new grad|"
    r"recent graduate|trainee|junior|no experience required|"
    r"no prior experience|0[-–]1 years?|0 years of experience)\b", re.I
)
FRIENDLY = re.compile(
    r"\b(customer support|customer service|customer care|"
    r"customer success|support agent|support representative|"
    r"support associate|helpdesk|help desk|technical support|"
    r"it support|data entry|annotator|annotation|content moderator|"
    r"moderator|sales development|sdr|bdr|virtual assistant|"
    r"social media|content writer|copywriter)\b", re.I
)


def clean(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return html.unescape(str(value or ""))


def plain(value):
    value = re.sub(r"<[^>]*>", " ", clean(value))
    return re.sub(r"\s+", " ", value).strip().lower()


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Switchremote/1.0 "
                        "(+https://sohilbaitha.github.io/Switchremote/)"
                    ),
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (400, 401, 403, 404):
                break
            time.sleep(2 * (attempt + 1))
        except Exception as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


def parse_date(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            if value > 10**12:
                value /= 1000
            return datetime.fromtimestamp(value, timezone.utc)

        value = str(value).strip()
        if value.isdigit():
            return parse_date(int(value))

        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def valid_url(url, hosts):
    parsed = urlparse(clean(url))
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and any(
            parsed.hostname == host
            or parsed.hostname.endswith("." + host)
            for host in hosts
        )
    )



def resolve_countries(location, eligible_countries=None):
    loc = clean(location).lower().strip()

    # Only allow country names present in our supported list.
    configured = [
        country for country in (eligible_countries or [])
        if country in ALL6
    ]

    # Explicit country names take priority.
    found = [
        country for country, pattern in COUNTRY_RX.items()
        if pattern.search(loc)
    ]

    if found:
        if configured:
            found = [country for country in found if country in configured]
        return found, "country" if found else ""

    # A regional label does not prove eligibility in every country.
    if REGION.search(loc) or RESTRICT.search(loc):
        return [], ""

    # Worldwide jobs can be shown for all six countries only when no
    # narrower employer allowlist has been supplied.
    if WORLD.search(loc):
        countries = configured if configured else ALL6[:]
        return countries, "worldwide" if countries else ""

    # Generic remote roles may use a configured employer country allowlist.
    # This must only be configured after checking the employer's hiring policy.
    if REMOTE_LOC.search(loc) and configured:
        return configured, "employer_allowlist"

    return [], ""



def consider(job_raw):
    title = clean(job_raw.get("title")).strip()
    title_lower = title.lower()
    location = clean(job_raw.get("location"))
    description = plain(job_raw.get("desc"))
    company = clean(job_raw.get("company")).strip()

    if not title or not job_raw.get("url") or not job_raw.get("id"):
        return False, "missing data", None

    if company.lower() in BLOCKED:
        return False, "blocked company", None

    allowed = job_raw.get("eligible_countries")
    countries, scope = resolve_countries(location, allowed)
    if not countries:
        return False, "country/location not verified", None

    remote_text = title + " " + location
    if not job_raw.get("remote_verified"):
        if not (
            REMOTE_LOC.search(remote_text)
            or REMOTE_DESC.search(description)
        ):
            return False, "remote not confirmed", None

    if HYBRID.search(remote_text):
        return False, "onsite/hybrid", None

    if SENIOR.search(title_lower) or job_raw.get("level") == "senior":
        return False, "experienced title", None

    combined = title_lower + " " + description
    if any(pattern.search(combined) for pattern in EXP):
        return False, "experience requirement", None

    if job_raw.get("entry_required", True):
        explicit_entry = (
            job_raw.get("level") == "entry"
            or ENTRY_TITLE.search(title_lower)
            or ENTRY_DESC.search(description)
        )
        relevant_role = FRIENDLY.search(title_lower)

        # Generic words like "assistant" and "associate" alone are
        # deliberately not entry-level evidence.
        if not (explicit_entry or relevant_role):
            return False, "not clearly entry-level", None

    posted = parse_date(job_raw.get("posted"))
    if not (
        posted
        and NOW - timedelta(days=MAX_AGE_DAYS) <= posted
        <= NOW + timedelta(days=1)
    ):
        return False, "missing/old posting date", None

    result = {
        "id": clean(job_raw["id"]),
        "title": title,
        "company": company,
        "url": clean(job_raw["url"]),
        "location": location,
        "category": clean(job_raw.get("category")),
        "type": "Remote",
        "salary": clean(job_raw.get("salary")),
        "logo": clean(job_raw.get("logo")),
        "source": job_raw["source"],
        "description": description[:1500],
        "postedAt": posted.isoformat(),
        "countries": countries,
        "scope": scope,
    }
    return True, "accepted", result
