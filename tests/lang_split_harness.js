// Runs index.html's own langSplit() against a table of screening lists.
// Driven by tests/test_lang_split.py; prints one JSON line.
//
// Sliced verbatim out of index.html between its marker comments and evaluated on its
// own: it is a pure function of a list of shows, so it needs no DOM.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const START = '// --- langSplit: pure, extracted verbatim by tests/lang_split_harness.js ---';
const END = '// --- end langSplit ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('langSplit markers not found in index.html');
  process.exit(2);
}
const source = HTML.slice(a, b);
if (!/const langSplit\s*=/.test(source)) {
  console.error('marker block does not contain langSplit');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source + '\nthis.langSplit = langSplit;', sandbox);
const langSplit = sandbox.langSplit;

// The four classes the committed data holds, plus the shapes that must not throw.
// Two entries minimum wherever agreement is the thing under test: a one-item list
// agrees with itself and would pass a broken comparison.
const cases = {
  // 73.3% of (area, film) pairs on 2026-09-20: one value above the schedule.
  all_same:            [{ lang: 'FI-A' }, { lang: 'FI-A' }],
  all_same_three:      [{ lang: 'EN-A, FI-S, SV-S' }, { lang: 'EN-A, FI-S, SV-S' },
                        { lang: 'EN-A, FI-S, SV-S' }],
  // 24.7%: nothing published anywhere, so nothing is drawn.
  all_missing:         [{ lang: '' }, { lang: '' }],
  all_absent_key:      [{}, {}],
  // 1.9%: Kojootti vs. ACME, dubbed beside subtitled.
  mixed_values:        [{ lang: 'FI-A' }, { lang: 'EN-A, FI-S, SV-S' }],
  // 0.1% here and 4 of 422 combined-city pairs: one screening said nothing. It must not
  // inherit the other's value, in either order.
  known_then_missing:  [{ lang: 'FI-A' }, { lang: '' }],
  missing_then_known:  [{ lang: '' }, { lang: 'FI-A' }],
  absent_key_then_known: [{}, { lang: 'FI-A' }],
  // Shapes the render path can hand it.
  single_known:        [{ lang: 'ES-A, FI-S, SV-S' }],
  single_missing:      [{ lang: '' }],
  empty_list:          [],
  null_list:           null,
  undefined_list:      undefined,
  null_member:         [null, { lang: 'FI-A' }],
  // Case and spacing are the adapter's to normalise, not this function's: two spellings
  // are two values, which keeps the per-screening line rather than picking one.
  spacing_differs:     [{ lang: 'FI-A, SV-S' }, { lang: 'FI-A,SV-S' }],
};

const out = {};
for (const [k, list] of Object.entries(cases)) {
  try {
    out[k] = langSplit(list);
  } catch (e) {
    out[k] = { threw: String(e && e.message || e) };
  }
}
process.stdout.write(JSON.stringify(out) + '\n');
