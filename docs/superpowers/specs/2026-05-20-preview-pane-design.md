# Live preview pane in the desktop GUI

**Date:** 2026-05-20
**Status:** Approved, pending spec review

## Problem

Users have to commit to a full poster generation (30–300 seconds + OSM fetch + matplotlib render) to see what a theme looks like on their location. Switching between 36 themes to find one that suits a city is impractical without a preview.

The user already has a mental model: a small thumbnail in the OUTPUT column of the GUI that shows the most-recently-generated location, re-renders instantly when the theme dropdown changes, and is updated to reflect the new location after each full generation. The thumbnail survives app restart.

## Goals

1. A small preview pane in column 3 (OUTPUT) of the desktop GUI showing a rendered thumbnail of a cached location.
2. Theme dropdown changes trigger a re-render of the cached location with the new theme, in well under 2 seconds, on a worker thread (no GUI freeze).
3. Successful poster generations atomically replace the cache file with the just-rendered location's data, then refresh the preview.
4. Cache survives app restart — preview is alive immediately on next launch.
5. First-launch / missing-cache state shows a placeholder ("Generate a poster to see preview") instead of an error or a blank frame.
6. No new runtime dependencies — uses geopandas/shapely/matplotlib/PIL that are already required.

## Non-goals

- Live updating the preview when feature toggles (sea, wetlands, religious, historic) or radius or dimensions change. Preview reflects cached layers + current theme only. Other settings update the preview only after the next full generation.
- Interactive zoom/pan in the preview.
- Multiple cached locations / a preview history.
- A preview for STL output. STL renders go through a different path; preview applies to raster/vector posters only.
- Auto-generating a default cache on first launch.

## Approach

### Cache format

Cache lives under `<base_dir>/preview_cache/`:

- `preview.gpkg` — GeoPackage with up to seven layers, each layer being a GeoDataFrame. Layers that weren't part of the source generation (e.g. `sea` if `--show-sea` was off) are simply absent from the file.

  | Layer name | Source | Notes |
  |---|---|---|
  | `roads` | `ox.graph_to_gdfs(g_proj, nodes=False)` | Sidesteps NetworkX serialization. Per-edge `highway` column preserved. |
  | `water` | Already-projected `water_polys` | Polygon/MultiPolygon only |
  | `parks` | `parks_polys` | |
  | `wetlands` | `wetlands_polys` | |
  | `religious` | `religious_polys` | |
  | `historic` | `historic_polys` | |
  | `sea` | `gpd.GeoDataFrame(geometry=sea_polys, crs=target_crs)` | shapely Polygons wrapped into a GDF |

- `preview.json` — small metadata sidecar:

  ```json
  {
    "version": 1,
    "city": "Koper",
    "country": "Slovenia",
    "center": [45.5479864, 13.7304781],
    "compensated_dist": 5000.0,
    "crop_xlim": [397150.74544764485, 404650.74544764485],
    "crop_ylim": [5039611.453483702, 5049611.453483702],
    "target_crs": "EPSG:32633",
    "width": 12,
    "height": 16
  }
  ```

  `version: 1` is checked at load time. If the loaded version is newer than the app expects, the cache is treated as missing (placeholder shown) and a warning is logged.

- Two-step write, JSON last: GeoPackage written first to `preview.gpkg.tmp` then `os.replace()`'d to `preview.gpkg`. JSON written second to `preview.json.tmp` then `os.replace()`'d to `preview.json`. Both individual files are atomic via the tmp-then-rename pattern.

  Order is deliberate: if anything fails during the gpkg write, no JSON is written and the loader sees an incomplete cache (missing JSON → treat as missing, show placeholder). The remaining narrow window — gpkg succeeds, JSON write fails — leaves a stale JSON with a fresh gpkg. The loader's existing `version` check catches schema-incompatible cases; mismatched-but-loadable-and-valid is functionally fine (preview renders with the older metadata for one cycle until the next successful generation overwrites both).

### Cache writer

Two execution paths in the GUI need to populate the cache.

**Frozen-EXE / direct-call path (`_run_direct`):** the GUI imports `create_poster()` directly and has in-memory access to the pipeline's intermediate GDFs and projected graph. The GUI calls a new helper `_save_preview_cache(cache_dir, city, country, point, compensated_dist, crop_xlim, crop_ylim, g_proj, water_polys, parks_polys, wetlands_polys, religious_polys, historic_polys, sea_polys, width, height)` at the end of a successful generation.

But `_run_direct` doesn't currently have access to all those intermediates — it just calls `create_poster()` which renders and saves the PNG/SVG/PDF internally. To make the cache writer work, we introduce an optional `cache_dir: Optional[str] = None` parameter on `create_poster()`. When set, the function calls a new internal helper `_save_preview_cache(cache_dir, ...)` right before returning, passing the already-computed intermediates.

This way, the cache-write logic lives in `create_map_poster.py` (next to where the data is produced), the GUI just passes the cache directory, and both execution paths benefit identically.

**Script-mode / subprocess path (`_run_subprocess`):** the subprocess invocation needs to opt into cache-writing too. Add a new CLI flag `--write-preview-cache <DIR>` to `create_map_poster.py`. The GUI's `_build_subprocess_cmd` appends `--write-preview-cache <cache_dir>` unconditionally in dev mode.

The CLI flag is documented as GUI-only infrastructure in its help text. It's not part of the upstream PR target (this whole feature is GUI-only).

### Cache reader

New helper `_load_preview_cache(cache_dir) -> Optional[PreviewCache]` in a new module `preview_cache.py` (so both the GUI and any tests can import it cleanly).

`PreviewCache` is a small dataclass:

```python
@dataclass
class PreviewCache:
    metadata: dict          # contents of preview.json
    roads: GeoDataFrame
    water: Optional[GeoDataFrame]
    parks: Optional[GeoDataFrame]
    wetlands: Optional[GeoDataFrame]
    religious: Optional[GeoDataFrame]
    historic: Optional[GeoDataFrame]
    sea: Optional[GeoDataFrame]
```

Behaviour:
- Missing directory or files → return `None` (caller shows placeholder)
- JSON parse error → log warning, return `None`
- GeoPackage read error → log warning, return `None`
- `version` newer than expected → log warning, return `None`

### Preview renderer

New helper `_render_preview(cache: PreviewCache, theme: dict, width_px: int, height_px: int) -> PIL.Image.Image` in `preview_cache.py`.

Renders the cached layers using matplotlib, just like the full pipeline does, but at thumbnail size and skipping expensive niceties:

1. Build a matplotlib figure sized to `(width_px, height_px)` at 72 DPI
2. `ax.set_facecolor(theme['bg'])`
3. For each present GDF, plot it at the same zorder as the full pipeline:
   - `sea` at 0.4 with `theme['water']`
   - `water` at 0.5 with `theme['water']`
   - `wetlands` at 0.6 with `theme['water']`
   - `parks` at 0.8 with `theme['parks']`
   - `religious` and `historic` at 1.5 with `theme.get('landmark', theme.get('text', '#444444'))`
   - `roads` at 2.0 with per-edge color/width via `road_categories.get_color/get_width`
4. Apply `crop_xlim` / `crop_ylim` from the metadata (so the preview shows exactly the cropped area, not the data bbox)
5. Apply the same top + bottom gradient fade as the full pipeline (looks correct at thumbnail size; tiny enough to be subtle)
6. **Skip text labels** (city name, coordinates) — unreadable at 180×240 and just adds visual noise
7. Save the figure to a `BytesIO`, open as PIL Image, return

### GUI changes

New widget in column 3 (OUTPUT), placed at the bottom (below the format-specific frame):

```python
self.preview_frame = ctk.CTkFrame(col3, fg_color="gray15", corner_radius=6, height=260)
self.preview_frame.pack(fill="x", padx=15, pady=(10, 15))
self.preview_label = ctk.CTkLabel(
    self.preview_frame, text="", anchor="center",
    width=180, height=240,
)
self.preview_label.pack(padx=10, pady=10)
self._preview_image_handle: Optional[ctk.CTkImage] = None
self._preview_render_thread: Optional[threading.Thread] = None
self._preview_render_token: int = 0
self._preview_cache: Optional[PreviewCache] = None
```

The `_preview_render_token` is a monotonic counter; each render schedules itself with the current token and aborts before publishing if `self._preview_render_token` has advanced. This is the "cancel stale render" mechanism.

Wiring:

- `__init__`: after `self.setup_ui()`, call `self._load_and_render_preview()`. If cache missing, the placeholder is shown.
- Theme dropdown's `command` (currently `self._on_theme_change`): extend to call `self._render_preview_async()` after the existing description-label update.
- `_run_direct` and `_run_subprocess`: on successful completion, reload the cache and re-render.

### Render trigger and concurrency

`_render_preview_async()` does:

1. If `self._preview_cache is None`: show placeholder text, return.
2. Increment `self._preview_render_token`. Capture the new value as `token`.
3. Spawn a daemon thread running `_render_worker(token, self._preview_cache, current_theme)`.

`_render_worker` does:

1. Render the PIL image (slow part, off-GUI-thread).
2. If `self._preview_render_token != token`: another render started after us, drop the result.
3. Otherwise, schedule a GUI-thread update via `self.after(0, lambda: self._publish_preview(image))`.

`_publish_preview(image)` runs on the GUI thread and updates the label.

### Placeholder

When `self._preview_cache is None`, the label shows a centred text in a muted colour:

```
Generate a poster
to see preview
```

The text and colour come from the current theme's `text` and `bg` so the placeholder still looks intentional after a theme change.

### Cache directory location

`<base_dir>/preview_cache/` next to the existing `posters/` and `themes/` directories.

In script mode `base_dir` is `os.path.dirname(__file__)`. In frozen EXE mode it's `os.path.dirname(sys.executable)`. Both paths are computed by the existing code (`BASE_DIR` in `create_map_poster.py`, `self.base_path` in the GUI).

### Cleanup on uninstall

Not handled. The cache is small (~1-5 MB) and lives in the app's own directory, so users uninstalling by deleting the folder remove it implicitly.

## Components

### `preview_cache.py` (NEW module)

Top-level functions:

- `save_preview_cache(cache_dir: str, *, metadata: dict, roads: GeoDataFrame, water: Optional[GeoDataFrame], parks: Optional[GeoDataFrame], wetlands: Optional[GeoDataFrame], religious: Optional[GeoDataFrame], historic: Optional[GeoDataFrame], sea_polys: Optional[list], target_crs: Any) -> None` — atomic write of GeoPackage + JSON sidecar.
- `load_preview_cache(cache_dir: str) -> Optional[PreviewCache]` — load and validate.
- `render_preview(cache: PreviewCache, theme: dict, width_px: int, height_px: int) -> PIL.Image.Image` — render to a PIL image.

`PreviewCache` dataclass as defined above.

### `create_map_poster.py` changes

- Import `from preview_cache import save_preview_cache` (lazy import inside the cache-write block to keep CLI startup fast if anyone uses `--list-themes` etc.)
- New parameter `write_preview_cache: Optional[str] = None` on `create_poster()`.
- New helper `_save_preview_cache_internal(...)` that gathers the local intermediates and calls `save_preview_cache`.
- Cache-write happens right before `create_poster()` returns successfully — never on the STL path (preview not supported for STL).
- New CLI argument `--write-preview-cache <DIR>` whose help text says it's GUI-only infrastructure.
- `__main__` passes `args.write_preview_cache` into the `create_poster(` call.

### `maptoposter_gui.py` changes

- Import `from preview_cache import load_preview_cache, render_preview, PreviewCache`.
- In `__init__`: add `self._preview_cache`, `self._preview_render_token`, `self._preview_image_handle` state.
- In `setup_ui`: add the preview frame at the bottom of col3.
- New methods `_load_and_render_preview()`, `_render_preview_async()`, `_render_worker()`, `_publish_preview()`, `_show_preview_placeholder()`.
- `_on_theme_change`: call `self._render_preview_async()` after the existing description update.
- `_build_subprocess_cmd`: append `["--write-preview-cache", str(self._preview_cache_dir)]`.
- `_run_direct`: pass `write_preview_cache=str(self._preview_cache_dir)` to `create_poster(...)`. After the call completes, schedule `self._load_and_render_preview()` on the GUI thread.
- `_run_subprocess`: on exit code 0, schedule `self._load_and_render_preview()` on the GUI thread.

### Helper property in GUI

```python
@property
def _preview_cache_dir(self) -> Path:
    return self.base_path / "preview_cache"
```

## Data flow

```
[Full generation]
  create_poster(write_preview_cache=...)
    ↓ (existing pipeline runs as before)
    ↓ (after PNG/SVG/PDF write, before return)
    _save_preview_cache_internal
      ↓
    preview_cache.save_preview_cache
      ↓
    <base>/preview_cache/preview.gpkg + preview.json (atomic)

[Theme change in GUI]
  _on_theme_change(theme_name)
    → existing description update
    → _render_preview_async()
        ↓ increment token, spawn thread
      _render_worker(token, cache, theme)
        ↓ matplotlib → PIL.Image
        ↓ check token still current
      self.after(0, _publish_preview)
        ↓
      self.preview_label.configure(image=...)

[App startup]
  __init__
    → setup_ui (preview frame created empty)
    → _load_and_render_preview()
        ↓
      load_preview_cache(<base>/preview_cache)
        ↓ Optional[PreviewCache]
      if None: _show_preview_placeholder()
      else: _render_preview_async()
```

## Edge cases

| Case | Behaviour |
|---|---|
| First launch, no cache | Placeholder text shown ("Generate a poster to see preview") |
| Cache file present but JSON corrupt | Log warning, treat as missing, show placeholder |
| Cache file present but GeoPackage corrupt | Log warning, treat as missing, show placeholder |
| Cache version > 1 (future) | Log warning, treat as missing, show placeholder |
| User changes theme while previous render still in-flight | Stale render is dropped via token check; new render starts immediately |
| User triggers a generation while a theme-change render is in-flight | Generation proceeds normally; when it finishes, the cache is rewritten and a fresh render kicks off with the new cache + current theme |
| Generation fails partway through | `_save_preview_cache_internal` is only called on success; cache is unchanged |
| STL generation | `write_preview_cache` is ignored on the STL path — preview cache logic only runs for raster/vector formats |
| Theme dropdown set to a theme without `landmark` key (e.g. user's custom theme) | Render uses the existing fallback chain `landmark → text → #444444`. No special handling. |
| Very large city (lots of road segments) | Render slows but stays sub-2s for typical 5-15km radii. No explicit budget — if a user picks 50km, the preview takes longer; not a problem since theme switching is on a worker thread. |
| Window resized | Preview frame stays a fixed 180×240 (or aspect-adjusted). No reflow. |

## Testing

Two pure-function unit tests in `test_mapstudio.py`:

### `test_preview_cache_roundtrip`

Build small synthetic GDFs (a single LineString for roads, one Polygon for water) and metadata, save via `save_preview_cache`, load via `load_preview_cache`, assert:
- Returned `PreviewCache` is not None
- `roads` GDF has the same number of rows as input
- `water` GDF has the same number of rows as input
- `parks` is None (not supplied)
- Metadata dict matches the input

### `test_preview_cache_handles_corrupt_file`

Write garbage bytes to `preview.gpkg`, write valid JSON to `preview.json`, assert:
- `load_preview_cache` returns `None`
- No exception raised
- Warning logged

Similar test with corrupt JSON, valid gpkg.

No GUI tests, no render tests (matplotlib side-effect; matches existing policy of no GUI/render unit tests).

## Manual verification

- Launch app fresh (delete `preview_cache/` first). Placeholder visible in col 3.
- Generate any poster. After completion, preview shows the generated location.
- Change theme dropdown. Preview re-renders within ~2s with the new theme.
- Restart app. Preview is alive immediately with the last-generated location.
- Generate a different city. Preview updates.
- Toggle a feature switch (e.g. Ocean off), DO NOT generate. Preview stays the same. Confirm intent: preview reflects cached, not current, layers.
- Run CLI with `--write-preview-cache <some_dir>` and confirm the gpkg + json appear in `<some_dir>/`.

## Out of scope (future work)

- Multiple preview slots / preview history
- Click-to-zoom preview into a larger window
- Animated transition when the preview changes
- A "Discard cache" button in the GUI
- Auto-generation of a default cache on first launch
- Preview for STL output

## PR strategy

This feature is GUI-only (`preview_cache.py` is new but only used by the GUI; the `--write-preview-cache` flag in `create_map_poster.py` is GUI-infrastructure noise from upstream's perspective).

- Branch off latest `Desktop` (already done — on `feature/preview-pane`)
- PR to your fork's `Desktop` first for visual verification
- Then cross-fork PR to `cyanidesugar/maptoposterwebapp`
- **Skip originalankur** — the upstream CLI repo has no GUI, so the preview pane has no analogue there. The `--write-preview-cache` CLI flag alone isn't worth a separate PR.
