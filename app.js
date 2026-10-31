const list = document.getElementById('list');
const statusEl = document.getElementById('status');
const q = document.getElementById('q');
const country = document.getElementById('country');
let jobs = [];

fetch('data/jobs.json')
  .then(r => r.json())
  .then(d => {
    jobs = d.jobs || [];
    if (d.updated) {
      document.getElementById('updated').textContent =
        'Last updated: ' + new Date(d.updated).toLocaleString();
    }
    render();
  })
  .catch(() => { statusEl.textContent = 'Could not load jobs. Please try again later.'; });

function ago(iso) {
  const d = Math.floor((Date.now() - new Date(iso)) / 864e5);
  if (d <= 0) return 'Today';
  return d === 1 ? '1 day ago' : d + ' days ago';
}

function render() {
  const t = q.value.trim().toLowerCase();
  const c = country.value;
  const rows = jobs.filter(j =>
    (!c || j.countries.includes(c) || j.countries.includes('Worldwide')) &&
    (!t || (j.title + ' ' + j.company).toLowerCase().includes(t))
  );
  list.replaceChildren();
  statusEl.textContent = rows.length
    ? rows.length + ' jobs'
    : 'No jobs found. Try another country or search.';
  rows.forEach(j => {
    const row = document.createElement('div');
    row.className = 'job';
    const info = document.createElement('div');
    const h = document.createElement('h2');
    h.textContent = j.title;
    const p = document.createElement('p');
    p.textContent = j.company + ' - ' + j.countries.join(', ') + ' - ' + ago(j.posted) + ' - via ' + j.source;
    info.append(h, p);
    const a = document.createElement('a');
    a.className = 'apply';
    a.href = j.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer nofollow';
    a.textContent = 'Apply now';
    row.append(info, a);
    list.append(row);
  });
}

q.addEventListener('input', render);
country.addEventListener('change', render);
