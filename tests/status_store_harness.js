// Drives status/index.html's own store: the two ways the page stays current, and the
// difference between them.
//
// The block is sliced verbatim out of status/index.html between its marker comments. The
// point of this file is the loop that shipped on 2026-09-07: sw.js posts `{fresh: path}`
// after every successful revalidation, including one that changed nothing, and the page
// answered by loading again. Each load fetched 38 files, each of those produced another
// message, and the origin rate-limited. Source-text checks did not catch it, so this
// counts real requests through a stubbed `io` instead.
//
// `net` and `cache` are separate counters on purpose. The whole rule is that a message
// may move `cache` and must never move `net`.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'status', 'index.html'), 'utf8');

const START = '// --- status store: pure, extracted verbatim by tests/status_store_harness.js ---';
const END = '// --- end status store ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('status store markers not found in status/index.html');
  process.exit(2);
}
const SRC = HTML.slice(a, b);
if (!/function makeStatusStore\s*\(/.test(SRC)) {
  console.error('marker block does not contain makeStatusStore');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(SRC + '\n;globalThis.__mk = makeStatusStore;', sandbox,
                { filename: 'statusStore' });
const makeStatusStore = sandbox.__mk;

const clone = x => JSON.parse(JSON.stringify(x));
const tick = () => new Promise(r => setImmediate(r));

// The published files, as the pipeline writes them.
const PROVIDERS = { providers: [
  { id: 'finnkino', label: 'Finnkino', host: 'finnkino.fi' },
  { id: 'orion', label: 'Cinema Orion', host: 'cinemaorion.fi' },
  { id: 'kinometso', label: 'Kino Metso', host: 'kinoaurora.fi' },
] };
const AREAS = { generated: '2026-09-07T06:00:00+00:00',
                areas: [{ id: '1004', name: 'Helsinki' }, { id: '1029', name: 'Valtakunnallinen' }] };
const venues = (gen, extra) => Object.assign({
  generated: gen, oldest: gen, status: 'ok', stale: [], unverified: [], pending: [],
  venues: [{ id: 'v1', name: 'Yksi', city: 'Helsinki' }],
}, extra || {});

function world(opts) {
  const files = clone((opts && opts.files) || {
    '/data/providers.json': PROVIDERS,
    '/data/areas.json': AREAS,
    '/data/venues-orion.json': venues('2026-09-07T06:00:00+00:00'),
    '/data/venues-kinometso.json': venues('2026-09-07T06:00:00+00:00'),
  });
  const st = { net: 0, cache: 0, renders: 0, netPaths: [], timers: [], heldCache: [] };
  // `holdCache` makes every cache read a promise the scenario settles by hand, which is
  // the only way to place a load inside a read's await.
  const io = {
    net: async p => { st.net++; st.netPaths.push(p); return files[p] ? clone(files[p]) : null; },
    cache: p => {
      st.cache++;
      if(!(opts && opts.holdCache)) return Promise.resolve(files[p] ? clone(files[p]) : null);
      return new Promise(resolve => st.heldCache.push({ path: p, resolve }));
    },
    now: () => st.clock,
    // Timers run when the scenario says so, so a burst can be posted before it fires.
    defer: (fn, ms) => { st.timers.push({ fn, ms }); return st.timers.length; },
    changed: () => { st.renders++; },
  };
  st.clock = Date.parse('2026-09-07T09:00:00Z');
  st.flush = async () => {
    while (st.timers.length) {
      const t = st.timers.shift();
      await t.fn();
      await tick();
    }
  };
  // Run the deferred pass without awaiting it, so a scenario can act while it is inside
  // an await, then settle the reads it is waiting on.
  st.startTimers = () => { while (st.timers.length) st.timers.shift().fn(); };
  st.settle = async (value) => {
    const r = st.heldCache.shift();
    if (!r) throw new Error('no cache read pending');
    r.resolve(value === undefined ? (files[r.path] ? clone(files[r.path]) : null) : value);
    await tick(); await tick();
    return r.path;
  };
  return { st, files, store: makeStatusStore(io) };
}

const out = {};

async function run() {

  // -- the first load reads every file over the network ---------------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    out.first_load = { net: w.st.net, renders: w.st.renders, cache: w.st.cache,
                       paths: w.st.netPaths.slice(),
                       providers: w.store.state().providers.length,
                       metaKeys: Object.keys(w.store.state().meta).sort() };
  }

  // -- the defect: messages after a load must add no network requests --------------------
  // sw.js posts one per revalidated file whether or not the bytes changed. Five of those
  // took the count from 38 to 228 before the fix.
  {
    const w = world();
    await w.store.load({ force: true });
    const afterLoad = w.st.net;
    for (const p of ['/data/venues-orion.json', '/data/venues-kinometso.json',
                     '/data/areas.json', '/data/providers.json',
                     '/data/venues-orion.json']) w.store.fresh(p);
    await w.st.flush();
    out.unchanged_messages = { netAfterLoad: afterLoad, netAfterMessages: w.st.net,
                               added: w.st.net - afterLoad, cacheReads: w.st.cache,
                               renders: w.st.renders };
  }

  // -- a burst folds into one pass rather than one per message ---------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    for (let i = 0; i < 20; i++) w.store.fresh('/data/venues-orion.json');
    out.burst = { timersScheduled: w.st.timers.length };
    await w.st.flush();
    out.burst.netAfter = w.st.net;
    out.burst.rendersTotal = w.st.renders;
  }

  // -- changed bytes in the cache update the state and redraw ----------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    const before = w.store.state().meta.orion.oldest;
    const rendersBefore = w.st.renders;
    w.files['/data/venues-orion.json'] = venues('2026-09-07T08:30:00+00:00');
    w.store.fresh('/data/venues-orion.json');
    await w.st.flush();
    out.changed_message = { before, after: w.store.state().meta.orion.oldest,
                            rendersAdded: w.st.renders - rendersBefore,
                            netAdded: w.st.netPaths.filter(p => p.includes('orion')).length };
  }

  // -- an unchanged re-read redraws nothing ----------------------------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    const rendersBefore = w.st.renders;
    w.store.fresh('/data/venues-orion.json');
    await w.st.flush();
    out.unchanged_no_redraw = { rendersAdded: w.st.renders - rendersBefore };
  }

  // -- a message for a file that is not in the cache changes nothing -----------------------
  {
    const w = world();
    await w.store.load({ force: true });
    const rendersBefore = w.st.renders, netBefore = w.st.net;
    delete w.files['/data/venues-orion.json'];
    w.store.fresh('/data/venues-orion.json');
    await w.st.flush();
    out.cache_miss = { rendersAdded: w.st.renders - rendersBefore,
                       netAdded: w.st.net - netBefore,
                       orionStillHeld: !!w.store.state().meta.orion };
  }

  // -- a resumed tab is throttled, and a later deliberate retry still works -----------------
  {
    const w = world();
    await w.store.load({ force: true });
    const afterFirst = w.st.net;
    const second = await w.store.load();                 // straight away: refused
    const afterSecond = w.st.net;
    w.st.clock += 61000;                                  // a minute later: allowed
    const third = await w.store.load();
    out.resume_throttle = { afterFirst, afterSecond, secondRan: second, thirdRan: third,
                            afterThird: w.st.net };
  }

  // -- a forced load is never throttled -------------------------------------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    const afterFirst = w.st.net;
    const ran = await w.store.load({ force: true });
    out.force_bypasses_throttle = { ran, netGrew: w.st.net > afterFirst };
  }

  // -- an out-of-order answer does not overwrite a newer load ----------------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    w.st.clock += 61000;
    const slow = w.store.load();      // starts
    w.st.clock += 61000;
    const fast = w.store.load({ force: true });
    const [a1, b1] = await Promise.all([slow, fast]);
    out.stale_load_dropped = { slowWrote: a1, fastWrote: b1 };
  }

  // -- providers.json failing leaves the rows that already loaded alone -------------------------
  {
    const w = world();
    await w.store.load({ force: true });
    const held = Object.keys(w.store.state().meta).length;
    delete w.files['/data/providers.json'];
    w.st.clock += 61000;
    await w.store.load({ force: true });
    out.provider_list_failed = { heldBefore: held,
                                 providersAfter: w.store.state().providers.length,
                                 checkedAtMoved: !!w.store.state().checkedAt };
  }

  // -- the reported defect: a cache read that started before a newer load must not win ----
  // 10:00 held, a pass begins its read, a load completes with 11:00, then the read answers
  // with the 10:00 bytes it captured. Writing those back regresses the page.
  {
    const w = world({ holdCache: true });
    await w.store.load({ force: true });
    const before = w.store.state().meta.orion.oldest;
    w.store.fresh('/data/venues-orion.json');
    w.st.startTimers();
    await tick();
    const pending = w.st.heldCache.length;
    // A newer load lands while the read is in flight.
    w.files['/data/venues-orion.json'] = venues('2026-09-07T11:00:00+00:00');
    w.st.clock += 61000;
    await w.store.load({ force: true });
    const afterLoad = w.store.state().meta.orion.oldest;
    // The read now answers with what it captured before the load.
    await w.st.settle(venues('2026-09-07T10:00:00+00:00'));
    out.stale_cache_read = { before, pendingReads: pending, afterLoad,
                             afterStaleRead: w.store.state().meta.orion.oldest };
  }

  // -- a refresh still applies when no load intervened -------------------------------------
  {
    const w = world({ holdCache: true });
    await w.store.load({ force: true });
    w.store.fresh('/data/venues-orion.json');
    w.st.startTimers();
    await tick();
    await w.st.settle(venues('2026-09-07T11:00:00+00:00'));
    out.fresh_applies_without_a_load = { after: w.store.state().meta.orion.oldest,
                                         renders: w.st.renders };
  }

  // -- passes do not overlap: a burst during a running pass is drained after it -------------
  {
    const w = world({ holdCache: true });
    await w.store.load({ force: true });
    w.store.fresh('/data/venues-orion.json');
    w.st.startTimers();
    await tick();
    // A second burst arrives while the first pass sits in its await.
    w.store.fresh('/data/venues-kinometso.json');
    const timersWhileRunning = w.st.timers.length;
    const readsWhileRunning = w.st.heldCache.length;
    await w.st.settle(venues('2026-09-07T11:00:00+00:00'));       // first pass read
    const secondPassStarted = w.st.heldCache.length;
    await w.st.settle(venues('2026-09-07T11:30:00+00:00'));       // drained follow-up
    out.no_overlapping_passes = {
      timersWhileRunning, readsWhileRunning, secondPassStarted,
      orion: w.store.state().meta.orion.oldest,
      kinometso: w.store.state().meta.kinometso.oldest,
      net: w.st.net,
    };
  }

  // -- a message arriving during an abandoned pass is not lost -----------------------------
  // The pass is overtaken by a load and drops its batch. Anything queued after that batch
  // was taken has not been looked at by anyone and still needs a pass.
  {
    const w = world({ holdCache: true });
    await w.store.load({ force: true });
    w.store.fresh('/data/venues-orion.json');
    w.st.startTimers();
    await tick();
    // Overtake the pass.
    w.files['/data/venues-orion.json'] = venues('2026-09-07T11:00:00+00:00');
    w.files['/data/venues-kinometso.json'] = venues('2026-09-07T11:00:00+00:00');
    w.st.clock += 61000;
    await w.store.load({ force: true });
    // A message lands while the pass is still inside its await.
    w.store.fresh('/data/venues-kinometso.json');
    await w.st.settle(venues('2026-09-07T10:00:00+00:00'));   // the abandoned read
    const timersAfterAbandon = w.st.timers.length;
    w.st.startTimers();
    await tick();
    w.files['/data/venues-kinometso.json'] = venues('2026-09-07T12:00:00+00:00');
    await w.st.settle(venues('2026-09-07T12:00:00+00:00'));
    out.abandoned_pass_requeues = {
      timersAfterAbandon,
      orion: w.store.state().meta.orion.oldest,
      kinometso: w.store.state().meta.kinometso.oldest,
      net: w.st.net,
    };
  }

}

// A scenario that throws, or one whose await never settles, used to print nothing, and a
// mutation run scores an empty stdout as "nothing went red" rather than as the breakage it
// is. That happened here: removing the requeue made `settle` throw with no pending read,
// and the mutation came back VOID. Whatever `out` holds is printed either way now, and the
// failure goes into `__error` for one test to fail on.
const WATCHDOG_MS = 10000;
let watchdog;
Promise.race([
  run(),
  new Promise((_, reject) => {
    watchdog = setTimeout(
      () => reject(new Error(`a scenario did not settle within ${WATCHDOG_MS} ms`)), WATCHDOG_MS);
  }),
]).catch(e => { out.__error = String((e && e.stack) || e); })
  .then(() => { clearTimeout(watchdog); process.stdout.write(JSON.stringify(out)); });
