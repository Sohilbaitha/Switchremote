"""One-off check: how many fresher jobs we would have if every country were allowed. Not part of the refresh."""
import sys, json, re, collections
from datetime import datetime, timezone, timedelta
sys.path.insert(0, "scripts")
import fetch_jobs as F

cfg = json.load(open("sources.json"))
orig = F.countries_for
def any_country(location):
    found = orig(location)
    return found or (["OTHER:" + re.sub(r"\s+", " ", location or "").strip()[:50]] if (location or "").strip() else [])
F.countries_for = any_country

EXTRA = ("greenhouse:airbnb greenhouse:stripe greenhouse:dropbox greenhouse:figma greenhouse:discord greenhouse:duolingo "
 "greenhouse:datadog greenhouse:asana greenhouse:airtable greenhouse:coursera greenhouse:okta greenhouse:pagerduty greenhouse:mongodb "
 "greenhouse:gusto greenhouse:instacart greenhouse:reddit greenhouse:pinterest greenhouse:calendly greenhouse:intercom greenhouse:vercel "
 "greenhouse:netlify greenhouse:circleci greenhouse:affirm greenhouse:toast greenhouse:samsara greenhouse:braze greenhouse:contentful "
 "greenhouse:smartsheet greenhouse:squarespace greenhouse:rubrik greenhouse:druva greenhouse:inmobi greenhouse:bitwarden greenhouse:anthropic "
 "greenhouse:agoda greenhouse:wise greenhouse:payoneer greenhouse:typeform greenhouse:grafanalabs greenhouse:fivetran greenhouse:chargepoint "
 "lever:spotify lever:outreach ashby:ramp ashby:linear ashby:vanta ashby:replit ashby:perplexity ashby:docker ashby:quora ashby:cohere "
 "ashby:langchain ashby:attio ashby:sierra ashby:synthesia").split()
tasks = [F.remotive, F.jobicy, F.himalayas, F.himalayas_search, F.remoteok]
for link in cfg["companies"]:
    k, s = F.detect(link)
    if k: tasks.append(lambda k=k, s=s: F.READERS[k](s))
for x in EXTRA:
    k, s = x.split(":"); tasks.append(lambda k=k, s=s: F.READERS[k](s))
jobs = []
for t in tasks:
    try: jobs += [j for j in t() if j]
    except Exception: pass
now = datetime.now(timezone.utc)
jobs = [j for j in jobs if F.parse_date(j["posted"]) >= now - timedelta(days=F.MAX_AGE_DAYS)]
# company boards from EXTRA count as approved for this check
cfg["approved_companies"] += [F.nice(x.split(":")[1]) for x in EXTRA]
jobs = F.final_pass(jobs, cfg, now)
ours = [j for j in jobs if not any(c.startswith("OTHER:") for c in j["countries"])]
other = [j for j in jobs if j not in ours]
print("RESULT now", len(ours), "extra_if_worldwide", len(other))
places = collections.Counter(c[6:] for j in other for c in j["countries"])
for p, n in places.most_common(40): print("PLACE", n, p)
for j in other[:60]: print("JOB", j["title"], "|", j["company"], "|", j["countries"][0][6:], "|", j["source"])
