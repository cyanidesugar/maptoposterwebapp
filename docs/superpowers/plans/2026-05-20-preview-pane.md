# Preview Pane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live preview pane to the desktop GUI that re-renders the most-recently-generated location with the currently selected theme, in well under 2 seconds, on a worker thread.

**Architecture:** New `preview_cache.py` module owns serialization (GeoPackage + JSON sidecar) and the preview-resolution renderer. `create_poster()` gains a `write_preview_cache` parameter (and a matching `--write-preview-cache` CLI flag) so both the direct-call GUI path and the subprocess path can populate the cache. GUI adds a preview widget at the bottom of column 3, plus theme-change wiring and a cancellable worker-thread render.

**Tech Stack:** Python 3.13, geopandas 1.1 (GeoPackage I/O), shapely 2.1, matplotlib 3.10 (Figure/FigureCanvasAgg for thread-safe rendering), PIL/Pillow 12 (image conversion), customtkinter (GUI image widget), pyogrio 0.12 (geopandas's GPKG driver, already a dependency).

**Spec:** `docs/superpowers/specs/2026-05-20-preview-pane-design.md`

**Repo root:** `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\`. Branch `feature/preview-pane` already checked out off `Desktop`.

---

## File Structure

**New file:**

| File | Responsibility |
|---|---|
| `preview_cache.py` | `PreviewCache` dataclass, `save_preview_cache`, `load_preview_cache`, `render_preview`. Self-contained module: GUI imports it for load+render; `create_map_poster.py` imports it only for save. |

**Modified files:**

| File | Responsibility |
|---|---|
| `create_map_poster.py` | New `write_preview_cache: Optional[str] = None` parameter on `create_poster()`. New `--write-preview-cache <DIR>` CLI flag. Cache-write call at end of successful generation (skipped for STL format). |
| `maptoposter_gui.py` | New preview widget in col3. New `_preview_cache_dir` property. New state attributes for cache + render token + image handle. New methods `_load_and_render_preview`, `_render_preview_async`, `_render_worker`, `_publish_preview`, `_show_preview_placeholder`. Wiring in `__init__`, `_on_theme_change`, `_build_subprocess_cmd`, `_run_direct`, `_run_subprocess`. |
| `test_mapstudio.py` | 3 new unit tests in a new `TestPreviewCache` class. |

---

## Task 1: `preview_cache.py` module (TDD)

**Files:**
- Create: `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\preview_cache.py`
- Modify: `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py`

### Step 1.1: Write failing tests

- [ ] Append to `test_mapstudio.py`:

```python
# ===========================================================================
# preview_cache — save / load roundtrip and corruption handling
# ===========================================================================

from shapely.geometry import LineString, Polygon  # noqa: E402, F811


class TestPreviewCache:
    """Tests for preview_cache.save_preview_cache and load_preview_cache.

    No GUI, no matplotlib rendering — just the data-layer roundtrip and
    failure-mode handling.
    """

    _CRS = "EPSG:32633"

    def _make_metadata(self):
        return {
            "version": 1,
            "city": "TestCity",
            "country": "TestCountry",
            "center": [45.0, 13.0],
            "compensated_dist": 5000.0,
            "crop_xlim": [-1000.0, 1000.0],
            "crop_ylim": [-1000.0, 1000.0],
            "target_crs": self._CRS,
            "width": 12,
            "height": 16,
        }

    def test_preview_cache_roundtrip(self, tmp_path):
        """save_preview_cache then load_preview_cache must roundtrip GDFs + metadata."""
        import preview_cache
        roads = gpd.GeoDataFrame(
            {"highway": ["residential", "primary"]},
            geometry=[
                LineString([(0, 0), (100, 100)]),
                LineString([(100, 100), (200, 0)]),
            ],
            crs=self._CRS,
        )
        water = gpd.GeoDataFrame(
            geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
            crs=self._CRS,
        )

        preview_cache.save_preview_cache(
            str(tmp_path),
            metadata=self._make_metadata(),
            roads=roads,
            water=water,
            parks=None,
            wetlands=None,
            religious=None,
            historic=None,
            sea_polys=None,
            target_crs=self._CRS,
        )

        result = preview_cache.load_preview_cache(str(tmp_path))
        assert result is not None
        assert len(result.roads) == 2
        assert list(result.roads["highway"]) == ["residential", "primary"]
        assert result.water is not None
        assert len(result.water) == 1
        assert result.parks is None
        assert result.wetlands is None
        assert result.religious is None
        assert result.historic is None
        assert result.sea is None
        assert result.metadata["city"] == "TestCity"
        assert result.metadata["version"] == 1

    def test_preview_cache_handles_corrupt_gpkg(self, tmp_path):
        """A corrupt GPKG file must result in None, no exception raised."""
        import preview_cache
        (tmp_path / "preview.gpkg").write_bytes(b"not a valid gpkg")
        (tmp_path / "preview.json").write_text(
            '{"version": 1, "city": "X", "country": "Y", "center": [0, 0], '
            '"compensated_dist": 1000, "crop_xlim": [0, 1], "crop_ylim": [0, 1], '
            '"target_crs": "EPSG:32633", "width": 12, "height": 16}',
            encoding="utf-8",
        )
        result = preview_cache.load_preview_cache(str(tmp_path))
        assert result is None

    def test_preview_cache_handles_corrupt_json(self, tmp_path):
        """A corrupt JSON file must result in None, no exception raised."""
        import preview_cache
        # Write a minimal valid gpkg so the JSON failure is what gets exercised
        roads = gpd.GeoDataFrame(
            {"highway": ["residential"]},
            geometry=[LineString([(0, 0), (1, 1)])],
            crs=self._CRS,
        )
        roads.to_file(str(tmp_path / "preview.gpkg"), driver="GPKG", layer="roads")
        (tmp_path / "preview.json").write_text("{not valid json", encoding="utf-8")
        result = preview_cache.load_preview_cache(str(tmp_path))
        assert result is None

    def test_preview_cache_missing_files_returns_none(self, tmp_path):
        """An empty cache directory must return None (placeholder state)."""
        import preview_cache
        result = preview_cache.load_preview_cache(str(tmp_path))
        assert result is None
```

### Step 1.2: Run tests to verify they fail

- [ ] From `H:\RAZVOJ\maptoposterwebapp\`:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py::TestPreviewCache -v
```

Expected: 4 failures with `ModuleNotFoundError: No module named 'preview_cache'`.

### Step 1.3: Create `preview_cache.py` with save + load (no render yet)

- [ ] Create `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\preview_cache.py`:

```python
"""
Preview cache for the desktop GUI's live preview pane.

Persists the geometry layers from a generated poster to disk (GeoPackage +
JSON sidecar) so that the GUI can re-render a thumbnail with a different
theme without re-fetching OSM data or recomputing projections.
"""

import json
import logging
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional

from geopandas import GeoDataFrame
import geopandas as gpd

logger = logging.getLogger("maptoposter")

_GPKG_NAME = "preview.gpkg"
_JSON_NAME = "preview.json"
_SCHEMA_VERSION = 1


@dataclass
class PreviewCache:
    """In-memory representation of a loaded preview cache."""
    metadata: dict
    roads: Optional[GeoDataFrame]
    water: Optional[GeoDataFrame]
    parks: Optional[GeoDataFrame]
    wetlands: Optional[GeoDataFrame]
    religious: Optional[GeoDataFrame]
    historic: Optional[GeoDataFrame]
    sea: Optional[GeoDataFrame]


def save_preview_cache(
    cache_dir: str,
    *,
    metadata: dict,
    roads: Optional[GeoDataFrame],
    water: Optional[GeoDataFrame],
    parks: Optional[GeoDataFrame],
    wetlands: Optional[GeoDataFrame],
    religious: Optional[GeoDataFrame],
    historic: Optional[GeoDataFrame],
    sea_polys: Optional[list],
    target_crs: Any,
) -> None:
    """Atomically write a preview cache to disk.

    Writes the GeoPackage first (tmp + os.replace), then the JSON (tmp +
    os.replace). If the gpkg write fails, no JSON is written and the loader
    sees an incomplete cache (treated as missing). Each individual file is
    atomic at the filesystem level.

    Args:
        cache_dir: Directory to write into. Created if missing.
        metadata: JSON-serializable dict including the schema 'version' key.
        roads, water, parks, wetlands, religious, historic: Layer GDFs to
            persist. Any may be None or empty (will be skipped).
        sea_polys: List of shapely Polygon objects; will be wrapped into a
            GeoDataFrame keyed under the 'sea' layer.
        target_crs: CRS to apply to the sea GDF (since sea_polys is a list
            without CRS info).
    """
    os.makedirs(cache_dir, exist_ok=True)
    gpkg_path = os.path.join(cache_dir, _GPKG_NAME)
    json_path = os.path.join(cache_dir, _JSON_NAME)
    gpkg_tmp = gpkg_path + ".tmp"
    json_tmp = json_path + ".tmp"

    # Remove any stale tmp from a previous failed write
    if os.path.exists(gpkg_tmp):
        os.remove(gpkg_tmp)

    layers = [
        ("roads", roads),
        ("water", water),
        ("parks", parks),
        ("wetlands", wetlands),
        ("religious", religious),
        ("historic", historic),
    ]

    wrote_any = False
    for layer_name, gdf in layers:
        if gdf is None or gdf.empty:
            continue
        mode = "w" if not wrote_any else "a"
        gdf.to_file(gpkg_tmp, driver="GPKG", layer=layer_name, mode=mode)
        wrote_any = True

    if sea_polys:
        sea_gdf = gpd.GeoDataFrame(geometry=sea_polys, crs=target_crs)
        if not sea_gdf.empty:
            mode = "w" if not wrote_any else "a"
            sea_gdf.to_file(gpkg_tmp, driver="GPKG", layer="sea", mode=mode)
            wrote_any = True

    if not wrote_any:
        raise ValueError(
            "save_preview_cache: no non-empty layers to persist"
        )

    os.replace(gpkg_tmp, gpkg_path)

    # Write JSON second so a partial write leaves the gpkg without a sidecar
    # (loader treats missing JSON as missing cache).
    with open(json_tmp, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    os.replace(json_tmp, json_path)


def load_preview_cache(cache_dir: str) -> Optional[PreviewCache]:
    """Load and validate a preview cache from disk.

    Returns:
        PreviewCache on success, or None if anything is missing, corrupt,
        or from a future schema version.

    Behaviour is fail-soft: any error is logged at warning level and None
    is returned. The caller shows a placeholder in that case.
    """
    json_path = os.path.join(cache_dir, _JSON_NAME)
    gpkg_path = os.path.join(cache_dir, _GPKG_NAME)

    if not os.path.exists(json_path) or not os.path.exists(gpkg_path):
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("preview_cache: failed to read JSON: %s", e)
        return None

    if metadata.get("version", 0) > _SCHEMA_VERSION:
        logger.warning(
            "preview_cache: schema version %s newer than expected (%s); ignoring cache",
            metadata.get("version"), _SCHEMA_VERSION,
        )
        return None

    try:
        from pyogrio import list_layers
        available = {row[0] for row in list_layers(gpkg_path)}
    except Exception as e:
        logger.warning("preview_cache: failed to list GPKG layers: %s", e)
        return None

    def _read(layer_name: str) -> Optional[GeoDataFrame]:
        if layer_name not in available:
            return None
        try:
            return gpd.read_file(gpkg_path, layer=layer_name)
        except Exception as e:
            logger.warning(
                "preview_cache: failed to read layer '%s': %s", layer_name, e,
            )
            return None

    try:
        return PreviewCache(
            metadata=metadata,
            roads=_read("roads"),
            water=_read("water"),
            parks=_read("parks"),
            wetlands=_read("wetlands"),
            religious=_read("religious"),
            historic=_read("historic"),
            sea=_read("sea"),
        )
    except Exception as e:
        logger.warning("preview_cache: failed to construct PreviewCache: %s", e)
        return None
```

### Step 1.4: Run tests to verify they pass

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py::TestPreviewCache -v
```

Expected: 4 passes.

### Step 1.5: Add `render_preview` (no unit test — matplotlib side-effect)

- [ ] Append to `preview_cache.py`:

```python
def render_preview(
    cache: PreviewCache,
    theme: dict[str, str],
    width_px: int,
    height_px: int,
) -> "Image.Image":
    """Render a cached location at the given pixel size with the given theme.

    Uses matplotlib's Figure + Agg backend directly (no pyplot global state)
    so it's safe to call from a worker thread. Returns a PIL Image.

    Skips text labels (unreadable at thumbnail size) but includes the
    gradient fades from the full pipeline (they're subtle and remain
    visually correct when downscaled).
    """
    # Lazy imports keep module load fast for the save/load-only path
    from PIL import Image  # noqa: F401
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import road_categories
    from create_map_poster import create_gradient_fade

    fig = Figure(
        figsize=(width_px / 72, height_px / 72), dpi=72,
        facecolor=theme["bg"],
    )
    ax = fig.add_subplot(111)
    ax.set_facecolor(theme["bg"])
    ax.set_position((0.0, 0.0, 1.0, 1.0))

    landmark_color = theme.get(
        "landmark", theme.get("text", "#444444"),
    )

    if cache.sea is not None and not cache.sea.empty:
        cache.sea.plot(ax=ax, facecolor=theme["water"], edgecolor="none", zorder=0.4)
    if cache.water is not None and not cache.water.empty:
        cache.water.plot(ax=ax, facecolor=theme["water"], edgecolor="none", zorder=0.5)
    if cache.wetlands is not None and not cache.wetlands.empty:
        cache.wetlands.plot(ax=ax, facecolor=theme["water"], edgecolor="none", zorder=0.6)
    if cache.parks is not None and not cache.parks.empty:
        cache.parks.plot(ax=ax, facecolor=theme["parks"], edgecolor="none", zorder=0.8)
    if cache.religious is not None and not cache.religious.empty:
        cache.religious.plot(ax=ax, facecolor=landmark_color, edgecolor="none", zorder=1.5)
    if cache.historic is not None and not cache.historic.empty:
        cache.historic.plot(ax=ax, facecolor=landmark_color, edgecolor="none", zorder=1.5)

    if cache.roads is not None and not cache.roads.empty and "highway" in cache.roads.columns:
        colors = [road_categories.get_color(hw, theme) for hw in cache.roads["highway"]]
        widths = [road_categories.get_width(hw) for hw in cache.roads["highway"]]
        cache.roads.plot(ax=ax, color=colors, linewidth=widths, zorder=2.0)

    ax.set_xlim(cache.metadata["crop_xlim"])
    ax.set_ylim(cache.metadata["crop_ylim"])
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()

    create_gradient_fade(ax, theme.get("gradient_color", theme["bg"]), location="bottom", zorder=10)
    create_gradient_fade(ax, theme.get("gradient_color", theme["bg"]), location="top", zorder=10)

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    buf = BytesIO()
    fig.savefig(
        buf, format="png", dpi=72,
        facecolor=theme["bg"], bbox_inches="tight", pad_inches=0,
    )
    buf.seek(0)
    from PIL import Image
    image = Image.open(buf).copy()
    buf.close()
    return image
```

### Step 1.6: Verify module imports cleanly

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp'); import preview_cache; print('module ok:', preview_cache.save_preview_cache, preview_cache.load_preview_cache, preview_cache.render_preview, preview_cache.PreviewCache)"
```

Expected: prints four function/class reprs.

### Step 1.7: Run full test suite

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 54 tests pass (50 existing + 4 new in `TestPreviewCache`).

### Step 1.8: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add preview_cache.py test_mapstudio.py
git commit -m "feat: preview_cache module with save/load/render helpers"
```

---

## Task 2: Wire `write_preview_cache` into `create_poster()`

**Files:**
- Modify: `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\create_map_poster.py`

### Step 2.1: Add the new parameter to `create_poster()` signature

- [ ] In `create_map_poster.py`, find the existing `create_poster(` definition. Locate the last positional parameter in the signature (currently `dpi: int = 300,`) and INSERT directly after it:

```python
    write_preview_cache: Optional[str] = None,
```

### Step 2.2: Add docstring entry

- [ ] In the `create_poster` docstring, find the entry for `dpi` (the last existing arg description). INSERT directly after it:

```
        write_preview_cache: If set, write a preview cache (GeoPackage +
            JSON sidecar) into this directory at the end of a successful
            generation. Used by the desktop GUI to populate its theme
            preview pane. Ignored for STL output.
```

### Step 2.3: Add the cache-write block before `create_poster` returns

- [ ] In `create_poster`, find the existing block at the end that handles the SVG/PDF/PNG save path. It currently ends with something like:

```python
        plt.savefig(output_file, format=fmt, **save_kwargs)
        plt.close()

        if svg_layers and fmt == "svg":
            logger.info("Organizing SVG into layers by road type...")
            organize_svg_layers(output_file)

        logger.info("Done! Poster saved as %s", output_file)
```

Insert IMMEDIATELY AFTER `logger.info("Done! Poster saved as %s", output_file)` and BEFORE the function returns (still inside the non-STL branch — STL output skips preview cache):

```python
        if write_preview_cache:
            try:
                from preview_cache import save_preview_cache
                roads_gdf = ox.graph_to_gdfs(g_proj, nodes=False)
                sea_geoms = list(sea_polys) if sea_polys else None
                preview_metadata = {
                    "version": 1,
                    "city": city,
                    "country": country,
                    "center": [point[0], point[1]],
                    "compensated_dist": compensated_dist,
                    "crop_xlim": [crop_xlim[0], crop_xlim[1]],
                    "crop_ylim": [crop_ylim[0], crop_ylim[1]],
                    "target_crs": str(g_proj.graph["crs"]),
                    "width": width,
                    "height": height,
                }
                save_preview_cache(
                    write_preview_cache,
                    metadata=preview_metadata,
                    roads=roads_gdf,
                    water=water_polys,
                    parks=parks_polys,
                    wetlands=wetlands_polys,
                    religious=religious_polys,
                    historic=historic_polys,
                    sea_polys=sea_geoms,
                    target_crs=g_proj.graph["crs"],
                )
                logger.info("Preview cache written to %s", write_preview_cache)
            except Exception as e:
                logger.warning("Failed to write preview cache: %s", e)
```

Note: `ox` is already imported at the top of the module — do not add another import inside the block. This block does NOT run when `output_format == "stl"` (STL has its own branch earlier in the function that returns before reaching here).

### Step 2.4: Add the argparse argument

- [ ] In `create_map_poster.py`, find the existing block:

```python
    parser.add_argument('--show-historic', action='store_true',
                       help='Render castles, palaces, monuments, ruins, and other historic features (off by default)')
```

Insert IMMEDIATELY AFTER it:

```python
    parser.add_argument('--write-preview-cache', type=str, default=None,
                       help='GUI-only infrastructure: write preview cache files (preview.gpkg + preview.json) to the given directory after generation')
```

### Step 2.5: Pass the new arg into `create_poster()` in `__main__`

- [ ] Find the `create_poster(` call in `__main__`. Locate the existing kwarg `dpi=args.dpi,` and INSERT directly after it:

```python
                write_preview_cache=args.write_preview_cache,
```

### Step 2.6: Verify

- [ ] Run the test suite:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 54 tests pass.

- [ ] Verify `--help` shows the new flag:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py --help 2>&1 | Select-String "write-preview-cache"
```

Expected: a line containing `--write-preview-cache` and the help text.

- [ ] Smoke-test the cache write end-to-end with a small, fast city:

```powershell
$tmpDir = Join-Path $env:TEMP "preview_cache_smoke_$(Get-Random)"
New-Item -ItemType Directory -Path $tmpDir | Out-Null
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean -d 2000 --write-preview-cache $tmpDir
Get-ChildItem $tmpDir
```

Expected: directory listing shows `preview.gpkg` (non-zero size) and `preview.json` (small).

- [ ] Inspect the metadata:

```powershell
Get-Content (Join-Path $tmpDir "preview.json")
```

Expected: valid JSON with `version: 1` and the expected fields.

- [ ] Verify the cache loads correctly:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp'); import preview_cache; c = preview_cache.load_preview_cache(r'$tmpDir'); print('loaded:', c is not None); print('roads rows:', len(c.roads) if c and c.roads is not None else 'N/A'); print('city:', c.metadata.get('city') if c else 'N/A')"
```

Expected: `loaded: True`, a positive roads-rows count, `city: Koper`.

### Step 2.7: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add create_map_poster.py
git commit -m "feat: --write-preview-cache CLI flag and create_poster parameter"
```

---

## Task 3: GUI integration

**Files:**
- Modify: `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\maptoposter_gui.py`

### Step 3.1: Add imports

- [ ] In `maptoposter_gui.py`, find the existing imports block at the top. After the last existing third-party import (around `from tkinter import messagebox`), INSERT:

```python
from preview_cache import load_preview_cache, render_preview, PreviewCache
```

(The file uses PEP 604 `X | None` union syntax — no `from typing import Optional` needed.)

### Step 3.2: Add state attributes in `__init__`

- [ ] In `__init__`, find the existing block (around the comments "# Generation state"):

```python
        # Generation state
        self._generating: bool = False
        self._process: subprocess.Popen | None = None
```

Insert IMMEDIATELY AFTER `self._process: subprocess.Popen | None = None`:

```python
        # Preview pane state
        self._preview_cache: PreviewCache | None = None
        self._preview_render_token: int = 0
        self._preview_image_handle: ctk.CTkImage | None = None
        self._preview_render_lock = threading.Lock()
```

### Step 3.3: Add `_preview_cache_dir` property

- [ ] After the existing `installed_fonts` property in the class (search for `@property\n    def installed_fonts`), add a new property:

```python
    @property
    def _preview_cache_dir(self) -> Path:
        """Directory where the preview cache lives (next to posters/)."""
        return self.base_path / "preview_cache"
```

### Step 3.4: Add the preview widget in `setup_ui`

- [ ] In `setup_ui`, find the end of column 3's setup. Locate the end of the STL settings block. Specifically, after this line (or its equivalent at the end of the column-3 frame setup):

```python
        self.stl_invert_sw = ctk.CTkSwitch(stl_print_container, text=" Invert",
                                           font=ctk.CTkFont(size=10))
        self.stl_invert_sw.pack(anchor="w", padx=10, pady=(2, 4))
```

INSERT directly after that block (still inside column 3's setup, just before the column 4 setup starts):

```python
        # ========== Preview pane ==========
        preview_container = ctk.CTkFrame(col3, fg_color="gray15", corner_radius=6)
        preview_container.pack(fill="x", padx=15, pady=(15, 15))

        ctk.CTkLabel(
            preview_container, text="Preview:", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(fill="x", padx=10, pady=(8, 4))

        self.preview_label = ctk.CTkLabel(
            preview_container, text="",
            width=180, height=240, anchor="center",
            fg_color="gray20", corner_radius=4,
        )
        self.preview_label.pack(padx=10, pady=(0, 10))
```

### Step 3.5: Add the placeholder helper

- [ ] After `setup_ui` method ends, add new methods to the class. Place these methods together near other UI helper methods (e.g., after `add_column_header` or `toggle_custom_text_sizes`). The exact location is flexible — pick any spot inside `class ModernMapPosterGUI` that isn't inside an existing method:

```python
    def _show_preview_placeholder(self) -> None:
        """Display the 'generate a poster' placeholder text in the preview label."""
        self._preview_image_handle = None
        try:
            self.preview_label.configure(
                image="", text="Generate a poster\nto see preview",
                text_color="gray50",
            )
        except Exception as e:
            logger.debug("Could not show preview placeholder: %s", e)
```

### Step 3.6: Add the cache loader

- [ ] In the same class, add:

```python
    def _load_and_render_preview(self) -> None:
        """Load the cache from disk and trigger a render. Safe to call from GUI thread."""
        cache = load_preview_cache(str(self._preview_cache_dir))
        self._preview_cache = cache
        if cache is None:
            self._show_preview_placeholder()
        else:
            self._render_preview_async()
```

### Step 3.7: Add the async render dispatcher

- [ ] In the same class, add:

```python
    def _render_preview_async(self) -> None:
        """Spawn a worker thread to render the cached preview with the current theme.

        Uses a monotonic token so that a stale render's result is dropped if the
        user changes the theme again before the first render finishes.
        """
        if self._preview_cache is None:
            self._show_preview_placeholder()
            return

        with self._preview_render_lock:
            self._preview_render_token += 1
            token = self._preview_render_token

        theme_name = self.theme_menu.get()
        if not theme_name or theme_name == "---":
            return  # Theme dropdown separator entry; skip

        from create_map_poster import load_theme
        theme = load_theme(theme_name)
        cache = self._preview_cache

        def _worker():
            try:
                image = render_preview(cache, theme, width_px=180, height_px=240)
            except Exception as e:
                logger.warning("Preview render failed: %s", e)
                return
            # Drop result if a newer render has been kicked off
            with self._preview_render_lock:
                if self._preview_render_token != token:
                    return
            # Marshal back to GUI thread
            self.after(0, lambda: self._publish_preview(image))

        threading.Thread(target=_worker, daemon=True).start()
```

### Step 3.8: Add the GUI-thread publisher

- [ ] In the same class, add:

```python
    def _publish_preview(self, pil_image) -> None:
        """Update the preview label with a freshly-rendered image. GUI thread only."""
        try:
            # CTkImage handles HiDPI scaling; pass both light/dark images as the same
            ctk_image = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image,
                size=(180, 240),
            )
            self._preview_image_handle = ctk_image  # keep reference alive
            self.preview_label.configure(image=ctk_image, text="")
        except Exception as e:
            logger.warning("Could not publish preview image: %s", e)
```

### Step 3.9: Wire startup to load the preview

- [ ] In `__init__`, find the existing line `self.setup_ui()`. After it (and after `self.check_script_exists()` and `self._load_last_used_settings()`), add:

```python
        # Load and render the preview from disk (or show placeholder if none)
        self._load_and_render_preview()
```

### Step 3.10: Wire theme changes to trigger preview re-render

- [ ] Find the existing `_on_theme_change` method:

```python
    def _on_theme_change(self, theme: str) -> None:
        """Update description label when theme selection changes."""
        desc = self.theme_descriptions.get(theme, "")
        self.theme_desc_label.configure(text=desc)
```

Replace with:

```python
    def _on_theme_change(self, theme: str) -> None:
        """Update description label and trigger preview re-render."""
        desc = self.theme_descriptions.get(theme, "")
        self.theme_desc_label.configure(text=desc)
        self._render_preview_async()
```

### Step 3.11: Wire subprocess path to write the cache

- [ ] In `_build_subprocess_cmd`, locate the END of the function (just before `return cmd`). INSERT:

```python
        cmd.extend(["--write-preview-cache", str(self._preview_cache_dir)])
```

### Step 3.12: Wire subprocess completion to refresh preview

- [ ] In `_run_subprocess`, find the existing success branch:

```python
            if return_code == 0:
                self.after(0, lambda: self.log_box.insert("end", "\n[OK] SUCCESS!\n"))
                self.after(0, lambda: messagebox.showinfo("Success", "Poster generated successfully!"))
```

Insert IMMEDIATELY AFTER the `messagebox.showinfo` line (still inside the `if return_code == 0:` block):

```python
                self.after(0, self._load_and_render_preview)
```

### Step 3.13: Wire direct-call path to write the cache + refresh

- [ ] In `_run_direct`, find the `create_poster(` call. Locate the last kwarg (currently `network_type=params.get("network_type", "all"),` based on prior work). INSERT directly after it:

```python
                    write_preview_cache=str(self._preview_cache_dir),
```

Then find the success branch:

```python
            self.after(0, lambda: self.log_box.insert("end", "\n[OK] SUCCESS!\n"))
            self.after(0, lambda: messagebox.showinfo("Success", "Poster generated successfully!"))
```

Insert IMMEDIATELY AFTER the `messagebox.showinfo` line:

```python
            self.after(0, self._load_and_render_preview)
```

### Step 3.14: Smoke test — GUI launches and shows placeholder when no cache

- [ ] First, delete any existing cache so the placeholder branch is exercised:

```powershell
Remove-Item -Recurse -Force H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\preview_cache -ErrorAction SilentlyContinue
```

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp'); import matplotlib; matplotlib.use('Agg'); from maptoposter_gui import ModernMapPosterGUI; app = ModernMapPosterGUI(); print('preview_label exists:', hasattr(app, 'preview_label')); print('preview text:', app.preview_label.cget('text')); print('preview_cache is None:', app._preview_cache is None); app.destroy()"
```

Expected output:
```
preview_label exists: True
preview text: Generate a poster
to see preview
preview_cache is None: True
```

### Step 3.15: Run test suite

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 54 tests pass.

### Step 3.16: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add maptoposter_gui.py
git commit -m "feat: live preview pane in GUI with theme-change re-render"
```

---

## Task 4: Manual verification

End-to-end testing of the preview lifecycle. The visual quality is the user's job — this task just confirms the lifecycle works.

### Step 4.1: First launch — placeholder

- [ ] Delete the cache directory and the GUI settings (to ensure a fresh state):

```powershell
Remove-Item -Recurse -Force H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\preview_cache -ErrorAction SilentlyContinue
```

- [ ] Launch the GUI:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe maptoposter_gui.py
```

Expected: GUI opens; the Preview frame in column 3 shows "Generate a poster to see preview".

### Step 4.2: Generate a poster — preview updates

- [ ] In the running GUI, enter `Koper` / `Slovenia`, theme `ocean`, radius 5000, click Generate.

Expected: poster generates as usual; when complete, the preview frame updates to show a small render of the Koper map in the ocean theme. The bottom log box should show a line like `Preview cache written to ...preview_cache`.

### Step 4.3: Theme change — preview re-renders

- [ ] Change the theme dropdown to several different themes (e.g. `terracotta`, `noir`, `neon_cyberpunk`, `dragons_lair`).

Expected: preview re-renders within ~1-2 seconds after each change. Theme switch is responsive (GUI doesn't freeze). The actual full-generation output is not affected — only the preview.

### Step 4.4: App restart — preview persists

- [ ] Close the GUI. Relaunch it:

```powershell
..\.venv\Scripts\python.exe maptoposter_gui.py
```

Expected: GUI opens; preview is immediately alive showing the last-rendered Koper map with the currently-selected theme. No "Generate a poster" placeholder.

### Step 4.5: Different city — preview replaces

- [ ] Enter `Tokyo` / `Japan`, theme `japanese_ink`, radius 10000, click Generate.

Expected: poster generates; on completion, preview switches from the Koper map to a Tokyo map. The Koper data is gone from the cache (was overwritten).

### Step 4.6: Toggle a feature without generating — preview unchanged

- [ ] In the running GUI, toggle the Ocean switch OFF (or any other feature toggle). Do NOT click Generate.

Expected: preview is unchanged (still shows the last-generated layers). Confirms that toggle changes don't affect preview until next generation.

### Step 4.7: Corrupted cache — placeholder

- [ ] Close the GUI. Corrupt the cache:

```powershell
Set-Content -Path H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\preview_cache\preview.json -Value "{not valid json"
```

- [ ] Relaunch the GUI:

```powershell
..\.venv\Scripts\python.exe maptoposter_gui.py
```

Expected: GUI opens; preview shows the placeholder ("Generate a poster..."). Log output (if visible) shows a warning about the JSON failing to load.

### Step 4.8: No commit (verification only)

This task produces no commits — it's manual verification.

---

## Self-review notes (already applied to plan)

- Spec requirement "atomic writes, JSON last" — Task 1.3's `save_preview_cache` writes gpkg first via tmp+replace, then JSON via tmp+replace.
- Spec requirement "version check on load" — Task 1.3's `load_preview_cache` validates `metadata.get('version', 0) > _SCHEMA_VERSION` and returns None.
- Spec requirement "render skips text labels but keeps gradient fade" — Task 1.5's `render_preview` calls `create_gradient_fade` twice and does not call any text rendering.
- Spec requirement "thread-safe matplotlib via Figure + FigureCanvasAgg" — Task 1.5 uses `from matplotlib.figure import Figure` and `FigureCanvasAgg`, not pyplot.
- Spec requirement "fallback color chain landmark → text → #444444" — Task 1.5's `render_preview` uses `theme.get('landmark', theme.get('text', '#444444'))`.
- Spec requirement "cancel-token via monotonic counter" — Task 3.7's `_render_preview_async` increments `self._preview_render_token` under a lock and the worker checks it again before publishing.
- Spec requirement "cache written via create_poster parameter, also via subprocess flag" — Task 2 handles both paths. The direct-call route passes `write_preview_cache=str(self._preview_cache_dir)`; the subprocess route appends `--write-preview-cache <dir>` to the argv.
- Spec requirement "STL output skips cache write" — Task 2.3 places the cache-write block inside the non-STL branch; STL has its own earlier return path.
- Spec requirement "no GUI test, no render test" — Task 1's tests cover save/load/corruption only.
- Task 3.10 replaces the entire `_on_theme_change` body to add the new call. Task 3.13 patches `_run_direct` in two places (kwarg + post-success refresh).
