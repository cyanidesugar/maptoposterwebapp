# Open Sea Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `--show-sea` flag (+ GUI toggle) to render the open sea for coastal map posters using OSM `natural=coastline` data and shapely polygonization.

**Architecture:** Fetch coastline LineStrings via OSMnx, project them to the graph CRS, clip to the visible bbox, polygonize the union of coastlines + bbox boundary, and classify each resulting polygon as land or sea using the OSM left-land/right-sea convention. Render sea polygons with `theme['water']` at `zorder=0.4`, below inland water (`0.5`).

**Tech Stack:** Python 3.13, OSMnx 2.0, shapely 2.1, geopandas 1.1, matplotlib 3.10, customtkinter (GUI).

**Spec:** `docs/superpowers/specs/2026-05-20-sea-rendering-design.md`

**Repo root for this plan:** `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\` (all paths below are relative to this directory).

---

## File Structure

**Modified files (no new files):**

| File | Responsibility for this feature |
|---|---|
| `create_map_poster.py` | New helpers `_fetch_coastlines`, `_compute_sea_polygons`, `_polygon_is_sea`, `_render_sea`. New `show_sea` parameter on `create_poster()`. New `--show-sea` CLI argument. |
| `maptoposter_gui.py` | New "Ocean" toggle switch. Plumbing through `_collect_form_settings`, `_apply_settings_to_form`, `_collect_generation_params`, `_build_subprocess_cmd`, `_run_direct`. |
| `test_mapstudio.py` | New `TestComputeSeaPolygons` test class with 4 tests (None, empty, simple coastline, island loop). |
| `CHANGELOG.md` | New entry under `[Unreleased] - Community Contributions` → `Added`. |

**No files split.** `create_map_poster.py` is already large (~1180 lines) but the new code is ~80 lines and lives naturally next to the existing fetch/render helpers — splitting it now is unrelated to this feature.

---

## Task 1: Sea polygon classification core

**Files:**
- Modify: `create_map_poster.py` (add helpers near the other `_render_*` / `_project_features` helpers, around line 545)
- Modify: `test_mapstudio.py` (append new test class at end)

This is the only TDD task — the rest is wiring around it.

### Step 1.1: Write the failing test class

- [ ] Append to `test_mapstudio.py`:

```python
# ===========================================================================
# create_map_poster — _compute_sea_polygons (sea classification)
# ===========================================================================

import geopandas as gpd  # noqa: E402
from shapely.geometry import LineString, box, Point  # noqa: E402


class TestComputeSeaPolygons:
    """Tests for _compute_sea_polygons in create_map_poster.

    These tests use a 1000m x 1000m bbox in EPSG:3857 so the function's
    internal 1.0 m probe offset is small relative to the bbox.
    """

    _CRS = "EPSG:3857"

    def _make_gdf(self, lines):
        return gpd.GeoDataFrame(geometry=lines, crs=self._CRS)

    def test_none_input_returns_empty_list(self):
        bbox = box(0, 0, 1000, 1000)
        assert cmp._compute_sea_polygons(None, bbox, self._CRS) == []

    def test_empty_gdf_returns_empty_list(self):
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs=self._CRS)
        bbox = box(0, 0, 1000, 1000)
        assert cmp._compute_sea_polygons(empty_gdf, bbox, self._CRS) == []

    def test_vertical_coastline_right_half_is_sea(self):
        """Coastline at x=500 going +Y -> right side (+X) is sea."""
        coastline = LineString([(500, 0), (500, 1000)])
        gdf = self._make_gdf([coastline])
        bbox = box(0, 0, 1000, 1000)

        result = cmp._compute_sea_polygons(gdf, bbox, self._CRS)

        assert len(result) >= 1, "Expected at least one sea polygon"
        sea_union = gpd.GeoSeries(result).unary_union
        assert sea_union.contains(Point(750, 500)), (
            "Right half (x=750) should be classified as sea"
        )
        assert not sea_union.contains(Point(250, 500)), (
            "Left half (x=250) should be land, not sea"
        )

    def test_island_loop_exterior_is_sea(self):
        """Counter-clockwise closed loop -> sea is exterior (right of direction)."""
        # CCW square: (400,400) -> (600,400) -> (600,600) -> (400,600) -> back
        # Segment 1 direction +X, right is -Y (exterior)
        # Segment 2 direction +Y, right is +X (exterior)
        # ...so exterior is sea per OSM convention.
        loop = LineString([
            (400, 400), (600, 400), (600, 600), (400, 600), (400, 400),
        ])
        gdf = self._make_gdf([loop])
        bbox = box(0, 0, 1000, 1000)

        result = cmp._compute_sea_polygons(gdf, bbox, self._CRS)

        assert len(result) >= 1, "Expected at least one sea polygon"
        sea_union = gpd.GeoSeries(result).unary_union
        assert sea_union.contains(Point(100, 100)), (
            "Outside the loop should be sea"
        )
        assert not sea_union.contains(Point(500, 500)), (
            "Inside the loop should be land, not sea"
        )
```

### Step 1.2: Run tests to verify they fail

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest maptoposterwebapp\test_mapstudio.py::TestComputeSeaPolygons -v
```

Expected: 4 failures with `AttributeError: module 'create_map_poster' has no attribute '_compute_sea_polygons'`.

### Step 1.3: Implement the helpers

- [ ] In `create_map_poster.py`, locate the existing `from shapely.geometry import Point` import (around line 70) and replace it with:

```python
from shapely.geometry import Point, box
from shapely.ops import polygonize, unary_union
```

- [ ] In `create_map_poster.py`, locate `from geopandas import GeoDataFrame` (around line 64) and replace with:

```python
from geopandas import GeoDataFrame, GeoSeries
```

- [ ] In `create_map_poster.py`, add these three functions immediately AFTER `_project_features` (search for `def _project_features` then place the new code right before `def _render_water`):

```python
def _polygon_is_sea(polygon: Any, coastlines: list) -> bool:
    """Determine whether a polygon lies on the sea side of any bounding coastline.

    OSM convention: when walking a coastline way in its native direction,
    land is on the LEFT and sea is on the RIGHT. For each coastline segment
    that touches this polygon's boundary, we offset the segment midpoint by
    1 m to the right (perpendicular direction (dy, -dx) / length) and check
    if the offset point is inside the polygon. If yes, the polygon is sea.

    Args:
        polygon: Candidate shapely Polygon to classify.
        coastlines: List of clipped shapely LineStrings (in the same CRS).

    Returns:
        True if any coastline segment classifies the polygon as sea.
    """
    poly_boundary = polygon.boundary
    for line in coastlines:
        if not poly_boundary.intersects(line):
            continue
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            dx = x1 - x0
            dy = y1 - y0
            length = (dx * dx + dy * dy) ** 0.5
            if length == 0:
                continue
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            probe_x = mid_x + (dy / length) * 1.0
            probe_y = mid_y - (dx / length) * 1.0
            if polygon.contains(Point(probe_x, probe_y)):
                return True
    return False


def _compute_sea_polygons(
    coastlines: Optional[GeoDataFrame],
    bbox_polygon: Any,
    target_crs: Any,
) -> list:
    """Partition the visible bbox into sea polygons using OSM coastline data.

    Args:
        coastlines: GeoDataFrame from `_fetch_coastlines`, may be None/empty.
        bbox_polygon: shapely Polygon describing the visible map area, in
            ``target_crs``.
        target_crs: CRS to project coastlines into (same CRS as the projected
            graph used for rendering).

    Returns:
        List of shapely Polygons classified as sea. Empty if no coastlines
        intersect the bbox or any error occurs.
    """
    if coastlines is None or coastlines.empty:
        return []
    try:
        lines = coastlines[coastlines.geometry.type.isin(
            ["LineString", "MultiLineString"]
        )]
        if lines.empty:
            return []
        if lines.crs is not None and str(lines.crs) != str(target_crs):
            lines = lines.to_crs(target_crs)

        clipped: list = []
        for geom in lines.geometry:
            if geom is None or geom.is_empty:
                continue
            clipped_geom = geom.intersection(bbox_polygon)
            if clipped_geom.is_empty:
                continue
            if clipped_geom.geom_type == "LineString":
                clipped.append(clipped_geom)
            elif clipped_geom.geom_type == "MultiLineString":
                clipped.extend(list(clipped_geom.geoms))

        if not clipped:
            return []

        merged = unary_union(clipped + [bbox_polygon.boundary])
        polygons = list(polygonize(merged))

        return [poly for poly in polygons if _polygon_is_sea(poly, clipped)]
    except Exception as e:
        logger.warning("Sea polygon computation failed: %s", e)
        return []
```

### Step 1.4: Run tests to verify they pass

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest maptoposterwebapp\test_mapstudio.py::TestComputeSeaPolygons -v
```

Expected: 4 passes.

### Step 1.5: Run the full test suite to confirm nothing else broke

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest maptoposterwebapp\test_mapstudio.py -v
```

Expected: all tests pass (existing + 4 new).

### Step 1.6: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add create_map_poster.py test_mapstudio.py
git commit -m "feat: add _compute_sea_polygons helper for sea classification"
```

---

## Task 2: Coastline fetch helper

**Files:**
- Modify: `create_map_poster.py` (add after `fetch_features`, around line 470)

### Step 2.1: Add the fetch helper

- [ ] In `create_map_poster.py`, locate the existing `def fetch_features` (the function that wraps `ox.features_from_point`). Immediately AFTER it, add:

```python
def _fetch_coastlines(
    point: tuple[float, float],
    dist: float,
) -> Optional[GeoDataFrame]:
    """Fetch OSM coastline LineStrings around a point.

    Coastlines are stored in OSM as ``natural=coastline`` ways (LineStrings,
    not polygons). The sea is reconstructed by polygonising them; see
    ``_compute_sea_polygons``.
    """
    try:
        return ox.features_from_point(
            point, tags={"natural": "coastline"}, dist=dist,
        )
    except Exception as e:
        logger.warning("OSMnx error while fetching coastlines: %s", e)
        return None
```

### Step 2.2: Verify it loads without import errors

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -c "import create_map_poster; print(create_map_poster._fetch_coastlines)"
```

Working directory must be `maptoposterwebapp\`:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe -c "import create_map_poster; print(create_map_poster._fetch_coastlines)"
```

Expected: prints `<function _fetch_coastlines at 0x...>`.

### Step 2.3: Commit

- [ ] Run:

```powershell
git add create_map_poster.py
git commit -m "feat: add _fetch_coastlines helper"
```

---

## Task 3: Sea render helper

**Files:**
- Modify: `create_map_poster.py` (add next to `_render_water`)

### Step 3.1: Add the render helper

- [ ] In `create_map_poster.py`, locate `def _render_water` and insert this function immediately BEFORE it:

```python
def _render_sea(
    ax: plt.Axes,
    sea_polygons: list,
    theme: dict[str, str],
    target_crs: Any,
) -> None:
    """Render sea polygons on the map axes.

    Drawn at ``zorder=0.4`` so inland water (``0.5``) paints cleanly on top.
    Both use ``theme['water']`` so the result is visually seamless.
    """
    if not sea_polygons:
        return
    GeoSeries(sea_polygons, crs=target_crs).plot(
        ax=ax, facecolor=theme["water"], edgecolor="none", zorder=0.4,
    )
```

### Step 3.2: Verify it loads

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe -c "import create_map_poster; print(create_map_poster._render_sea)"
```

Expected: prints `<function _render_sea at 0x...>`.

### Step 3.3: Commit

- [ ] Run:

```powershell
git add create_map_poster.py
git commit -m "feat: add _render_sea helper"
```

---

## Task 4: Wire `show_sea` into `create_poster`

**Files:**
- Modify: `create_map_poster.py` — `create_poster()` signature, docstring, and body.

### Step 4.1: Update the function signature

- [ ] In `create_map_poster.py`, find the `create_poster(` definition. Locate the `no_parks: bool = False,` line in the parameter list and INSERT directly after it:

```python
    show_sea: bool = False,
```

### Step 4.2: Update the docstring

- [ ] In the same function's docstring, find the `no_parks: If True, hide park features` line and insert directly after it:

```
        show_sea: If True, render open sea/ocean using OSM coastline data
            (off by default; ignored when no_water is True)
```

### Step 4.3: Add the fetch + compute block

- [ ] In `create_poster`, locate the existing block:

```python
    # Determine cropping limits
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)
```

Insert IMMEDIATELY AFTER it:

```python
    # Sea polygons (opt-in via show_sea; honours no_water)
    sea_polys: list = []
    if show_sea and not no_water:
        coastlines = _fetch_coastlines(point, compensated_dist)
        bbox_polygon = box(
            crop_xlim[0], crop_ylim[0], crop_xlim[1], crop_ylim[1],
        )
        sea_polys = _compute_sea_polygons(
            coastlines, bbox_polygon, g_proj.graph["crs"],
        )
```

### Step 4.4: Render sea BEFORE inland water

- [ ] In `create_poster`, locate this block (just below where you inserted in 4.3):

```python
    if not no_water:
        _render_water(ax, water_polys, theme)
```

Replace it with:

```python
    if sea_polys:
        _render_sea(ax, sea_polys, theme, g_proj.graph["crs"])

    if not no_water:
        _render_water(ax, water_polys, theme)
```

Note: the existing `_render_water` block in the file is BEFORE the crop-limits computation (around line 820). The sea block must run AFTER crop limits are known but BEFORE `_render_water` paints. To do that cleanly without restructuring, also MOVE the existing `if not no_water: _render_water(...)` block (and the adjacent `if not no_parks: _render_parks(...)` block) to come AFTER the new sea block.

Concretely, the section around line 815–824 currently reads:

```python
    # Render layers
    water_polys = _project_features(water, g_proj)
    parks_polys = _project_features(parks, g_proj)

    if not no_water:
        _render_water(ax, water_polys, theme)

    if not no_parks:
        _render_parks(ax, parks_polys, theme)

    # Determine cropping limits
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)
```

Reorder it to:

```python
    # Project features (water/parks) to graph CRS
    water_polys = _project_features(water, g_proj)
    parks_polys = _project_features(parks, g_proj)

    # Determine cropping limits BEFORE rendering so we can build the sea bbox
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)

    # Sea polygons (opt-in via show_sea; honours no_water)
    sea_polys: list = []
    if show_sea and not no_water:
        coastlines = _fetch_coastlines(point, compensated_dist)
        bbox_polygon = box(
            crop_xlim[0], crop_ylim[0], crop_xlim[1], crop_ylim[1],
        )
        sea_polys = _compute_sea_polygons(
            coastlines, bbox_polygon, g_proj.graph["crs"],
        )

    # Render layers: sea (lowest), then inland water, then parks
    if sea_polys:
        _render_sea(ax, sea_polys, theme, g_proj.graph["crs"])

    if not no_water:
        _render_water(ax, water_polys, theme)

    if not no_parks:
        _render_parks(ax, parks_polys, theme)
```

The original block that called `get_crop_limits` further down (originally after the `_render_parks` block) is now redundant — delete that duplicate. Verify the file only computes `crop_xlim, crop_ylim` ONCE.

### Step 4.5: Run full test suite

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe -m pytest test_mapstudio.py -v
```

Expected: all tests pass.

### Step 4.6: Commit

- [ ] Run:

```powershell
git add create_map_poster.py
git commit -m "feat: wire show_sea into create_poster render pipeline"
```

---

## Task 5: CLI flag

**Files:**
- Modify: `create_map_poster.py` — argparse block and `create_poster` call in `__main__`.

### Step 5.1: Add the argparse argument

- [ ] In `create_map_poster.py`, find the existing block:

```python
    parser.add_argument('--no-parks', action='store_true',
                       help='Hide parks/green spaces from the map')
```

Insert IMMEDIATELY AFTER it:

```python
    parser.add_argument('--show-sea', action='store_true',
                       help='Render open sea/ocean for coastal locations (off by default)')
```

### Step 5.2: Pass it into `create_poster`

- [ ] In the `__main__` block, find the `create_poster(` call. Locate the existing kwarg `no_parks=args.no_parks,` and insert directly after it:

```python
                show_sea=args.show_sea,
```

### Step 5.3: Smoke-test the help output

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py --help
```

Expected: output contains `--show-sea` with the help text.

### Step 5.4: Commit

- [ ] Run:

```powershell
git add create_map_poster.py
git commit -m "feat: add --show-sea CLI flag"
```

---

## Task 6: GUI toggle

**Files:**
- Modify: `maptoposter_gui.py` — UI widget, settings collection/restore, subprocess command builder, direct-call path.

### Step 6.1: Add the switch widget

- [ ] In `maptoposter_gui.py`, find the block:

```python
        self.park_sw = ctk.CTkSwitch(toggle_frame, text=" Parks")
        self.park_sw.select()
        self.park_sw.pack(anchor="w", padx=10, pady=8)
```

Insert IMMEDIATELY AFTER it:

```python
        self.sea_sw = ctk.CTkSwitch(toggle_frame, text=" Ocean")
        self.sea_sw.pack(anchor="w", padx=10, pady=8)
```

(No `.select()` call — default is unselected = off, matching CLI default.)

### Step 6.2: Persist in `_collect_form_settings`

- [ ] In `maptoposter_gui.py`, find `_collect_form_settings`. Locate `"parks": self.park_sw.get(),` and insert directly after it:

```python
            "show_sea": self.sea_sw.get(),
```

### Step 6.3: Restore in `_apply_settings_to_form`

- [ ] In `_apply_settings_to_form`, find the loop:

```python
            for sw, key, default in [
                (self.text_sw, "text", True),
                (self.road_sw, "roads", True),
                (self.water_sw, "water", True),
                (self.park_sw, "parks", True),
            ]:
```

Replace it with:

```python
            for sw, key, default in [
                (self.text_sw, "text", True),
                (self.road_sw, "roads", True),
                (self.water_sw, "water", True),
                (self.park_sw, "parks", True),
                (self.sea_sw, "show_sea", False),
            ]:
```

### Step 6.4: Collect in `_collect_generation_params`

- [ ] In `_collect_generation_params`, find the existing block:

```python
        # Feature toggles
        params["no_text"] = not self.text_sw.get()
        params["no_roads"] = not self.road_sw.get()
        params["no_water"] = not self.water_sw.get()
        params["no_parks"] = not self.park_sw.get()
```

Insert IMMEDIATELY AFTER `params["no_parks"] = ...`:

```python
        params["show_sea"] = bool(self.sea_sw.get())
```

### Step 6.5: Propagate via subprocess cmd

- [ ] In `_build_subprocess_cmd`, find:

```python
        if params.get("no_parks"):
            cmd.append("--no-parks")
```

Insert IMMEDIATELY AFTER it:

```python
        if params.get("show_sea"):
            cmd.append("--show-sea")
```

### Step 6.6: Propagate via direct call (frozen EXE mode)

- [ ] In `_run_direct`, find the `create_poster(` call. Locate `no_parks=params.get("no_parks", False),` and insert directly after it:

```python
                    show_sea=params.get("show_sea", False),
```

### Step 6.7: Smoke-test the GUI launches

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe maptoposter_gui.py
```

Expected: the GUI window opens and the FEATURES column shows the new "Ocean" switch alongside Text/Roads/Water/Parks/All Themes. The Ocean switch should default to OFF (unfilled). Close the window without generating.

### Step 6.8: Commit

- [ ] Run:

```powershell
git add maptoposter_gui.py
git commit -m "feat: add Ocean toggle to GUI"
```

---

## Task 7: Changelog

**Files:**
- Modify: `CHANGELOG.md`.

### Step 7.1: Add the entry

- [ ] In `CHANGELOG.md`, find the section header:

```markdown
## [Unreleased] - Community Contributions

### Added
```

Insert a new bullet at the TOP of the existing `### Added` list under that header:

```markdown
- **Open sea/ocean rendering** - `--show-sea` flag renders the open sea for coastal locations using the theme's `water` colour. Uses OSM `natural=coastline` data and the OSM left-land/right-sea convention. Off by default; existing behaviour unchanged.
```

### Step 7.2: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add CHANGELOG.md
git commit -m "docs: changelog entry for --show-sea"
```

---

## Task 8: Manual verification

These checks confirm the feature actually works on real OSM data and that the default behaviour is unchanged. They are required before the PR is sent.

### Step 8.1: Verify default (no flag) for a coastal city is byte-identical to current behaviour

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean -d 4000
```

Expected: poster generated in `posters/`, Adriatic appears as theme background (blank, not water-coloured). This matches current behaviour. Open the file and confirm.

### Step 8.2: Verify `--show-sea` renders the Adriatic for Koper

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean -d 4000 --show-sea
```

Expected: poster generated, Adriatic now rendered with the `water` colour. Open the new file in `posters/` and visually confirm. Compare with the file from Step 8.1.

### Step 8.3: Verify inland city is unaffected by `--show-sea`

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Vienna" -C "Austria" --theme blueprint -d 8000 --show-sea
```

Expected: poster generated successfully, no warnings about coastline-related failures in the log, visual output looks like a normal Vienna poster (no spurious water fills, no errors).

### Step 8.4: Verify `--no-water --show-sea` hides the sea

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean -d 4000 --show-sea --no-water
```

Expected: poster generated, Adriatic NOT rendered (because `--no-water` overrides `--show-sea`). Same visual result as Step 8.1.

### Step 8.5: Verify the GUI toggle works

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe maptoposter_gui.py
```

In the GUI: City = "Koper", Country = "Slovenia", Theme = "ocean", Radius = 4000, turn on the Ocean toggle, click Generate.

Expected: poster generated with Adriatic visible. Generate again with the Ocean toggle off and confirm the Adriatic disappears.

### Step 8.6: Commit nothing (verification only)

No commit for this task — it's manual verification.

---

## Self-review notes (already applied to plan)

- Spec requires the bbox to be built from `crop_xlim`/`crop_ylim` AFTER `get_crop_limits` runs. The original `create_poster` ordering computes water/parks rendering BEFORE `get_crop_limits`, so Task 4 includes the necessary reorder.
- Spec requires the existing 1-metre probe offset, which is small relative to typical OSMnx UTM bboxes (tens of km) but would be too large for unit-sized test bboxes. Tests use 1000m × 1000m bboxes accordingly.
- `_render_water` uses geopandas `.plot()` on the GeoDataFrame; `_render_sea` uses geopandas `GeoSeries.plot()` for the same code path and to handle any holes from polygonize.
- Coastline reprojection uses `to_crs(target_crs)` rather than `ox.projection.project_gdf` so the result is guaranteed to match the graph's CRS (avoids potential UTM-zone mismatch latent in `_project_features`).
- The plan does not add a `--no-sea` separate flag — confirmed during brainstorming that `--no-water` semantics include sea.
