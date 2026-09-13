// Drives index.html's screeningHash(), screeningUrl(), parseSheetHash() and
// screeningTarget() against fixed inputs. Driven by tests/test_screening_link.py; prints
// one JSON line.
//
// The block is sliced verbatim out of index.html between its marker comments, the way
// nextMatch and the area routing are, together with nextMatch itself (screeningTarget
// falls back to it) and the Helsinki date helpers, so the real code runs.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

function slice(start, end, name) {
  const a = HTML.indexOf(start);
  const b = HTML.indexOf(end);
  if (a === -1 || b === -1 || b < a) {
    console.error(name + ' markers not found in index.html');
    process.exit(2);
  }
  return HTML.slice(a, b);
}
const SRC = slice('  // --- screening link: pure, extracted verbatim by tests/screening_link_harness.js ---',
                  '  // --- end screening link ---', 'screening link');
for (const fn of ['screeningHash', 'screeningUrl', 'parseSheetHash', 'screeningTarget']) {
  if (!new RegExp('function ' + fn + '\\s*\\(').test(SRC)) {
    console.error('marker block does not contain ' + fn);
    process.exit(2);
  }
}
const NEXT = slice('  // --- nextMatch: pure, extracted verbatim by tests/next_match_harness.js ---',
                   '  // --- end nextMatch ---', 'nextMatch');
const HELPERS = HTML.slice(HTML.indexOf("  const FI_TZ = 'Europe/Helsinki';"),
                           HTML.indexOf('  const fiToday = () => fiDate(new Date());'));
if (!/fiDate = /.test(HELPERS)) {
  console.error('date helpers not found in index.html');
  process.exit(2);
}
const sandbox = { URL, URLSearchParams, encodeURIComponent };
vm.createContext(sandbox);
vm.runInContext(HELPERS + '\n' + NEXT + '\n' + SRC
                + '\n;globalThis.__h = screeningHash; globalThis.__u = screeningUrl;'
                + 'globalThis.__p = parseSheetHash; globalThis.__t = screeningTarget; globalThis.__d = fiDate;',
                sandbox, { filename: 'screeningLink' });
const screeningHash = sandbox.__h, screeningUrl = sandbox.__u;
const parseSheetHash = sandbox.__p, screeningTarget = sandbox.__t, fiDate = sandbox.__d;

const out = { hash: {}, url: {}, parse: {}, target: {} };

// -- building ---------------------------------------------------------------------------
out.hash.plain = screeningHash('HO00000413');
out.hash.full = screeningHash('HO00000413', '2026-09-13', '2026-09-13T15:10:00+03:00');
out.hash.odd_id = screeningHash('a&b=c #x', '', '');
out.url.full = screeningUrl('https://leffavuoro.fi/?area=old&lang=sv#m=zzz', '1004',
                            'HO00000413', '2026-09-13', '2026-09-13T15:10:00+03:00');
out.url.bare = screeningUrl('https://leffavuoro.fi/', 'city:Helsinki', '1499');
out.url.from_page = screeningUrl('https://leffavuoro.fi/kaupunki/tampere/', 'city:Tampere', '61');

// -- parsing -----------------------------------------------------------------------------
out.parse.round_trip = parseSheetHash('#' + out.hash.full);
out.parse.odd_id = parseSheetHash('#' + out.hash.odd_id);
out.parse.old_link = parseSheetHash('#m=HO00000413');
out.parse.old_link_encoded = parseSheetHash('#m=' + encodeURIComponent('Ryhmä Hau: Dinoelokuva'));
out.parse.bad_day = parseSheetHash('#m=x&d=2026-9-1&t=2026-09-13T15:10:00+03:00');
out.parse.bad_start = parseSheetHash('#m=x&d=2026-09-13&t=tonight');
out.parse.no_film = parseSheetHash('#d=2026-09-13&t=2026-09-13T15:10:00%2B03:00');
out.parse.empty_film = parseSheetHash('#m=&d=2026-09-13');
out.parse.nothing = parseSheetHash('');
out.parse.other_hash = parseSheetHash('#top');

// -- the screening the sheet opens on --------------------------------------------------
// Helsinki is UTC+3 in September. `at` is 'YYYY-MM-DDTHH:MM' Helsinki wall time.
const show = (at) => ({ start: new Date(at + ':00+03:00'), at });
const shows = ['2026-09-13T12:00', '2026-09-13T15:10', '2026-09-14T18:00', '2026-09-16T20:45'].map(show);
const now = new Date('2026-09-13T14:00:00+03:00');
const pick = (hit) => hit ? hit.at : null;
const target = (want) => pick(screeningTarget(shows, want, now, fiDate));
out.target.exact_ahead = target({ day: '2026-09-13', start: '2026-09-13T15:10:00+03:00' });
out.target.exact_other_offset = target({ day: '', start: '2026-09-13T12:10:00Z' });     // same instant, UTC
out.target.exact_gone_same_day = target({ day: '2026-09-13', start: '2026-09-13T12:00:00+03:00' });
out.target.start_unknown_day_known = target({ day: '2026-09-14', start: '2026-09-14T21:00:00+03:00' });
out.target.day_only = target({ day: '2026-09-16', start: '' });
out.target.day_past = target({ day: '2026-09-12', start: '2026-09-12T18:00:00+03:00' });
out.target.day_without_screenings = target({ day: '2026-09-15', start: '' });
out.target.nothing_named = target({ day: '', start: '' });
out.target.no_want = pick(screeningTarget(shows, null, now, fiDate));
out.target.all_gone = pick(screeningTarget(shows, { day: '2026-09-13', start: '' },
                                           new Date('2026-09-17T00:00:00+03:00'), fiDate));
out.target.empty = pick(screeningTarget([], { day: '2026-09-13', start: '' }, now, fiDate));

process.stdout.write(JSON.stringify(out) + '\n');
