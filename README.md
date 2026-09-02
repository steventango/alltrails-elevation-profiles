# Alberta hike elevation profiles (AllTrails style)

Compare relative elevation change vs distance for Alberta hikes, styled like AllTrails elevation charts.

Elevation is **relative to the trailhead** (every series starts at `0 m`). Distance is scaled to each map’s AllTrails `distanceTotal`.

## Add a hike

1. Export / save an AllTrails map JSON (needs `polyline.pointsData` + `indexedElevationData`).
2. Drop it in `data/` as `anything.json`.
3. Run:

```bash
python plot_alltrails_elevation.py
```

Trails are **auto-discovered** from `data/*.json`. No code edits required. Longest hike is drawn first and gets brand onyx; remaining colors cycle a fixed AllTrails token palette.

## Colors (AllTrails light theme tokens)

Assigned longest → shortest:

| Order | Token | Hex |
| --- | --- | --- |
| 1 | `--color-brand-onyx` | `#161f13` |
| 2 | `--color-green-500` | `#4da330` |
| 3 | `--color-blue-500` | `#4c8bf9` |
| 4 | `--color-yellow-400` | `#edb326` |
| 5 | `--color-purple-500` | `#ac7adf` |
| 6 | `--color-teal-500` | `#329ea5` |
| 7+ | orange / pink / map-route accents | … |

Axis labels use `--color-neutral-700` (`#535b52`); separators use `--color-neutral-200` (`#e6eae6`).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fonts (not in this repo)

AllTrails Aeonik is proprietary, so font files are gitignored. Place these TTFs under `fonts/`:

- `AllTrailsAeonikRegular_Regular.ttf`
- `AllTrailsAeonikMedium_Regular.ttf`

### Data currently included

- Folding Mountain
- Cirque Peak (via Helen Lake)
- Sulphur Skyline
- Ha Ling Peak
- Morro Peak
- Hidden Valley

## Output

Writes `elevation-gain-alltrails-style.png` and `.pdf`.

## Notes

- Peak height on the chart is net elevation above the start, which can differ from AllTrails’ cumulative `elevationGain` when the trail undulates.
