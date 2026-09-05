// Drives index.html's own background-refresh handler -- what a `{fresh: path}` message
// from the service worker does to the page's payload cache -- against scenarios where the
// reader changes cinema, or the cache is emptied, while a read is in flight. Run by
// tests/test_swr_refresh.py; prints one JSON line.
//
// The handler is sliced verbatim out of index.html between its marker comments and
// evaluated on its own, the way healthState, venueRows and the area routing are. It is a
// function of the `io` object it is built with -- the current selection, the payload
// cache, the city groups, the readers and the clock -- so every one of those is a stub
// here and the shipped decision runs against them. The reads are promises the scenario
// resolves by hand, which is the only way to put "the reader switched cinema during the
// await" under test at all.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const START = '// --- background refresh: pure, extracted verbatim by tests/swr_refresh_harness.js ---';
const END = '// --- end background refresh ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('background refresh markers not found in index.html');
  process.exit(2);
}
const source = HTML.slice(a, b);
if (!/function makeFreshHandler\s*\(/.test(source)) {
  console.error('marker block does not contain makeFreshHandler');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source + '\n;globalThis.__mk = makeFreshHandler;', sandbox, { filename: 'backgroundRefresh' });
const makeFreshHandler = sandbox.__mk;

// A payload the way an area file arrives: `generated` and the shows. The show list is
// what proves which cinema's programme ended up in a slot.
const payload = (venue, generated) => ({
  generated,
  dates: ['2026-09-05'],
  shows: [{ title: `Film at ${venue}`, start: '2026-09-05T18:00:00+03:00', theatre: venue }],
});
const clone = x => JSON.parse(JSON.stringify(x));

// A read the scenario settles by hand. `pending` holds the resolvers by path.
function makeReads() {
  const pending = new Map();
  const calls = [];
  const read = p => {
    calls.push(p);
    return new Promise((resolve, reject) => pending.set(p, { resolve, reject }));
  };
  return { read, calls, pending };
}

// Every scenario builds a handler over the same shape of `io` and returns what the
// cache and the render hook look like afterwards. `now` advances by hand so the
// handler's own timing rules are exercised, not the wall clock.
function setup(opts) {
  const reads = makeReads();
  const st = { area: opts.area, applied: 0, now: 1000000 };
  const cache = clone(opts.cache);
  const io = {
    area: () => st.area,
    cache,
    groups: () => opts.groups || {},
    now: () => st.now,
    fetchJSON: reads.read,
    // loadCity here is the thin thing it is in the app -- read every member, fold. The
    // fold itself is not under test in this file; the slot the result lands in is.
    loadCity: async city => {
      const ids = (opts.groups || {})[city] || [];
      const parts = await Promise.all(ids.map(id => reads.read(`data/area-${id}.json`).catch(() => null)));
      const gen = parts.filter(Boolean).map(p => p.generated).sort()[0] || '';
      return { generated: gen, shows: parts.filter(Boolean).flatMap(p => p.shows), dates: [], missing: [] };
    },
    applied: () => { st.applied++; },
  };
  return { io, st, cache, reads, handler: makeFreshHandler(io) };
}

const tick = () => new Promise(r => setImmediate(r));

const A1 = payload('A', '2026-09-05T06:00:00+00:00');
const A2 = payload('A', '2026-09-05T09:00:00+00:00');
const B1 = payload('B', '2026-09-05T07:00:00+00:00');

async function run() {
  const out = {};

  // -- the reported defect: a late answer for A after the reader moved to B -------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.st.area = 'B';                                   // the reader switches during the read
    s.reads.pending.get('data/area-A.json').resolve(clone(A2));
    await done;
    out.late_answer_after_switch = {
      reads: s.reads.calls, applied: s.st.applied,
      B: s.cache.B, A: s.cache.A,
    };
  }

  // -- the same read with the reader still on A -----------------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.reads.pending.get('data/area-A.json').resolve(clone(A2));
    await done;
    out.answer_still_selected = { reads: s.reads.calls, applied: s.st.applied, A: s.cache.A, B: s.cache.B };
  }

  // -- the cache emptied during the read (refreshAll on resume does exactly this) -------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    for (const k of Object.keys(s.cache)) delete s.cache[k];
    s.reads.pending.get('data/area-A.json').resolve(clone(A2));
    await done;
    out.invalidated_during_read = { applied: s.st.applied, keys: Object.keys(s.cache) };
  }

  // -- nothing changed: the same generated comes back --------------------------------------
  {
    const s = setup({ area: 'A', cache: { A: A1, B: B1 } });
    const done = s.handler('/data/area-A.json');
    await tick();
    s.reads.pending.get('data/area-A.json').resolve(clone(A1));
    await done;
    out.unchanged = { applied: s.st.applied, A: s.cache.A };
  }

  // -- a member of the selected city -----------------------------------------------------
  {
    const groups = { X: ['a', 'b'] };
    const cityA = payload('a', '2026-09-05T06:00:00+00:00');
    const cityB = payload('b', '2026-09-05T07:00:00+00:00');
    const held = { generated: cityA.generated, shows: [...cityA.shows, ...cityB.shows], dates: [], missing: [] };
    const s = setup({ area: 'city:X', groups, cache: { 'city:X': held, A: A1 } });
    const done = s.handler('/data/area-b.json');
    await tick();
    s.reads.pending.get('data/area-a.json').resolve(payload('a', '2026-09-05T10:00:00+00:00'));
    s.reads.pending.get('data/area-b.json').resolve(clone(cityB));
    await done;
    out.city_member = { reads: s.reads.calls.slice().sort(), applied: s.st.applied, A: s.cache.A,
                        generated: s.cache['city:X'].generated };
  }

  // -- a file the selection does not include ---------------------------------------------
  {
    const s = setup({ area: 'A', groups: { X: ['a', 'b'] }, cache: { A: A1, 'city:X': { generated: 'x', shows: [] } } });
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

  process.stdout.write(JSON.stringify(out));
}

run().catch(e => { console.error(e && e.stack || e); process.exit(1); });
