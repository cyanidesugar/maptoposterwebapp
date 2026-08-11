# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-08-09 (Overpass reliability)

### Fixed
- **Overpass fetch reliability** - the street-network fetch no longer fails when
  the default Overpass server is slow, overloaded, or unreachable. `fetch_graph()`
  now:
  - Tries a prioritised list of planet-wide Overpass endpoints
    (`lz4.overpass-api.de` first, then `z.`/`overpass-api.de`, `maps.mail.ru`,
    `kumi.systems`, `private.coffee`) with automatic fail-over.
  - Health-probes each endpoint with a trivial query before sending the heavy
    request, so dead/stalled servers are skipped in seconds instead of hanging on
    the long read timeout.
  - Re-probes the whole list for several rounds (Overpass congestion is transient).
- **`lz4.overpass-api.de` is the new default endpoint** - its IP (65.x) is
  reachable from many networks where the main `overpass-api.de` hostname (162.x)
  is not; the bare hostname is demoted to a mid-list fallback.
- **Force IPv4 for outbound HTTP** - several Overpass hosts publish unroutable
  IPv6 records; Python's requests library tried them first and ate the full
  connect timeout before falling back to IPv4. Name resolution is now restricted
  to IPv4 (disable with `MAPTOPOSTER_FORCE_IPV4=0`).
- **Valid Overpass query timeout** - the request timeout is a plain integer
  again; OSMnx interpolates it into the query's `[timeout:N]` clause, so a tuple
  produced an invalid query that strict servers rejected.

### Added
- Environment overrides: `MAPTOPOSTER_OVERPASS_URL` (preferred endpoint first),
  `MAPTOPOSTER_OVERPASS_TIMEOUT` (read-timeout seconds),
  `MAPTOPOSTER_OVERPASS_ROUNDS` (fail-over passes), `MAPTOPOSTER_FORCE_IPV4`.

---

## [0.4.0] - 2026-05-25 (Community Contributions, @gabr42)

### Added
- **Live theme preview** - The desktop GUI now shows a thumbnail of the most-recently-generated location in the OUTPUT column, re-rendered automatically when the theme dropdown changes. The cache (`preview_cache/preview.gpkg` + `preview_cache/preview.json`) survives app restart. Includes a new `--write-preview-cache <DIR>` CLI flag and a `write_preview_cache` parameter on `create_poster()` (GUI infrastructure; off by default).
- **Historic feature rendering** - `--show-historic` flag renders OSM `historic=*` polygons (castles, palaces, ruins, monuments, etc.) using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
- **Religious building rendering** - `--show-religious` flag renders churches, mosques, synagogues, temples, and other places of worship using the theme's new `landmark` colour. Off by default; existing behaviour unchanged.
- **Wetland rendering** - `--show-wetlands` flag renders OSM `natural=wetland` polygons (marshes, reedbeds, swamps, etc.) using the theme's `water` colour, useful for areas like the Bertoška Bonifika near Koper that are technically marshes but visually water bodies. Off by default; existing behaviour unchanged.
- **Open sea/ocean rendering** - `--show-sea` flag renders the open sea for coastal locations using the theme's `water` colour. Uses OSM `natural=coastline` data and the OSM left-land/right-sea convention. Off by default; existing behaviour unchanged.
- **uv package manager support** ([PR #20](https://github.com/originalankur/maptoposter/pull/20))
  - Added `pyproject.toml` with project metadata and dependencies
  - Added `uv.lock` for reproducible builds
  - Added shebang to `create_map_poster.py` for direct execution
  - Updated README with uv installation instructions
- **Python version specification** - `requires-python = ">=3.11"` in pyproject.toml (fixes [#79](https://github.com/originalankur/maptoposter/issues/79))
- **Coordinate override** - `--latitude` and `--longitude` arguments to override the geocoded center point (existing from upstream PR #106, clarifies [#100](https://github.com/originalankur/maptoposter/issues/100))
  - Still requires `--city` and `--country` for display name
  - Useful for precise location control

### Fixed
- **Historic/religious layer "ghost buildings"** - `--show-historic` and `--show-religious` now drop features that also carry a `landuse=*` tag. OSM occasionally tags a land-use area (e.g. a former factory site marked `historic=ruins` + `landuse=brownfield`) with a historic or religious value; without this filter, the entire land area rendered as a misleading building footprint.
- **Z-order bug** - Roads now render above parks and water features (fixes [#39](https://github.com/originalankur/maptoposter/issues/39), relates to [PR #42](https://github.com/originalankur/maptoposter/pull/42))
  - Water layer: `zorder=1` → `zorder=0.5`
  - Parks layer: `zorder=2` → `zorder=0.8`
  - Roads remain at `zorder=2` (matplotlib default), ensuring proper layering
- **Text scaling for landscape orientations** - Font size now scales based on `min(height, width)` instead of just width (fixes [#112](https://github.com/originalankur/maptoposter/issues/112))

### Changed
- Updated `.gitignore` with poster outputs, Python build artifacts, IDE files, and OS-specific files
- **Theme schema** - new `landmark` colour key added to all 36 built-in themes (used by `--show-religious` and `--show-historic`). User-authored themes without this key fall back to the theme's `text` colour, so no migration is required.

---

## [0.3.0] - 2026-01-27 (Maintainer: @originalankur)

### Added
- **Custom coordinates support** - `--latitude` and `--longitude` arguments ([#106](https://github.com/originalankur/maptoposter/pull/106))
- **Emerald theme** - Lush dark green aesthetic with mint accents ([#114](https://github.com/originalankur/maptoposter/pull/114))
- **GitHub Actions** - PR checks workflow ([#98](https://github.com/originalankur/maptoposter/pull/98))
- **Conflict labeling** - Auto-label PRs with merge conflicts

### Changed
- **Default theme** changed from `feature_based` to `terracotta` ([#131](https://github.com/originalankur/maptoposter/pull/131))
- **Default distance** changed from 12000m to 18000m ([#128](https://github.com/originalankur/maptoposter/pull/128))
- **Max dimensions** enforced at 20 inches for width/height (supports up to 4K resolution) ([#128](https://github.com/originalankur/maptoposter/pull/128), [#129](https://github.com/originalankur/maptoposter/pull/129))

### Removed
- `feature_based` theme ([#131](https://github.com/originalankur/maptoposter/pull/131))

### Fixed
- Cache directory handling ([#109](https://github.com/originalankur/maptoposter/pull/109))
- Dynamic font scaling based on poster width

---

## [0.2.1] - 2026-01-18 (Maintainer: @originalankur)

### Added
- **SVG/PDF export** - `--format` flag for vector output ([#57](https://github.com/originalankur/maptoposter/pull/57))
- **Variable poster dimensions** - `-W` and `-H` arguments ([#59](https://github.com/originalankur/maptoposter/pull/59))
- **Caching** - Downloaded OSM data is now cached locally
- **Rate limiting** - 0.3s delay between API requests

### Fixed
- Map warping issues with variable dimensions ([#59](https://github.com/originalankur/maptoposter/pull/59))
- Edge nodes retention for complete road networks ([#27](https://github.com/originalankur/maptoposter/pull/27))
- Point geometry filtering to prevent dots on maps
- Dynamic font size adjustment for long city names
- Nominatim timeout increased to 10 seconds

### Changed
- Graph projection to linear coordinates for proper aspect ratio
- Improved cache handling with hashed filenames and error handling

---

## [0.2.0] - 2026-01-17 (Tag: v0.2)

### Added
- Example poster images in README
- Initial theme collection

---

## [0.1.0] - 2026-01-17 (Initial Release)

### Added
- Initial maptoposter source code
- README with usage instructions
- 17 built-in themes:
  - autumn, blueprint, contrast_zones, copper_patina
  - forest, gradient_roads, japanese_ink, midnight_blue
  - monochrome_blue, neon_cyberpunk, noir, ocean
  - pastel_dream, sunset, terracotta, warm_beige
- Core features:
  - City/country based map generation
  - Customizable themes via JSON
  - Road hierarchy coloring
  - Water and park feature rendering
  - Typography with Roboto font
  - Coordinate display
  - OSM attribution
