// Runs index.html's own staleNotice() against a table of (sources, now) cases.
// Driven by tests/test_stale_notice.py; prints one JSON line.
//
// Sliced verbatim out of index.html between its marker comments and evaluated on its
// own: it is a pure function of a source list, a clock and a threshold, so it needs no
// DOM. The clock is passed in, so nothing here depends on when the test runs.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const START = '// --- staleNotice: pure, extracted verbatim by tests/stale_notice_harness.js ---';
const END = '// --- end staleNotice ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('staleNotice markers not found in index.html');
  process.exit(2);
}
const source = HTML.slice(a, b);
if (!/const staleNotice\s*=/.test(source)) {
  console.error('marker block does not contain staleNotice');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source + '\nthis.staleNotice = staleNotice;', sandbox);
const staleNotice = sandbox.staleNotice;

const NOW = Date.parse('2026-09-20T12:00:00Z');
const H = 8;
const at = hoursAgo => new Date(NOW - hoursAgo * 36e5).toISOString();

const fresh = p => ({ provider: p, generated: at(2) });
const late9 = p => ({ provider: p, generated: at(9) });
const late12 = p => ({ provider: p, generated: at(12) });

const cases = {
  // Nothing to say.
  none_late:            [fresh('finnkino'), fresh('biorex')],
  empty_list:           [],
  null_list:            null,
  undefined_list:       undefined,
  // One cinema: its own site can be offered.
  one_source_late:      [late9('finnkino')],
  one_late_of_three:    [fresh('biorex'), late9('finnkino'), fresh('kinola')],
  // Two late in a combined city: both named, and neither is "the" affected cinema, so
  // `only` is empty and the caller falls back to the status page.
  two_late:             [late9('finnkino'), late12('biorex')],
  two_late_order:       [late9('finnkino'), late12('biorex'), fresh('kinola')],
  // Unknown stays unknown: a part that published no timestamp is not called late.
  missing_generated:    [{ provider: 'finnkino', generated: '' }, late9('biorex')],
  absent_generated:     [{ provider: 'finnkino' }, late9('biorex')],
  unparseable_date:     [{ provider: 'finnkino', generated: 'not-a-date' }, late9('biorex')],
  all_unknown:          [{ provider: 'finnkino', generated: '' }, { provider: 'biorex' }],
  null_member:          [null, late9('biorex')],
  // Strictly greater: exactly at the threshold is not late.
  exactly_at_threshold: [{ provider: 'finnkino', generated: at(8) }],
  just_over_threshold:  [{ provider: 'finnkino', generated: at(8.5) }],
  // A provider with no id still reports; the caller maps an unknown id to a label.
  blank_provider:       [{ provider: '', generated: at(9) }],
};

const out = {};
for (const [k, list] of Object.entries(cases)) {
  try {
    out[k] = staleNotice(list, NOW, H);
  } catch (e) {
    out[k] = { threw: String((e && e.message) || e) };
  }
}
process.stdout.write(JSON.stringify(out) + '\n');
