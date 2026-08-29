#!/usr/bin/env python3
"""Measure the chain accents against each other, in normal and deuteranope vision.

Run it:

    python3 scripts/accent_check.py            # same-city pairs, worst first
    python3 scripts/accent_check.py --all      # every pair
    python3 scripts/accent_check.py --candidate '#B47ACC' --city Helsinki
    python3 scripts/accent_check.py --selftest # CIEDE2000 against Sharma's test data

IDEAS says accents are "measured against the set, not picked". It recorded the results
and not the method, so the numbers could not be checked and two of them turned out to
disagree with each other. This file is the method. Prose can be misread; a script can be
run, and its CIEDE2000 is checked against published reference data on every run.

Nothing in the pipeline imports this. It exists to be run by hand before an accent is
chosen, and to be re-run when the set changes.

WHAT IS COMPUTED, EXACTLY
-------------------------
1. sRGB hex -> linear RGB, using the piecewise IEC 61966-2-1 transfer function, not a
   gamma-2.2 approximation.
2. Deuteranope simulation, applied to LINEAR RGB. Doing it on gamma-encoded values is
   the classic error and shifts the numbers a long way; it is the likeliest explanation
   for the figures this script contradicts.
   - Primary: Vienot, Brettel & Mollon (1999), the LMS projection every mainstream
     simulator implements. Full dichromacy, no severity parameter.
   - Cross-check: Machado, Oliveira & Fernandes (2009), deuteranomaly at severity 1.0.
     Two independently derived models agreeing is what makes a verdict here trustworthy.
3. Linear RGB -> CIE XYZ (sRGB primaries, D65) -> CIELAB (D65, 2 degree observer).
4. CIEDE2000 (Sharma, Wu & Dalal 2005 formulation), kL = kC = kH = 1.

A pair's separation is its dE00. For a set, the number that matters is the MINIMUM over
the pairs that can appear together, because that is the pair a reader has to tell apart.
"""
import argparse
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "providers"))
import registry                                            # noqa: E402

DATA = HERE.parent / "data"


# ---------------------------------------------------------------- colour

def hex_to_srgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(c):
    """IEC 61966-2-1 piecewise transfer function. Not gamma 2.2 -- they differ most in
    the dark end, which is where several of these accents sit."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def mat3(m, v):
    return tuple(sum(m[r][c] * v[c] for c in range(3)) for r in range(3))


# Linear sRGB (D65) -> CIE XYZ. sRGB primaries, IEC 61966-2-1.
RGB_TO_XYZ = ((0.4124564, 0.3575761, 0.1804375),
              (0.2126729, 0.7151522, 0.0721750),
              (0.0193339, 0.1191920, 0.9503041))

# Vienot, Brettel & Mollon (1999). Linear RGB -> LMS on the Smith & Pokorny cone
# fundamentals, the matrix pair used by Vischeck and everything downstream of it.
RGB_TO_LMS = ((17.8824, 43.5161, 4.11935),
              (3.45565, 27.1554, 3.86714),
              (0.0299566, 0.184309, 1.46709))
LMS_TO_RGB = ((0.080944, -0.130504, 0.116721),
              (-0.0102485, 0.0540194, -0.113615),
              (-0.000365294, -0.00412163, 0.693513))
# Deuteranope: the M cone is absent, so M is reconstructed as a fixed combination of the
# two remaining cones. L and S pass through untouched.
LMS_DEUTAN = ((1.0, 0.0, 0.0),
              (0.494207, 0.0, 1.24827),
              (0.0, 0.0, 1.0))

# Machado, Oliveira & Fernandes (2009), deuteranomaly severity 1.0, on linear RGB.
# Derived from a different starting point (a stage-based opponent model) than Vienot,
# so agreement between the two is real corroboration rather than one model restated.
MACHADO_DEUTAN_100 = ((0.367322, 0.860646, -0.227968),
                      (0.280085, 0.672501, 0.047413),
                      (-0.011820, 0.042940, 0.968881))

D65 = (0.95047, 1.00000, 1.08883)


def deutan_vienot(lin):
    lms = mat3(RGB_TO_LMS, lin)
    return mat3(LMS_TO_RGB, mat3(LMS_DEUTAN, lms))


def deutan_machado(lin):
    return mat3(MACHADO_DEUTAN_100, lin)


def lab(lin):
    """Linear RGB -> CIELAB, D65 2 degree observer."""
    x, y, z = mat3(RGB_TO_XYZ, lin)

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(max(0.0, x) / D65[0]), f(max(0.0, y) / D65[1]), f(max(0.0, z) / D65[2])
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(lab1, lab2, kL=1.0, kC=1.0, kH=1.0):
    """CIEDE2000, following Sharma, Wu & Dalal (2005). Checked by --selftest."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7))) if Cbar > 0 else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = 0.0 if (a1p == 0 and b1 == 0) else math.degrees(math.atan2(b1, a1p)) % 360
    h2p = 0.0 if (a2p == 0 and b2 == 0) else math.degrees(math.atan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)

    Lbar = (L1 + L2) / 2
    Cbarp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbarp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbarp = (h1p + h2p + 360) / 2
    else:
        hbarp = (h1p + h2p - 360) / 2

    T = (1 - 0.17 * math.cos(math.radians(hbarp - 30))
         + 0.24 * math.cos(math.radians(2 * hbarp))
         + 0.32 * math.cos(math.radians(3 * hbarp + 6))
         - 0.20 * math.cos(math.radians(4 * hbarp - 63)))
    dtheta = 30 * math.exp(-(((hbarp - 275) / 25) ** 2))
    RC = 2 * math.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25.0 ** 7)) if Cbarp > 0 else 0.0
    SL = 1 + (0.015 * (Lbar - 50) ** 2) / math.sqrt(20 + (Lbar - 50) ** 2)
    SC = 1 + 0.045 * Cbarp
    SH = 1 + 0.015 * Cbarp * T
    RT = -math.sin(math.radians(2 * dtheta)) * RC

    return math.sqrt((dLp / (kL * SL)) ** 2 + (dCp / (kC * SC)) ** 2
                     + (dHp / (kH * SH)) ** 2
                     + RT * (dCp / (kC * SC)) * (dHp / (kH * SH)))


def labs_for(hexcolour):
    """-> (normal, vienot deutan, machado deutan) CIELAB triples for one hex colour."""
    lin = tuple(srgb_to_linear(c) for c in hex_to_srgb(hexcolour))
    return lab(lin), lab(deutan_vienot(lin)), lab(deutan_machado(lin))


def dE(a, b):
    """-> (normal, vienot, machado) dE00 between two hex colours."""
    la, lb = labs_for(a), labs_for(b)
    return tuple(ciede2000(la[i], lb[i]) for i in range(3))


# ---------------------------------------------------------------- the set

def cities_by_provider():
    """-> {provider_id: {city, ...}} measured from the committed data, not listed here.

    Finnkino keeps the legacy areas.json shape with no city field; its venue names end
    in the city, which is the same rule the client's picker uses.
    """
    out = {}
    for f in sorted(DATA.glob("venues-*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        pid = doc.get("provider") or f.stem.replace("venues-", "")
        for v in doc["venues"]:
            out.setdefault(pid, set()).add(v["city"])
    areas = json.loads((DATA / "areas.json").read_text(encoding="utf-8"))["areas"]
    out["finnkino"] = {a["name"].split()[-1] for a in areas}
    return out


def shared_city_pairs(extra=None):
    """-> [(city, a, b)] for every pair of providers that can appear in one list.

    A combined city view is the only place two chains sit side by side, so this is the
    exact set of pairs the 3 px rule has to survive. `extra` adds a hypothetical
    (id, city) so a candidate accent can be tested before it is committed.
    """
    by = cities_by_provider()
    if extra:
        by.setdefault(extra[0], set()).add(extra[1])
    pairs = []
    for city in sorted({c for cs in by.values() for c in cs}):
        here = sorted(p for p, cs in by.items() if city in cs)
        for i in range(len(here)):
            for j in range(i + 1, len(here)):
                pairs.append((city, here[i], here[j]))
    return pairs


# ---------------------------------------------------------------- selftest

# Sharma, Wu & Dalal (2005), "The CIEDE2000 Color-Difference Formula: Implementation
# Notes ...", Table 1. The pairs chosen here are the ones that exercise the parts an
# implementation gets wrong: the hue-difference wrap, the arithmetic-mean-hue branch,
# and the RT rotation term near hue 275.
SHARMA = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


def selftest():
    bad = 0
    for l1, l2, want in SHARMA:
        got = ciede2000(l1, l2)
        ok = abs(got - want) < 1e-4
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  want {want:8.4f}  got {got:8.4f}")
    # A colour is unchanged by its own comparison, and a grey is unchanged by any
    # dichromat simulation -- the confusion line runs through the neutral axis.
    assert dE("#E4551F", "#E4551F") == (0.0, 0.0, 0.0)
    g = labs_for("#808080")
    assert max(ciede2000(g[0], g[i]) for i in (1, 2)) < 1.0, "grey moved under simulation"
    print(f"\n{len(SHARMA) - bad}/{len(SHARMA)} CIEDE2000 reference pairs match")
    return 1 if bad else 0


# ---------------------------------------------------------------- report

def row(label, a, b, n, v, m):
    return (f"{n:7.1f} {v:7.1f} {m:7.1f}   {label:<26} {a:<14} {b}")


# L* window for the 3 px border. Below ~38 the rule disappears against the dark theme,
# above ~60 it washes out against the light one. Inherited from the Engel search, which
# is the one constraint in the old notes that did not depend on the broken metric.
L_MIN, L_MAX = 38.0, 60.0


def search(pid, accents, step=6, top=12):
    """Best replacement accent for one provider. -> [(worst_deutan, worst_normal, hex)]

    Maximises the *minimum* separation against the chains that share a city with this
    one, because the minimum is what a reader actually has to resolve. Chains it never
    appears beside are unconstrained -- the same reasoning that lets Kino Akseli keep a
    gold that is 0.8 dE00 from Finnkino's orange, since Nummela has one chain.
    """
    rivals = sorted({b if a == pid else a
                     for _, a, b in shared_city_pairs() if pid in (a, b)})
    if not rivals:
        return [], rivals
    fixed = [labs_for(accents[r]) for r in rivals]
    out = []
    for r in range(0, 256, step):
        for g in range(0, 256, step):
            for b in range(0, 256, step):
                h = f"#{r:02X}{g:02X}{b:02X}"
                cand = labs_for(h)
                if not (L_MIN <= cand[0][0] <= L_MAX):
                    continue
                wn = min(ciede2000(cand[0], f[0]) for f in fixed)
                wd = min(min(ciede2000(cand[i], f[i]) for i in (1, 2)) for f in fixed)
                out.append((wd, wn, h))
    out.sort(reverse=True)
    return out[:top], rivals


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all", action="store_true",
                    help="every pair in the set, not only pairs that share a city")
    ap.add_argument("--candidate", metavar="HEX",
                    help="test a hypothetical accent before committing it")
    ap.add_argument("--city", metavar="CITY", default=None,
                    help="city the candidate would appear in (repeatable via commas)")
    ap.add_argument("--search", metavar="PROVIDER_ID",
                    help="best replacement accent for one chain, against its own city")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    accents = {p["id"]: p["accent"] for p in registry.PROVIDERS}
    labels = {p["id"]: p["label"] for p in registry.PROVIDERS}
    extra = None
    if args.candidate:
        if not args.city:
            ap.error("--candidate needs --city")
        accents["candidate"] = args.candidate
        labels["candidate"] = f"CANDIDATE {args.candidate}"

    if args.search:
        accents = {p["id"]: p["accent"] for p in registry.PROVIDERS}
        labels = {p["id"]: p["label"] for p in registry.PROVIDERS}
        if args.search not in accents:
            ap.error(f"unknown provider id: {args.search}")
        best, rivals = search(args.search, accents)
        if not rivals:
            print(f"{labels[args.search]} shares no city with another chain, so its "
                  f"accent is unconstrained. Nothing to search.")
            return 0
        cur = labs_for(accents[args.search])
        fixed = [labs_for(accents[r]) for r in rivals]
        cn = min(ciede2000(cur[0], f[0]) for f in fixed)
        cd = min(min(ciede2000(cur[i], f[i]) for i in (1, 2)) for f in fixed)
        print(f"{labels[args.search]} shares a city with: "
              f"{', '.join(labels[r] for r in rivals)}")
        print(f"current {accents[args.search]}: worst normal {cn:.1f}, "
              f"worst deutan {cd:.1f}\n")
        print(f"best candidates in L* {L_MIN:.0f}-{L_MAX:.0f}, ranked by worst deutan:")
        print("  hex       worst deutan  worst normal")
        for wd, wn, h in best:
            print(f"  {h}   {wd:11.1f}   {wn:11.1f}")
        return 0

    print("dE00 between chain accents. Higher is more separable; the number that")
    print("matters for a set is the smallest one, since that is the pair a reader")
    print("has to tell apart. Deutan columns are full dichromacy.\n")
    print(" normal  vienot machado   where                      chain          chain")
    print(" " + "-" * 84)

    if args.all:
        ids = sorted(accents)
        rows = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                n, v, m = dE(accents[ids[i]], accents[ids[j]])
                rows.append((min(v, m), row("(any)", labels[ids[i]], labels[ids[j]],
                                            n, v, m)))
        for _, line in sorted(rows):
            print(line)
        worst = min(r[0] for r in rows)
        print(f"\nglobal minimum over all pairs: {worst:.1f} dE00 (worse of the two models)")
        return 0

    for city in (args.city or "").split(","):
        city = city.strip()
        if city:
            extra = ("candidate", city)
            break

    rows = []
    for city, a, b in shared_city_pairs(extra):
        n, v, m = dE(accents[a], accents[b])
        rows.append((min(v, m), city, row(city, labels[a], labels[b], n, v, m)))
    if not rows:
        print("no city has two chains in it")
        return 0
    for _, _, line in sorted(rows):
        print(line)

    worst = rows[0] if len(rows) == 1 else sorted(rows)[0]
    print(f"\nworst same-city pair: {worst[0]:.1f} dE00 under the harsher of the two "
          f"deutan models, in {worst[1]}")
    print("L* of each accent (the 3 px rule needs this legible on both themes):")
    for pid in sorted(accents):
        print(f"  {labels[pid]:<26} {accents[pid]}  L* {labs_for(accents[pid])[0][0]:5.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
