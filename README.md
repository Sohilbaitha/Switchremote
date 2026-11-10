# Switchremote

**Remote jobs for freshers.** Live at [switchremote.world](https://switchremote.world)

Switchremote is a free job board for freshers and early-career people looking for remote work. You pick where you live and it shows the remote jobs open to you.

I built it because freshers searching for remote jobs keep running into fake listings, registration fees and jobs that were closed months ago. Switchremote only lists jobs that come straight from company career pages and trusted remote job boards, and it's free for everyone. No sign-up, no fees.

> This is an MVP. I'm improving it every week.

## How it works

- A Python script (`scripts/fetch_jobs.py`) collects remote jobs from:
  - company career boards on Greenhouse, Lever, Ashby, Workable and Recruitee (listed in `sources.json`)
  - remote job feeds: Remotive, Jobicy, Himalayas and Remote OK
  - jobs submitted by employers through our Google Form
- It keeps only remote roles that freshers can apply for, removes duplicates and closed listings, and drops every job 14 days after it was posted.
- Jobs from job feeds are shown only for companies on the approved list in `sources.json`. Companies not checked yet are listed in `data/review.json`.
- `scripts/build_pages.py` writes one page per country and the sitemap.
- A GitHub Actions workflow runs every 6 hours (triggered by cron-job.org), so the list stays fresh without any manual work.
- The site is a static page hosted on GitHub Pages.

## Tech

HTML, CSS, JavaScript, Python, GitHub Actions, GitHub Pages

## For employers

Hiring remotely and open to freshers? You can list your job for free. Email **contact@switchremote.world** or use the employer form on the site.

## Contact

- Website: [switchremote.world](https://switchremote.world)
- Email: contact@switchremote.world
- Instagram: [@switchremote.world](https://www.instagram.com/switchremote.world)

Built by [Sohil Baitha](https://github.com/Sohilbaitha).

