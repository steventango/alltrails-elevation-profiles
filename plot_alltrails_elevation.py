"""AllTrails-style relative elevation profiles from AllTrails map JSON exports.

Drop any AllTrails map JSON into ./data/ and re-run — trails are discovered
automatically. Colors cycle through AllTrails light-theme tokens (onyx + one
green + non-green accents). Longest hike gets onyx first.

Expects:
  ./fonts/AllTrailsAeonikRegular_Regular.ttf
  ./fonts/AllTrailsAeonikMedium_Regular.ttf
  ./data/*.json

Usage:
  python plot_alltrails_elevation.py
"""
from __future__ import annotations

import json
import math
import re
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
BG = "#ffffff"  # --color-neutral-white
SEP = "#e6eae6"  # --color-neutral-200
TEXT_SEC = "#535b52"  # --color-neutral-700
TEXT_PRIMARY = "#161f13"  # --color-brand-onyx

# Ordered palette: black, one green, then non-green accents for contrast
PALETTE = [
    "#161f13",  # brand-onyx
    "#4da330",  # green-500
    "#4c8bf9",  # blue-500
    "#edb326",  # yellow-400
    "#ac7adf",  # purple-500
    "#329ea5",  # teal-500
    "#f8903c",  # orange-400
    "#e96098",  # pink-500
    "#7d76ff",  # map-custom-route-2
    "#65dde1",  # map-custom-route-1
    "#8858bb",  # purple-600
    "#ba4c21",  # red-600
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


def load_trail(path: Path) -> dict:
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
        lo = max((k for k in keys if k <= i), default=keys[0])
        hi = min((k for k in keys if k >= i), default=keys[-1])
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

    return {
        "name": m["name"],
        "path": path,
        "dist_km": dist / 1000.0,
        "rel_m": elevs - elevs[0],
        "stats": m["summaryStats"],
    }


def short_name(name: str) -> str:
    name = re.sub(r"\s+Trail$", "", name)
    name = re.sub(r"^(.+?)\s+via\s+.+$", r"\1", name, flags=re.I)
    return name


def discover_trails(data_dir: Path) -> list[dict]:
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise SystemExit(f"No JSON files in {data_dir}")
    trails = [load_trail(p) for p in paths]
    # Longest first: stable visual hierarchy, onyx on the biggest hike
    trails.sort(key=lambda t: (-t["dist_km"][-1], t["name"].lower()))
    for i, t in enumerate(trails):
        t["color"] = PALETTE[i % len(PALETTE)]
        t["label"] = short_name(t["name"])
    return trails


def legend_positions(n: int, cols: int | None = None) -> list[tuple[float, float]]:
    """Return (x, y) in axes-fraction for n legend entries, wrapping as needed."""
    if n <= 0:
        return []
    if cols is None:
        cols = 3 if n >= 6 else (4 if n == 5 else max(n, 1))
    cols = min(cols, n)
    rows = math.ceil(n / cols)
    # Top of axes is 1.0; stack rows above the plot
    row_height = 0.085
    positions = []
    for i in range(n):
        r, c = divmod(i, cols)
        # actual columns in this row (last row may be short)
        row_count = min(cols, n - r * cols)
        # spread across [0, 0.98]
        if row_count == 1:
            x = 0.0
        else:
            x = c / (cols - 1) * 0.78 if cols > 1 else 0.0
            # better: even spacing for items in full grid
            x = c * (0.98 / cols)
        y = 1.0 + (rows - r) * row_height
        positions.append((x, y))
    return positions, rows


def main():
    trails = discover_trails(DATA_DIR)
    for t in trails:
        print(
            f"{t['label']:20s} {t['dist_km'][-1]:5.2f} km  "
            f"+{t['rel_m'].max():.0f} m peak  "
            f"{int(t['stats']['elevationGain'])} m gain  {t['color']}"
        )

    xmax = max(t["dist_km"][-1] for t in trails)
    ymax = max(t["rel_m"].max() for t in trails)
    ytop = int(math.ceil(ymax / 50.0) * 50)
    ybot = 0

    n = len(trails)
    cols = 3 if n >= 6 else (4 if n == 5 else n)
    positions, rows = legend_positions(n, cols=cols)

    fig_w = 12.5 if n <= 5 else 13.5
    top_margin = 0.78 - 0.04 * max(0, rows - 1)
    fig, ax = plt.subplots(figsize=(fig_w, 4.4 + 0.35 * rows), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.axhline(ytop, color=SEP, lw=0.8, alpha=0.9, zorder=1)
    ax.axhline((ytop + ybot) / 2, color=SEP, lw=0.8, alpha=0.9, linestyle=(0, (6, 6)), zorder=1)
    ax.axhline(ybot, color=SEP, lw=0.8, alpha=0.9, zorder=1)

    # Draw longest first so shorter trails sit on top
    for t in trails:
        ax.plot(
            t["dist_km"],
            t["rel_m"],
            color=t["color"],
            lw=2.2,
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

    name_size = 8.5 if n <= 5 else 8.0
    stat_size = 7.0 if n <= 5 else 6.5
    for (x, y), t in zip(positions, trails):
        name_kwargs = {"color": t["color"], "fontsize": name_size}
        if PROP_MED is not None:
            name_kwargs["fontproperties"] = PROP_MED
        ax.text(x, y, t["label"], transform=ax.transAxes, ha="left", va="bottom", **name_kwargs)
        sub_kwargs = {"color": TEXT_SEC, "fontsize": stat_size}
        if PROP_REG is not None:
            sub_kwargs["fontproperties"] = PROP_REG
        ax.text(
            x, y - 0.055,
            f"{t['stats']['distanceTotal']/1000:.1f} km · {int(t['stats']['elevationGain'])} m gain",
            transform=ax.transAxes, ha="left", va="bottom", **sub_kwargs,
        )

    fig.subplots_adjust(left=0.02, right=0.90, top=top_margin, bottom=0.12)
    out_png = ROOT / "elevation-gain-alltrails-style.png"
    out_pdf = ROOT / "elevation-gain-alltrails-style.pdf"
    fig.savefig(out_png, facecolor=BG, edgecolor="none", dpi=200)
    fig.savefig(out_pdf, facecolor=BG)
    print("saved", out_png)


if __name__ == "__main__":
    main()
