
from jobs_core import *

accepted = []
stats = {}
errors = []
MAX_SMARTRECRUITERS_PAGES = 10
MIN_PUBLISH_JOBS = 5


def run(key, label, raws):
    checked, got, rejected = 0, 0, {}

    for raw in raws:
        checked += 1
        ok, reason, job = consider(raw)

        if ok:
            job["sourceKey"] = key
            accepted.append(job)
            got += 1
        else:
            rejected[reason] = rejected.get(reason, 0) + 1

    stats[key] = True
    print(
        f"{label}: checked {checked}, accepted {got}, "
        f"rejected {rejected}"
    )


def employer_items(emp):
    name = clean(emp.get("company"))
    kind = clean(emp.get("source_type")).lower()
    token = clean(emp.get("board_token"))
    allowed = [
        c for c in (emp.get("eligible_countries") or [])
        if c in ALL6
    ]
    entry_required = emp.get("entry_level_only") is not False
    out = []

    if kind == "greenhouse":
        data = fetch(
            "https://boards-api.greenhouse.io/v1/boards/"
            + token + "/jobs?content=true"
        )

        for item in data.get("jobs", []):
            url = clean(item.get("absolute_url"))
            if not valid_url(
                url, ["boards.greenhouse.io", "job-boards.greenhouse.io"]
            ):
                continue

            out.append({
                "id": name + "-" + clean(item.get("id")),
                "title": item.get("title"),
                "company": name,
                "url": url,
                "location": (item.get("location") or {}).get("name"),
                "desc": item.get("content"),
                "posted": item.get("first_published"),
                "source": "Greenhouse",
            })

    elif kind == "lever":
        data = fetch(
            "https://api.lever.co/v0/postings/" + token + "?mode=json"
        )
        if not isinstance(data, list):
            data = []

        for item in data:
            url = clean(item.get("hostedUrl"))
            if not valid_url(url, ["jobs.lever.co"]):
                continue

            categories = item.get("categories") or {}
            locations = [clean(categories.get("location"))]

            for extra in categories.get("allLocations") or []:
                extra = clean(extra)
                if extra and extra not in locations:
                    locations.append(extra)

            out.append({
                "id": name + "-" + clean(item.get("id")),
                "title": item.get("text"),
                "company": name,
                "url": url,
                "location": ", ".join(x for x in locations if x),
                "desc": (
                    item.get("descriptionPlain")
                    or item.get("description")
                ),
                "posted": item.get("createdAt"),
                "remote_verified": (
                    clean(item.get("workplaceType")).lower() == "remote"
                ),
                "source": "Lever",
            })

    elif kind == "ashby":
        data = fetch(
            "https://api.ashbyhq.com/posting-api/job-board/" + token
        )

        for item in data.get("jobs", []):
            if item.get("isListed") is not True:
                continue

            url = clean(item.get("jobUrl"))
            if not valid_url(url, ["jobs.ashbyhq.com"]):
                continue

            secondary = [
                clean(loc.get("location"))
                for loc in (item.get("secondaryLocations") or [])
                if isinstance(loc, dict)
            ]
            locations = [clean(item.get("location"))] + secondary
            compensation = item.get("compensation") or {}

            out.append({
                "id": name + "-" + url,
                "title": item.get("title"),
                "company": name,
                "url": url,
                "location": ", ".join(x for x in locations if x),
                "desc": (
                    item.get("descriptionPlain")
                    or item.get("descriptionHtml")
                ),
                "posted": item.get("publishedAt"),
                "salary": compensation.get(
                    "scrapeableCompensationSalarySummary"
                ),
                "remote_verified": (
                    item.get("isRemote") is True
                    or clean(item.get("workplaceType")).lower() == "remote"
                ),
                "source": "Ashby",
            })

    elif kind == "smartrecruiters":
        limit = 100
        offset = 0

        for _ in range(MAX_SMARTRECRUITERS_PAGES):
            api_url = (
                "https://api.smartrecruiters.com/v1/companies/"
                + token
                + f"/postings?limit={limit}&offset={offset}"
            )
            data = fetch(api_url)
            items = data.get("content", [])

            if not items:
                break

            for item in items:
                url = clean(item.get("ref"))
                if not valid_url(url, ["jobs.smartrecruiters.com"]):
                    continue

                location_data = item.get("location") or {}
                sections = (item.get("jobAd") or {}).get("sections") or {}
                description = (
                    sections.get("jobDescription") or {}
                ).get("text", "")

                out.append({
                    "id": name + "-" + clean(item.get("id")),
                    "title": item.get("name"),
                    "company": name,
                    "url": url,
                    "location": (
                        location_data.get("fullLocation")
                        if isinstance(location_data, dict)
                        else location_data
                    ),
                    "desc": description,
                    "posted": item.get("releasedDate"),
                    "source": "SmartRecruiters",
                })

            offset += len(items)
            total = data.get("totalFound")

            if len(items) < limit:
                break
            if isinstance(total, int) and offset >= total:
                break

    else:
        raise ValueError("Unsupported source type: " + kind)

    for item in out:
        item["eligible_countries"] = allowed
        item["entry_required"] = entry_required

    return out


def jobicy_items():
    try:
        data = fetch("https://jobicy.com/api/v2/remote-jobs?count=100")
    except Exception:
        data = fetch("https://jobicy.com/api/jobs?count=200")

    out = []

    for item in data.get("jobs", []):
        url = clean(item.get("url"))
        if not valid_url(url, ["jobicy.com"]):
            continue

        level = clean(item.get("jobLevel")).lower()
        types = clean(item.get("jobType")).lower()
        job_level = ""

        if any(w in level for w in (
            "senior", "mid", "manager", "lead"
        )):
            job_level = "senior"
        elif any(w in level for w in (
            "junior", "entry", "intern", "graduate"
        )) or "intern" in types:
            job_level = "entry"

        out.append({
            "id": "Jobicy-" + clean(item.get("id")),
            "title": item.get("jobTitle"),
            "company": item.get("companyName"),
            "url": url,
            "location": item.get("jobGeo"),
            "desc": item.get("jobDescription"),
            "posted": item.get("pubDate"),
            "logo": item.get("companyLogo"),
            "category": item.get("jobIndustry"),
            "remote_verified": True,
            "level": job_level,
            "source": "Jobicy",
        })

    return out


def remotive_items():
    data = fetch("https://remotive.com/api/remote-jobs")
    out = []

    for item in data.get("jobs", []):
        url = clean(item.get("url"))
        if not valid_url(url, ["remotive.com"]):
            continue

        out.append({
            "id": "Remotive-" + clean(item.get("id")),
            "title": item.get("title"),
            "company": item.get("company_name"),
            "url": url,
            "location": item.get("candidate_required_location"),
            "desc": item.get("description"),
            "posted": item.get("publication_date"),
            "logo": item.get("company_logo"),
            "category": item.get("category"),
            "salary": item.get("salary"),
            "remote_verified": True,
            "source": "Remotive",
        })

    return out


def remoteok_items():
    data = fetch("https://remoteok.com/api")
    out = []

    for item in data:
        if (
            not isinstance(item, dict)
            or not item.get("id")
            or not item.get("position")
        ):
            continue

        url = clean(item.get("url"))
        if not valid_url(url, ["remoteok.com"]):
            continue

        out.append({
            "id": "RemoteOK-" + clean(item.get("id")),
            "title": item.get("position"),
            "company": item.get("company"),
            "url": url,
            "location": item.get("location"),
            "desc": item.get("description"),
            "posted": item.get("date") or item.get("epoch"),
            "logo": item.get("logo"),
            "category": ", ".join((item.get("tags") or [])[:3]),
            "remote_verified": True,
            "source": "RemoteOK",
        })

    return out


def keep_fresh_old_jobs(old_jobs, failed_keys):
    """Keep recent cached jobs belonging to failed sources."""
    kept = []
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)

    for old in old_jobs:
        key = (
            old.get("sourceKey")
            or old.get("company")
            or old.get("source")
        )
        if key not in failed_keys:
            continue

        posted = parse_date(old.get("postedAt"))
        if not posted or not (cutoff <= posted <= NOW + timedelta(days=1)):
            continue

        countries = [
            country for country in old.get("countries", [])
            if country in ALL6
        ]
        if not countries or old.get("scope") == "region":
            continue

        old["countries"] = countries
        kept.append(old)

    return kept


def main():
    try:
        with open("jobs.json", encoding="utf-8") as file:
            old_jobs = json.load(file).get("jobs", [])
    except (OSError, ValueError, TypeError):
        old_jobs = []

    old_jobs = [
        job for job in old_jobs
        if clean(job.get("company")).lower() not in BLOCKED
    ]

    with open("employers.json", encoding="utf-8") as file:
        employers = json.load(file).get("employers", [])

    for employer in employers:
        if employer.get("approved") is not True:
            continue

        name = clean(employer.get("company"))
        kind = clean(employer.get("source_type")).lower()

        if not name or not clean(employer.get("board_token")):
            errors.append(f"{name or 'Employer'}: missing token")
            continue

        try:
            run(name, f"{name} ({kind})", employer_items(employer))
        except Exception as exc:
            stats[name] = False
            errors.append(f"{name} ({kind}): {exc}")

    for key, source_function in (
        ("Jobicy", jobicy_items),
        ("Remotive", remotive_items),
        ("RemoteOK", remoteok_items),
    ):
        try:
            run(key, key, source_function())
        except Exception as exc:
            stats[key] = False
            errors.append(f"{key}: {exc}")

    for error in errors:
        print("SOURCE ERROR:", error)

    if not stats or not any(stats.values()):
        print("ALL SOURCES FAILED - keeping old jobs.json")
        raise SystemExit(1)

    failed_keys = {
        key for key, success in stats.items() if not success
    }
    cached = keep_fresh_old_jobs(old_jobs, failed_keys)
    accepted.extend(cached)

    if cached:
        print(f"Kept {len(cached)} fresh jobs from failed sources")

    if not accepted:
        print("No qualifying jobs found; keeping existing jobs.json.")
        raise SystemExit(1)

    seen_urls = set()
    seen_signatures = set()
    final_jobs = []

    for job in accepted:
        url = clean(job.get("url")).split("?")[0].rstrip("/").lower()
        signature = (
            clean(job.get("title")).lower().strip(),
            clean(job.get("company")).lower().strip(),
            ",".join(sorted(job.get("countries", []))),
        )

        if not url or url in seen_urls or signature in seen_signatures:
            continue

        seen_urls.add(url)
        seen_signatures.add(signature)
        final_jobs.append(job)

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    final_jobs.sort(
        key=lambda job: parse_date(job.get("postedAt")) or epoch,
        reverse=True,
    )

    # Fail-safe: avoid replacing a healthy existing feed with a sudden
    # near-empty result. Return successfully so scheduled runs stay green.
    if old_jobs and len(final_jobs) < MIN_PUBLISH_JOBS:
        print(
            f"FAIL-SAFE: only {len(final_jobs)} qualifying jobs found; "
            f"minimum is {MIN_PUBLISH_JOBS}. "
            "Existing jobs.json will be kept unchanged."
        )
        return

    coverage = {
        country: sum(
            1 for job in final_jobs
            if country in job.get("countries", [])
        )
        for country in ALL6
    }

    print("Country coverage:", coverage)

    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(
            {"updatedAt": NOW.isoformat(), "jobs": final_jobs},
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Saved {len(final_jobs)} qualifying jobs")


if __name__ == "__main__":
    main()
