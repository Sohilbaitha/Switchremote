// Job page: a quick look at one job before the person opens the original listing.
(function () {
  var box = document.getElementById('jd');
  var SOURCE_SITES = { Remotive: 'https://remotive.com', Jobicy: 'https://jobicy.com', Himalayas: 'https://himalayas.app', 'Remote OK': 'https://remoteok.com' };
  var KEEP_DAYS = 14;
  var id = null;
  try { id = new URLSearchParams(location.search).get('id'); } catch (e) {}

  function jobId(j) {
    var h = 2166136261;
    for (var ch of j.url) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
    return (h >>> 0).toString(36);
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function placeName(x) { return x === 'Worldwide' ? 'Any country' : x === 'Asia' ? 'Asia-Pacific' : x; }
  function days(iso) { return Math.floor((Date.now() - new Date(iso)) / 864e5); }
  function postedText(iso) {
    var d = days(iso);
    return d <= 0 ? 'Today' : d === 1 ? 'Yesterday' : d + ' days ago';
  }
  function applyLabel(j) {
    if (j.source === 'Employer' || j.source === 'Company site') return 'Apply on the company site';
    return 'Apply on ' + j.source;
  }
  function relFor(j) { return j.source === 'Remote OK' ? 'noopener' : 'noopener noreferrer nofollow'; }
  function toast(msg) {
    var t = document.getElementById('toast');
    if (!t) { t = el('div', 'toast'); t.id = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }
  function avatar(j) {
    var av = el('div', 'av av-' + (parseInt(jobId(j), 36) % 3), (j.company || '?').trim().charAt(0).toUpperCase());
    if (j.logo) {
      var im = document.createElement('img');
      im.alt = ''; im.referrerPolicy = 'no-referrer'; im.hidden = true;
      im.onload = function () { if (im.naturalWidth > 1) { av.firstChild.remove(); im.hidden = false; av.className = 'av has-logo'; } else { im.remove(); } };
      im.onerror = function () { im.remove(); };
      av.append(im);
      im.src = j.logo;
    }
    return av;
  }
  function fact(dl, label, value) {
    if (!value) return;
    var d = el('div');
    d.append(el('dt', null, label));
    var dd = el('dd');
    dd.append(value);
    d.append(dd);
    dl.append(d);
  }

  function gone() {
    document.title = 'Job no longer listed | Switchremote';
    box.replaceChildren();
    box.append(el('h1', null, 'This job is no longer listed'));
    box.append(el('p', 'jd-lead', 'It has probably closed, or it passed our ' + KEEP_DAYS + '-day limit. New remote jobs for freshers come in every 6 hours.'));
    var a = el('a', 'apply', 'See the latest jobs');
    a.href = './';
    box.append(a);
  }

  function show(j, all) {
    document.title = j.title + ' at ' + j.company + ' | Switchremote';
    box.replaceChildren();

    var back = el('a', 'jd-back', 'All jobs');
    back.href = './';
    box.append(back);

    var head = el('div', 'jd-head');
    var hb = el('div', 'jd-hb');
    hb.append(el('h1', null, j.title), el('p', 'company', j.company));
    head.append(avatar(j), hb);
    box.append(head);

    var tags = el('div', 'tags');
    if (days(j.posted) <= 0) tags.append(el('span', 'age new', 'New'));
    var remote = el('span', 'tag'); remote.append(el('i', 'sw'), 'Remote'); tags.append(remote);
    if (j.kind) tags.append(el('span', 'tag', j.kind));
    box.append(tags);

    var dl = el('dl', 'facts');
    fact(dl, 'You can apply from', j.countries.map(placeName).join(', '));
    fact(dl, 'Pay (as the source states it)', j.pay || '');
    fact(dl, 'Posted', postedText(j.posted));
    var left = KEEP_DAYS - days(j.posted);
    fact(dl, 'On Switchremote for', left > 1 ? left + ' more days' : 'Last day today');
    if (j.source === 'Employer') fact(dl, 'Listed by', 'The employer, reviewed by us');
    else if (SOURCE_SITES[j.source]) {
      var s = el('a', null, j.source);
      s.href = SOURCE_SITES[j.source]; s.target = '_blank';
      s.rel = j.source === 'Remote OK' ? 'noopener' : 'noopener noreferrer';
      fact(dl, 'Found on', s);
    } else fact(dl, 'Found on', "The company's own careers page");
    box.append(dl);

    if (j.summary) {
      box.append(el('h2', null, 'A quick look'));
      box.append(el('blockquote', 'jd-sum', j.summary));
      box.append(el('p', 'jd-note', 'This is a short extract from the original listing. Open the listing to read the full details, requirements and how to apply.'));
    } else {
      box.append(el('h2', null, 'About this job'));
      box.append(el('p', 'jd-note', 'Open the original listing to read the full details, requirements and how to apply.'));
    }

    var act = el('div', 'actions jd-actions');
    var apply = el('a', 'apply', applyLabel(j));
    apply.href = j.url; apply.target = '_blank'; apply.rel = relFor(j);
    apply.addEventListener('click', function () {
      if (window.track) track('apply_click', { job_title: j.title, company: j.company, source: j.source, country: j.countries.join(','), from: 'job_page' });
    });
    var share = el('button', 'ghost', 'Share');
    share.type = 'button';
    share.addEventListener('click', function () {
      var url = 'https://switchremote.world/job.html?id=' + jobId(j);
      var text = j.title + ' at ' + j.company + ' (remote). Free remote jobs for freshers on Switchremote.';
      if (window.track) track('share_click', { job_title: j.title, company: j.company });
      if (navigator.share) { navigator.share({ title: j.title + ' | Switchremote', text: text, url: url }).catch(function () {}); return; }
      if (navigator.clipboard) navigator.clipboard.writeText(text + ' ' + url).then(function () { toast('Link copied. Paste it anywhere to share.'); }, function () { window.prompt('Copy this link:', url); });
      else window.prompt('Copy this link:', url);
    });
    var report = el('a', 'report', 'Report');
    report.href = 'mailto:contact@switchremote.world?subject=' + encodeURIComponent('Report a job: ' + j.title) +
      '&body=' + encodeURIComponent('Job: ' + j.title + ' at ' + j.company + '\nLink: ' + j.url + '\n\nWhat is wrong with this job?\n');
    act.append(apply, share, report);
    box.append(act);

    var tips = el('div', 'jd-tips');
    tips.append(el('h2', null, 'Before you apply'));
    var ul = el('ul');
    ['Read the full listing first. The employer decides the final requirements.',
     'Apply only on the page this button opens. We never collect applications ourselves.',
     'A real employer will never ask you to pay for a job, training or equipment.'].forEach(function (t) { ul.append(el('li', null, t)); });
    tips.append(ul);
    box.append(tips);

    var more = all.filter(function (x) {
      return x !== j && x.countries.some(function (c) { return j.countries.indexOf(c) > -1 || c === 'Worldwide'; });
    }).slice(0, 4);
    if (more.length) {
      box.append(el('h2', null, 'More remote jobs like this'));
      var ml = el('div', 'jd-more');
      more.forEach(function (x) {
        var a = el('a', 'jd-row');
        a.href = 'job.html?id=' + jobId(x);
        var t = el('span', 'jd-row-t');
        t.append(el('b', null, x.title), el('span', null, x.company + ' · ' + x.countries.map(placeName).join(', ')));
        a.append(avatar(x), t);
        ml.append(a);
      });
      box.append(ml);
    }
    if (window.track) track('job_view', { job_title: j.title, company: j.company, source: j.source });
  }

  fetch('data/jobs.json?v=' + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var all = d.jobs || [];
      var j = id ? all.find(function (x) { return jobId(x) === id; }) : null;
      if (j) show(j, all); else gone();
    })
    .catch(function () { box.replaceChildren(el('p', 'status', 'Could not load this job. Please try again later.')); });
})();
