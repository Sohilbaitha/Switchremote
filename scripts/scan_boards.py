"""One-off check: how many jobs pass today's fresher rules, and how many would pass if jobs that
do not ask for any experience at all were also allowed. Prints counts and the extra jobs."""
import sys, json, re
from datetime import datetime, timezone, timedelta
sys.path.insert(0, "scripts")
import fetch_jobs as F

cfg = json.load(open("sources.json"))
strict_rule = F.fresher_ok

def loose_rule(title, text, level=""):
    if strict_rule(title, text, level):
        return True
    years = F.exp_years(text or "")
    # Allowed only when the listing asks for no experience at all: no number of years, no "experience required"
    return years is None and not F.HARD_EXP.search(text or "")

def collect():
    tasks = [F.remotive, F.jobicy, F.himalayas, F.himalayas_search, F.remoteok]
    for link in cfg["companies"]:
        k, s = F.detect(link)
        if k: tasks.append(lambda k=k, s=s: F.READERS[k](s))
    out = []
    for t in tasks:
        try: out += [j for j in t() if j]
        except Exception as e: pass
    now = datetime.now(timezone.utc)
    out = [j for j in out if F.parse_date(j["posted"]) >= now - timedelta(days=F.MAX_AGE_DAYS)]
    return F.final_pass(out, cfg, now)

F.fresher_ok = strict_rule; a = collect()
F.fresher_ok = loose_rule;  b = collect()
ka = {F.job_key(j) for j in a}
print("RESULT strict", len(a), "loose", len(b))
for j in b:
    if F.job_key(j) not in ka:
        print("EXTRA", j["title"], "|", j["company"], "|", ",".join(j["countries"]), "|", j["source"], "|", j["url"])
