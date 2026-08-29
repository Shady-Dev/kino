// Bump on any UI release: the page is network-first, so a fresh index.html always
// wins online, but the old copy stays as the offline fallback until its cache is dropped.
// Data JSON is the other way around -- served from cache at once, refreshed behind --
// because a launch that waits on the network is the single largest cost on a slow
// connection and the page can tell honestly how old its data is (IDEAS, 2026-08-29).
const CACHE = 'leffavuoro-v57';

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

  if (url.pathname.includes('/data/posters/')) {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return r;
      }))
    );
    return;
  }

  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
