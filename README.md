# Alberta hike elevation profiles (AllTrails style)

Compare relative elevation change vs distance for Alberta hikes, styled like AllTrails elevation charts.

**Trails included**
- Folding Mountain
- Sulphur Skyline
- Morro Peak
- Hidden Valley

Elevation is **relative to the trailhead** (all series start at `0 m`). Distance is scaled to each map’s AllTrails `distanceTotal`.

## Colors (AllTrails light theme tokens)

| Trail | Token | Hex |
| --- | --- | --- |
| Folding Mountain | `--color-brand-onyx` | `#161f13` |
| Sulphur Skyline | `--color-green-500 | `#4da330`` |
| Morro Peak | `--color-blue-500` | `#4c8bf9` |
| Hidden Valley | `--color-yellow-400` | `#edb326` |
| Axis / labels | `--color-neutral-700` | `#535b52` |
| Separators | `--color-neutral-200` | `#e6eae6` |
| Background | `--color-neutral-white` | `#ffffff` |

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

(Convert from `.woff2` with fontTools if needed.)

### Data

AllTrails map JSON exports live in `data/`:

- `folding-mountain.json`
- `sulphur-skyline.json`
- `morro-peak.json`
- `hidden-valley.json`

## Run

```bash
python plot_alltrails_elevation.py
```

Writes `elevation-gain-alltrails-style.png` and `.pdf`.

## Notes

- Profiles come from each JSON’s `polyline.pointsData` + `indexedElevationData`.
- Peak height on the chart is net elevation above the start, which can differ from AllTrails’ cumulative `elevationGain` when the trail undulates.
