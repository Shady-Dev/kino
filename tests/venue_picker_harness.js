// Runs the real venue-picker model out of index.html and prints one JSON line of
// results per scenario. Driven by tests/test_venue_picker.py.
//
// The model (vfold / vhl / venueRows) is pure by construction -- it renders no DOM and
// reads no globals -- so it is extracted verbatim between its markers and executed in a
// bare vm context, the same technique tests/health_state_harness.js uses. What cannot
// be tested this way stays verified live: focus, inert, Escape handling and the
// on-screen-keyboard behavior are DOM and event plumbing, not decisions of this model.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const START = '// --- venue picker model: pure, extracted verbatim by tests/venue_picker_harness.js ---';
const END = '// --- end venue picker model ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('venue picker model markers not found in index.html');
  process.exit(2);
}
const source = HTML.slice(a, b);
if (!/function venueRows\s*\(/.test(source)) {
  console.error('marker block does not contain venueRows');
  process.exit(2);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source + '\n;globalThis.__rows = venueRows; globalThis.__hl = vhl;',
                sandbox, { filename: 'venueRows' });
const venueRows = sandbox.__rows;
const vhl = sandbox.__hl;

// A small fixture in the shape fillAreaSelect builds: labels are chain-prefixed and
// carry no city; the city lives on the group. Turku is here for the Swedish alias.
const VENUES = {
  itis:   { id: 'itis',   provider: 'finnkino', label: 'Finnkino Itis',   city: 'Helsinki' },
  tripla: { id: 'tripla', provider: 'biorex',   label: 'BioRex Tripla',   city: 'Helsinki' },
  ja:     { id: 'ja',     provider: 'jarvelankino', label: 'Järvelän Kino', city: 'Järvelä' },
  tku:    { id: 'tku',    provider: 'x',        label: 'Kinopalatsi',     city: 'Turku' },
};
const cityOrder = ['Helsinki', 'Järvelä', 'Turku'];
const cityVenues = {
  Helsinki: [VENUES.itis, VENUES.tripla],
  'Järvelä': [VENUES.ja],
  Turku: [VENUES.tku],
};
const SV_CITY = { Helsinki: 'Helsingfors', Turku: 'Åbo' };

function ctx(overrides) {
  const lang = (overrides && overrides.lang) || 'fi';
  return Object.assign({
    T: { allIn: lang === 'sv' ? 'Alla i' : 'Kaikki', vOwn: 'Oma teatteri' },
    fav: null,
    area: 'itis',
    cityOrder,
    cityVenues,
    venueIndex: VENUES,
    labelOf: v => v.label,
    cityOf: v => v.city,
    cityLabel: c => (lang === 'sv' && SV_CITY[c]) || c,
  }, overrides || {});
}

const rowsOf = (q, o) => venueRows(q, ctx(o))
  .map(r => (r.kind === 'head' ? `#${r.text}` : `${r.kind}:${r.id}`));

const out = {
  no_query: rowsOf(''),
  diacritics: rowsOf('jarvela'),
  venue_query_first_row: rowsOf('itis'),
  city_query: rowsOf('helsinki'),
  kaikki_query: rowsOf('kaikki'),
  sv_alias_fi_name: rowsOf('turku', { lang: 'sv' }),
  sv_alias_sv_name: rowsOf('abo', { lang: 'sv' }),
  fav_venue: rowsOf('', { fav: 'ja' }),
  fav_city: rowsOf('', { fav: 'city:Helsinki' }),
  fav_city_filtered_out: rowsOf('turku', { fav: 'city:Helsinki' }),
  none: rowsOf('zzzz'),
  hl: vhl('Järvelän Kino', 'jarvela', s => s),
};
process.stdout.write(JSON.stringify(out));
