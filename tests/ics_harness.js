// Drives index.html's icsFor() against fixed screenings. Driven by tests/test_ics.py;
// prints one JSON line of file texts.
//
// The block is sliced verbatim out of index.html between its marker comments, with the
// Helsinki date helpers and safeUrl it calls, so the real code runs.
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
const SRC = slice('  // --- ics: pure, extracted verbatim by tests/ics_harness.js ---',
                  '  // --- end ics ---', 'ics');
if (!/function icsFor\s*\(/.test(SRC)) {
  console.error('marker block does not contain icsFor');
  process.exit(2);
}
const HELPERS = HTML.slice(HTML.indexOf("  const FI_TZ = 'Europe/Helsinki';"),
                           HTML.indexOf('  const fiToday = () => fiDate(new Date());'));
const SAFE = HTML.slice(HTML.indexOf('  const CTRL = /'), HTML.indexOf('  const safeAssetUrl'));
if (!/fiDate = /.test(HELPERS) || !/safeUrl/.test(SAFE)) {
  console.error('helpers not found in index.html');
  process.exit(2);
}
const sandbox = { URL };
vm.createContext(sandbox);
vm.runInContext(HELPERS + '\n' + SAFE + '\n' + SRC + '\n;globalThis.__i = icsFor;',
                sandbox, { filename: 'ics' });
const icsFor = sandbox.__i;

const NOW = new Date('2026-09-13T12:00:00Z');
const base = {
  title: 'Ryhmä Hau: Dinoelokuva', len: '88', aud: 'Sali 3', method: '2D',
  start: new Date('2026-09-15T16:30:00+03:00'),
  url: 'https://www.finnkino.fi/liput/valitse-paikat/?showtimeId=1004-5281',
};
const finnkino = { id: '1004', label: 'Finnkino Promenadi', city: 'Pori' };
const out = {};
out.plain = icsFor(base, finnkino, 'fi', NOW);
out.no_hall = icsFor({ ...base, aud: '' }, { id: 'kr-regina', label: 'Kino Regina', city: 'Helsinki' }, 'fi', NOW);
out.no_len_fi = icsFor({ ...base, len: '' }, finnkino, 'fi', NOW);
out.no_len_sv = icsFor({ ...base, len: undefined }, finnkino, 'sv', NOW);
out.no_len_en = icsFor({ ...base, len: '0' }, finnkino, 'en', NOW);
out.punctuation = icsFor({ ...base, title: 'Mission: Impossible, Part; Two\\Three', method: 'IMAX · dubattu' },
                         { id: 'br-tripla', label: 'BioRex Tripla', city: 'Helsinki' }, 'fi', NOW);
out.long_title = icsFor({ ...base, title: 'Ääkkösiä '.repeat(12).trim() }, finnkino, 'fi', NOW);
out.bad_url = icsFor({ ...base, url: 'javascript:alert(1)' }, finnkino, 'fi', NOW);
out.iso_start = icsFor({ ...base, start: '2026-11-01T18:00:00+02:00' }, finnkino, 'fi', NOW);   // winter time
out.same_again = icsFor(base, finnkino, 'fi', new Date('2027-01-01T00:00:00Z'));

process.stdout.write(JSON.stringify(out) + '\n');
