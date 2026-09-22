/* Parseh — the service worker of the mobile interface installed as an app
   (docs/mobile.md, "Parseh as an app").  Served by serve.py at /sw.js, so
   that its scope is the whole toolbox; registered by lib/parseh.js and by
   the exercise pages' decks.js while the mode is mobile.

   IT IS NOT A CACHE OF THE TOOLBOX.  Parseh is a server on somebody's own
   computer, reached over their own network: every page, every book, every
   recording comes from there, fresh, exactly as it does with no worker at
   all.  What an installed app needs of a worker is that there is one, and
   that it answers the app's pages -- a browser installs only a site that
   has one -- and what the app gets back is a page of its own when the
   computer cannot be reached (asleep, off, the phone out of the house),
   instead of the browser's error.  So:
     - a page opened -- a navigation -- goes to the network as it always
       has, and only when the network fails is the offline page answered;
     - nothing else is touched: a recording and its ranges, a picture, an
       upload, every call of the API go by as if there were no worker.
   The offline page (/m/offline/, lib/mobile.py) is the one thing kept, when
   the worker is installed; a new VERSION here keeps it again and lets the
   old copy go. */
'use strict';
const VERSION = 'parseh-app-1';
const OFFLINE = '/m/offline/';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION)
    .then(c => c.add(new Request(OFFLINE, {cache: 'reload'})))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('parseh-app-') && k !== VERSION)
                                  .map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.mode !== 'navigate' || r.method !== 'GET') return;
  e.respondWith(fetch(r).catch(() =>
    caches.match(OFFLINE).then(page => page || Response.error())));
});
