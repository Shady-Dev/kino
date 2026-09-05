// Bump on any UI release: the page is network-first, so a fresh index.html always
// wins online, but the old copy stays as the offline fallback until its cache is dropped.
// Data JSON is the other way around -- served from cache at once, refreshed behind --
// because a launch that waits on the network is the single largest cost on a slow
// connection and the page can tell honestly how old its data is (IDEAS, 2026-08-29).
// v73-v76 are reserved by the unmerged onboarding-tooling branch; this jumped to v77.
const CACHE = 'leffavuoro-v116';

self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil((async () => {
  // Drop caches from previous versions so an old index.html cannot come back offline.
  const keys = await caches.keys();
  await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
  await clients.claim();
})()));

// page network-first with cache fallback; posters cache-first; data JSON cache-first
// with background refresh
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (url.pathname.includes('/data/') && url.pathname.endsWith('.json')) {
    e.respondWith((async () => {
      const cached = await caches.match(e.request);
      // cache:'no-cache' forces this to revalidate with the origin instead of being
      // answered from the browser's own HTTP cache. Pages serves max-age=600, so a
      // plain fetch() here was handed the same stale body the HTTP cache already held
      // and wrote it straight back into the SW cache -- the copy renewed itself and the
      // app could sit on old data indefinitely. Seen live: the origin had a refreshed
      // file while the page still rendered the previous one after several reloads.
      const refresh = fetch(new Request(e.request, { cache: 'no-cache' })).then(async r => {
        if (r.ok) {
          const c = await caches.open(CACHE);
          await c.put(e.request, r.clone());
          // Tell the page fresher bytes landed, but only when it was handed the stale
          // copy -- a first fetch already returned this response. The page compares
          // `generated` and re-renders only on a real change.
          if (cached) {
            for (const cl of await self.clients.matchAll({ type: 'window' }))
              cl.postMessage({ fresh: url.pathname });
          }
        }
        return r;
      });
      if (cached) {
        e.waitUntil(refresh.catch(() => {}));
        return cached;
      }
      return refresh;
    })());
    return;
  }

  // r.ok before every put, on every branch. A failed response used to be cached like
  // any other, and posters are cache-first: one 404 during a deploy race, or a poster
  // pruned upstream, and that tile stayed broken for the life of the cache version --
  // the request never reached the network again to find out it had been fixed. The
  // caller still gets the real response, so nothing here hides an error; it just stops
  // a transient becoming permanent. The data-JSON branch above already did this.
  // Every cache write below goes through e.waitUntil: once the response promise has
  // settled the browser may terminate the worker, and a fire-and-forget put() races
  // that shutdown. Online nothing is lost -- the next visit refetches -- but the write
  // that loses the race is exactly the one the offline fallback needed. The data-JSON
  // branch above already extends its refresh; these two did not.
  if (url.pathname.includes('/data/posters/')) {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
        if (r.ok) {
          const copy = r.clone();
          e.waitUntil(caches.open(CACHE).then(c => c.put(e.request, copy))
            .catch(() => {}));
        }
        return r;
      }))
    );
    return;
  }

  e.respondWith(
    fetch(e.request).then(r => {
      // Caching a 500 here is worse than caching a broken poster: this branch holds
      // index.html, and the cached copy is what the offline fallback serves.
      if (r.ok) {
        const copy = r.clone();
        e.waitUntil(caches.open(CACHE).then(c => c.put(e.request, copy))
          .catch(() => {}));
      }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
