// Switchremote service worker.
// It lets phones offer "Install app". It does not cache anything, so jobs are always fresh.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  // Go to the network as normal; if the phone is offline, show a short message for pages
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(() => new Response(
    '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline | Switchremote</title>' +
    '<body style="font-family:sans-serif;padding:32px;text-align:center"><h1 style="font-size:22px">You are offline</h1>' +
    '<p>Connect to the internet to see the latest remote jobs on Switchremote.</p></body>',
    { headers: { 'Content-Type': 'text/html; charset=utf-8' } })));
});
