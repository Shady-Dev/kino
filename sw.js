// Bump on every index.html change. The page is network-first, so a fresh index.html
// wins online, but the old copy stays as the offline fallback until its cache is dropped.
// Data JSON is served from cache at once and refreshed behind, because waiting on the
// network is the largest launch cost on a slow connection and the page reports its
// data's age (IDEAS, 2026-08-29). v73-v76 are reserved by an unmerged branch.
const CACHE = 'leffavuoro-v117';

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
      // cache:'no-cache' revalidates with the origin instead of the browser's HTTP cache.
      // Pages serves max-age=600, so a plain fetch() was handed the stale body the HTTP
      // cache held and wrote it back here; the copy renewed itself indefinitely.
      const refresh = fetch(new Request(e.request, { cache: 'no-cache' })).then(async r => {
        if (r.ok) {
          const c = await caches.open(CACHE);
          await c.put(e.request, r.clone());
          // Tell the page fresher bytes landed, but only when it was handed the stale
          // copy; a first fetch already returned this response. The page re-renders
          // only on a real change.
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

  // r.ok before every put. Posters are cache-first, so a cached 404 (a deploy race, a
  // poster pruned upstream) would stay broken for the life of the cache version. The
  // caller still gets the real response.
  // Every cache write goes through e.waitUntil: once the response promise settles the
  // browser may terminate the worker, and a fire-and-forget put() can lose that race.
  // The write lost is the one the offline fallback needed.
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
      // This branch holds index.html, and the cached copy is the offline fallback, so a
      // 500 must not be cached.
      if (r.ok) {
        const copy = r.clone();
        e.waitUntil(caches.open(CACHE).then(c => c.put(e.request, copy))
          .catch(() => {}));
      }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
