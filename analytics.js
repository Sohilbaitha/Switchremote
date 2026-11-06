// Paste your Google Analytics Measurement ID below (it looks like G-ABC123XYZ9).
var GA_ID = 'G-E2DQ5J7SHY';

var HAS_ID = GA_ID.indexOf('XXXX') === -1;
var KEY = 'sr_cookies';

window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }

window.track = function (name, params) {
  if (window.__gaLoaded) gtag('event', name, params || {});
};

function getChoice() {
  try { return localStorage.getItem(KEY); } catch (e) { return null; }
}
function setChoice(v) {
  try { localStorage.setItem(KEY, v); } catch (e) {}
}

function loadGA() {
  if (!HAS_ID || window.__gaLoaded) return;
  window.__gaLoaded = true;
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  gtag('js', new Date());
  gtag('config', GA_ID);
}

function clearGaCookies() {
  document.cookie.split(';').forEach(function (c) {
    var name = c.split('=')[0].trim();
    if (name.indexOf('_ga') === 0) {
      document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
      document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=' + location.hostname;
      document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=.' + location.hostname;
    }
  });
}

function showBanner() {
  if (document.getElementById('cookie')) return;
  var box = document.createElement('div');
  box.id = 'cookie';
  box.className = 'cookie';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', 'Cookie choice');
  box.innerHTML =
    '<p>We would like to use Google Analytics cookies to count visits and clicks, so we can improve Switchremote. ' +
    'You can say no and still use the whole site. <a href="legal.html#privacy">Read our privacy policy</a>.</p>' +
    '<div class="cookie-btns"><button type="button" class="yes">Accept</button>' +
    '<button type="button" class="no">No thanks</button></div>';
  document.body.appendChild(box);
  box.querySelector('.yes').addEventListener('click', function () {
    setChoice('yes'); loadGA(); box.remove();
  });
  box.querySelector('.no').addEventListener('click', function () {
    setChoice('no'); clearGaCookies(); window.__gaLoaded = false; box.remove();
  });
}

if (HAS_ID) {
  var choice = getChoice();
  if (choice === 'yes') loadGA();
  else if (!choice) showBanner();
}

document.addEventListener('click', function (e) {
  var t = e.target.closest && e.target.closest('[data-cookie-settings]');
  if (t) { e.preventDefault(); if (HAS_ID) showBanner(); return; }
  var a = e.target.closest && e.target.closest('a[data-track]');
  if (a) window.track(a.getAttribute('data-track'), {});
});

// Hide the "Cookie settings" link while analytics is switched off.
if (!HAS_ID) {
  document.querySelectorAll('[data-cookie-settings]').forEach(function (el) {
    if (el.parentNode) el.parentNode.style.display = 'none';
  });
}
