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
# Output: dist/MapToPoster.exe (~110 MB)
```

## Architecture

**Entry points:**
- `create_map_poster.py` — CLI + core rendering engine. `create_poster()` is the main function.
- `maptoposter_gui.py` — CustomTkinter desktop GUI. Calls the engine via **subprocess** (non-blocking, with threaded output capture).
- `streamlit_app.py` — Web interface alternative.
- `stl_generator.py` — Converts a generated map into a 3D-printable STL relief.

**Shared modules:**
- `road_categories.py` — OSM highway tag → road tier classification. Used by both the engine and STL generator.
- `font_management.py` — Google Fonts download + local Roboto fallback, with module-level cache.
- `lat_lon_parser.py` — Parses coordinate strings in many formats (decimal, DMS, cardinal directions).

**Data flow:**
1. Geocode city name → lat/lon via Nominatim
2. Fetch OSM graph + features (water, parks) via OSMnx — cached as JSON in `~/.cache/maptoposter/` (or `MAPTOPOSTER_CACHE_DIR`)
3. Load theme from `themes/<name>.json`
4. Load fonts
5. Render layers with matplotlib: background → water/parks → roads (by hierarchy) → gradient fade → text labels
6. Save PNG/SVG/PDF to `posters/`

**Themes:** 37 JSON files in `themes/`. Schema has `bg`, `text`, `gradient_color`, `water`, `parks`, and per-road-tier color keys (`road_motorway`, `road_primary`, `road_secondary`, `road_tertiary`, `road_residential`, `road_default`).

**GUI settings** persist to `gui_settings.json` (recent cities, presets, favorites, last-used form values).

**EXE packaging:** `build_exe.py` uses PyInstaller with hidden imports for all geospatial libs and bundles `themes/`, `fonts/`, and the `customtkinter` asset tree. The `MapToPoster.spec` file is the generated spec. **Always run via `.venv/Scripts/python.exe build_exe.py`** — using any other Python (e.g. a uv temp env) causes Shapely DLL path mismatches that break the EXE at runtime.

## Key constraints

- NetworkX graphs are **not** cached (not JSON-serializable) — OSMnx's internal cache handles network data.
- `create_poster()` receives `theme` as an explicit dict parameter — no global theme state.
- Feature toggles (`no_roads`, `no_water`, `no_parks`) are explicit bool params, not globals.
- The GUI never calls engine functions directly — always via `subprocess` to keep the GUI responsive.
- Tests in `test_mapstudio.py` cover only pure functions (no network calls, no GUI, no OSM downloads).
