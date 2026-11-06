// Paste your Google Analytics Measurement ID below (it looks like G-ABC123XYZ9).
var GA_ID = 'G-E2DQ5J7SHY';

window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }

var GA_ON = GA_ID.indexOf('XXXX') === -1;

window.track = function (name, params) {
  if (GA_ON) gtag('event', name, params || {});
};

if (GA_ON) {
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  gtag('js', new Date());
  gtag('config', GA_ID);
}

// Any link with a data-track="name" attribute is counted when clicked.
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[data-track]');
  if (a) window.track(a.getAttribute('data-track'), {});
});
