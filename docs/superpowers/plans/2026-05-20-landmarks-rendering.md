# Landmarks Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two opt-in CLI flags (`--show-religious` and `--show-historic`) and matching GUI toggles to render churches, mosques, synagogues, temples, monuments, castles, and other historic features on coastal/historic-city posters.

**Architecture:** Mirrors the wetlands layer from the previous PR. Two new `_fetch_*` helpers query OSM, a single `_render_landmarks` helper paints both layers in one z-stack slot at `zorder=1.5` using a new theme key `landmark`. The `_project_features` helper already handles polygon filtering + CRS projection. All 36 built-in themes get explicit `landmark` colours.

**Tech Stack:** Python 3.13, OSMnx 2.0, shapely 2.1, geopandas 1.1, matplotlib 3.10, customtkinter (GUI). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-20-landmarks-rendering-design.md`

**Repo root:** `H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\` (all paths relative to this directory).

**Branch:** `feature/show-landmarks` (already checked out, off `Desktop`).

---

## File Structure

**Modified files (no new files):**

| File | Responsibility |
|---|---|
| `create_map_poster.py` | New helpers `_fetch_religious`, `_fetch_historic`, `_render_landmarks`. New `show_religious` and `show_historic` parameters on `create_poster()`. Two new argparse args. |
| `maptoposter_gui.py` | Two new `CTkSwitch` widgets (Religious sites, Historical sites). 12 plumbing edits across `_collect_form_settings`, `_apply_settings_to_form`, `_collect_generation_params`, `_build_subprocess_cmd`, `_run_direct`. |
| `themes/*.json` | All 36 theme files get one new `landmark` key with a carefully-chosen colour value (table in Task 1). |
| `CHANGELOG.md` | Two new bullets in `[Unreleased] - Community Contributions / Added` plus one bullet noting the theme schema addition. |

No new tests — all new code is glue (matplotlib plotting + OSMnx wrappers) and follows the existing no-test policy for that category. The pre-existing 50 tests must still pass after every change.

---

## Task 1: Theme files — add `landmark` key to all 36

**Files:**
- Modify: all 36 files under `themes/` (autumn.json through warm_beige.json)

The colour values below were chosen per-theme using the spec's palette philosophy: visible against `bg`, distinct from `water` / `parks` / `text`, harmonious with theme mood. They are final values — do not modify them.

### Step 1.1: Add `landmark` key to every theme JSON

- [ ] For each file below, add a new `landmark` key with the listed value, placed alphabetically (after `gradient_color`, before `parks`). Use exact hex values as shown.

| Theme | landmark value | Rationale (for reviewer context) |
|---|---|---|
| `autumn.json` | `#A63A20` | Rust/russet — deeper than the saddle brown text |
| `blueprint.json` | `#D4C5A0` | Warm parchment — pops against the deep blue, distinct from white text |
| `bubblegum_bright.json` | `#E91E63` | Bubblegum pink — playful accent distinct from cyan/green |
| `candy_shop.json` | `#C97A8A` | Dusty rose — more saturated than the soft pastel palette |
| `citrus_pop.json` | `#E67E22` | Citrus orange — fits the theme name |
| `cloudy_day.json` | `#8B6F4E` | Warm bronze — breaks up the cool grey palette |
| `contrast_zones.json` | `#C0392B` | Single deep red accent on monochrome |
| `copper_patina.json` | `#B87333` | Copper — literal interpretation of theme name |
| `cream_mauve.json` | `#8B5A6B` | Dusty mauve — fits the mauve cream pairing |
| `dragons_lair.json` | `#C8741A` | Burnt amber — distinct from the ember text colour |
| `dusty_peach.json` | `#A55D45` | Terracotta-brown — warm contrast |
| `elven_forest.json` | `#C9A04A` | Golden bronze — sunlit stone in a forest |
| `emerald.json` | `#C9A04A` | Warm gold — luxury accent on dark green |
| `enchanted_night.json` | `#B8956B` | Antique gold — magical luxury accent |
| `fantasy_realm.json` | `#B8860B` | Dark goldenrod — the "gold" of the mystical purple-and-gold |
| `forest.json` | `#7A6F5C` | Weathered bronze — distinct from the green palette |
| `gradient_roads.json` | `#5A4434` | Deep sepia — single warm accent on monochrome |
| `hangzhou_ink.json` | `#A0392B` | Cinnabar / Chinese seal red — culturally appropriate accent |
| `japanese_ink.json` | `#B73E36` | Vermilion — classic Japanese ink-painting accent |
| `lavender_dream.json` | `#9B6B8E` | Dusty rose-purple — deepens the lavender mood |
| `midnight_blue.json` | `#B87333` | Copper — distinct from the existing gold text |
| `mint_fresh.json` | `#C95745` | Terracotta-coral — warm contrast against mint |
| `misty_lavender.json` | `#8B5F6F` | Dusty mauve-rose — warm undertone of the theme |
| `monochrome_blue.json` | `#6B5945` | Warm sepia — gentle break from pure blue monochrome |
| `mystical_realm.json` | `#A88C5C` | Antique brass — distinct from the gold text on dark purple |
| `neon_cyberpunk.json` | `#FF1493` | Deep pink/magenta — second neon distinct from cyan text |
| `night_drive.json` | `#C8392B` | Brake-light red — fits theme description |
| `noir.json` | `#C8A464` | Warm amber — gallery spotlight feel on pure black |
| `ocean.json` | `#C97345` | Warm coral — lighthouse vibe against coastal blues |
| `pastel_dream.json` | `#B08090` | Dusty rose — fits the dreamy soft palette |
| `peach_sorbet.json` | `#D87850` | Deep coral — saturated peach |
| `sage_garden.json` | `#A65D40` | Terracotta — the "terracotta touches" from the description |
| `soft_sakura.json` | `#B86875` | Deep cherry rose — deeper sakura |
| `sunset.json` | `#8B3B26` | Burnt sienna — deeper than the existing sunset orange text |
| `terracotta.json` | `#A04020` | Deeper brick red — extends terracotta family |
| `warm_beige.json` | `#8B6B4A` | Deeper sepia — fits the vintage map feel |

Concrete example — `terracotta.json` after edit:

```json
{
  "name": "Terracotta",
  "description": "Mediterranean warmth - burnt orange and clay tones on cream",
  "bg": "#F5EDE4",
  "text": "#8B4513",
  "gradient_color": "#F5EDE4",
  "landmark": "#A04020",
  "water": "#A8C4C4",
  "parks": "#E8E0D0",
  "road_motorway": "#A0522D",
  "road_primary": "#B8653A",
  "road_secondary": "#C9846A",
  "road_tertiary": "#D9A08A",
  "road_residential": "#E5C4B0",
  "road_default": "#D9A08A"
}
```

The `landmark` key goes alphabetically — between `gradient_color` and `parks`. Match the existing 2-space indentation and trailing-comma style for each file.

### Step 1.2: Verify all themes still parse as valid JSON

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import json, os, glob; [json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\themes\*.json'))]; print('All 36 themes parse OK')"
```

Expected output: `All 36 themes parse OK`.

### Step 1.3: Verify all themes now contain the `landmark` key

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import json, glob; missing = [p for p in sorted(glob.glob(r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\themes\*.json')) if 'landmark' not in json.load(open(p, encoding='utf-8'))]; print('Missing landmark in:', missing) if missing else print('All 36 themes have landmark')"
```

Expected output: `All 36 themes have landmark`.

### Step 1.4: Run the existing test suite to make sure nothing regressed

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 50 tests pass.

### Step 1.5: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add themes/
git commit -m "feat: add landmark colour key to all 36 themes"
```

---

## Task 2: CLI — helpers, wiring, flag, CHANGELOG

**Files:**
- Modify: `create_map_poster.py`
- Modify: `CHANGELOG.md`

### Step 2.1: Add `_fetch_religious` helper

- [ ] In `create_map_poster.py`, find the existing `_fetch_wetlands` function. Add this function IMMEDIATELY AFTER it:

```python
def _fetch_religious(
    point: tuple[float, float],
    dist: float,
) -> Optional[GeoDataFrame]:
    """
    Fetch OSM religious-building polygons around a point.

    Queries both the structural ``building=*`` tag (for churches, cathedrals,
    chapels, mosques, synagogues, temples, monasteries, shrines) and the
    functional ``amenity=place_of_worship`` tag, which OSMnx OR's into a
    single query.

    Returns None on any error; the caller renders without religious sites in
    that case, so this is logged at warning rather than error level. Returns
    None silently (debug log) when no religious buildings exist in the
    queried area.

    Args:
        point: (latitude, longitude) tuple for center point
        dist: Distance in meters from center point
    """
    try:
        return ox.features_from_point(
            point,
            tags={
                "building": [
                    "church", "cathedral", "chapel", "mosque", "synagogue",
                    "temple", "monastery", "shrine",
                ],
                "amenity": "place_of_worship",
            },
            dist=dist,
        )
    except InsufficientResponseError:
        logger.debug("No religious buildings found in the requested area")
        return None
    except Exception as e:
        logger.warning("OSMnx error while fetching religious buildings: %s", e)
        return None
```

### Step 2.2: Add `_fetch_historic` helper

- [ ] Immediately after `_fetch_religious`, add:

```python
def _fetch_historic(
    point: tuple[float, float],
    dist: float,
) -> Optional[GeoDataFrame]:
    """
    Fetch OSM ``historic=*`` features (any value) around a point.

    The result may include points (statues, memorials without footprints),
    lines, and polygons; the render step filters to Polygon/MultiPolygon.

    Returns None on any error; logged at warning level (debug for the
    expected ``InsufficientResponseError`` no-features case).

    Args:
        point: (latitude, longitude) tuple for center point
        dist: Distance in meters from center point
    """
    try:
        return ox.features_from_point(
            point, tags={"historic": True}, dist=dist,
        )
    except InsufficientResponseError:
        logger.debug("No historic features found in the requested area")
        return None
    except Exception as e:
        logger.warning("OSMnx error while fetching historic features: %s", e)
        return None
```

### Step 2.3: Add `_render_landmarks` helper

- [ ] In `create_map_poster.py`, locate `_render_wetlands`. Add IMMEDIATELY AFTER it:

```python
def _render_landmarks(
    ax: plt.Axes,
    religious_polys: Optional[GeoDataFrame],
    historic_polys: Optional[GeoDataFrame],
    theme: dict[str, str],
) -> None:
    """Render religious and historic building polygons on the map axes.

    Both GDFs are painted into the same ``zorder=1.5`` slot using the theme's
    ``landmark`` colour (falls back to ``text``, then ``#444444`` for themes
    that don't define ``landmark``). Roads at ``zorder=2`` paint on top, so
    building footprints sit behind the road network.

    The caller has already passed each GDF through ``_project_features``,
    which both filters to Polygon/MultiPolygon and projects to the graph CRS.
    """
    color = theme.get('landmark', theme.get('text', '#444444'))
    if religious_polys is not None and not religious_polys.empty:
        religious_polys.plot(ax=ax, facecolor=color, edgecolor='none', zorder=1.5)
    if historic_polys is not None and not historic_polys.empty:
        historic_polys.plot(ax=ax, facecolor=color, edgecolor='none', zorder=1.5)
```

### Step 2.4: Update `create_poster()` signature

- [ ] In `create_map_poster.py`, find the `create_poster(` definition. Locate `show_wetlands: bool = False,` and INSERT directly after it:

```python
    show_religious: bool = False,
    show_historic: bool = False,
```

### Step 2.5: Update docstring

- [ ] In the same function's docstring, find the entry for `show_wetlands`. Insert directly after it:

```
        show_religious: If True, render OSM places of worship (churches,
            mosques, synagogues, temples, monasteries, shrines, etc.) using
            the theme's ``landmark`` colour (off by default)
        show_historic: If True, render OSM ``historic=*`` polygons (castles,
            palaces, ruins, monuments with footprints, archaeological sites,
            etc.) using the theme's ``landmark`` colour (off by default)
```

### Step 2.6: Extend the tqdm fetch block

- [ ] In `create_poster()`, find the existing tqdm block. It currently looks like (with the wetlands work):

```python
    fetch_wetlands = show_wetlands and not no_water
    total_steps = 3 + (1 if fetch_wetlands else 0)
    with tqdm(
        total=total_steps,
        ...
    ) as pbar:
        ...
        wetlands = None
        if fetch_wetlands:
            pbar.set_description("Downloading wetlands")
            wetlands = _fetch_wetlands(point, compensated_dist)
            pbar.update(1)
```

Replace the `fetch_wetlands` / `total_steps` lines and the entire `wetlands` fetch sub-block with this expanded version:

```python
    fetch_wetlands = show_wetlands and not no_water
    total_steps = 3 + (
        (1 if fetch_wetlands else 0)
        + (1 if show_religious else 0)
        + (1 if show_historic else 0)
    )
    with tqdm(
        total=total_steps,
        desc="Fetching map data",
        unit="step",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
    ) as pbar:
```

(Keep the existing 3 sub-steps for street network / water / parks unchanged.)

Then replace the existing `wetlands = None` sub-block (the last conditional inside the tqdm `with` block) with:

```python
        wetlands = None
        if fetch_wetlands:
            pbar.set_description("Downloading wetlands")
            wetlands = _fetch_wetlands(point, compensated_dist)
            pbar.update(1)

        religious = None
        if show_religious:
            pbar.set_description("Downloading religious sites")
            religious = _fetch_religious(point, compensated_dist)
            pbar.update(1)

        historic = None
        if show_historic:
            pbar.set_description("Downloading historic features")
            historic = _fetch_historic(point, compensated_dist)
            pbar.update(1)
```

### Step 2.7: Project the new GDFs

- [ ] Find the existing projection block:

```python
    # Project features (water/parks/wetlands) to graph CRS
    water_polys = _project_features(water, g_proj)
    parks_polys = _project_features(parks, g_proj)
    wetlands_polys = _project_features(wetlands, g_proj)
```

Replace with:

```python
    # Project features (water/parks/wetlands/landmarks) to graph CRS
    water_polys = _project_features(water, g_proj)
    parks_polys = _project_features(parks, g_proj)
    wetlands_polys = _project_features(wetlands, g_proj)
    religious_polys = _project_features(religious, g_proj)
    historic_polys = _project_features(historic, g_proj)
```

### Step 2.8: Render the landmarks layer

- [ ] Find the existing render block that ends with `_render_parks`:

```python
    if not no_parks:
        _render_parks(ax, parks_polys, theme)
```

Insert IMMEDIATELY AFTER it:

```python
    if show_religious or show_historic:
        _render_landmarks(ax, religious_polys, historic_polys, theme)
```

### Step 2.9: Add the argparse arguments

- [ ] Find the existing `--show-wetlands` argparse line:

```python
    parser.add_argument('--show-wetlands', action='store_true',
                       help='Render OSM wetland polygons as water (off by default)')
```

Insert IMMEDIATELY AFTER it:

```python
    parser.add_argument('--show-religious', action='store_true',
                       help='Render churches, mosques, synagogues, temples, and other places of worship (off by default)')
    parser.add_argument('--show-historic', action='store_true',
                       help='Render castles, palaces, monuments, ruins, and other historic features (off by default)')
```

### Step 2.10: Pass new args into `create_poster()` in `__main__`

- [ ] Find the `create_poster(` call in `__main__`. Locate the existing kwarg `show_wetlands=args.show_wetlands,` and INSERT directly after it (match indentation):

```python
                show_religious=args.show_religious,
                show_historic=args.show_historic,
```

### Step 2.11: CHANGELOG entries

- [ ] In `CHANGELOG.md`, locate the `## [Unreleased] - Community Contributions` → `### Added` section. The current top bullet is the wetlands entry. Insert two new bullets at the TOP of the Added list (so historic becomes the new #1 and religious the new #2, above wetlands):

```markdown
- **Historic feature rendering** - `--show-historic` flag renders OSM `historic=*` polygons (castles, palaces, ruins, monuments, etc.) using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
- **Religious building rendering** - `--show-religious` flag renders churches, mosques, synagogues, temples, and other places of worship using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
```

- [ ] If a `### Changed` subsection does NOT exist within the `[Unreleased] - Community Contributions` section, ADD it directly after the `### Added` block, with this single bullet:

```markdown
### Changed
- **Theme schema** - new `landmark` colour key added to all 36 built-in themes (used by `--show-religious` and `--show-historic`). User-authored themes without this key fall back to the theme's `text` colour, so no migration is required.
```

If `### Changed` already exists in that section, simply append the bullet to its existing list.

### Step 2.12: Verify

- [ ] Run the existing test suite:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 50 tests pass.

- [ ] Verify `--help` shows both new flags:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py --help
```

Expected output contains:
```
  --show-religious      Render churches, mosques, synagogues, temples, and
                        other places of worship (off by default)
  --show-historic       Render castles, palaces, monuments, ruins, and other
                        historic features (off by default)
```

- [ ] Quick smoke test that all new functions are importable:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp'); from create_map_poster import _fetch_religious, _fetch_historic, _render_landmarks; print('ok')"
```

Expected: prints `ok`.

### Step 2.13: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add create_map_poster.py CHANGELOG.md
git commit -m "feat: --show-religious and --show-historic CLI flags"
```

---

## Task 3: GUI — Religious sites + Historical sites toggles

**Files:**
- Modify: `maptoposter_gui.py`

12 plumbing edits total (6 per toggle), all mirroring the existing Ocean/Wetlands switches exactly.

### Step 3.1: Add the two switch widgets

- [ ] In `maptoposter_gui.py`, find the existing block:

```python
        self.wetlands_sw = ctk.CTkSwitch(toggle_frame, text=" Wetlands")
        self.wetlands_sw.pack(anchor="w", padx=10, pady=8)
```

Insert IMMEDIATELY AFTER it:

```python
        self.religious_sw = ctk.CTkSwitch(toggle_frame, text=" Religious sites")
        self.religious_sw.pack(anchor="w", padx=10, pady=8)

        self.historic_sw = ctk.CTkSwitch(toggle_frame, text=" Historical sites")
        self.historic_sw.pack(anchor="w", padx=10, pady=8)
```

NO `.select()` calls — defaults are OFF, matching CLI defaults.

### Step 3.2: Persist in `_collect_form_settings`

- [ ] Locate the line:

```python
            "show_wetlands": self.wetlands_sw.get(),
```

Insert directly after it:

```python
            "show_religious": self.religious_sw.get(),
            "show_historic": self.historic_sw.get(),
```

### Step 3.3: Restore in `_apply_settings_to_form`

- [ ] In the restore-loop tuple list, find:

```python
                (self.wetlands_sw, "show_wetlands", False),
```

Insert directly after it (preserve trailing comma and indentation):

```python
                (self.religious_sw, "show_religious", False),
                (self.historic_sw, "show_historic", False),
```

### Step 3.4: Collect in `_collect_generation_params`

- [ ] Find:

```python
        params["show_wetlands"] = bool(self.wetlands_sw.get())
```

Insert directly after it:

```python
        params["show_religious"] = bool(self.religious_sw.get())
        params["show_historic"] = bool(self.historic_sw.get())
```

### Step 3.5: Propagate via subprocess cmd

- [ ] In `_build_subprocess_cmd`, find:

```python
        if params.get("show_wetlands"):
            cmd.append("--show-wetlands")
```

Insert directly after it:

```python
        if params.get("show_religious"):
            cmd.append("--show-religious")
        if params.get("show_historic"):
            cmd.append("--show-historic")
```

### Step 3.6: Propagate via direct call (frozen EXE mode)

- [ ] In `_run_direct`, find the kwarg:

```python
                    show_wetlands=params.get("show_wetlands", False),
```

Insert directly after it (match indentation):

```python
                    show_religious=params.get("show_religious", False),
                    show_historic=params.get("show_historic", False),
```

### Step 3.7: Smoke test the GUI launches with both switches present

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp'); import matplotlib; matplotlib.use('Agg'); from maptoposter_gui import ModernMapPosterGUI; app = ModernMapPosterGUI(); print('Religious switch:', hasattr(app, 'religious_sw'), app.religious_sw.cget('text'), 'default=', app.religious_sw.get()); print('Historic switch:', hasattr(app, 'historic_sw'), app.historic_sw.cget('text'), 'default=', app.historic_sw.get()); app.destroy()"
```

Expected output:
```
Religious switch: True  Religious sites default= 0
Historic switch: True  Historical sites default= 0
```

### Step 3.8: Run the test suite

- [ ] Run:

```powershell
H:\RAZVOJ\maptoposterwebapp\.venv\Scripts\python.exe -m pytest H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\test_mapstudio.py -v
```

Expected: 50 tests pass (GUI changes don't affect the CLI test suite).

### Step 3.9: Commit

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
git add maptoposter_gui.py
git commit -m "feat: Religious sites and Historical sites toggles in GUI"
```

---

## Task 4: Manual verification

Run CLI commands matching the spec's manual verification section. The goal is to confirm: no crashes, exit code 0, file produced. Visual quality is the user's job.

### Step 4.1: Koper combined regression

- [ ] Run:

```powershell
cd H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp
..\.venv\Scripts\python.exe create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean --show-religious --show-historic -d 5000 --show-sea
```

Expected: exit 0, file in `posters/`. tqdm shows 5 steps total: street network, water features, parks, religious sites, historic features. (Sea fetch happens outside the tqdm block so it doesn't add a step.)

### Step 4.2: Rome — many churches

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Rome" -C "Italy" --theme terracotta --show-religious -d 5000
```

Expected: exit 0, file produced. tqdm shows 4 steps (3 base + 1 for religious).

### Step 4.3: Edinburgh — castle + historic

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Edinburgh" -C "UK" --theme blueprint --show-historic -d 4000
```

Expected: exit 0, file produced. tqdm shows 4 steps (3 base + 1 for historic).

### Step 4.4: Istanbul — verify "religious" really is broader than Christian

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Istanbul" -C "Turkey" --theme japanese_ink --show-religious -d 8000
```

Expected: exit 0, file produced. (Visual check: should show many mosques.)

### Step 4.5: No flags — confirm byte-identical behaviour

- [ ] Run:

```powershell
..\.venv\Scripts\python.exe create_map_poster.py -c "Rome" -C "Italy" --theme terracotta -d 5000
```

Expected: exit 0, file produced. tqdm shows the original 3 steps (no new fetches when flags absent).

### Step 4.6: Verify recent posters list

- [ ] Run:

```powershell
Get-ChildItem H:\RAZVOJ\maptoposterwebapp\maptoposterwebapp\posters -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name, Length, LastWriteTime | Format-Table -AutoSize
```

Expected: 5 new files from the runs above.

### Step 4.7: No commit (verification only)

This task produces no commits — it's a manual sanity check.

---

## Self-review notes (already applied to plan)

- Spec requirement "use existing `_project_features` for polygon filter + projection" — Task 2.7 routes the new GDFs through it. No new polygon-filter helper.
- Spec requirement "no new unit tests" — only the existing 50-test regression is checked at each step.
- Spec requirement "render at zorder=1.5, between parks 0.8 and roads 2.0" — Task 2.3 sets `zorder=1.5`.
- Spec requirement "single `landmark` colour for both layers" — `_render_landmarks` uses one `color` variable for both `.plot()` calls.
- Spec requirement "`--no-water` does NOT gate religious/historic" — Task 2.6 conditions on `show_religious` / `show_historic` only (no `not no_water` clause).
- Spec requirement "fallback chain `landmark` → `text` → `#444444`" — Task 2.3 implements exactly that.
- All 36 theme colour values pre-picked in Task 1.1 — no implementer judgment required.
- GUI labels use "Religious sites" and "Historical sites" per the user's preference; the CLI flags use `--show-religious` / `--show-historic` (single-word, matches convention).
