"""One-off report: which countries would add the most jobs that already pass every fresher,
remote and safety rule. Changes nothing on the site."""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "scripts" / "fetch_jobs.py").read_text()
src = re.sub(r"\nmain\(\)\s*$", "\n", src)
ns = {"__file__": str(ROOT / "scripts" / "fetch_jobs.py"), "__name__": "scan"}
exec(compile(src, "fetch_jobs.py", "exec"), ns)

CANDIDATES = ["Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Nigeria", "Kenya", "Ghana", "Egypt",
              "South Africa", "Brazil", "Mexico", "Colombia", "Argentina", "Peru", "Chile",
              "Turkey", "United Kingdom", "Canada", "United States", "Germany", "Poland", "Spain",
              "Portugal", "Romania", "Ukraine", "Singapore", "Japan", "Australia", "United Arab Emirates"]
WORDS = {c: [c.lower()] for c in CANDIDATES}
WORDS["United States"] += ["usa", "u.s.", "us only", "united states of america", "us-based", "us based", "america"]
WORDS["United Kingdom"] += ["uk", "england", "london"]
WORDS["United Arab Emirates"] += ["uae", "dubai"]
REGIONS = {"Latin America": ["latam", "latin america", "south america"], "Europe": ["europe", "eu ", "emea"],
           "Africa": ["africa"], "North America": ["north america"], "Middle East": ["middle east", "mena"]}

ns["HIMALAYAS_PLACES"] = list(ns["HIMALAYAS_PLACES"]) + CANDIDATES
# Go slowly so Himalayas does not rate limit the extra country searches
import time
_hget = ns["himalayas_get"]
def slow_get(url):
    for attempt in range(3):
        time.sleep(6)
        try:
            return _hget(url)
        except Exception as e:
            if "429" not in str(e) or attempt == 2:
                raise
            time.sleep(30)
ns["himalayas_get"] = slow_get
orig = ns["countries_for"]
def tagged(location):
    found = orig(location)
    return found or ["OTHER::" + (location or "").strip()[:160]]
ns["countries_for"] = tagged

captured = {}
orig_final = ns["final_pass"]
def final_pass(all_jobs, cfg, now):
    all_jobs = list(all_jobs)
    captured["all"] = all_jobs
    kept = orig_final(all_jobs, cfg, now)
    captured["kept"] = kept
    return kept
ns["final_pass"] = final_pass
ns["OUT"] = ROOT / "scan" / "jobs_scan.json"
ns["REVIEW_OUT"] = ROOT / "scan" / "review_scan.json"
ns["main"]()

def places(loc):
    t = " " + loc.lower() + " "
    out = [c for c, w in WORDS.items() if any(re.search(r"(?<![a-z])" + re.escape(x.strip()) + r"(?![a-z])", t) for x in w)]
    out += [r for r, w in REGIONS.items() if any(x in t for x in w)]
    return out or ["(unclear: " + loc[:60] + ")"]

def report(jobs):
    other = [j for j in jobs if j["countries"][0].startswith("OTHER::")]
    by = defaultdict(list)
    for j in other:
        for p in places(j["countries"][0][7:]):
            by[p].append(j)
    return other, by

kept_other, kept_by = report(captured.get("kept", []))
all_other, all_by = report(captured.get("all", []))
target_now = [j for j in captured.get("kept", []) if not j["countries"][0].startswith("OTHER::")]
out = {"live_rule_jobs_now": len(target_now),
       "blocked_only_by_country_and_approved": len(kept_other),
       "blocked_only_by_country_any_company": len(all_other),
       "by_place_approved": {p: [{"title": j["title"], "company": j["company"], "source": j["source"],
                                   "where": j["countries"][0][7:], "url": j["url"]} for j in v]
                             for p, v in sorted(kept_by.items(), key=lambda x: -len(x[1]))},
       "by_place_any_company": {p: [{"title": j["title"], "company": j["company"], "source": j["source"],
                                      "where": j["countries"][0][7:], "url": j["url"]} for j in v]
                                for p, v in sorted(all_by.items(), key=lambda x: -len(x[1]))}}
(ROOT / "scan" / "country_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("target-country jobs:", len(target_now))
print("approved, blocked only by country:", len(kept_other))
for p, v in sorted(kept_by.items(), key=lambda x: -len(x[1])):
    print(f"  {p}: {len(v)}")
print("companies waiting for review:", len(ns["REVIEW"]))
print("any company, blocked only by country:", len(all_other))
for p, v in sorted(all_by.items(), key=lambda x: -len(x[1]))[:25]:
    print(f"  {p}: {len(v)}")

print("=== DETAIL any company ===")
for p, v in sorted(all_by.items(), key=lambda x: -len(x[1])):
    for j in v:
        print(f"{p} | {j['company']} | {j['title'][:60]} | {j['source']} | {j['countries'][0][7:][:60]}")
