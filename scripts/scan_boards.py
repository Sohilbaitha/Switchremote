"""One-off scan: which well-known company career boards have remote fresher jobs open to our countries.
Uses the same rules as fetch_jobs.py. Prints one line per board. Not part of the regular refresh."""
import sys, collections
sys.path.insert(0, "scripts")
import fetch_jobs as F

CANDIDATES = """
greenhouse: airbnb stripe dropbox figma discord duolingo datadog asana airtable coursera okta pagerduty mongodb gusto
 instacart reddit pinterest grammarly calendly intercom webflow vercel netlify hashicorp circleci sentry affirm toast samsara
 braze contentful smartsheet squarespace udemy chegg unity3d rubrik nutanix druva browserstack phonepe inmobi unacademy
 upgrad zeta hevodata chargebee innovaccer mindtickle wingify hackerearth vimeo bitwarden anthropic agoda lalamove ninjavan
 carousell deliveryhero cambly airwallex wise payoneer thinkific kong mural miro typeform hubspot zendesk freshbooks
 grafanalabs gitbook clevertap moengage whatfix leadsquared darwinbox exotel spinny acko jupiter slice cars24 meesho
 coinswitch smallcase zoho fivetran dbtlabs airbyte appsmith tooljet hasura chargepoint benchling teachable kajabi
 wellfound turing toptal andela
lever: plaid spotify upstox dreamsports swiggy mpl sharechat rapido zepto outreach traveloka gojek mynt carsome aspire
 atome fundingsocieties kumu tiket hackerrank pharmeasy cred groww jar khatabook vedantu byjus simplilearn whitehatjr
 eightfold highradius rocketlane signeasy leena gupshup
ashby: ramp linear vanta retool rippling loom mercury replit perplexity lattice docker quora anysphere cohere mistral
 posthog langchain huggingface clay attio sierra elevenlabs synthesia runway notion zapier deel
workable: toggl hotjar bunq pipedrive
smartrecruiters: Visa ServiceNow Bosch IKEA Equinix Ubisoft Wolt LinkedIn Square Atlassian
"""

seen = {(k, s.lower()) for k, s in (F.detect(l) for l in __import__("json").load(open("sources.json"))["companies"]) if k}
rows = []
for line in CANDIDATES.strip().split("\n"):
    pass
blocks = collections.OrderedDict()
cur = None
for tok in CANDIDATES.replace("\n", " ").split():
    if tok.endswith(":"):
        cur = tok[:-1]; blocks[cur] = []
    else:
        blocks[cur].append(tok)
for kind, slugs in blocks.items():
    for slug in slugs:
        if (kind, slug.lower()) in seen:
            print(f"SKIP already-added {kind}:{slug}"); continue
        try:
            got = list(F.READERS[kind](slug))
            ok = [j for j in got if j]
            print(f"RESULT {kind}:{slug} total={len(got)} pass={len(ok)} " +
                  " | ".join(f"{j['title']} [{','.join(j['countries'])}]" for j in ok[:4]), flush=True)
        except Exception as e:
            print(f"ERROR {kind}:{slug} {str(e)[:80]}", flush=True)
