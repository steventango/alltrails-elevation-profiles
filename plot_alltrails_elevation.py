"""AllTrails-style relative elevation profiles from AllTrails map JSON exports.

Colors are taken from AllTrails light theme design tokens
(`--color-brand-onyx`, `--color-green-*`, neutrals).

Expects:
  ./fonts/AllTrailsAeonikRegular_Regular.ttf
  ./fonts/AllTrailsAeonikMedium_Regular.ttf
  ./data/*.json

Usage:
  python plot_alltrails_elevation.py
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
DATA_DIR = ROOT / "data"

FONT_REGULAR = FONT_DIR / "AllTrailsAeonikRegular_Regular.ttf"
FONT_MEDIUM = FONT_DIR / "AllTrailsAeonikMedium_Regular.ttf"
for f in (FONT_REGULAR, FONT_MEDIUM):
    if f.exists():
        fm.fontManager.addfont(str(f))
PROP_REG = fm.FontProperties(fname=str(FONT_REGULAR)) if FONT_REGULAR.exists() else None
PROP_MED = fm.FontProperties(fname=str(FONT_MEDIUM)) if FONT_MEDIUM.exists() else None

# AllTrails light-theme tokens
BG = "#ffffff"  # --color-neutral-white / background-primary
SEP = "#e6eae6"  # --color-neutral-200 (border-separator approx)
TEXT_SEC = "#535b52"  # --color-neutral-700 / text-secondary
TEXT_PRIMARY = "#161f13"  # --color-brand-onyx / text-primary

# Multi-series line colors from brand + green scale
COLORS = {
    "Folding Mountain": "#161f13",  # brand-onyx
    "Cirque Peak via Helen Lake Trail": "#ac7adf",  # purple-500
    "Sulphur Skyline Trail": "#4da330",  # green-500
    "Morro Peak": "#4c8bf9",  # blue-500
    "Hidden Valley": "#edb326",  # yellow-400
}

TRAIL_FILES = [
    ("Folding Mountain", "folding-mountain.json"),
    ("Cirque Peak via Helen Lake Trail", "cirque-peak.json"),
    ("Sulphur Skyline Trail", "sulphur-skyline.json"),
    ("Morro Peak", "morro-peak.json"),
    ("Hidden Valley", "hidden-valley.json"),
]


def decode_polyline(encoded: str):
    coords, index, lat, lng = [], 0, 0, 0
    length = len(encoded)
    while index < length:
        for is_lat in (True, False):
            result = shift = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if result & 1 else (result >> 1)
            if is_lat:
                lat += d
            else:
                lng += d
        coords.append((lat / 1e5, lng / 1e5))
    return coords


def decode_indexed_elevation(encoded: str):
    s = encoded[1:] if encoded[:1] in "?@" else encoded
    values, index, length = [], 0, len(s)
    while index < length:
        result = shift = 0
        while True:
            if index >= length:
                break
            b = ord(s[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        else:
            break
        d = ~(result >> 1) if result & 1 else (result >> 1)
        values.append(d)
    elev = idx = 0
    out = []
    for i in range(0, len(values) - 1, 2):
        elev += values[i]
        idx += values[i + 1]
        out.append((idx / 100.0, elev / 100000.0))
    return out


def haversine_m(a, b):
    R = 6371000.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(h))


def load_trail(path: Path):
    d = json.load(open(path))
    m = d["maps"][0]
    poly = m["routes"][0]["lineSegments"][0]["polyline"]
    pts = decode_polyline(poly["pointsData"])
    elev_pairs = decode_indexed_elevation(poly["indexedElevationData"])

    dist = [0.0]
    for i in range(1, len(pts)):
        dist.append(dist[-1] + haversine_m(pts[i - 1], pts[i]))

    elev_by_idx = {int(round(i)): e for i, e in elev_pairs}
    keys = sorted(elev_by_idx)
    elevs = []
    for i in range(len(pts)):
        lo = max([k for k in keys if k <= i], default=keys[0])
        hi = min([k for k in keys if k >= i], default=keys[-1])
        if lo == hi:
            elevs.append(elev_by_idx[lo])
        else:
            t = (i - lo) / (hi - lo)
            elevs.append(elev_by_idx[lo] * (1 - t) + elev_by_idx[hi] * t)

    dist = np.array(dist, dtype=float)
    elevs = np.array(elevs, dtype=float)
    official = float(m["summaryStats"]["distanceTotal"])
    if dist[-1] > 0:
        dist = dist * (official / dist[-1])

    rel = elevs - elevs[0]
    return {
        "name": m["name"],
        "dist_km": dist / 1000.0,
        "rel_m": rel,
        "stats": m["summaryStats"],
    }


def short_name(name: str) -> str:
    name = name.replace(" Trail", "")
    if name.startswith("Cirque Peak"):
        return "Cirque Peak"
    return name


def main():
    trails = []
    for label, fname in TRAIL_FILES:
        t = load_trail(DATA_DIR / fname)
        t["label"] = label
        trails.append(t)

    xmax = max(t["dist_km"][-1] for t in trails)
    ymax = max(t["rel_m"].max() for t in trails)
    ytop = int(math.ceil(ymax / 50.0) * 50)
    ybot = 0

    fig, ax = plt.subplots(figsize=(11.5, 4.6), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.axhline(ytop, color=SEP, lw=0.8, alpha=0.9, zorder=1)
    ax.axhline((ytop + ybot) / 2, color=SEP, lw=0.8, alpha=0.9, linestyle=(0, (6, 6)), zorder=1)
    ax.axhline(ybot, color=SEP, lw=0.8, alpha=0.9, zorder=1)

    for t in sorted(trails, key=lambda x: -x["dist_km"][-1]):
        ax.plot(
            t["dist_km"],
            t["rel_m"],
            color=COLORS.get(t["label"], TEXT_PRIMARY),
            lw=2.3,
            solid_capstyle="round",
            zorder=3,
        )

    ax.set_xlim(0, xmax)
    ax.set_ylim(ybot, ytop)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.grid(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    text_kwargs = {"color": TEXT_SEC, "fontsize": 9}
    if PROP_REG is not None:
        text_kwargs["fontproperties"] = PROP_REG

    trans = ax.get_xaxis_transform()
    for x, ha in zip([0.0, xmax / 2, xmax], ["left", "center", "right"]):
        ax.text(x, -0.06, f"{x:.1f} km", transform=trans, ha=ha, va="top", **text_kwargs)

    ax.text(
        1.01, ytop, f"{ytop:,} m", transform=ax.get_yaxis_transform(),
        ha="left", va="center", **text_kwargs,
    )
    ax.text(
        1.01, ybot, f"{ybot} m", transform=ax.get_yaxis_transform(),
        ha="left", va="center", **text_kwargs,
    )

    for x, t in zip([0.0, 0.26, 0.52, 0.76], trails):
        color = COLORS[t["label"]]
        name_kwargs = {"color": color, "fontsize": 9.5}
        if PROP_MED is not None:
            name_kwargs["fontproperties"] = PROP_MED
        ax.text(
            x, 1.10, short_name(t["label"]), transform=ax.transAxes,
            ha="left", va="bottom", **name_kwargs,
        )
        sub_kwargs = {"color": TEXT_SEC, "fontsize": 7.5}
        if PROP_REG is not None:
            sub_kwargs["fontproperties"] = PROP_REG
        ax.text(
            x, 1.03,
            f"{t['stats']['distanceTotal']/1000:.1f} km · {int(t['stats']['elevationGain'])} m gain",
            transform=ax.transAxes, ha="left", va="bottom", **sub_kwargs,
        )

    fig.subplots_adjust(left=0.02, right=0.90, top=0.80, bottom=0.14)
    out_png = ROOT / "elevation-gain-alltrails-style.png"
    out_pdf = ROOT / "elevation-gain-alltrails-style.pdf"
    fig.savefig(out_png, facecolor=BG, edgecolor="none", dpi=200)
    fig.savefig(out_pdf, facecolor=BG)
    print("saved", out_png)


if __name__ == "__main__":
    main()
