// Finnkino token fetcher — deploy on Cloudflare Workers (free tier).
// Fetches a finnkino.fi page from Cloudflare's network (which Finnkino
// doesn't block) and returns the embedded API token as JSON: {"token": "..."}
const PAGES = [
  "https://www.finnkino.fi/",
  "https://www.finnkino.fi/teatterit/finnkino-tennispalatsi/",
  "https://www.finnkino.fi/teatterit/finnkino-plevna/",
];
const JWT = /eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/;
const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
};

export default {
  async fetch() {
    const errors = [];
    for (const url of PAGES) {
      try {
        const r = await fetch(url, { headers: HEADERS });
        if (!r.ok) { errors.push(`${url}: HTTP ${r.status}`); continue; }
        const html = await r.text();
        const m = html.match(JWT);
        if (m) {
          return new Response(JSON.stringify({ token: m[0] }), {
            headers: { "content-type": "application/json" },
          });
        }
        errors.push(`${url}: no token in page`);
      } catch (e) {
        errors.push(`${url}: ${e.message}`);
      }
    }
    return new Response(JSON.stringify({ error: errors }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  },
};
