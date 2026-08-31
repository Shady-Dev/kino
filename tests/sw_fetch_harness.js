// Drives the real sw.js fetch handler with stubbed Cache/fetch and reports what it
// stored. Run by tests/test_sw_cache.py; prints one JSON line.
//
// The service worker cannot be exercised in a browser here (the harness browser blocks
// registration), and the behaviour under test is a decision this file makes -- "was
// r.ok true before put" -- not something the Cache API does on its own. So a stub is the
// right instrument: it records the calls the code chose to make.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SW = path.join(__dirname, '..', 'sw.js');
const ORIGIN = 'https://leffavuoro.fi';

function response(status, body) {
  const r = {
    status,
    ok: status >= 200 && status < 300,
    headers: { get: () => null },
    clone() { return Object.assign({}, r); },
    body: body || '',
  };
  return r;
}

function run(cases) {
  const listeners = {};
  const stored = [];           // every url the code chose to cache
  const extended = [];         // every promise the code passed to e.waitUntil
  let cached = new Map();      // what caches.match will answer with

  // put() settles on a macrotask, not inline: a real Cache write is asynchronous work
  // that outlives the response, and an inline stub would let a fire-and-forget write
  // "finish" before the harness could model the worker being terminated.
  const cacheObj = {
    put: (req, res) => new Promise(resolve => setImmediate(() => {
      stored.push(String(req.url || req));
      resolve();
    })),
  };
  const sandbox = {
    self: {
      addEventListener: (name, fn) => { listeners[name] = fn; },
      skipWaiting: () => {},
      clients: { matchAll: async () => [], claim: async () => {} },
    },
    caches: {
      open: async () => cacheObj,
      keys: async () => [],
      delete: async () => true,
      match: async (req) => cached.get(String(req.url || req)),
    },
    clients: { claim: async () => {} },
    location: { origin: ORIGIN },
    URL,
    Request: function (input, init) {
      const url = typeof input === 'string' ? input : input.url;
      return { url, method: (init && init.method) || (input && input.method) || 'GET' };
    },
    fetch: null,               // set per case
    console,
  };
  sandbox.self.location = sandbox.location;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SW, 'utf8'), sandbox, { filename: 'sw.js' });

  const out = [];
  for (const c of cases) {
    stored.length = 0;
    extended.length = 0;
    cached = new Map(c.cached || []);
    sandbox.fetch = async () => response(c.status);

    let responded = null;
    const event = {
      request: { url: c.url, method: c.method || 'GET' },
      respondWith: (p) => { responded = p; },
      waitUntil: (p) => { extended.push(p); },
    };
    listeners.fetch(event);
    out.push({ name: c.name, responded: responded !== null, promise: responded });
  }
  return { out, stored, extended, cacheObj };
}

(async () => {
  const results = [];
  const cases = [
    { name: 'poster_404', url: `${ORIGIN}/data/posters/missing.jpg`, status: 404 },
    { name: 'poster_500', url: `${ORIGIN}/data/posters/broken.jpg`, status: 500 },
    { name: 'poster_200', url: `${ORIGIN}/data/posters/good.jpg`, status: 200 },
    { name: 'page_500', url: `${ORIGIN}/index.html`, status: 500 },
    { name: 'page_200', url: `${ORIGIN}/index.html`, status: 200 },
    { name: 'data_404', url: `${ORIGIN}/data/areas.json`, status: 404 },
    { name: 'data_200', url: `${ORIGIN}/data/areas.json`, status: 200 },
    { name: 'cross_origin', url: 'https://example.test/x.js', status: 200 },
    { name: 'not_get', url: `${ORIGIN}/index.html`, status: 200, method: 'POST' },
  ];

  for (const c of cases) {
    const { out, stored, extended } = run([c]);
    const r = out[0];
    if (r.promise) { try { await r.promise; } catch (e) { /* the caller still sees it */ } }
    // The worker-termination model: once the response has settled, the browser keeps
    // the worker alive only for promises passed to e.waitUntil. Whatever `stored`
    // holds after these settle is what a real worker is guaranteed to have written;
    // a put() the code fired and forgot is still pending here and is counted lost.
    await Promise.allSettled(extended);
    results.push({ name: c.name, intercepted: r.responded, stored: stored.slice() });
  }
  process.stdout.write(JSON.stringify(results));
})();
