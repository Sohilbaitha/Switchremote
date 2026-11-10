const list = document.getElementById('list');
const statusEl = document.getElementById('status');
const chipsEl = document.getElementById('chips');
const q = document.getElementById('q');
const PLACES = [
  ['', 'All jobs'],
  ['new', 'New today'],
  ['Worldwide', '\u{1F30D} Worldwide'],
  ['Indonesia', '\u{1F1EE}\u{1F1E9} Indonesia'],
  ['Vietnam', '\u{1F1FB}\u{1F1F3} Vietnam'],
  ['Malaysia', '\u{1F1F2}\u{1F1FE} Malaysia'],
  ['Philippines', '\u{1F1F5}\u{1F1ED} Philippines'],
  ['Thailand', '\u{1F1F9}\u{1F1ED} Thailand'],
  ['India', '\u{1F1EE}\u{1F1F3} India']
];
const POST_URL = 'post-a-job.html';
// Every country has its own page, so the country chips are real links
const PAGES = {
  '': './',
  Worldwide: 'remote-jobs-worldwide.html',
  Indonesia: 'remote-jobs-indonesia.html',
  Vietnam: 'remote-jobs-vietnam.html',
  Malaysia: 'remote-jobs-malaysia.html',
  Philippines: 'remote-jobs-philippines.html',
  Thailand: 'remote-jobs-thailand.html',
  India: 'remote-jobs-india.html'
};
// Each job feed asks us to credit it and link back, so the source label is a link
const SOURCE_SITES = { Remotive: 'https://remotive.com', Jobicy: 'https://jobicy.com', Himalayas: 'https://himalayas.app', 'Remote OK': 'https://remoteok.com' };
let jobs = [];
// Country pages (remote-jobs-india.html and so on) set SR_PLACE so they open on that country
const HOME = window.SR_PLACE || '';
let place = HOME;
// A shared link (?job=...) pins that job at the top once, then the page behaves normally
let sharedKey = null, shared = null;
try {
  const sp = new URLSearchParams(location.search);
  sharedKey = sp.get('job');
  // ?q=word opens the page with that search already typed in
  if (sp.get('q')) q.value = sp.get('q');
  if (sharedKey) history.replaceState(null, '', location.pathname + location.hash);
} catch (e) {}

function jobId(j) {
  let h = 2166136261;
  for (const ch of j.url) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(36);
}

fetch('data/jobs.json?v=' + Date.now())
  .then(r => r.json())
  .then(d => {
    jobs = d.jobs || [];
    if (sharedKey) shared = jobs.find(j => jobId(j) === sharedKey) || null;
    const live = jobs.filter(j => inPlace(j, HOME)).length;
    const countEl = document.getElementById('count');
    const dot = document.createElement('i');
    dot.className = 'live';
    countEl.replaceChildren(dot, live + (live === 1 ? ' job' : ' jobs') + ' live right now');
    if (d.updated) {
      const fresh = document.createElement('span');
      fresh.className = 'fresh';
      fresh.textContent = 'Updated ' + ago(d.updated);
      countEl.append(fresh);
      document.getElementById('updated').textContent =
        'Last updated: ' + new Date(d.updated).toLocaleString();
    }
    render();
    if (shared) list.scrollIntoView({ block: 'start' });
  })
  .catch(() => { statusEl.textContent = 'Could not load jobs. Please try again later.'; });

function shareJob(j) {
  const where = j.countries.includes('Worldwide') ? 'anywhere in the world' : j.countries.map(placeName).join(', ');
  const url = 'https://switchremote.world/job.html?id=' + jobId(j);
  const text = j.title + ' at ' + j.company + ' (remote, ' + where + '). Free remote jobs for freshers on Switchremote.';
  if (window.track) track('share_click', { job_title: j.title, company: j.company });
  if (navigator.share) {
    navigator.share({ title: j.title + ' | Switchremote', text: text, url: url }).catch(() => {});
    return;
  }
  const done = () => toast('Link copied. Paste it anywhere to share.');
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text + ' ' + url).then(done, () => window.prompt('Copy this link:', url));
  } else {
    window.prompt('Copy this link:', url);
  }
}

function toast(msg) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2200);
}

// "2 hours ago" style wording for the last refresh
function ago(iso) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso)) / 6e4));
  if (m < 2) return 'just now';
  if (m < 60) return m + ' minutes ago';
  const h = Math.round(m / 60);
  return h < 24 ? h + (h === 1 ? ' hour ago' : ' hours ago') : Math.round(h / 24) + ' days ago';
}

function jobUrl(j) {
  return 'job.html?id=' + jobId(j);
}

function isNew(j) {
  return Date.now() - new Date(j.posted) < 864e5;
}

function inPlace(j, p) {
  if (!p) return true;
  if (p === 'new') return isNew(j) && inPlace(j, HOME);
  if (p === 'Worldwide') return j.countries.includes('Worldwide');
  return j.countries.includes(p) || j.countries.includes('Worldwide') || j.countries.includes('Asia');
}

// 'Asia' marks jobs open across Asia-Pacific but not the whole world
function placeName(x) {
  return x === 'Worldwide' ? 'Anywhere in the World' : x === 'Asia' ? 'Asia-Pacific' : x;
}

function age(iso) {
  const d = Math.floor((Date.now() - new Date(iso)) / 864e5);
  return d <= 0 ? 'Today' : d + 'd';
}

function tag(text, withSwitch) {
  const s = document.createElement('span');
  s.className = 'tag';
  if (withSwitch) {
    const sw = document.createElement('i');
    sw.className = 'sw';
    s.append(sw);
  }
  s.append(text);
  return s;
}

function sourceTag(source) {
  if (source === 'Employer') return tag('Posted by employer');
  const site = SOURCE_SITES[source];
  if (!site) return tag(source);
  const a = document.createElement('a');
  a.className = 'tag tag-src';
  a.href = site;
  a.target = '_blank';
  a.rel = source === 'Remote OK' ? 'noopener' : 'noopener noreferrer';
  a.textContent = 'via ' + source;
  return a;
}

// Windows does not draw flag emoji (it shows letters like "IN"), so hide flags there
const FLAGS_OK = (() => {
  try {
    const c = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
    c.canvas.width = c.canvas.height = 20;
    c.textBaseline = 'top';
    c.font = '16px sans-serif';
    c.fillText('\u{1F1EE}\u{1F1F3}', 0, 0);
    const d = c.getImageData(0, 0, 20, 20).data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i + 3] && (Math.abs(d[i] - d[i + 1]) > 40 || Math.abs(d[i + 1] - d[i + 2]) > 40)) return true;
    }
  } catch (e) {}
  return false;
})();

function drawChips() {
  chipsEl.replaceChildren();
  PLACES.forEach(([value, label]) => {
    // The chip for this page and "New today" filter in place. Every other chip opens that country's page.
    const isLink = value !== 'new' && value !== HOME;
    const b = document.createElement(isLink ? 'a' : 'button');
    b.className = 'chip' + (value === place ? ' on' : '');
    if (isLink) {
      b.href = PAGES[value];
    } else {
      b.type = 'button';
      b.setAttribute('aria-pressed', value === place);
      b.addEventListener('click', () => { place = value; shared = null; render(); });
    }
    b.append(FLAGS_OK ? label : label.replace(/^[\u{1F1E6}-\u{1F1FF}]{2} /u, ''));
    if (value === 'new') {
      b.classList.add('chip-new');
      const dot = document.createElement('i');
      dot.className = 'dot';
      b.prepend(dot);
    }
    const n = document.createElement('span');
    n.textContent = jobs.filter(j => inPlace(j, value)).length;
    b.append(n);
    chipsEl.append(b);
  });
  // On phones the chips scroll sideways, so bring the selected one into view
  const on = chipsEl.querySelector('.on');
  if (on && chipsEl.scrollWidth > chipsEl.clientWidth) chipsEl.scrollLeft = on.offsetLeft - chipsEl.offsetLeft - 16;
}

let firstPaint = true;
function render() {
  drawChips();
  const t = q.value.trim().toLowerCase();
  const rows = jobs.filter(j =>
    inPlace(j, place) && (!t || t.split(/\s+/).every(w => (j.title + ' ' + j.company + ' ' + j.countries.join(' ') + ' ' + j.source + (j.countries.includes('Worldwide') ? ' anywhere world' : '') + (j.countries.includes('Asia') ? ' asia pacific apac' : '')).toLowerCase().includes(w)))
  );
  if (shared && !t && !place) { rows.splice(rows.indexOf(shared), 1); rows.unshift(shared); }
  list.replaceChildren();
  if (rows.length) {
    statusEl.textContent = rows.length + (rows.length === 1 ? ' job' : ' jobs');
  } else {
    const link = document.createElement('a');
    link.href = POST_URL;
    link.setAttribute('data-track', 'post_job_click');
    link.textContent = 'Post your job for free';
    statusEl.replaceChildren('No jobs found here yet. Try another country or search, or ', link, '.');
  }
  list.classList.toggle('rise', firstPaint);
  firstPaint = false;
  rows.forEach((j, n) => {
    const card = document.createElement('article');
    card.className = 'job';
    card.style.setProperty('--n', Math.min(n, 11));
    // Tapping the card (not a button or link inside it) opens the job page
    card.addEventListener('click', e => { if (!e.target.closest('a,button')) location.href = jobUrl(j); });
    if (j === shared) {
      card.classList.add('shared');
      const lb = document.createElement('p');
      lb.className = 'shared-label';
      lb.textContent = 'Shared with you';
      card.append(lb);
    }
    const av = document.createElement('div');
    av.className = 'av av-' + (parseInt(jobId(j), 36) % 3);
    av.textContent = (j.company || '?').trim().charAt(0).toUpperCase();
    if (j.logo) {
      // The image sits inside the box from the start (hidden), so the browser always loads it
      const im = document.createElement('img');
      im.alt = '';
      im.referrerPolicy = 'no-referrer';
      im.decoding = 'async';
      im.hidden = true;
      im.onload = () => { if (im.naturalWidth > 1) { av.firstChild.remove(); im.hidden = false; av.className = 'av has-logo'; } else { im.remove(); } };
      im.onerror = () => im.remove();
      av.append(im);
      im.src = j.logo;
    }
    const body = document.createElement('div');
    body.className = 'body';
    const top = document.createElement('div');
    top.className = 'top';
    const h = document.createElement('h2');
    const hl = document.createElement('a');
    hl.href = jobUrl(j);
    hl.textContent = j.title;
    h.append(hl);
    const a = document.createElement('span');
    a.className = 'age';
    if (isNew(j)) { a.classList.add('new'); a.textContent = 'New'; } else { a.textContent = age(j.posted); }
    top.append(h, a);
    const c = document.createElement('p');
    c.className = 'company';
    c.textContent = j.company;
    const tags = document.createElement('div');
    tags.className = 'tags';
    tags.append(tag('Remote', true));
    if (j.kind) tags.append(tag(j.kind));
    j.countries.forEach(x => tags.append(tag(placeName(x))));
    tags.append(sourceTag(j.source));
    // The card opens the job page; applying happens there, next to the summary and safety tips
    const apply = document.createElement('a');
    apply.className = 'apply';
    apply.href = jobUrl(j);
    apply.textContent = 'View job';
    apply.addEventListener('click', () => {
      if (window.track) track('view_job_click', { job_title: j.title, company: j.company, source: j.source });
    });
    const actions = document.createElement('div');
    actions.className = 'actions';
    const report = document.createElement('a');
    report.className = 'report';
    report.href = 'mailto:contact@switchremote.world?subject=' + encodeURIComponent('Report a job: ' + j.title) +
      '&body=' + encodeURIComponent('Job: ' + j.title + ' at ' + j.company + '\nLink: ' + j.url + '\n\nWhat is wrong with this job?\n');
    report.textContent = 'Report';
    const share = document.createElement('button');
    share.type = 'button';
    share.className = 'share';
    share.setAttribute('aria-label', 'Share this job');
    share.title = 'Share';
    share.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>';
    share.addEventListener('click', () => shareJob(j));
    actions.append(apply, share, report);
    body.append(top, c, tags, actions);
    card.append(av, body);
    list.append(card);
  });
}

// "Share Switchremote" button under the job list
const shareSite = document.getElementById('share-site');
if (shareSite) shareSite.addEventListener('click', () => {
  const url = 'https://switchremote.world/';
  const text = 'Remote jobs for freshers across Asia and the world. Free, no signup.';
  if (window.track) track('share_site_click', {});
  if (navigator.share) { navigator.share({ title: 'Switchremote', text: text, url: url }).catch(() => {}); return; }
  if (navigator.clipboard) navigator.clipboard.writeText(text + ' ' + url).then(() => toast('Link copied. Paste it anywhere to share.'), () => window.prompt('Copy this link:', url));
  else window.prompt('Copy this link:', url);
});

q.addEventListener('input', () => { shared = null; render(); });
q.addEventListener('search', render);
q.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q.blur(); } });

// Hero greeting: one language at a time, unless the person prefers no motion
(() => {
  const hello = document.querySelector('.hello');
  if (!hello || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const words = [...hello.children];
  if (words.length < 2) return;
  let i = 0;
  hello.classList.add('rot');
  words[0].classList.add('on');
  setInterval(() => {
    words[i].classList.remove('on');
    i = (i + 1) % words.length;
    words[i].classList.add('on');
  }, 2200);
})();
