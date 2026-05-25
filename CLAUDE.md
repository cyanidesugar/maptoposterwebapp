# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the GUI
python maptoposter_gui.py

# Run the CLI
python create_map_poster.py "Tokyo" --theme midnight_blue --distance 3000

# Run tests
pytest test_mapstudio.py -v

# Run a single test class
pytest test_mapstudio.py::TestLatLonParse -v

# Build the standalone EXE — must use venv Python directly
.venv/Scripts/python.exe build_exe.py
# Output: dist/MapToPoster.exe (~118 MB as of v0.4.0)
```

## Architecture

**Entry points:**
- `create_map_poster.py` — CLI + core rendering engine. `create_poster()` is the main function.
- `maptoposter_gui.py` — CustomTkinter desktop GUI. When frozen, calls `_run_direct()` which imports `create_poster()` directly (no subprocess). In script mode, uses subprocess.
- `stl_generator.py` — Converts a generated map into a 3D-printable STL relief. Confirmed working (watertight mesh).

**Shared modules:**
- `road_categories.py` — OSM highway tag → road tier classification. Used by both the engine and STL generator.
- `font_management.py` — Google Fonts download + local Roboto fallback, with module-level cache.
- `lat_lon_parser.py` — Parses coordinate strings in many formats (decimal, DMS, cardinal directions).
- `preview_cache.py` — GeoPackage-backed cache (`preview.gpkg` + `preview.json`) for the GUI's live theme preview pane. `create_poster()` writes the cache when `write_preview_cache=<dir>` is passed (or `--write-preview-cache` on CLI); GUI re-renders thumbnails from it on theme change without touching OSM.

**Data flow:**
1. Geocode city name → lat/lon via Nominatim
2. Fetch OSM graph + features (water, parks) via OSMnx — cached as JSON in `~/.cache/maptoposter/` (or `MAPTOPOSTER_CACHE_DIR`)
3. Load theme from `themes/<name>.json`
4. Load fonts
5. Render layers with matplotlib: background → water/parks → roads (by hierarchy) → gradient fade → text labels
6. Save PNG/SVG/PDF to `posters/`

**Themes:** 36 JSON files in `themes/`. Schema has `bg`, `text`, `gradient_color`, `water`, `parks`, `landmark` (v0.4.0+, used by `--show-religious`/`--show-historic`), and per-road-tier color keys (`road_motorway`, `road_primary`, `road_secondary`, `road_tertiary`, `road_residential`, `road_default`). Custom themes without `landmark` fall back to `text` via `theme.get('landmark', theme.get('text', '#444444'))`.

**Feature toggles (opt-in, off by default, added in v0.4.0 PRs from @gabr42):** `--show-sea` (coastal ocean via OSM coastline polygonisation), `--show-wetlands` (OSM `natural=wetland`), `--show-religious` (places of worship), `--show-historic` (castles, ruins, monuments). All four exist as both CLI flags and GUI checkboxes; sea/wetlands render with theme `water` colour, religious/historic with `landmark`.

**GUI settings** persist to `gui_settings.json`. The Recent dropdown stores full location snapshots in `recent_locations` (mode + city + country + lat/lon + custom display overrides) — restoring an entry switches the input-mode radio and refills every field. Legacy `recent_cities` (list of "City, Country" strings) is auto-migrated on first load.

**EXE packaging:** `build_exe.py` uses PyInstaller and bundles `themes/`, `fonts/`, and the `customtkinter` asset tree. **Always run via `.venv/Scripts/python.exe build_exe.py`** — using any other Python causes Shapely DLL path mismatches. Output: `dist/MapToPoster.exe` (~118 MB as of v0.4.0).

**Distribution:** zip `dist/MapToPoster.exe` + `themes/` folder → `MapToPoster_release.zip`. The EXE reads themes from `<exe_dir>/themes/` at runtime (not from the PyInstaller temp dir), so themes must ship alongside the EXE.

**PyInstaller gotchas (hard-won):**
- `--clean` flag causes `PermissionError` on `build/MapToPoster/localpycs` — removed from build args.
- `customtkinter` requires `--add-data` (assets not found via hidden import alone).
- `trimesh` requires `--collect-all=trimesh` (not just `--hidden-import`).
- `pyogrio` requires `--collect-all=pyogrio` (GDAL DLLs + driver data; needed for `preview_cache.py`'s GeoPackage I/O).
- `preview_cache` is an explicit `--hidden-import` even though it's imported at the top of `maptoposter_gui.py` (defensive, matches the project-module pattern).
- matplotlib's PyInstaller hook overrides `--hidden-import` for backends and only bundles `Agg`. Fix: explicitly import `matplotlib.backends.backend_svg/pdf/agg` at the top of `create_map_poster.py` so static analysis picks them up before the hook runs. `--collect-submodules=matplotlib.backends` is also set as a fallback.

## Key constraints

- NetworkX graphs are **not** cached (not JSON-serializable) — OSMnx's internal cache handles network data.
- `create_poster()` receives `theme` as an explicit dict parameter — no global theme state.
- Feature toggles (`no_roads`, `no_water`, `no_parks`) are explicit bool params, not globals.
- In frozen EXE mode the GUI calls `_run_direct()` (direct import), not subprocess.
- Tests in `test_mapstudio.py` cover only pure functions (no network calls, no GUI, no OSM downloads).
- Default GitHub branch is `Desktop` (there is no `main`). Releases are published to `cyanidesugar/maptoposterwebapp`.
- `pip` is not in the venv (created by uv). To install packages: bootstrap with `python.exe -m ensurepip` then `python.exe -m pip install <pkg>`.
