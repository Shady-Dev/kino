// Drives index.html's own background-refresh handler -- what a `{fresh: path}` message
// from the service worker does to the page's payload cache -- and the city fold it
// compares with. Run by tests/test_swr_refresh.py; prints one JSON line.
//
// Two blocks are sliced verbatim out of index.html between their marker comments and
// evaluated together, the way healthState, venueRows and the area routing are: the city
// fold (`cityPayload`, `mergeIds`) and the refresh handler (`refreshKey`, `readCached`,
// `makeFreshHandler`). The handler is a function of the `io` object it is built with --
// the current selection, the payload cache, the city groups and the readers -- so every
// one of those is a stub here and the shipped decision runs against them. Where a
// scenario needs "the reader switched cinema during the await", the read is a promise the
// scenario settles by hand; where it needs the copy the worker just cached, `caches` is a
// stub store and the real readCached() reads it. The sandbox has no fetch on purpose: a
// re-read that reached for the network would be the message loop coming back.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

function slice(start, end, mustHave) {
  const a = HTML.indexOf(start);
  const b = HTML.indexOf(end);
  if (a === -1 || b === -1 || b < a) {
    console.error(`markers not found in index.html: ${start}`);
    process.exit(2);
  }
  const src = HTML.slice(a, b);
  for (const fn of mustHave) {
    if (!new RegExp('function ' + fn + '\\s*\\(').test(src)) {
      console.error('marker block does not contain ' + fn);
      process.exit(2);
    }
  }
  return src;
}

const FOLD = slice('// --- city fold: pure, extracted verbatim by tests/swr_refresh_harness.js ---',
                   '// --- end city fold ---', ['cityPayload', 'mergeIds']);
const HANDLER = slice('// --- background refresh: pure, extracted verbatim by tests/swr_refresh_harness.js ---',
                      '// --- end background refresh ---', ['refreshKey', 'readCached', 'makeFreshHandler']);

// What `caches.match` answers with, by relative path -- the copy the worker put there.
const store = new Map();
const sandbox = {
  caches: {
    match: async p => store.has(p) ? { json: async () => clone(store.get(p)) } : undefined,
  },
};
vm.createContext(sandbox);
vm.runInContext(FOLD + '\n' + HANDLER +
                '\n;globalThis.__mk = makeFreshHandler; globalThis.__fold = cityPayload;' +
                ' globalThis.__rc = readCached; globalThis.__key = refreshKey;',
                sandbox, { filename: 'backgroundRefresh' });
const makeFreshHandler = sandbox.__mk;
const cityPayload = sandbox.__fold;
const readCached = sandbox.__rc;
const refreshKey = sandbox.__key;

function clone(x) { return JSON.parse(JSON.stringify(x)); }

// A payload the way an area file arrives: `generated` and the shows. The show list is
// what proves which cinema's programme ended up in a slot.
const payload = (venue, generated, title) => ({
  generated,
  dates: ['2026-09-05'],
  shows: [{ title: title || `Film at ${venue}`, start: '2026-09-05T18:00:00+03:00',
            theatre: venue, eventId: `${venue}-1` }],
});

// The two-member city every city scenario uses. The fold needs the venue index for the
// member names and providers, and a merge key; the identity rule is not under test here.
const GROUPS = { X: ['a', 'b'] };
const VENUES = {
  a: { id: 'a', provider: 'p1', short: 'A', label: 'Chain A' },
  b: { id: 'b', provider: 'p2', short: 'B', label: 'Chain B' },
};
const CTX = { venueIndex: VENUES, mergeKey: t => t.toLowerCase() };
const fold = parts => cityPayload(GROUPS.X, parts, CTX);

// Reads a scenario settles by hand, in arrival order per path.
function makeReads() {
  const queue = [];
  const calls = [];
  const read = p => {
    calls.push(p);
    return new Promise((resolve, reject) => queue.push({ p, resolve, reject }));
  };
  const settle = (p, value) => {
    const i = queue.findIndex(q => q.p === p);
    if (i === -1) throw new Error('no pending read for ' + p);
    const [q] = queue.splice(i, 1);
    if (value instanceof Error) q.reject(value); else q.resolve(clone(value));
  };
  return { read, calls, settle, queue };
}

// Every scenario builds a handler over the same shape of `io`. `read` is either the
// hand-settled one or the real readCached over the stub store.
function setup(opts) {
  const reads = makeReads();
  const st = { area: opts.area, applied: 0 };
  const cache = clone(opts.cache);
  const io = {
    area: () => st.area,
    cache,
    groups: () => opts.groups || GROUPS,
    read: opts.cached ? readCached : reads.read,
    // loadCity is the thin thing it is in the app -- read every member, fold with the
    // real cityPayload -- minus the prefs write.
    loadCity: async (city, read) => {
      const ids = (opts.groups || GROUPS)[city] || [];
      const parts = await Promise.all(ids.map(id => read(`data/area-${id}.json`).catch(() => null)));
      return cityPayload(ids, parts, CTX);
    },
    applied: () => { st.applied++; },
  };
  return { io, st, cache, reads, handler: makeFreshHandler(io) };
}

const tick = () => new Promise(r => setImmediate(r));
const titles = p => (p.shows || []).map(s => s.title);
const summary = p => ({ generated: p.generated, oldest: p.oldest, missing: p.missing,
                        titles: titles(p), key: refreshKey(p) });

const A1 = payload('A', '2026-09-05T06:00:00+00:00');
const A2 = payload('A', '2026-09-05T09:00:00+00:00');
const B1 = payload('B', '2026-09-05T07:00:00+00:00');
const a1 = payload('a', '2026-09-05T06:00:00+00:00');
const a2 = payload('a', '2026-09-05T09:00:00+00:00', 'Film at a, later');
const b1 = payload('b', '2026-09-05T07:00:00+00:00');
const b2 = payload('b', '2026-09-05T08:00:00+00:00', 'Film at b, later');

async function run() {
  const out = {};

  // ===== the slot a late answer lands in ================================================

  // -- a late answer for A after the reader moved to B -----------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.st.area = 'B';                                   // the reader switches during the read
    s.reads.settle('data/area-A.json', A2);
    await done;
    out.late_answer_after_switch = { reads: s.reads.calls, applied: s.st.applied, B: s.cache.B, A: s.cache.A };
  }

  // -- the same read with the reader still on A -----------------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.reads.settle('data/area-A.json', A2);
    await done;
    out.answer_still_selected = { reads: s.reads.calls, applied: s.st.applied, A: s.cache.A, B: s.cache.B };
  }

  // -- the cache emptied during the read (refreshAll on resume does exactly this) -------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    for (const k of Object.keys(s.cache)) delete s.cache[k];
    s.reads.settle('data/area-A.json', A2);
    await done;
    out.invalidated_during_read = { applied: s.st.applied, keys: Object.keys(s.cache) };
  }

  // -- nothing changed: the same generated comes back --------------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.reads.settle('data/area-A.json', A1);
    await done;
    out.unchanged = { applied: s.st.applied, A: s.cache.A };
  }

  // -- a file the selection does not include ---------------------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, 'city:X': fold([a1, b1]) } });
    await s.handler('/data/area-B.json');
    await s.handler('/data/area-b.json');
    await s.handler('/data/venues-finnkino.json');
    await s.handler('');
    out.not_a_hit = { reads: s.reads.calls, applied: s.st.applied };
  }

  // -- nothing loaded yet for the selection ----------------------------------------------
  {
    const s = setup({ area: 'A', cache: { B: B1 } });
    await s.handler('/data/area-A.json');
    out.nothing_held = { reads: s.reads.calls, applied: s.st.applied, keys: Object.keys(s.cache) };
  }

  // ===== a combined city: every member counts ============================================

  // -- the fold itself: freshness is the oldest member's ----------------------------------
  {
    out.fold = { both: summary(fold([a1, b1])), a_missing: summary(fold([null, b1])),
                 a_newer: summary(fold([a2, b1])), none: summary(fold([null, null])) };
  }

  // -- the reported defect: the newer member updates, the oldest one does not -------------
  {
    store.clear(); store.set('data/area-a.json', a1); store.set('data/area-b.json', b2);
    const s = setup({ area: 'city:X', cached: true, cache: { 'city:X': fold([a1, b1]), A: A1 } });
    await s.handler('/data/area-b.json');
    out.newer_member_updates = { applied: s.st.applied, city: summary(s.cache['city:X']), A: s.cache.A };
  }

  // -- the oldest member updates: the banner's source moves to the other one ---------------
  {
    store.clear(); store.set('data/area-a.json', a2); store.set('data/area-b.json', b1);
    const s = setup({ area: 'city:X', cached: true, cache: { 'city:X': fold([a1, b1]) } });
    await s.handler('/data/area-a.json');
    out.oldest_member_updates = { applied: s.st.applied, city: summary(s.cache['city:X']) };
  }

  // -- a member drops out of the cache, and one comes back ----------------------------------
  {
    store.clear(); store.set('data/area-a.json', a1);
    const s = setup({ area: 'city:X', cached: true, cache: { 'city:X': fold([a1, b1]) } });
    await s.handler('/data/area-a.json');
    out.member_goes_missing = { applied: s.st.applied, city: summary(s.cache['city:X']) };
  }
  {
    store.clear(); store.set('data/area-a.json', a1); store.set('data/area-b.json', b1);
    const s = setup({ area: 'city:X', cached: true, cache: { 'city:X': fold([a1, null]) } });
    await s.handler('/data/area-b.json');
    out.member_comes_back = { applied: s.st.applied, city: summary(s.cache['city:X']) };
  }

  // -- nothing moved --------------------------------------------------------------------------
  {
    store.clear(); store.set('data/area-a.json', a1); store.set('data/area-b.json', b1);
    const s = setup({ area: 'city:X', cached: true, cache: { 'city:X': fold([a1, b1]) } });
    await s.handler('/data/area-b.json');
    out.city_unchanged = { applied: s.st.applied, city: summary(s.cache['city:X']) };
  }

  // -- a burst: every member messages within the first read -----------------------------------
  {
    const s = setup({ area: 'city:X', cache: { 'city:X': fold([a1, b1]) } });
    const first = s.handler('/data/area-a.json');
    await tick();
    const afterFirst = s.reads.calls.length;
    const second = s.handler('/data/area-b.json');      // arrives while the read runs
    const third = s.handler('/data/area-a.json');
    await tick();
    const duringFirst = s.reads.calls.length;
    s.reads.settle('data/area-a.json', a2);
    s.reads.settle('data/area-b.json', b1);              // b has not landed yet
    await tick(); await tick();
    const afterSecondStarted = s.reads.calls.length;
    s.reads.settle('data/area-a.json', a2);
    s.reads.settle('data/area-b.json', b2);              // now it has
    await Promise.all([first, second, third]);
    const settled = s.reads.calls.length;
    // The drain is over; a later message starts a fresh read rather than being swallowed.
    const fourth = s.handler('/data/area-b.json');
    await tick();
    const afterFourth = s.reads.calls.length;
    s.reads.settle('data/area-a.json', a2);
    s.reads.settle('data/area-b.json', b2);
    await fourth;
    out.burst = { afterFirst, duringFirst, afterSecondStarted, settled, afterFourth,
                  applied: s.st.applied, city: summary(s.cache['city:X']),
                  pending: s.reads.queue.length };
  }

  // -- the reader the handler is built with -----------------------------------------------------
  {
    store.clear(); store.set('data/area-a.json', a1);
    const hit = await readCached('data/area-a.json');
    let miss = null;
    try { await readCached('data/area-zz.json'); } catch (e) { miss = String(e.message); }
    out.read_cached = { hit: summary(hit), miss, fetchDefined: typeof sandbox.fetch !== 'undefined' };
  }

  process.stdout.write(JSON.stringify(out));
}

run().catch(e => { console.error(e && e.stack || e); process.exit(1); });
