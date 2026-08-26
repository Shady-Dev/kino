"""Fetch Finnkino XML schedule data and write compact JSON files into data/."""
import json, time, sys, pathlib, datetime
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://www.finnkino.fi/xml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    "Referer": "https://www.finnkino.fi/",
}

def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def txt(el, tag: str) -> str:
    n = el.find(tag)
    return (n.text or "").strip() if n is not None and n.text else ""

def main() -> int:
    out = pathlib.Path("data")
    out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    root = ET.fromstring(get(BASE + "/TheatreAreas/"))
    areas = [{"id": txt(a, "ID"), "name": txt(a, "Name")} for a in root.iter("TheatreArea")]
    areas = [a for a in areas if a["id"] and a["id"] != "1029"]
    if not areas:
        print("ERROR: theatre area list came back empty", file=sys.stderr)
        return 1

    (out / "areas.json").write_text(
        json.dumps({"generated": now, "areas": areas}, ensure_ascii=False), encoding="utf-8"
    )
    print(f"areas.json written ({len(areas)} areas)")

    failed = 0
    for a in areas:
        try:
            sroot = ET.fromstring(get(f"{BASE}/Schedule/?area={a['id']}&nrOfDays=7"))
            shows = []
            for s in sroot.iter("Show"):
                shows.append({
                    "eventId": txt(s, "EventID"),
                    "title": txt(s, "Title"),
                    "original": txt(s, "OriginalTitle"),
                    "len": txt(s, "LengthInMinutes"),
                    "rating": txt(s, "Rating"),
                    "genres": txt(s, "Genres"),
                    "method": txt(s, "PresentationMethodAndLanguage"),
                    "theatre": txt(s, "Theatre"),
                    "aud": txt(s, "TheatreAuditorium"),
                    "start": txt(s, "dttmShowStart"),
                    "url": txt(s, "ShowURL"),
                    "img": txt(s, ".//EventSmallImagePortrait") or txt(s, ".//EventMediumImagePortrait"),
                })
            (out / f"area-{a['id']}.json").write_text(
                json.dumps({"generated": now, "shows": shows}, ensure_ascii=False), encoding="utf-8"
            )
            print(f"area {a['id']} ({a['name']}): {len(shows)} shows")
            time.sleep(0.5)
        except Exception as e:
            failed += 1
            print(f"area {a['id']} failed: {e}", file=sys.stderr)

    if failed == len(areas):
        print("ERROR: every schedule fetch failed", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
