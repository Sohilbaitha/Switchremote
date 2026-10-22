
import json
import re
import html
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 3
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

# Allow intermediate experience up to 3 years.
# Reject clear requirements for 4+ years.
EXP = [
    re.compile(
        r"\b(?:4|5|6|7|8|9|1\d)\s*\+?\s*"
        r"(?:(?:-|–|to)\s*\d+\s*)?years?\b"
        r"[^.]{0,60}\bexperience\b", re.I
    ),
    re.compile(
        r"\bexperience\b[^.]{0,40}\b"
        r"(?:4|5|6|7|8|9|1\d)\s*\+?\s*years?\b", re.I
    ),
    re.compile(
        r"\b(?:minimum|min\.?|at least)\s+(?:of\s+)?"
        r"(?:4|5|6|7|8|9|1\d)\s*\+?\s*years?\b", re.I
    ),
]

ENTRY_TITLE = re.compile(
    r"\b(intern|internship|entry[- ]level|graduate|fresh graduate|"
    r"new grad|trainee|junior|associate|early career)\b", re.I
)
ENTRY_DESC = re.compile(
    r"\b(intern|internship|entry[- ]level|fresh graduate|new grad|"
    r"recent graduate|trainee|junior|early career|"
    r"no experience required|no prior experience|"
    r"0[-–]1 years?|0 years of experience)\b", re.I
)
FRIENDLY = re.compile(
    r"\b("
    r"customer support|customer service|customer care|customer success|"
    r"support agent|support representative|support associate|"
    r"technical support|it support|helpdesk|help desk|"
    r"data entry|data analyst|business analyst|"
    r"annotator|annotation|content moderator|moderator|"
    r"sales development|sales representative|account executive|sdr|bdr|"
    r"virtual assistant|social media|content writer|copywriter|"
    r"digital marketing|marketing associate|seo specialist|"
    r"recruiter|talent acquisition|operations associate|operations analyst|"
    r"qa tester|quality assurance|software developer|software engineer|"
    r"web developer|frontend developer|front-end developer|"
    r"backend developer|back-end developer|"
    r"graphic designer|ui designer|ux designer|"
    r"product support|implementation specialist|"
    r"project coordinator|research assistant|research associate"
    r")\b", re.I
)


def clean(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return html.unescape(str(value or "")).strip()


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
    loc = clean(location).lower()
    configured = [
        c for c in (eligible_countries or [])
        if c in ALL6
    ]

    found = [
        country for country, pattern in COUNTRY_RX.items()
        if pattern.search(loc)
    ]

    if found:
        if configured:
            found = [c for c in found if c in configured]
        return found, "country" if found else ""

    # Do not assume APAC/Asia means every supported country.
    if REGION.search(loc) or RESTRICT.search(loc):
        return [], ""

    if WORLD.search(loc):
        countries = configured if configured else ALL6[:]
        return countries, "worldwide"

    # Generic remote location needs an explicitly configured
    # employer hiring allowlist.
    if REMOTE_LOC.search(loc) and configured:
        return configured, "employer_allowlist"

    return [], ""


def consider(job_raw):
    title = clean(job_raw.get("title"))
    title_lower = title.lower()
    company = clean(job_raw.get("company"))
    location = clean(job_raw.get("location"))
    description = plain(job_raw.get("desc"))
    url = clean(job_raw.get("url"))
    logo = clean(job_raw.get("logo"))

    if not title or not company or not job_raw.get("id"):
        return False, "missing identity data", None

    if company.lower() in BLOCKED:
        return False, "blocked company", None

    allowed_hosts = [
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "jobs.smartrecruiters.com",
        "jobicy.com",
        "remotive.com",
        "remoteok.com",
    ]
    if not valid_url(url, allowed_hosts):
        return False, "invalid application URL", None

    # Require a company logo/profile image.
    if not logo or urlparse(logo).scheme != "https":
        return False, "missing logo", None

    allowed = job_raw.get("eligible_countries")
    countries, scope = resolve_countries(location, allowed)
    if not countries:
        return False, "country eligibility not verified", None

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
        return False, "senior title", None

    combined = title_lower + " " + description
    if any(pattern.search(combined) for pattern in EXP):
        return False, "4+ years experience required", None

    if job_raw.get("entry_required", True):
        explicit_entry = (
            job_raw.get("level") == "entry"
            or bool(ENTRY_TITLE.search(title_lower))
            or bool(ENTRY_DESC.search(description))
        )
        relevant_role = bool(FRIENDLY.search(title_lower))

        if not (explicit_entry or relevant_role):
            return False, "not a relevant early-career role", None

    posted = parse_date(job_raw.get("posted"))
    if not (
        posted
        and NOW - timedelta(days=MAX_AGE_DAYS) <= posted <= NOW
    ):
        return False, "missing or older than 3 days", None

    result = {
        "id": clean(job_raw["id"]),
        "title": title,
        "company": company,
        "url": url,
        "location": location,
        "category": clean(job_raw.get("category")),
        "type": "Remote",
        "salary": clean(job_raw.get("salary")),
        "logo": logo,
        "source": clean(job_raw.get("source")),
        "description": description[:1500],
        "postedAt": posted.isoformat(),
        "countries": countries,
        "scope": scope,
    }
    return True, "accepted", result
