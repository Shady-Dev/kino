// Bump on every index.html change. The page is network-first, so a fresh index.html
// wins online, but the old copy stays as the offline fallback until its cache is dropped.
// Data JSON is served from cache at once and refreshed behind, because waiting on the
// network is the largest launch cost on a slow connection and the page reports its
// data's age (IDEAS, 2026-08-29). v73-v76 are reserved by an unmerged branch.
const CACHE = 'leffavuoro-v212';

// This app's own caches and nothing else. The sweep below used to delete every key it
// did not recognise, which on a shared origin is somebody else's storage.
const OWNED = /^leffavuoro-v(\d+)$/;
const versionOf = k => { const m = OWNED.exec(k); return m ? Number(m[1]) : -1; };
// What survives a version bump: the schedule JSON and the mirrored posters, both under
// /data/. Never the app shell. Dropping the old cache wholesale also threw away data the
// new worker had no copy of -- it activates empty, because the navigation that discovered
// the update was served by the *old* worker and network-first -- so an update left the
// next offline launch with no schedule at all. Carrying /data/ over fixes that without
// touching the rule the delete was there for: the shell is not migrated, so an old
// index.html still cannot come back as the offline fallback.
const MIGRATES = p => p.startsWith('/data/');

self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil((async () => {
  const keys = await caches.keys();
  const old = keys.filter(k => k !== CACHE && OWNED.test(k))
                  .sort((a, b) => versionOf(b) - versionOf(a));   // newest first
  const target = await caches.open(CACHE);
  for (const key of old) {
    const prev = await caches.open(key);
    for (const req of await prev.keys()) {
      const url = new URL(req.url, location.origin);
      if (url.origin !== location.origin || !MIGRATES(url.pathname)) continue;
      if (await target.match(req)) continue;
      const res = await prev.match(req);
      if (res) await target.put(req, res);
    }
  }
  await Promise.all(old.map(k => caches.delete(k)));
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
