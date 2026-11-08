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
const POST_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSeFsL9SU7VFMi27pCQri7ZziHbTVDPguEFP6cJvhidkb2psNQ/viewform';
let jobs = [];
let place = '';
// A shared link (?job=...) pins that job at the top once, then the page behaves normally
let sharedKey = null, shared = null;
try {
  const sp = new URLSearchParams(location.search);
  sharedKey = sp.get('job') || sp.get('q');
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
    if (sharedKey) shared = jobs.find(j => jobId(j) === sharedKey || j.title === sharedKey) || null;
    document.getElementById('count').textContent = jobs.length + (jobs.length === 1 ? ' job' : ' jobs') + ' live right now';
    if (d.updated) {
      document.getElementById('updated').textContent =
        'Last updated: ' + new Date(d.updated).toLocaleString();
    }
    render();
    if (shared) list.scrollIntoView({ block: 'start' });
  })
  .catch(() => { statusEl.textContent = 'Could not load jobs. Please try again later.'; });

function shareJob(j) {
  const where = j.countries.includes('Worldwide') ? 'anywhere in the world' : j.countries.join(', ');
  const url = 'https://switchremote.world/?job=' + jobId(j);
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

function isNew(j) {
  return Date.now() - new Date(j.posted) < 864e5;
}

function inPlace(j, p) {
  if (!p) return true;
  if (p === 'new') return isNew(j);
  if (p === 'Worldwide') return j.countries.includes('Worldwide');
  return j.countries.includes(p) || j.countries.includes('Worldwide');
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

function drawChips() {
  chipsEl.replaceChildren();
  PLACES.forEach(([value, label]) => {
    const b = document.createElement('button');
    b.className = 'chip' + (value === place ? ' on' : '');
    b.textContent = label;
    if (value === 'new') {
      b.classList.add('chip-new');
      const dot = document.createElement('i');
      dot.className = 'dot';
      b.prepend(dot);
    }
    const n = document.createElement('span');
    n.textContent = jobs.filter(j => inPlace(j, value)).length;
    b.append(n);
    b.addEventListener('click', () => { place = value; shared = null; render(); });
    chipsEl.append(b);
  });
}

function render() {
  drawChips();
  const t = q.value.trim().toLowerCase();
  const rows = jobs.filter(j =>
    inPlace(j, place) && (!t || t.split(/\s+/).every(w => (j.title + ' ' + j.company + ' ' + j.countries.join(' ') + ' ' + j.source + (j.countries.includes('Worldwide') ? ' anywhere world' : '')).toLowerCase().includes(w)))
  );
  if (shared && !t && !place) { rows.splice(rows.indexOf(shared), 1); rows.unshift(shared); }
  list.replaceChildren();
  if (rows.length) {
    statusEl.textContent = rows.length + (rows.length === 1 ? ' job' : ' jobs');
  } else {
    const link = document.createElement('a');
    link.href = POST_URL;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.setAttribute('data-track', 'post_job_click');
    link.textContent = 'Post your job for free';
    statusEl.replaceChildren('No jobs found here yet. Try another country or search, or ', link, '.');
  }
  rows.forEach(j => {
    const card = document.createElement('article');
    card.className = 'job';
    if (j === shared) {
      card.classList.add('shared');
      const lb = document.createElement('p');
      lb.className = 'shared-label';
      lb.textContent = 'Shared with you';
      card.append(lb);
    }
    const av = document.createElement('div');
    av.className = 'av';
    av.textContent = (j.company || '?').trim().charAt(0).toUpperCase();
    if (j.logo) {
      // The image sits inside the box from the start (hidden), so the browser always loads it
      const im = document.createElement('img');
      im.alt = '';
      im.referrerPolicy = 'no-referrer';
      im.decoding = 'async';
      im.hidden = true;
      im.onload = () => { if (im.naturalWidth > 1) { av.firstChild.remove(); im.hidden = false; av.classList.add('has-logo'); } else { im.remove(); } };
      im.onerror = () => im.remove();
      av.append(im);
      im.src = j.logo;
    }
    const body = document.createElement('div');
    body.className = 'body';
    const top = document.createElement('div');
    top.className = 'top';
    const h = document.createElement('h2');
    h.textContent = j.title;
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
    j.countries.forEach(x => tags.append(tag(x === 'Worldwide' ? 'Anywhere in the World' : x)));
    tags.append(tag(j.source));
    const apply = document.createElement('a');
    apply.className = 'apply';
    apply.href = j.url;
    apply.target = '_blank';
    apply.rel = j.source === 'Remote OK' ? 'noopener' : 'noopener noreferrer nofollow';
    apply.textContent = 'Apply now';
    apply.addEventListener('click', () => {
      if (window.track) track('apply_click', { job_title: j.title, company: j.company, source: j.source, country: j.countries.join(',') });
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

q.addEventListener('input', () => { shared = null; render(); });
q.addEventListener('search', render);
q.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q.blur(); } });
