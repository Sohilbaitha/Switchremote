from jobs_core import *

accepted = []
stats = {}
errors = []


def run(key, label, raws):
    checked, got, rej = 0, 0, {}
    for r in raws:
        checked += 1
        ok, reason, job = consider(r)
        if ok:
            job["sourceKey"] = key
            accepted.append(job)
            got += 1
        else:
            rej[reason] = rej.get(reason, 0) + 1
    stats[key] = True
    print(f"{label}: checked {checked}, accepted {got}, rejected {rej}")


def employer_items(emp):
    name = clean(emp.get("company"))
    kind = clean(emp.get("source_type")).lower()
    token = clean(emp.get("board_token"))
    allowed = emp.get("eligible_countries") or None
    entry_req = emp.get("entry_level_only") is not False
    out = []

    if kind == "greenhouse":
        data = fetch("https://boards-api.greenhouse.io/v1/boards/"
                     + token + "/jobs?content=true")
        hosts = ["boards.greenhouse.io", "job-boards.greenhouse.io"]
        for it in data.get("jobs", []):
            url = clean(it.get("absolute_url"))
            if not valid_url(url, hosts):
                continue
            out.append(dict(
                id=name + "-" + clean(it.get("id")),
                title=it.get("title"), company=name, url=url,
                location=(it.get("location") or {}).get("name"),
                desc=it.get("content"),
                posted=it.get("first_published"),
                source="Greenhouse"))

    elif kind == "lever":
        data = fetch("https://api.lever.co/v0/postings/"
                     + token + "?mode=json")
        if not isinstance(data, list):
            data = []
        for it in data:
            url = clean(it.get("hostedUrl"))
            if not valid_url(url, ["jobs.lever.co"]):
                continue
            cat = it.get("categories") or {}
            locs = [clean(cat.get("location"))]
            for extra in cat.get("allLocations") or []:
                if clean(extra) not in locs:
                    locs.append(clean(extra))
            out.append(dict(
                id=name + "-" + clean(it.get("id")),
                title=it.get("text"), company=name, url=url,
                location=", ".join(x for x in locs if x),
                desc=it.get("descriptionPlain") or it.get("description"),
                posted=it.get("createdAt"),
                remote_verified=(
                    clean(it.get("workplaceType")).lower() == "remote"),
                source="Lever"))

    elif kind == "ashby":
        data = fetch("https://api.ashbyhq.com/posting-api/job-board/"
                     + token)
        for it in data.get("jobs", []):
            if it.get("isListed") is not True:
                continue
            url = clean(it.get("jobUrl"))
            if not valid_url(url, ["jobs.ashbyhq.com"]):
                continue
            secs = [clean(s.get("location"))
                    for s in (it.get("secondaryLocations") or [])
                    if isinstance(s, dict)]
            locs = [clean(it.get("location"))] + secs
            comp = it.get("compensation") or {}
            out.append(dict(
                id=name + "-" + url, title=it.get("title"),
                company=name, url=url,
                location=", ".join(x for x in locs if x),
                desc=it.get("descriptionPlain")
                     or it.get("descriptionHtml"),
                posted=it.get("publishedAt"),
                salary=comp.get("scrapeableCompensationSalarySummary"),
                remote_verified=(
                    it.get("isRemote") is True
                    or clean(it.get("workplaceType")).lower() == "remote"),
                source="Ashby"))

    elif kind == "smartrecruiters":
        data = fetch("https://api.smartrecruiters.com/v1/companies/"
                     + token + "/postings?limit=100")
        for it in data.get("content", []):
            url = clean(it.get("ref"))
            if not valid_url(url, ["jobs.smartrecruiters.com"]):
                continue
            ld = it.get("location")
            sections = (it.get("jobAd") or {}).get("sections") or {}
            out.append(dict(
                id=name + "-" + clean(it.get("id")),
                title=it.get("name"), company=name, url=url,
                location=(ld.get("fullLocation")
                          if isinstance(ld, dict) else ld),
                desc=(sections.get("jobDescription") or {}).get("text", ""),
                posted=it.get("releasedDate"),
                source="SmartRecruiters"))
    else:
        raise ValueError("unsupported source " + kind)

    for o in out:
        o["eligible_countries"] = allowed
        o["entry_required"] = entry_req
    return out


def jobicy_items():
    try:
        data = fetch("https://jobicy.com/api/v2/remote-jobs?count=100")
    except Exception:
        data = fetch("https://jobicy.com/api/jobs?count=200")
    out = []
    for it in data.get("jobs", []):
        url = clean(it.get("url"))
        if not valid_url(url, ["jobicy.com"]):
            continue
        level = clean(it.get("jobLevel")).lower()
        types = clean(it.get("jobType")).lower()
        lv = ""
        if any(w in level for w in ("senior", "mid", "manager", "lead")):
            lv = "senior"
        elif (any(w in level for w in
                  ("junior", "entry", "intern", "graduate"))
              or "intern" in types):
            lv = "entry"
        out.append(dict(
            id="Jobicy-" + clean(it.get("id")),
            title=it.get("jobTitle"),
            company=it.get("companyName"), url=url,
            location=it.get("jobGeo"),
            desc=it.get("jobDescription"),
            posted=it.get("pubDate"),
            logo=it.get("companyLogo"),
            category=it.get("jobIndustry"),
            remote_verified=True, level=lv, source="Jobicy"))
    return out


def remotive_items():
    data = fetch("https://remotive.com/api/remote-jobs")
    out = []
    for it in data.get("jobs", []):
        url = clean(it.get("url"))
        if not valid_url(url, ["remotive.com"]):
            continue
        out.append(dict(
            id="Remotive-" + clean(it.get("id")),
            title=it.get("title"),
            company=it.get("company_name"), url=url,
            location=it.get("candidate_required_location"),
            desc=it.get("description"),
            posted=it.get("publication_date"),
            logo=it.get("company_logo"),
            category=it.get("category"),
            salary=it.get("salary"),
            remote_verified=True, source="Remotive"))
    return out


def remoteok_items():
    data = fetch("https://remoteok.com/api")
    out = []
    for it in data:
        if (not isinstance(it, dict) or not it.get("id")
                or not it.get("position")):
            continue
        url = clean(it.get("url"))
        if not valid_url(url, ["remoteok.com"]):
            continue
        out.append(dict(
            id="RemoteOK-" + clean(it.get("id")),
            title=it.get("position"),
            company=it.get("company"), url=url,
            location=it.get("location"),
            desc=it.get("description"),
            posted=it.get("date") or it.get("epoch"),
            logo=it.get("logo"),
            category=", ".join((it.get("tags") or [])[:3]),
            remote_verified=True, source="RemoteOK"))
    return out


def main():
    try:
        with open("jobs.json", encoding="utf-8") as f:
            old_jobs = json.load(f).get("jobs", [])
    except Exception:
        old_jobs = []
    old_jobs = [j for j in old_jobs
                if clean(j.get("company")).lower() not in BLOCKED]

    with open("employers.json", encoding="utf-8") as f:
        employers = json.load(f).get("employers", [])

    for emp in employers:
        if emp.get("approved") is not True:
            continue
        name = clean(emp.get("company"))
        kind = clean(emp.get("source_type")).lower()
        if not name or not clean(emp.get("board_token")):
            errors.append(f"{name or 'Employer'}: missing token")
            continue
        try:
            run(name, f"{name} ({kind})", employer_items(emp))
        except Exception as exc:
            stats[name] = False
            errors.append(f"{name} ({kind}): {exc}")

    for key, fn in (("Jobicy", jobicy_items),
                    ("Remotive", remotive_items),
                    ("RemoteOK", remoteok_items)):
        try:
            run(key, key, fn())
        except Exception as exc:
            stats[key] = False
            errors.append(f"{key}: {exc}")

    for e in errors:
        print("SOURCE ERROR:", e)

    if stats and not any(stats.values()):
        print("ALL SOURCES FAILED - keeping old jobs.json")
        sys.exit(1)

    kept = 0
    for key in [k for k, ok in stats.items() if not ok]:
        for j in old_jobs:
            if (j.get("sourceKey") == key or j.get("company") == key
                    or j.get("source") == key):
                accepted.append(j)
                kept += 1
    if kept:
        print(f"Kept {kept} old jobs from failed sources")

    final_list = accepted
    if not final_list and old_jobs:
        print("WARNING: 0 jobs found, keeping old jobs")
        final_list = old_jobs

    seen_url, seen_sig, final = set(), set(), []
    for j in final_list:
        u = j["url"].split("?")[0].rstrip("/").lower()
        sig = (j["title"].lower().strip(),
               j["company"].lower().strip(),
               ",".join(sorted(j.get("countries", []))))
        if u in seen_url or sig in seen_sig:
            continue
        seen_url.add(u)
        seen_sig.add(sig)
        final.append(j)

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    final.sort(key=lambda j: parse_date(j.get("postedAt")) or epoch,
               reverse=True)

    cover = {c: sum(1 for j in final if c in j.get("countries", []))
             for c in ALL6}
    print("Country coverage:", cover)

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump({"updatedAt": NOW.isoformat(), "jobs": final},
                  f, ensure_ascii=False, indent=2)

    print(f"Saved {len(final)} qualifying jobs")


main()
