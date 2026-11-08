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
try { const s = new URLSearchParams(location.search).get('q'); if (s) q.value = s.slice(0, 80); } catch (e) {}

fetch('data/jobs.json?v=' + Date.now())
  .then(r => r.json())
  .then(d => {
    jobs = d.jobs || [];
    document.getElementById('count').textContent = jobs.length + (jobs.length === 1 ? ' job' : ' jobs') + ' live right now';
    if (d.updated) {
      document.getElementById('updated').textContent =
        'Last updated: ' + new Date(d.updated).toLocaleString();
    }
    render();
  })
  .catch(() => { statusEl.textContent = 'Could not load jobs. Please try again later.'; });

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
    b.addEventListener('click', () => { place = value; render(); });
    chipsEl.append(b);
  });
}

function render() {
  drawChips();
  const t = q.value.trim().toLowerCase();
  const rows = jobs.filter(j =>
    inPlace(j, place) && (!t || t.split(/\s+/).every(w => (j.title + ' ' + j.company + ' ' + j.countries.join(' ') + ' ' + j.source + (j.countries.includes('Worldwide') ? ' anywhere world' : '')).toLowerCase().includes(w)))
  );
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
    const share = document.createElement('a');
    share.className = 'share';
    const place2 = j.countries.includes('Worldwide') ? 'anywhere in the world' : j.countries.join(', ');
    const msg = j.title + ' at ' + j.company + ' (remote, ' + place2 + ')\nFree remote jobs for freshers on Switchremote:\nhttps://switchremote.world/?q=' + encodeURIComponent(j.title);
    share.href = 'https://wa.me/?text=' + encodeURIComponent(msg);
    share.target = '_blank';
    share.rel = 'noopener noreferrer';
    share.setAttribute('aria-label', 'Share this job on WhatsApp');
    share.title = 'Share on WhatsApp';
    share.innerHTML = '<svg viewBox="0 0 448 512" aria-hidden="true"><path d="M380.9 97.1A223.5 223.5 0 0 0 222 31C98.3 31-2.4 131.7-2.4 255.4c0 39.5 10.3 78.1 29.9 112L-4 480l115.6-30.4a223 223 0 0 0 106.4 27.1h.1c123.6 0 224.4-100.7 224.4-224.4 0-60-23.3-116.3-61.6-155.2zM222 438.6c-33.4 0-66.2-9-94.7-25.9l-6.8-4-68.6 18 18.3-66.9-4.4-6.9a185.8 185.8 0 0 1-28.5-99.4c0-102.8 83.7-186.5 186.7-186.5 49.8 0 96.6 19.4 131.8 54.7a185.4 185.4 0 0 1 54.6 131.9c0 102.9-83.8 186.6-188.4 186.6zm102.2-139.7c-5.6-2.8-33.1-16.3-38.2-18.2-5.1-1.9-8.8-2.8-12.6 2.8-3.7 5.6-14.4 18.2-17.7 22-3.3 3.7-6.5 4.2-12.1 1.4-33.3-16.6-55.1-29.7-77.1-67.3-5.8-10 5.8-9.3 16.6-30.9 1.8-3.7.9-7-.5-9.8-1.4-2.8-12.6-30.3-17.2-41.5-4.5-10.9-9.1-9.4-12.6-9.6-3.2-.2-7-.2-10.7-.2-3.7 0-9.8 1.4-15 7-5.1 5.6-19.6 19.2-19.6 46.7s20.1 54.2 22.9 57.9c2.8 3.7 39.5 60.3 95.7 84.6 35.5 15.3 49.4 16.6 67.2 14 10.8-1.6 33.1-13.5 37.8-26.6 4.7-13.1 4.7-24.3 3.3-26.6-1.3-2.5-5-3.9-10.6-6.6z"/></svg>';
    share.addEventListener('click', () => {
      if (window.track) track('share_click', { job_title: j.title, company: j.company });
    });
    actions.append(apply, share, report);
    body.append(top, c, tags, actions);
    card.append(av, body);
    list.append(card);
  });
}

q.addEventListener('input', render);
q.addEventListener('search', render);
q.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q.blur(); } });

