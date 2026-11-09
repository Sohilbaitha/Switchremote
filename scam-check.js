(function(){
  // w = points for "Yes", n = points for "Not sure", stop = one "Yes" means high risk
  var Q = [
    {q:'Did they ask you to pay anything?', h:'A registration fee, training, a deposit, a "starter kit", a laptop or equipment, or any money that "will be refunded later".', stop:true, why:'They asked you to pay. Real employers never ask candidates to pay for a job.'},
    {q:'Is the work about liking videos, rating products or doing "tasks" for commission?', h:'Including tasks you must top up or "recharge" money to unlock.', stop:true, why:'This is how task scams work. They pay small amounts first, then ask you to put in money.'},
    {q:'Do they want you to receive money or parcels and send them on?', h:'For example "payment processing agent", "money transfer agent" or forwarding packages.', stop:true, why:'Moving money or parcels for strangers can make you part of a crime, even if you did not know.'},
    {q:'Did the whole hiring happen only on WhatsApp or Telegram chat?', h:'No video call, no phone interview, no email from a company address.', w:3, n:1, why:'The hiring happened only on chat apps. Real companies usually interview you properly.'},
    {q:'Did they offer you the job without any interview or test?', h:'', w:3, n:1, why:'You got an offer without any interview or test.'},
    {q:'Did they ask for Aadhaar, PAN, ID, bank details or an OTP before a written offer?', h:'', w:3, n:1, why:'They wanted personal or bank details before giving you a written offer.'},
    {q:'Is the recruiter writing from a personal email like Gmail or Yahoo?', h:'Instead of an email that ends with the company\u2019s own website name.', w:2, n:1, why:'The recruiter uses a personal email, not a company email.'},
    {q:'Does the pay sound too good for very little work and no experience?', h:'', w:2, n:0, why:'The pay sounds too good for the work and experience asked.'},
    {q:'Are they rushing you, like "join today" or "only a few seats left"?', h:'', w:1, n:0, why:'They are rushing you to decide fast.'},
    {q:'Does the company have its own website and a real LinkedIn page?', h:'Search the company name yourself. Do not use links they sent you.', invert:true, w:2, n:1, why:'We could not confirm the company has its own website and LinkedIn page.'},
    {q:'Can you find this same job on the company\u2019s official careers page or a trusted job site?', h:'', invert:true, w:2, n:1, why:'The job could not be found on the company\u2019s own careers page or a trusted job site.'}
  ];
  var app = document.getElementById('app'), i = -1, ans = [];
  function el(t, c, txt){ var e = document.createElement(t); if (c) e.className = c; if (txt != null) e.textContent = txt; return e; }
  function intro(){
    app.replaceChildren();
    app.append(el('p','q','11 quick questions, under 2 minutes.'));
    app.append(el('p','hint','Answer Yes, No or Not sure. Think of one specific job offer while you answer.'));
    var b = el('button','apply start','Start the check'); b.type = 'button';
    b.onclick = function(){ i = 0; ans = []; ask(); };
    app.append(b);
  }
  function ask(){
    var x = Q[i];
    app.replaceChildren();
    var p = el('div','prog'), bar = el('i'); bar.style.width = (i / Q.length * 100) + '%'; p.append(bar); app.append(p);
    app.append(el('p','step','Question ' + (i + 1) + ' of ' + Q.length));
    app.append(el('p','q',x.q));
    if (x.h) app.append(el('p','hint',x.h));
    var o = el('div','opts');
    [['Yes','y'],['No','n'],['Not sure','u']].forEach(function(a){
      var b = el('button','opt',a[0]); b.type = 'button';
      b.onclick = function(){ ans[i] = a[1]; i++; i < Q.length ? ask() : result(); };
      o.append(b);
    });
    app.append(o);
    if (i > 0) { var bk = el('button','back','Back'); bk.type = 'button'; bk.onclick = function(){ i--; ask(); }; app.append(bk); }
    var f = app.querySelector('.opt'); if (f) f.focus({preventScroll:true});
  }
  function result(){
    var score = 0, stop = false, why = [];
    Q.forEach(function(x, k){
      var a = ans[k], bad = x.invert ? a === 'n' : a === 'y';
      if (bad) { if (x.stop) stop = true; else score += x.w; why.push(x.why); }
      else if (a === 'u' && !x.stop) { score += x.n; if (x.n) why.push('Not sure: ' + x.q.replace(/\?$/, '') + '. Try to find this out.'); }
      else if (a === 'u' && x.stop) { score += 3; why.push('Not sure: ' + x.q.replace(/\?$/, '') + '. Please find out before you go ahead.'); }
    });
    var lvl = stop || score >= 5 ? 'high' : score >= 2 ? 'mid' : 'low';
    var T = {
      high: ['High risk', 'This offer shows strong signs of a scam.', ['Do not pay anything and do not share any more personal or bank details.', 'Stop replying to them until you have checked the company yourself.', 'If you found this job on Switchremote, tap Report on the job so we can check it and take it down.']],
      mid:  ['Be careful', 'Some things about this offer do not look right.', ['Search the company name yourself and check its website and LinkedIn page.', 'Ask for a video interview and a written offer from a company email address.', 'Do not pay anything or share bank details while you check.']],
      low:  ['Few warning signs', 'We did not see the usual scam signs in your answers.', ['This does not mean the job is real. Still check the company yourself before you share personal details.', 'Apply only through the company\u2019s own page or a trusted job site.']]
    }[lvl];
    app.replaceChildren();
    var ICON = {
      high: '<path d="M12 3l9 16H3z"/><path d="M12 10v4"/><path d="M12 17.5v.01"/>',
      mid:  '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
      low:  '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>'
    };
    var CHEER = {
      high: 'Good call checking before you went ahead. That one step can save you a lot.',
      mid:  'Smart move to pause and check. A few minutes now can save you trouble later.',
      low:  'Nice work being careful. Keep checking every offer like this.'
    };
    var r = el('div','res');
    var top = el('div','hero-r');
    var ic = el('div','ico ' + lvl); ic.setAttribute('aria-hidden','true');
    ic.innerHTML = '<svg viewBox="0 0 24 24">' + ICON[lvl] + '</svg>';
    var tx = el('div');
    tx.append(el('span','lvl ' + lvl, T[0]));
    tx.append(el('p','cheer', CHEER[lvl]));
    top.append(ic, tx); r.append(top);
    var m = el('div','meter ' + lvl); m.setAttribute('aria-hidden','true'); m.append(el('span'), el('span'), el('span')); r.append(m);
    var ml = el('div','meter-l'); ml.setAttribute('aria-hidden','true'); ml.append(el('span',null,'Few signs'), el('span',null,'Some signs'), el('span',null,'Many signs')); r.append(ml);
    r.append(el('h2', null, T[1]));
    if (why.length) { r.append(el('h3', null, 'What we noticed')); var u = el('ul'); why.forEach(function(w){ u.append(el('li', null, w)); }); r.append(u); }
    r.append(el('h3', null, 'What to do next'));
    var u2 = el('ul'); T[2].forEach(function(w){ u2.append(el('li', null, w)); }); r.append(u2);
    var g = el('div','gold'); g.append(el('h3', null, 'Always remember'));
    var ol = el('ol');
    ['Never pay money to get a job, training, equipment or a "starter kit".', 'Never share OTPs, passwords or bank details with a recruiter.', 'Apply only on the company\u2019s own careers page or a trusted job site.'].forEach(function(w){ ol.append(el('li', null, w)); });
    g.append(ol); r.append(g);
    var b = el('button','apply again','Check another job'); b.type = 'button'; b.onclick = intro; r.append(b);
    app.append(r);
    if (window.track) track('scam_check_done', { result: lvl });
    app.scrollIntoView({block:'start'});
  }
  intro();
})();
