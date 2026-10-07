// One cookieless PostHog $pageview for a generated city or theatre page.
//
// The app's privacy contract in index.html, held to it by tests/test_analytics_privacy.py:
// the same project, host, pinned bundle, integrity hash, init options, scrubber, origin
// guard and Do Not Track / Global Privacy Control check. The page names its category on
// the script tag and nothing else; the only URL PostHog receives is built from that
// category. See README.md's Privacy section and /tietosuoja/.
(function(){
  'use strict';
  const PH_KEY  = 'phc_zTiDPrATqb3MbLoYZ25XKhkNpdR7GsdeofZL6rnd5GzV';
  const PH_HOST = 'https://eu.i.posthog.com';
  const PH_VERSION = '1.434.2';

  // --- analyticsScrub: pure, extracted verbatim by tests/analytics_harness.js ---
  // The app's scrubber, unchanged, over a smaller table: a generated page sends a page
  // view and nothing else, and only with one of its two categories.
  const PH_ALLOW = {
    $pageview: ['category'],
  };
  const PH_CATEGORIES = ['generated_city', 'generated_theatre'];
  const PH_URL_BASE = 'https://leffavuoro.fi/pages/';

  function analyticsScrub(event){
    if(!event || !Object.prototype.hasOwnProperty.call(PH_ALLOW, event.event)) return null;
    const keep = PH_ALLOW[event.event], src = event.properties || {}, out = {};
    for(const k of keep){
      const v = src[k];
      if(v !== undefined && v !== null && v !== '') out[k] = v;
    }
    // Required: strip either and posthog-js builds no request at all (measured
    // 2026-09-20). distinct_id in cookieless mode is the constant "$posthog_cookieless".
    for(const k of ['token', 'distinct_id'])
      if(src[k] !== undefined) out[k] = src[k];
    // $pageview's URL is constructed here, never forwarded. An unknown category drops
    // the event rather than guessing a view that was not on screen.
    if(event.event === '$pageview'){
      if(PH_CATEGORIES.indexOf(out.category) === -1) return null;
      out.$current_url = PH_URL_BASE + out.category;
    }
    event.properties = out;
    // Person properties. person_profiles:'never' already no-ops these; drop them anyway.
    delete event.$set;
    delete event.$set_once;
    return event;
  }
  // --- end analyticsScrub ---

  // --- phAllowedOrigin: pure, extracted verbatim by tests/analytics_harness.js ---
  function phAllowedOrigin(protocol, hostname){
    return protocol === 'https:' && hostname === 'leffavuoro.fi';
  }
  // --- end phAllowedOrigin ---

  const phDNT = () => navigator.doNotTrack === '1' || window.doNotTrack === '1'
                   || navigator.msDoNotTrack === '1' || navigator.globalPrivacyControl === true;

  // The category comes from the tag that loaded this file, set by build_pages.py. Every
  // check runs before any request, so a bad category, another origin, DNT or GPC means
  // nothing is fetched from PostHog, not even the bundle.
  const me = document.currentScript;
  const category = me ? me.getAttribute('data-category') : null;
  if(PH_CATEGORIES.indexOf(category) === -1) return;
  if(phDNT() || !phAllowedOrigin(location.protocol, location.hostname)) return;

  function phInit(){
    const sc = document.createElement('script');
    sc.src = PH_HOST.replace('.i.posthog.com', '-assets.i.posthog.com')
           + '/static/' + PH_VERSION + '/array.js';
    // The app's hash for the 1.434.2 bundle; a rebuilt bundle never runs.
    sc.integrity = 'sha384-BmbtQMM1P8wo232drqi6RUQiNd0ZFk56bltD3yk2/94kez4jFURztoW+DlYzT2Ah';
    sc.crossOrigin = 'anonymous';
    sc.async = true;
    sc.onload = () => {
      try{
        window.posthog.init(PH_KEY, {
          api_host: PH_HOST,
          cookieless_mode: 'always',     // no cookie, no localStorage, no sessionStorage
          person_profiles: 'never',      // no person profile, and identify() becomes a no-op
          persistence: 'memory',
          disable_persistence: true,
          respect_dnt: true,
          autocapture: false,            // no clicks, no element text
          capture_pageview: false,       // $pageview below is ours, with a synthetic URL
          capture_pageleave: false,
          capture_dead_clicks: false,
          capture_heatmaps: false,
          capture_performance: false,
          capture_exceptions: false,
          disable_session_recording: true,
          disable_surveys: true,
          enable_recording_console_log: false,
          // No /decide call, so no feature flags, no surveys, no toolbar and no remote
          // configuration: nothing about what this page collects can be turned on from
          // outside this file.
          advanced_disable_decide: true,
          advanced_disable_feature_flags: true,
          before_send: analyticsScrub,
        });
        // Only the category. The URL is the scrubber's to build.
        window.posthog.capture('$pageview', { category: category });
      }catch(_){}
    };
    document.head.appendChild(sc);
  }

  // After the load event, so a slow or blocked PostHog cannot hold up the page or its
  // load event. A page restored from the back-forward cache does not run this again.
  if(document.readyState === 'complete') phInit();
  else window.addEventListener('load', phInit, { once: true });
})();
