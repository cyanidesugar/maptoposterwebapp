# Render open sea/ocean for coastal posters

**Date:** 2026-05-20
**Status:** Approved, pending spec review

## Problem

`create_map_poster.py` currently fetches water features with the OSM tags
`{"natural": "water", "waterway": "riverbank"}`. This captures lakes, rivers,
and riverbanks but does **not** capture the open sea / ocean, because OSM
models the sea as `natural=coastline` LineStrings, not polygons. The "outside"
of the coastline is implicit and is reconstructed by tile renderers from a
separately maintained polygon dataset.

Posters of coastal cities (e.g. Koper, Slovenia) therefore have a blank
background where the sea should be, while inland water bodies are still
coloured correctly.

## Goals

1. Render the open sea in coastal posters, using the same `water` colour from
   the active theme so it merges seamlessly with any river mouths or harbours.
2. Keep the default CLI behaviour **exactly unchanged** — the feature is
   opt-in via a new flag. This is a requirement for accepting the PR upstream
   to `originalankur/maptoposter` without breaking any existing user's
   pipeline.
3. Surface the feature in the desktop GUI (`maptoposter_gui.py`) as a toggle,
   defaulting off.
4. No new runtime dependencies. `shapely` is already required.

## Non-goals

- Sea rendering for locations entirely at sea (no coastlines in the bbox).
  This would require synthesising an "all sea" classification from a separate
  signal; nobody posters open ocean, so we skip it.
- A separate `sea` colour in the theme schema. Decided against during
  brainstorming — same `water` colour keeps every existing theme working and
  gives a visually coherent result.
- Streaming or async coastline downloads. Coastline fetch is one extra
  synchronous `ox.features_from_point` call, gated behind the opt-in flag.

## Approach

OSM's coastline convention is the key:

> Coastline ways are tagged `natural=coastline` and are drawn in a direction
> such that **land is on the left and sea is on the right** when walking
> along the way.

This lets us classify polygons without external context:

1. Fetch `natural=coastline` features for the same point/distance as roads and
   water (only when `show_sea` is enabled).
2. Clip each coastline LineString to the visible bounding box.
3. Compute the planar partition of the bbox induced by the union of
   coastlines + bbox boundary, via `shapely.ops.polygonize`.
4. For each resulting polygon, sample a probe point 1 m to the right of one
   of its bounding coastline segments (right-perpendicular: rotate the
   segment direction by −90°). If the probe lies inside the polygon, the
   polygon is on the sea side of that coastline → classify as sea.
5. Render the sea polygons with `theme['water']` at `zorder=0.4`, below
   inland water (`0.5`), parks (`0.8`), and roads (`2`).

Drawing sea **below** inland water means a river that meets the coastline
paints over the sea with the same colour — visually seamless, no double-fill
artefacts.

## Components

All changes live in `create_map_poster.py`. No new module.

### `_fetch_coastlines(point, dist) -> Optional[GeoDataFrame]`

Thin wrapper around `ox.features_from_point` with
`tags={'natural': 'coastline'}`. Same exception swallowing pattern as
`fetch_features` — logs a warning and returns `None` on OSMnx errors so the
poster still renders.

### `_compute_sea_polygons(coastlines, bbox_polygon, target_crs) -> list[Polygon]`

Pure function. Inputs:

- `coastlines`: `GeoDataFrame` from `_fetch_coastlines`, possibly `None` or
  empty.
- `bbox_polygon`: the visible map area as a `shapely.geometry.Polygon`,
  already in `target_crs`.
- `target_crs`: the projected CRS of the rendered graph
  (`g_proj.graph['crs']`), used to reproject coastlines.

Behaviour:

1. Return `[]` if `coastlines` is `None` or empty.
2. Filter to `LineString`/`MultiLineString` geometries; flatten MultiLineStrings.
3. Reproject to `target_crs` via `ox.projection.project_gdf` (same call
   `_project_features` uses for water/parks).
4. Clip each line to `bbox_polygon` via `line.intersection(bbox_polygon)`.
   Keep only `LineString` and `MultiLineString` results (drop `Point`-only
   touches).
5. If no clipped lines remain → return `[]`.
6. `merged = unary_union(clipped_lines + [bbox_polygon.boundary])`.
7. `polygons = list(polygonize(merged))`.
8. For each polygon, run `_polygon_is_sea(polygon, clipped_lines)`; collect
   the sea ones.
9. Wrap any exception during steps 3–8 in a `try/except`, log a warning,
   return `[]` — never fail the whole poster.

### `_polygon_is_sea(polygon, coastlines) -> bool`

For each coastline segment that touches `polygon.boundary`:

1. Pick the midpoint of the segment for numerical stability.
2. Compute the unit right-perpendicular: if the segment direction is
   `(dx, dy)`, the right normal is `(dy, -dx) / length`.
3. Offset the midpoint by 1.0 metre in that direction (projected CRS is
   metric — OSMnx projects to UTM zones).
4. If `polygon.contains(Point(probe))` → return `True`.

Returns `False` if no segment passes the test.

### `_render_sea(ax, sea_polygons, theme, target_crs) -> None`

If list is non-empty, build a `GeoSeries(sea_polygons, crs=target_crs)` and
call `.plot(ax=ax, facecolor=theme['water'], edgecolor='none', zorder=0.4)`.
This matches the existing `_render_water` / `_render_parks` pattern and
correctly handles any polygon holes that might arise from polygonize.

### Changes to `create_poster()`

New parameter:

```python
show_sea: bool = False,
```

Inserted after `no_parks` to keep adjacent feature-toggle params together.
Logic inside `create_poster`:

```python
sea_polys: list[Polygon] = []
if show_sea and not no_water:
    coastlines = _fetch_coastlines(point, compensated_dist)
    bbox_polygon = box(crop_xlim[0], crop_ylim[0], crop_xlim[1], crop_ylim[1])
    sea_polys = _compute_sea_polygons(coastlines, bbox_polygon, g_proj.graph['crs'])

# In the render section, BEFORE _render_water:
if sea_polys:
    _render_sea(ax, sea_polys, theme, g_proj.graph['crs'])
```

Note: `crop_xlim`/`crop_ylim` are `(min, max)` tuples; `shapely.geometry.box`
takes `(minx, miny, maxx, maxy)`. Add `box` to the existing
`from shapely.geometry import Point` import.

### CLI argument

```python
parser.add_argument(
    '--show-sea', action='store_true',
    help='Render open sea/ocean for coastal locations (off by default)',
)
```

Passed to `create_poster(..., show_sea=args.show_sea, ...)` in the
`__main__` block.

## GUI integration (`maptoposter_gui.py`)

Add a fifth toggle next to the existing Text/Roads/Water/Parks switches in
column 4 of the controls grid:

```python
self.sea_sw = ctk.CTkSwitch(toggle_frame, text=" Ocean")
self.sea_sw.pack(anchor="w", padx=10, pady=8)
# default: not selected (off)
```

Plumbing:

- `_collect_form_settings` → add `"show_sea": self.sea_sw.get()`.
- `_apply_settings_to_form` → in the per-switch loop, add
  `(self.sea_sw, "show_sea", False)` to the list of `(switch, key, default)`
  tuples.
- `_collect_generation_params` → add `params["show_sea"] = bool(self.sea_sw.get())`.
- `_build_subprocess_cmd` → `if params.get("show_sea"): cmd.append("--show-sea")`.
- `_run_direct` → pass `show_sea=params.get("show_sea", False)` to
  `create_poster`.

Default-off means saved `gui_settings.json` files from before this change
silently default to the existing behaviour — no migration needed.

## Data flow

```
fetch_graph
fetch_features (water)          ┐
fetch_features (parks)          ├── existing
_fetch_coastlines (NEW, gated)  ┘
        │
project_graph (existing)
        │
crop_xlim, crop_ylim ─► bbox_polygon (NEW)
        │
_compute_sea_polygons (NEW)
        │
        ▼
Layer order:
  bg
  _render_sea       zorder 0.4   (NEW)
  _render_water     zorder 0.5   (existing)
  _render_parks     zorder 0.8   (existing)
  _render_roads     zorder 2     (existing)
  gradient_fade     zorder 10    (existing)
  text              zorder 11    (existing)
```

## Edge cases

| Case | Behaviour |
|---|---|
| `--show-sea` not set (default) | No coastline fetch, no rendering changes. Exact prior behaviour. |
| `--show-sea` + `--no-water` | Sea hidden (same flag controls water-coloured fills). |
| Inland location, no coastlines in bbox | `_fetch_coastlines` returns empty GDF, `_compute_sea_polygons` returns `[]`, nothing rendered. |
| Single straight coastline crossing the bbox | One sea polygon (the half on the line's right side) rendered. |
| Island fully inside bbox (closed-loop coastline, wound clockwise per OSM) | Two polygons from polygonize: interior is on the line's left (land) → not rendered; exterior is on the right (sea) → rendered. |
| Multiple coastlines (strait, archipelago) | `polygonize` produces multiple regions; classifier evaluates each independently. |
| OSMnx fetch fails | Warning logged, returns `None` → empty sea list → poster still renders normally without sea. |
| Shapely exception during polygonize/classification | Warning logged, returns `[]` → poster still renders. |
| Degenerate coastline (collinear, zero-length segment) | Skipped during classification (`length == 0` guard). |

## Testing

Add to `test_mapstudio.py` (pure functions, no network — matches existing
test policy):

1. **`test_sea_classification_simple_coastline`**

   Vertical coastline from `(0.5, 0)` to `(0.5, 1)` (direction +Y → right
   side is +X, so the right half of the unit bbox is sea). Bbox is the unit
   square `[0,1] × [0,1]` in a flat metric CRS.

   Asserts:
   - One sea polygon returned.
   - Sea polygon `contains(Point(0.75, 0.5))` (right half).
   - Sea polygon does NOT contain `Point(0.25, 0.5)` (left half).

2. **`test_sea_classification_island_loop`**

   Closed-loop coastline: square with corners `(0.4,0.4) → (0.6,0.4) →
   (0.6,0.6) → (0.4,0.6) → (0.4,0.4)`. This winding is counter-clockwise,
   which per OSM convention means **sea on the right = exterior**.

   Asserts:
   - At least one sea polygon returned.
   - Combined sea geometry contains `Point(0.1, 0.1)` (outside the loop).
   - Combined sea geometry does NOT contain `Point(0.5, 0.5)` (inside the
     loop, i.e. land).

3. **`test_no_coastlines_returns_empty`**

   `_compute_sea_polygons(None, bbox, crs)` → `[]`.
   `_compute_sea_polygons(empty_gdf, bbox, crs)` → `[]`.

These tests construct GeoDataFrames in-memory with a dummy projected CRS
(e.g. `EPSG:3857`) and a unit bbox. No OSMnx call.

`_fetch_coastlines` is not unit-tested (consistent with the existing
no-network policy for `fetch_graph` / `fetch_features`).

## Manual verification

Out of scope for the spec but planned post-implementation:

- Run CLI: `python create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean --show-sea -d 4000` → confirm Adriatic visible.
- Run CLI without flag: same command minus `--show-sea` → byte-for-byte identical to current output (no Adriatic).
- Run CLI for an inland city: `python create_map_poster.py -c "Vienna" -C "Austria" --show-sea` → no warnings, no visual difference from current output.

## Changelog

`CHANGELOG.md`, under `[Unreleased] - Community Contributions` → `Added`:

```
- **Open sea/ocean rendering** - `--show-sea` flag renders the open
  sea for coastal locations using the theme's water colour. Uses
  OSM `natural=coastline` data and the OSM left-land/right-sea
  convention. Off by default; existing behaviour unchanged.
```

## Out of scope (future work)

- Land/sea boundaries that wrap across the antimeridian.
- Coastline data quality issues in specific regions (broken topology,
  unclosed loops crossing the bbox edge in unusual ways) — fall back to
  no-sea via the broad try/except, future work could log the specific
  failure mode.
- Caching the polygonized sea between renders of the same area (OSMnx
  caches the coastline fetch itself; the polygonize step is fast).
- A separate `sea` colour key in the theme schema (decided against; may
  revisit if a user requests it).
