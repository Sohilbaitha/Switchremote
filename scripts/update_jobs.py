import json
import re
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from jobs_core import NOW, MAX_AGE_DAYS, clean, parse_date, consider


ROOT = Path(__file__).resolve().parent.parent
EMPLOYERS_FILE = ROOT / "employers.json"
JOBS_FILE = ROOT / "jobs.json"

MAX_SMARTRECRUITERS_PAGES = 10
MAX_JOB_AGE = timedelta(days=3)

GREENHOUSE_HOSTS = ("boards.greenhouse.io", "job-boards.greenhouse.io")
LEVER_HOSTS = ("jobs.lever.co",)
ASHBY_HOSTS = ("jobs.ashbyhq.com",)
SMARTRECRUITERS_HOSTS = ("jobs.smartrecruiters.com",)


def fetch_json(url, tries=3):
    last_error = None

    for attempt in range(tries):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Switchremote/1.0 "
                        "(+https://sohilbaitha.github.io/Switchremote/)"
                    ),
                    "Accept": "application/json",
                },
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            last_error = exc

            if exc.code in (400, 401, 403, 404):
                break

            time.sleep(2 * (attempt + 1))

        except Exception as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))

    raise last_error


def is_https_url(value):
    parsed = urlparse(clean(value))
    return parsed.scheme == "https" and bool(parsed.hostname)


def valid_job_url(value, allowed_hosts):
    parsed = urlparse(clean(value))

    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and any(
            parsed.hostname == host
            or parsed.hostname.endswith("." + host)
            for host in allowed_hosts
        )
    )


def make_id(source, company, title, url):
    raw = "|".join(
        (
            clean(source).lower(),
            clean(company).lower(),
            clean(title).lower(),
            clean(url).lower(),
        )
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def get_description(item):
    return clean(
        item.get("description")
        or item.get("text")
        or item.get("content")
        or item.get("jobDescription")
        or item.get("job_description")
        or item.get("desc")
    )


def get_location(item):
    if isinstance(item.get("location"), dict):
        location = item["location"]
        return clean(
            location.get("name")
            or location.get("location")
            or location.get("displayName")
        )

    if isinstance(item.get("location"), list):
        return ", ".join(
            clean(
                value.get("name")
                if isinstance(value, dict)
                else value
            )
            for value in item["location"]
            if value
        )

    categories = item.get("categories") or {}
    if isinstance(categories, dict):
        location = categories.get("location")
    else:
        location = ""

    return clean(
        item.get("location")
        or item.get("locationName")
        or item.get("workplace")
        or location
    )


def get_salary(item):
    salary = (
        item.get("salary")
        or item.get("salaryRange")
        or item.get("compensation")
        or ""
    )

    if isinstance(salary, dict):
        parts = [
            clean(salary.get("min") or salary.get("minimum")),
            clean(salary.get("max") or salary.get("maximum")),
            clean(salary.get("currency")),
            clean(salary.get("interval") or salary.get("period")),
        ]
        return " ".join(part for part in parts if part)

    return clean(salary)


def get_logo(item, employer):
    return clean(
        item.get("logo")
        or item.get("company_logo")
        or item.get("companyLogo")
        or item.get("company_logo_url")
        or employer.get("logo")
    )


def normalize_job(
    item,
    employer,
    source,
    posted,
    url,
    location=None,
    logo=None,
    remote_verified=False,
    level="",
):
    company = clean(
        item.get("company")
        or item.get("companyName")
        or item.get("organization")
        or item.get("employer")
        or employer.get("company")
    )

    title = clean(
        item.get("title")
        or item.get("name")
        or item.get("jobTitle")
    )

    description = get_description(item)

    if location is None:
        location = get_location(item)

    if logo is None:
        logo = get_logo(item, employer)

    job_id = clean(
        item.get("id")
        or item.get("job_id")
        or item.get("requisitionId")
        or item.get("uuid")
    )

    if not job_id:
        job_id = make_id(source, company, title, url)

    eligible_countries = employer.get("eligible_countries") or []

    return {
        "id": job_id,
        "title": title,
        "company": company,
        "url": clean(url),
        "location": clean(location),
        "category": clean(
            item.get("category")
            or item.get("department")
            or item.get("team")
        ),
        "salary": get_salary(item),
        "logo": clean(logo),
        "source": source,
        "desc": description,
        "posted": posted,
        "remote_verified": bool(remote_verified),
        "level": level,
        "eligible_countries": eligible_countries,
        "entry_required": employer.get("entry_level_only", True) is not False,
    }


def greenhouse_jobs(employer):
    token = clean(employer.get("board_token"))

    if not token:
        raise ValueError("Missing Greenhouse board token")

    api_url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        + token
        + "/jobs?content=true"
    )

    data = fetch_json(api_url)
    jobs = data.get("jobs", [])
    results = []

    for item in jobs:
        url = clean(item.get("absolute_url"))

        if not valid_job_url(url, GREENHOUSE_HOSTS):
            continue

        location = get_location(item)
        content = item.get("content") or ""
        description = get_description(item) or clean(content)

        offices = item.get("offices") or []
        if not location and offices:
            location = ", ".join(
                clean(office.get("name"))
                for office in offices
                if isinstance(office, dict) and office.get("name")
            )

        normalized = normalize_job(
            item={
                **item,
                "description": description,
            },
            employer=employer,
            source="Greenhouse",
            posted=(
                item.get("first_published")
                or item.get("first_published_at")
                or item.get("published_at")
            ),
            url=url,
            location=location,
            remote_verified=False,
        )

        results.append(normalized)

    return results


def lever_jobs(employer):
    token = clean(employer.get("board_token"))

    if not token:
        raise ValueError("Missing Lever board token")

    api_url = "https://api.lever.co/v0/postings/" + token + "?mode=json"
    data = fetch_json(api_url)

    if not isinstance(data, list):
        raise ValueError("Unexpected Lever API response")

    results = []

    for item in data:
        url = clean(item.get("hostedUrl") or item.get("applyUrl"))

        if not valid_job_url(url, LEVER_HOSTS):
            continue

        categories = item.get("categories") or {}
        location = clean(
            categories.get("location")
            or item.get("workplaceType")
            or ""
        )

        workplace_type = clean(item.get("workplaceType")).lower()
        remote_verified = workplace_type == "remote"

        description = clean(
            item.get("descriptionPlain")
            or item.get("description")
            or item.get("additionalPlain")
            or item.get("additional")
        )

        normalized = normalize_job(
            item={
                **item,
                "description": description,
                "location": location,
            },
            employer=employer,
            source="Lever",
            posted=item.get("createdAt"),
            url=url,
            location=location,
            remote_verified=remote_verified,
        )

        results.append(normalized)

    return results


def ashby_jobs(employer):
    token = clean(employer.get("board_token"))

    if not token:
        raise ValueError("Missing Ashby board token")

    api_url = (
        "https://api.ashbyhq.com/posting-api/job-board/"
        + token
    )

    data = fetch_json(api_url)
    jobs = data.get("jobs", [])

    results = []

    for item in jobs:
        if item.get("isListed") is False:
            continue

        url = clean(item.get("jobUrl") or item.get("applyUrl"))

        if not valid_job_url(url, ASHBY_HOSTS):
            continue

        location = clean(
            item.get("location")
            or item.get("locationName")
            or ""
        )

        workplace_type = clean(
            item.get("workplaceType")
        ).lower()

        remote_verified = (
            item.get("isRemote") is True
            or workplace_type == "remote"
        )

        normalized = normalize_job(
            item=item,
            employer=employer,
            source="Ashby",
            posted=(
                item.get("publishedAt")
                or item.get("published_at")
            ),
            url=url,
            location=location,
            remote_verified=remote_verified,
        )

        results.append(normalized)

    return results


def smartrecruiters_jobs(employer):
    token = clean(employer.get("board_token"))

    if not token:
        raise ValueError("Missing SmartRecruiters company identifier")

    results = []

    for page in range(MAX_SMARTRECRUITERS_PAGES):
        api_url = (
            "https://api.smartrecruiters.com/v1/companies/"
            + token
            + "/postings?limit=100&offset="
            + str(page * 100)
        )

        data = fetch_json(api_url)
        content = data.get("content", [])

        if not content:
            break

        for item in content:
            posting_id = clean(item.get("id"))
            if not posting_id:
                continue

            url = (
                "https://jobs.smartrecruiters.com/"
                + token
                + "/"
                + posting_id
            )

            if not valid_job_url(url, SMARTRECRUITERS_HOSTS):
                continue

            location_data = item.get("location") or {}

            if isinstance(location_data, dict):
                location = ", ".join(
                    part
                    for part in [
                        clean(location_data.get("city")),
                        clean(location_data.get("region")),
                        clean(location_data.get("country")),
                    ]
                    if part
                )
            else:
                location = clean(location_data)

            normalized = normalize_job(
                item=item,
                employer=employer,
                source="SmartRecruiters",
                posted=(
                    item.get("releasedDate")
                    or item.get("releaseDate")
                ),
                url=url,
                location=location,
                remote_verified=False,
            )

            results.append(normalized)

        total_found = data.get("totalFound")

        if total_found is not None and (page + 1) * 100 >= int(total_found):
            break

        if len(content) < 100:
            break

    return results


def employer_items(employer):
    source_type = clean(employer.get("source_type")).lower()

    if source_type == "greenhouse":
        return greenhouse_jobs(employer)

    if source_type == "lever":
        return lever_jobs(employer)

    if source_type == "ashby":
        return ashby_jobs(employer)

    if source_type == "smartrecruiters":
        return smartrecruiters_jobs(employer)

    raise ValueError("Unsupported source type: " + source_type)


def jobicy_jobs():
    urls = [
        "https://jobicy.com/api/v2/remote-jobs?count=100",
        "https://jobicy.com/api/jobs?count=200",
    ]

    last_error = None

    for api_url in urls:
        try:
            data = fetch_json(api_url)
            jobs = data.get("jobs", [])

            results = []

            for item in jobs:
                url = clean(
                    item.get("url")
                    or item.get("jobUrl")
                    or item.get("apply_url")
                )

                if not is_https_url(url):
                    continue

                level_text = clean(
                    item.get("jobLevel")
                    or item.get("job_level")
                ).lower()

                if any(
                    word in level_text
                    for word in ("senior", "manager", "lead", "director")
                ):
                    level = "senior"
                elif any(
                    word in level_text
                    for word in ("junior", "entry", "intern", "graduate")
                ):
                    level = "entry"
                else:
                    level = ""

                normalized = normalize_job(
                    item=item,
                    employer={},
                    source="Jobicy",
                    posted=(
                        item.get("pubDate")
                        or item.get("publication_date")
                        or item.get("publishedAt")
                    ),
                    url=url,
                    location=get_location(item),
                    logo=get_logo(item, {}),
                    remote_verified=True,
                    level=level,
                )

                normalized["eligible_countries"] = [
                    "India",
                    "Indonesia",
                    "Philippines",
                    "Vietnam",
                    "Malaysia",
                    "Thailand",
                ]
                normalized["entry_required"] = True
                results.append(normalized)

            return results

        except Exception as exc:
            last_error = exc

    raise last_error


def remotive_jobs():
    api_url = "https://remotive.com/api/remote-jobs"
    data = fetch_json(api_url)
    results = []

    for item in data.get("jobs", []):
        url = clean(item.get("url"))

        if not is_https_url(url):
            continue

        normalized = normalize_job(
            item=item,
            employer={},
            source="Remotive",
            posted=(
                item.get("publication_date")
                or item.get("published_at")
            ),
            url=url,
            location=clean(
                item.get("candidate_required_location")
                or item.get("location")
                or "Remote"
            ),
            logo=clean(item.get("company_logo")),
            remote_verified=True,
            level="",
        )

        normalized["eligible_countries"] = [
            "India",
            "Indonesia",
            "Philippines",
            "Vietnam",
            "Malaysia",
            "Thailand",
        ]
        normalized["entry_required"] = True
        results.append(normalized)

    return results


def remoteok_jobs():
    api_url = "https://remoteok.com/api"
    data = fetch_json(api_url)

    if not isinstance(data, list):
        raise ValueError("Unexpected RemoteOK API response")

    results = []

    for item in data:
        if not isinstance(item, dict) or not item.get("id"):
            continue

        url = clean(item.get("url"))

        if not is_https_url(url):
            continue

        posted = (
            item.get("date")
            or item.get("epoch")
            or item.get("timestamp")
        )

        normalized = normalize_job(
            item=item,
            employer={},
            source="RemoteOK",
            posted=posted,
            url=url,
            location=clean(item.get("location") or "Remote"),
            logo=clean(item.get("company_logo") or item.get("logo")),
            remote_verified=True,
            level="",
        )

        normalized["eligible_countries"] = [
            "India",
            "Indonesia",
            "Philippines",
            "Vietnam",
            "Malaysia",
            "Thailand",
        ]
        normalized["entry_required"] = True
        results.append(normalized)

    return results


def read_json(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def is_fresh_job(job):
    posted = parse_date(
        job.get("postedAt")
        or job.get("posted")
        or job.get("date")
    )

    return bool(
        posted
        and NOW - MAX_JOB_AGE <= posted <= NOW
    )


def keep_fresh_old_jobs(old_jobs, failed_sources):
    if not failed_sources:
        return []

    kept = []

    for job in old_jobs:
        if clean(job.get("source")) not in failed_sources:
            continue

        if not is_fresh_job(job):
            continue

        if not is_https_url(job.get("logo")):
            continue

        if not is_https_url(job.get("url")):
            continue

        kept.append(job)

    return kept


def deduplicate(jobs):
    unique = {}
    seen_signatures = set()

    for job in jobs:
        url = clean(job.get("url")).rstrip("/").lower()

        if not url:
            continue

        if url in unique:
            continue

        signature = (
            clean(job.get("company")).lower(),
            clean(job.get("title")).lower(),
            clean(job.get("location")).lower(),
        )

        if signature in seen_signatures:
            continue

        unique[url] = job
        seen_signatures.add(signature)

    return list(unique.values())


def run_source(label, source_function, stats, failures):
    try:
        raw_jobs = source_function()
        accepted_count = 0

        for raw_job in raw_jobs:
            accepted, reason, normalized = consider(raw_job)

            if accepted and normalized:
                normalized["source"] = (
                    normalized.get("source") or label
                )
                normalized["sourceKey"] = label
                accepted_jobs.append(normalized)
                accepted_count += 1

        stats[label] = {
            "fetched": len(raw_jobs),
            "accepted": accepted_count,
            "status": "ok",
        }

        print(
            f"{label}: fetched={len(raw_jobs)}, "
            f"accepted={accepted_count}"
        )

    except Exception as exc:
        failures.add(label)
        stats[label] = {
            "fetched": 0,
            "accepted": 0,
            "status": "failed",
            "error": str(exc),
        }

        print(f"{label}: FAILED: {exc}")


def main():
    global accepted_jobs
    accepted_jobs = []

    old_data = read_json(JOBS_FILE, {"jobs": []})
    old_jobs = old_data.get("jobs", [])

    employers_data = read_json(EMPLOYERS_FILE, {"employers": []})
    employers = employers_data.get("employers", [])

    stats = {}
    failed_sources = set()

    approved_employers = [
        employer
        for employer in employers
        if employer.get("approved") is True
    ]

    for employer in approved_employers:
        company = clean(employer.get("company"))
        source_type = cl
