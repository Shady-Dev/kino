// Runs index.html's sharedTags() and ownTags(), with stubTags and GLYPH, for tests/test_ticket_tags.py.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

function block(name) {
  const start = `// --- ${name}: pure, extracted verbatim by tests/`;
  const end = `// --- end ${name} ---`;
  const a = HTML.indexOf(start);
  const b = HTML.indexOf(end);
  if (a === -1 || b === -1 || b < a) {
    console.error(`${name} markers not found in index.html`);
    process.exit(2);
  }
  return HTML.slice(a, b);
}

const glyph = HTML.match(/const GLYPH = \{[^\n]*\};/);
if (!glyph) {
  console.error('GLYPH table not found in index.html');
  process.exit(2);
}
const source = [glyph[0], block('stubTags'), block('ticketTags')].join('\n');
if (!/const sharedTags\s*=/.test(source) || !/const ownTags\s*=/.test(source)) {
  console.error('marker block does not contain sharedTags and ownTags');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source + '\nthis.sharedTags = sharedTags; this.ownTags = ownTags;'
                + '\nthis.isGlyph = f => !!GLYPH[(f || "").toLowerCase()];', sandbox);
const { sharedTags, ownTags, isGlyph } = sandbox;

const s = (method, aud) => ({ method, aud });
// The first three are the live cases of 2026-11-02 (Riviera, The Odyssey, BioRex Tripla).
const groups = {
  afternoon_tea: [s('', 'Sali 1'), s('Afternoon Tea', 'Sali 2'), s('', 'Sali 1')],
  imax_and_luxe: [s('2D · Anniskelu · IMAX', 'IMAX'), s('2D · Anniskelu · LUXE', 'LUXE 8'),
                  s('2D · Anniskelu', 'Sali 10'), s('', 'Sali 2')],
  described:     [s('Senioribio · Kuvaileva tekstitys · Anniskelu · Plus', '2 Plus'),
                  s('', 'Sali 1')],
  imax_in_sali:  [s('2D · IMAX', 'Sali 2'), s('2D', 'Sali 3')],
  shared_35mm:   [s('35 mm · Senioribio', 'Sali 1'), s('35 mm', 'Sali 2')],
  all_anniskelu: [s('Anniskelu', 'Sali 1'), s('Anniskelu', 'Sali 2')],
  one_screening: [s('Seniorikino', 'Gilda 2')],
  order_kept:    [s('Atmos · Event cinema', 'Sali 1'), s('Event cinema · Atmos', 'Sali 2')],
  no_method:     [{ aud: 'Sali 1' }, s(null, 'Sali 2')],
  empty:         [],
};
const out = {};
for (const [k, shows] of Object.entries(groups)) {
  const shared = sharedTags(shows, isGlyph);
  out[k] = { shared, own: shows.map(x => ownTags(x, shared)) };
}
process.stdout.write(JSON.stringify(out) + '\n');
