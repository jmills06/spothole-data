# spothole-data

A standalone data layer for amateur-radio spotting. A scheduled GitHub Action
pulls outdoor-programme activity from the [Spothole API](https://spothole.app),
enriches it with QRZ lookups and locally-derived fields, and publishes a stable
set of JSON files to GitHub Pages. **This repo hosts no boards** — its product is
the published JSON URLs below, consumed cross-origin by other projects.

```
Base URL:  https://jmills06.github.io/spothole-data/data/latest
```

Data refreshes roughly every 5 minutes. Read `manifest.json` for the canonical
freshness timestamp and per-feed status.

---

## Data contract (`data/latest/`)

| File | Shape | Notes |
|------|-------|-------|
| `spots.json` | array of spot objects | **Master:** all outdoor-programme (xOTA) activity, QRZ-enriched, newest first, **not** deduped |
| `pota.json` | array of spots | `sig == "POTA"`, latest spot per call, newest first |
| `ssb.json` | array of spots | `mode` in `SSB`/`USB`/`LSB`, latest per call, newest first |
| `map-points.json` | array of spots | `dx_location_good == true` (trustworthy coordinates), all fixes kept, newest first |
| `alerts.json` | array of alert objects | Upcoming planned activations |
| `solar.json` | object | Solar indices, HF/VHF band conditions, and forecasts. May contain nulls — handle gracefully |
| `dxstats.json` | nested object | Spot counts, DE continent → DX continent → band, last hour |
| `options.json` | object | Enumerations (bands, modes, sigs, sources) for legends/filters |
| `manifest.json` | object | Freshness + per-feed `url`/`count`/`updated`/`ok`, plus QTH constants |

The `data/latest/` filenames and field names are a **public interface** other
repos depend on — they are not changed casually. Breaking changes bump
`schema_version` in the manifest (currently `1`).

### `manifest.json`

```jsonc
{
  "generated": 1784225615,               // epoch seconds, this run
  "generated_iso": "2026-07-16T18:13:35Z",
  "schema_version": 1,
  "distance_unit": "mi",                 // miles
  "qth": { "call": "K8JKU", "lat": 42.7228522, "lon": -83.4197040, "cq_zone": 4 },
  "feeds": {
    "spots": { "url": "data/latest/spots.json", "count": 722, "updated": 1784225615, "ok": true },
    "solar": { "url": "data/latest/solar.json", "count": null, "updated": 1784225615, "ok": true }
    // ...one entry per feed. `count` is null for object-shaped feeds.
  }
}
```

If a feed fails on a given run, its previous file is **left in place** and its
manifest entry is marked `"ok": false` (with no fresh `updated`). Only
`manifest.generated` reflects every run. A total network failure therefore
changes almost nothing on disk rather than blanking every board.

---

## Spot object

Each spot in `spots.json` / `pota.json` / `ssb.json` / `map-points.json` carries
the raw Spothole fields plus the derived fields this repo adds. Common raw fields:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Stable hash id for the spot |
| `dx_call` | string | Activator (spotted station) callsign |
| `dx_qth` | string | Reference/park name and id |
| `dx_grid` | string | Maidenhead grid |
| `dx_latitude` / `dx_longitude` | number | Activation coordinates |
| `dx_location_good` | bool | True when coordinates are a real fix (not a DXCC centroid guess) |
| `dx_cq_zone` / `dx_itu_zone` | int | Operator's CQ / ITU zone (passed through unchanged) |
| `dx_continent` / `dx_country` | string | Activator location |
| `de_call` | string | Spotter callsign |
| `mode` / `mode_type` | string | e.g. `SSB` / `PHONE`, `CW` / `CW`, `FT8` / `DATA` |
| `band` | string | e.g. `20m` |
| `freq` | number | Frequency in Hz |
| `sig` | string | Programme, e.g. `POTA` |
| `sig_refs` | array | Reference details (id, name, url, coords) |
| `time` / `time_iso` | number / string | Spot time |
| `received_time` | number | When Spothole received it (used for history watermark) |
| `comment` | string | Spotter comment |
| `qrt` | bool | Activator has signed off |

### Fields this repo adds to every spot

| Field | Type | Meaning |
|-------|------|---------|
| `in_my_cq_zone` | bool or null | `dx_cq_zone == 4` (home zone). **Null** when the spot has no CQ zone. |
| `distance_from_qth_mi` | number or null | Great-circle **miles** from the Clarkston, MI QTH. **Null unless `dx_location_good` is true**, so a non-null value is always trustworthy. |

**CQ-zone caveat:** `dx_cq_zone` is the *operator's* zone (where they're
licensed/home), not necessarily where they're standing during a portable
activation. Treat `in_my_cq_zone` as a coarse "same region" proxy.
`distance_from_qth_mi`, when present, is the stronger "can I hear them" signal
because it reflects the activation's actual location (often the park itself).

---

## Consuming from another repo

No proxy needed — fetch directly (CORS is open on GitHub Pages):

```js
const BASE = "https://jmills06.github.io/spothole-data/data/latest";

const spots = await (await fetch(`${BASE}/pota.json`)).json();
const inZone = spots.filter(s => s.in_my_cq_zone);           // coarse "my region"
const nearby = spots
  .filter(s => s.distance_from_qth_mi != null)
  .sort((a, b) => a.distance_from_qth_mi - b.distance_from_qth_mi);

// One canonical freshness stamp for the whole layer:
const { generated } = await (await fetch(`${BASE}/manifest.json`)).json();
```

---

## Repo layout

```
collector/            # replaceable machinery
  config.py           # QTH constants + feed definitions
  spothole.py         # thin API client (QRZ creds, User-Agent, timeout)
  derive.py           # haversine miles, CQ-zone flag, slice builder
  collect.py          # orchestrator / entry point
  requirements.txt
data/
  latest/             # the public contract (files above)
  history/
    state.json        # { "last_received": <epoch> } watermark
    spots/YYYY-MM-DD.jsonl   # append-only, unique spots by id
.github/workflows/
  collect.yml         # workflow_dispatch, triggered by cron-job.org
```

### Scope (v1)

Outdoor programmes only (`needs_sig=true`). The general DX cluster and the RBN
firehose are deliberately excluded from the master file and history; they may
become opt-in feeds later.

### Running locally

```bash
py collector/collect.py        # Windows (py launcher)
python collector/collect.py    # Linux / CI
```

QRZ enrichment is applied when `QRZ_USERNAME` / `QRZ_PASSWORD` are set in the
environment; without them the collector still runs, unenriched.

---

Source data: Spothole (Unlicense / public domain). Distances in miles from a
public-space proxy near Clarkston, MI.
