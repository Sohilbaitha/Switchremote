const list = document.getElementById('list');
const statusEl = document.getElementById('status');
const chipsEl = document.getElementById('chips');
const q = document.getElementById('q');
const PLACES = [
  ['', 'All jobs'],
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

function inPlace(j, p) {
  if (!p) return true;
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
    inPlace(j, place) && (!t || (j.title + ' ' + j.company).toLowerCase().includes(t))
  );
  list.replaceChildren();
  if (rows.length) {
    statusEl.textContent = rows.length + (rows.length === 1 ? ' job' : ' jobs');
  } else {
    const link = document.createElement('a');
    link.href = POST_URL;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'Post your job for free';
    statusEl.replaceChildren('No jobs found here yet. Try another country or search, or ', link, '.');
  }
  rows.forEach(j => {
    const card = document.createElement('article');
    card.className = 'job';
    const av = document.createElement('div');
    av.className = 'av';
    av.textContent = (j.company || '?').trim().charAt(0).toUpperCase();
    const body = document.createElement('div');
    body.className = 'body';
    const top = document.createElement('div');
    top.className = 'top';
    const h = document.createElement('h2');
    h.textContent = j.title;
    const a = document.createElement('span');
    a.className = 'age';
    a.textContent = age(j.posted);
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
    apply.rel = 'noopener noreferrer nofollow';
    apply.textContent = 'Apply now';
    body.append(top, c, tags, apply);
    card.append(av, body);
    list.append(card);
  });
}

q.addEventListener('input', render);
