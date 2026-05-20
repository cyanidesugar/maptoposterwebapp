# Render religious buildings and historical landmarks

**Date:** 2026-05-20
**Status:** Approved, pending spec review

## Problem

The current poster pipeline renders roads, water (inland, sea, wetlands), and parks — but no buildings. For posters of European cities, capital cities, or historic centres, the absence of churches, cathedrals, mosques, castles, and other landmark structures is visually noticeable. Adding them as an opt-in layer gives users a way to put the cultural skeleton of a city on the poster without forcing the choice on anyone who likes the current minimal style.

## Goals

1. Two new opt-in CLI flags: `--show-religious` and `--show-historic`. Both default off so existing posters render byte-identically.
2. Matching GUI toggles in the FEATURES column, plumbed through both execution modes (subprocess in dev, direct-call in frozen EXE).
3. Single new theme colour key `landmark`, shared by both layers. The 36 built-in themes get carefully-chosen values; user-authored themes that lack the key fall back gracefully.
4. Polygons rendered with solid fill at `zorder=1.5` — above parks (0.8), below roads (2.0). Roads should remain on top of buildings.
5. No new runtime dependencies.

## Non-goals

- Generic-building rendering. Only religious buildings and historic-tagged features. Tagging the entire `building=*` layer would dominate every dense urban poster and isn't what the user asked for.
- A separate colour for religious vs historic. Single `landmark` key keeps the theme schema small and produces a visually coherent layer.
- Building labels, heights, or 3D treatment. Out of scope for this PR.
- Custom subtype filters (e.g. "only Christian churches" or "only castles"). The broad scope is the default and is consistent with how `--show-wetlands` handles all `natural=wetland` subtypes.

## Approach

Two parallel fetch+render layers, similar in structure to the wetlands layer added in the prior PR.

### OSM tag scope

**Religious** — both the structural `building=*` tags and the functional `amenity=place_of_worship` tag, since OSM features can have either or both:

```python
tags = {
    "building": ["church", "cathedral", "chapel", "mosque", "synagogue",
                 "temple", "monastery", "shrine"],
    "amenity": "place_of_worship",
}
```

OSMnx OR's keys in a single query, so one fetch returns the union. Despite the flag name `--show-religious`, the result includes every religion — the scope is "places of worship", not "Christian churches".

**Historic** — every `historic=*` value:

```python
tags = {"historic": True}
```

This catches castles, forts, palaces, manors, ruins, monuments, memorials, archaeological sites, and the generic `historic=building`. The render step filters to `Polygon`/`MultiPolygon` only, so node-only features (most statues, milestones, plaques) are dropped naturally — no crash, just nothing rendered for them.

### Z-order

Sea (0.4) < inland water (0.5) < wetlands (0.6) < parks (0.8) < **landmarks (1.5)** < roads (2.0) < gradient fade (10) < text (11).

Landmarks above parks and water means a church that overlaps a park polygon paints as a landmark, not as park. Below roads means streets still draw on top of building footprints, preserving the existing road-as-figure aesthetic.

### Single render function for both layers

`_render_landmarks(ax, churches_polys, historic_polys, theme)` takes both GeoDataFrames (either may be None) and paints them in one `zorder=1.5` layer using `theme['landmark']`. Two separate fetches but one render call means a single z-stack entry — overlapping religious+historic features paint once.

### Theme key fallback chain

`theme.get('landmark', theme.get('text', '#444444'))`. All 36 built-in themes get explicit `landmark` values during implementation. A user's custom JSON theme without the key falls back to the theme's `text` colour, then to `#444444` as a last resort — guarantees the layer always renders some visible colour.

## Components

All changes in `create_map_poster.py`, `maptoposter_gui.py`, `CHANGELOG.md`, and the 36 theme files in `themes/`.

### `_fetch_religious(point, dist) -> Optional[GeoDataFrame]`

Mirrors `_fetch_wetlands`. Wraps `ox.features_from_point` with the multi-key tag dict for religious buildings. Catches `InsufficientResponseError` at debug (expected for areas with no places of worship), other exceptions at warning. Same docstring style as `_fetch_wetlands` / `_fetch_coastlines`.

### `_fetch_historic(point, dist) -> Optional[GeoDataFrame]`

Same pattern with `tags={"historic": True}`. Returns whatever OSMnx returns — points, lines, and polygons mixed. The render step filters.

### `_render_landmarks(ax, churches_polys, historic_polys, theme)`

Single function for both layers. Receives already-projected, polygon-only GDFs (or None) — the caller runs them through the existing `_project_features` helper before passing them in, exactly like water/parks/wetlands. `_project_features` already filters out non-polygon geometries (so statues, monuments without footprints, and other point features are dropped for free).

For each non-None input GDF:

```python
gdf.plot(ax=ax, facecolor=color, edgecolor='none', zorder=1.5)
```

where `color = theme.get('landmark', theme.get('text', '#444444'))`.

Painting both GDFs in the same `zorder` slot via two `.plot()` calls is fine — matplotlib stacks them within the same z-layer in insertion order.

### `create_poster()` signature

Two new parameters, inserted after `show_wetlands`:

```python
show_religious: bool = False,
show_historic: bool = False,
```

Docstring entries added in the same style as `show_sea` / `show_wetlands`.

### Tqdm extension

Current code computes `total_steps = 3 + (1 if fetch_wetlands else 0)`. Extends to:

```python
fetch_religious = show_religious
fetch_historic = show_historic
total_steps = 3 + (
    (1 if fetch_wetlands else 0)
    + (1 if fetch_religious else 0)
    + (1 if fetch_historic else 0)
)
```

Each enabled layer adds one progress step inside the existing tqdm block, fetched right after wetlands.

Note: religious/historic are NOT gated by `not no_water` (unlike sea/wetlands). They're rendered with the landmark colour, not water colour, so `--no-water` has no semantic claim on them.

### Render pipeline

The render call is placed AFTER `_render_parks`, matching the z-stack reading order (landmarks paint above parks). Z-order is what determines the visual stacking, not the call order — but matching the two avoids future confusion.

```python
if not no_parks:
    _render_parks(ax, parks_polys, theme)

if show_religious or show_historic:
    _render_landmarks(ax, churches_polys, historic_polys, theme)
```

`churches_polys` and `historic_polys` are initialised to `None` when the corresponding flag is off; the render function handles `None` inputs without raising.

### CLI arguments

```python
parser.add_argument('--show-religious', action='store_true',
                   help='Render churches, mosques, synagogues, temples, and other places of worship (off by default)')
parser.add_argument('--show-historic', action='store_true',
                   help='Render castles, palaces, monuments, ruins, and other historic features (off by default)')
```

Placed after `--show-wetlands`, before `--verbose`.

`__main__` kwargs `show_religious=args.show_religious, show_historic=args.show_historic,` added to the `create_poster(` call after `show_wetlands=args.show_wetlands,`.

## GUI integration

Two new switches in the FEATURES toggle column, after `wetlands_sw`:

```python
self.religious_sw = ctk.CTkSwitch(toggle_frame, text=" Religious sites")
self.religious_sw.pack(anchor="w", padx=10, pady=8)

self.historic_sw = ctk.CTkSwitch(toggle_frame, text=" Historical sites")
self.historic_sw.pack(anchor="w", padx=10, pady=8)
```

No `.select()` calls — default OFF, matching CLI default.

Plumbing — six edits total per switch (12 edits across both):

- `_collect_form_settings` — add `"show_religious": self.religious_sw.get()` and `"show_historic": self.historic_sw.get()` after the existing `show_wetlands` entry
- `_apply_settings_to_form` — add `(self.religious_sw, "show_religious", False)` and `(self.historic_sw, "show_historic", False)` to the restore tuple list
- `_collect_generation_params` — `params["show_religious"] = bool(self.religious_sw.get())` and `params["show_historic"] = bool(self.historic_sw.get())` after the existing `show_wetlands` entry
- `_build_subprocess_cmd` — `if params.get("show_religious"): cmd.append("--show-religious")` and the historic equivalent
- `_run_direct` — `show_religious=params.get("show_religious", False),` and `show_historic=params.get("show_historic", False),` in the `create_poster(` kwargs

## Theme schema update

Every JSON in `themes/` gets one new key, `landmark`, placed alphabetically after `gradient_color` (or wherever it lands when the file is JSON-formatted). Initial values are chosen per-theme using the following palette philosophy:

### Palette philosophy by theme family

| Theme family | Approach | Example themes | Indicative palette |
|---|---|---|---|
| Warm / earth | Deeper, richer shade of the dominant accent | terracotta, autumn, sunset, dusty_peach, peach_sorbet, sage_garden, warm_beige, cream_mauve | burnt umber, sepia, deep amber |
| Dark / luxury | Warm gold or brass — pops against dark bg | midnight_blue, noir, enchanted_night, mystical_realm, neon_cyberpunk, night_drive, dragons_lair, copper_patina | aged brass `#B8860B`-ish, antique gold |
| Blueprint | Muted off-white that reads as "drafting paper" | blueprint | `#D4C5A0` parchment |
| Cool / blue | Muted slate or grey-brown for visual weight | ocean, monochrome_blue, hangzhou_ink, cloudy_day, japanese_ink | deep slate, charcoal |
| Pastel / soft | Slightly desaturated mid-tone of the text colour | candy_shop, bubblegum_bright, lavender_dream, misty_lavender, mint_fresh, pastel_dream, soft_sakura, citrus_pop | dusty rose, mauve, lavender-grey |
| Forest / nature | Weathered stone / pewter | forest, elven_forest, emerald | pewter grey, weathered bronze |
| Other | Case-by-case | gradient_roads, contrast_zones, fantasy_realm | tuned to theme |

### Principles applied to every value

- **Visible against `bg`** — minimum 3:1 contrast ratio
- **Distinct from `water` and `parks`** — landmarks should not be visually confused with terrain
- **Distinct from `text`** — building footprints should not compete with city-name labels for attention
- **Harmonious with the overall theme mood** — not jarring

Actual hex values picked one theme at a time during implementation. The full table of chosen values goes into the implementation plan, not the spec.

## Edge cases

| Case | Behaviour |
|---|---|
| Neither flag set | No fetches, no rendering — exact prior behaviour |
| Inland city with no places of worship | `_fetch_religious` returns None (debug log), no render |
| `historic=*` returns only nodes (no polygons) | Polygon filter empties the GDF, render skipped |
| User custom theme without `landmark` key | Falls back to `theme['text']`, then `#444444` |
| Religious + historic overlap (a historic church) | Renders twice in same colour — visually identical to once |
| `--no-water` with `--show-religious` | Religious still renders. Unlike sea/wetlands (which use water colour), landmarks use a separate colour, so `--no-water` does not gate them |
| `--no-roads` with `--show-religious` | Roads suppressed, landmarks still visible — they sit below the road layer |
| Very large radius poster covering a metropolitan area | OSMnx fetches everything; could be slow on first run but cached. No special handling needed |

## Testing

No new unit tests are added for this feature. All the new code is glue:

- `_fetch_religious` / `_fetch_historic` — thin OSMnx wrappers, consistent with the existing no-fetch-test policy
- `_render_landmarks` — matplotlib plotting; the same policy applies as `_render_water` / `_render_wetlands` (no unit tests for side-effecting plotters)
- The polygon-only filtering is inherited from the existing `_project_features` helper, already exercised by the water/parks/wetlands paths

The pre-existing 50-test suite must continue to pass — that's the regression check.

## Manual verification

Out of scope for the spec but planned post-implementation:

- CLI: `python create_map_poster.py -c "Koper" -C "Slovenia" --theme ocean --show-religious --show-historic -d 5000 --show-sea` — combined regression test alongside the previously-added coastal feature; expect both religious sites (the Koper old-town churches) and historic features to render together with the Adriatic
- CLI: `python create_map_poster.py -c "Rome" -C "Italy" --theme terracotta --show-religious -d 5000` — expect dozens of churches visible
- CLI: `python create_map_poster.py -c "Edinburgh" -C "UK" --theme blueprint --show-historic -d 4000` — castle and historic landmarks visible
- CLI: `python create_map_poster.py -c "Istanbul" -C "Turkey" --theme japanese_ink --show-religious -d 8000` — mosques visible (verifies that "religious" really is broader than Christian)
- CLI: no flags on the same cities — byte-identical to current behaviour
- GUI: both toggles work in subprocess mode, defaults are OFF, saved settings persist correctly across launches

## Changelog

`CHANGELOG.md`, two bullets at the top of `[Unreleased] - Community Contributions / Added`:

```
- **Historic feature rendering** - `--show-historic` flag renders OSM `historic=*` polygons (castles, palaces, ruins, monuments, etc.) using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
- **Religious building rendering** - `--show-religious` flag renders churches, mosques, synagogues, temples, and other places of worship using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
```

Plus one bullet in a new `Changed` subsection if absent:

```
- **Theme schema** - new `landmark` colour key added to all 36 built-in themes (used by `--show-religious` and `--show-historic`). User-authored themes without this key fall back to the theme's `text` colour, so no migration is required.
```

## Out of scope (future work)

- A separate `--show-buildings` for the generic `building=*` layer.
- Distinct colours per landmark subtype (religious vs castle vs ruin).
- Building labels (church name, monument name).
- Building height extrusion for 3D-style posters.
- Combined `--show-landmarks` shorthand that enables both `--show-religious` and `--show-historic` (deferrable; users can pass both flags).
