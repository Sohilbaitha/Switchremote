"""One-off: find the new job board of companies whose old board link now returns 404. Not part of the refresh."""
import sys
sys.path.insert(0, "scripts")
import fetch_jobs as F
TRY = {
 "postman": "greenhouse:postmanlabs ashby:postman lever:postman workable:postman smartrecruiters:Postman",
 "doist": "ashby:doist workable:doist recruitee:doist lever:doist",
 "hotjar": "greenhouse:contentsquare ashby:hotjar lever:hotjar workable:hotjar ashby:contentsquare lever:contentsquare smartrecruiters:Contentsquare",
 "xendit": "greenhouse:xendit ashby:xendit workable:xendit smartrecruiters:Xendit",
 "paymongo": "ashby:paymongo greenhouse:paymongo workable:paymongo recruitee:paymongo",
 "g2": "greenhouse:g2 ashby:g2 lever:g2 ashby:g2crowd lever:g2crowd",
 "helpscout": "ashby:helpscout ashby:help-scout greenhouse:helpscout workable:helpscout",
 "jumpcloud": "ashby:jumpcloud lever:jumpcloud workable:jumpcloud",
 "onesignal": "ashby:onesignal lever:onesignal workable:onesignal",
 "thumbtack": "ashby:thumbtack lever:thumbtack greenhouse:thumbtackinc",
 "interviewkickstart": "ashby:interviewkickstart lever:interviewkickstart workable:interviewkickstart ashby:interview-kickstart",
}
for co, opts in TRY.items():
    for o in opts.split():
        k, s = o.split(":")
        try:
            got = list(F.READERS[k](s))
            ok = [j for j in got if j]
            print(f"RESULT {co} {k}:{s} total={len(got)} pass={len(ok)}", flush=True)
        except Exception as e:
            print(f"ERROR {co} {k}:{s} {str(e)[:60]}", flush=True)
