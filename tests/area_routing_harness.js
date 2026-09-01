// Runs index.html's own startupArea() and areaParamAfterSelect() against a table of
// deep-link, favourite and stored-area combinations. Driven by tests/test_area_routing.py;
// prints one JSON line.
//
// Sliced verbatim out of index.html between its marker comments and evaluated on its own,
// the way healthState, venueRows and priceLabel are. Both functions are pure -- the
// routing one takes the deep-link string, the prefs object and a validity predicate; the
// URL one takes a query string and an id -- so neither needs a DOM, and the real code
// runs rather than a copy of it.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const START = '// --- area routing: pure, extracted verbatim by tests/area_routing_harness.js ---';
const END = '// --- end area routing ---';

const a = HTML.indexOf(START);
const b = HTML.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('area routing markers not found in index.html');
  process.exit(2);
}
const source = HTML.slice(a, b);
for (const fn of ['startupArea', 'areaParamAfterSelect']) {
  if (!new RegExp('function ' + fn + '\\s*\\(').test(source)) {
    console.error('marker block does not contain ' + fn);
    process.exit(2);
  }
}

const sandbox = { URLSearchParams };
vm.createContext(sandbox);
vm.runInContext(source + '\n;globalThis.__s = startupArea; globalThis.__p = areaParamAfterSelect;',
                sandbox, { filename: 'areaRouting' });
const startupArea = sandbox.__s;
const areaParamAfterSelect = sandbox.__p;

// The venues this fixture knows about. `known` is the same shape the app builds: a venue
// id, or a `city:` id for a city with more than one venue.
const VENUES = ['fi-cine-atlas', 'sk-tapio', 'sk-maxim', 'br-redi'];
const MULTI_CITIES = ['Helsinki'];
const known = id => !!id && (VENUES.includes(id) ||
  (id.startsWith('city:') && MULTI_CITIES.includes(id.slice(5))));

// [name, deep, prefs]
const CASES = [
  // -- the reported defect ------------------------------------------------------------
  ['fav_only_no_deep',        '',              { fav: 'fi-cine-atlas', area: 'sk-maxim' }],
  ['fav_and_deep',            'sk-tapio',      { fav: 'fi-cine-atlas', area: 'sk-maxim' }],
  // the second load of the same tab: the param is still there, so it decides again
  ['reload_with_deep',        'sk-tapio',      { fav: 'fi-cine-atlas', area: 'sk-tapio' }],
  // -- the ordinary restore -------------------------------------------------------------
  ['stored_only',             '',              { fav: '', area: 'sk-maxim' }],
  ['nothing_at_all',          '',              { fav: '', area: '' }],
  ['fav_beats_stored',        '',              { fav: 'br-redi', area: 'sk-maxim' }],
  // -- cities ----------------------------------------------------------------------------
  ['city_deep',               'city:Helsinki', { fav: 'fi-cine-atlas', area: '' }],
  ['city_fav_no_deep',        '',              { fav: 'city:Helsinki', area: 'sk-maxim' }],
  ['city_deep_single_venue',  'city:Tapiola',  { fav: 'fi-cine-atlas', area: '' }],
  // -- links that name nothing -----------------------------------------------------------
  ['unknown_deep',            'sk-gone',       { fav: 'fi-cine-atlas', area: 'sk-maxim' }],
  ['unknown_deep_no_fav',     'sk-gone',       { fav: '', area: 'sk-maxim' }],
  ['unknown_deep_nothing',    'sk-gone',       { fav: '', area: '' }],
  ['empty_deep',              '',              { fav: 'fi-cine-atlas', area: '' }],
  ['stale_stored',            '',              { fav: '', area: 'sk-gone' }],
];

const routing = {};
for (const [name, deep, pr] of CASES) routing[name] = startupArea(deep, pr, known);

// [name, search, id]
const URL_CASES = [
  ['deep_then_pick',        '?area=sk-tapio',           'sk-maxim'],
  ['deep_then_pick_city',   '?area=sk-tapio',           'city:Helsinki'],
  ['deep_then_pick_same',   '?area=sk-tapio',           'sk-tapio'],
  ['deep_with_other_params','?area=sk-tapio&lang=en',   'sk-maxim'],
  ['no_param',              '',                          'sk-maxim'],
  ['other_params_only',     '?lang=en',                  'sk-maxim'],
  ['empty_area_param',      '?area=',                    'sk-maxim'],
];
const urls = {};
for (const [name, search, id] of URL_CASES) urls[name] = areaParamAfterSelect(search, id);

process.stdout.write(JSON.stringify({ routing, urls }));
