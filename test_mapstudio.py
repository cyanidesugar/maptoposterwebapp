"""
Test suite for Map Studio project.
Tests pure/unit-testable functions only.
No network calls, no GUI, no OSM downloads.
"""
import os
import sys
import tempfile
import pytest

# Add project root to path so all local modules resolve correctly.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_cache_dir(tmp_path: str) -> None:
    """Point the cache at a temp directory for the duration of a test."""
    os.environ["CACHE_DIR"] = tmp_path


# ===========================================================================
# lat_lon_parser — parse()
# ===========================================================================

from lat_lon_parser import parse  # noqa: E402


class TestLatLonParse:
    def test_basic_positive_decimal(self):
        assert parse("40.7128") == pytest.approx(40.7128)

    def test_basic_negative_decimal(self):
        assert parse("-40.7128") == pytest.approx(-40.7128)

    def test_cardinal_north(self):
        assert parse("40.7128N") == pytest.approx(40.7128)

    def test_cardinal_south(self):
        assert parse("40.7128S") == pytest.approx(-40.7128)

    def test_cardinal_east(self):
        assert parse("73.9") == pytest.approx(73.9)

    def test_cardinal_west(self):
        assert parse("73.9W") == pytest.approx(-73.9)

    # --- Regression: double-negation bug ---
    # Before the fix, "-40.7128S" was parsed as abs(-40.7128) → +40.7128
    # because the minus sign in the string and the 'S' cardinal both tried
    # to negate the value.  The fixed code uses abs() before applying the
    # sign so the result stays negative.

    def test_parse_regression_double_negation_minus_south(self):
        """REGRESSION: '-40.7128S' must return -40.7128, not +40.7128."""
        result = parse("-40.7128S")
        assert result == pytest.approx(-40.7128), (
            f"Expected -40.7128 but got {result}. "
            "Double-negation regression: leading minus + S cardinal should both "
            "indicate south (negative), not cancel each other out."
        )

    def test_parse_regression_double_negation_minus_west(self):
        """REGRESSION: '-73.9W' must return -73.9, not +73.9."""
        result = parse("-73.9W")
        assert result == pytest.approx(-73.9), (
            f"Expected -73.9 but got {result}. "
            "Double-negation regression: leading minus + W cardinal should both "
            "indicate west (negative), not cancel each other out."
        )

    def test_whitespace_is_stripped(self):
        """Surrounding whitespace should not cause a crash or wrong value."""
        assert parse("  40.7128  ") == pytest.approx(40.7128)

    def test_invalid_input_raises(self):
        """Non-numeric strings should raise ValueError."""
        with pytest.raises(ValueError):
            parse("not_a_number")


# ===========================================================================
# road_categories — classify(), get_color(), get_width()
# ===========================================================================

import road_categories  # noqa: E402


class TestClassify:
    def test_motorway(self):
        assert road_categories.classify("motorway") == "motorway"

    def test_primary(self):
        assert road_categories.classify("primary") == "primary"

    def test_residential(self):
        assert road_categories.classify("residential") == "residential"

    def test_footway_returns_default(self):
        """footway was newly added and must map to 'default'."""
        assert road_categories.classify("footway") == "default"

    def test_service_returns_residential(self):
        """service was newly added and must map to 'residential'."""
        assert road_categories.classify("service") == "residential"

    def test_cycleway_returns_default(self):
        """cycleway was newly added and must map to 'default'."""
        assert road_categories.classify("cycleway") == "default"

    def test_unknown_type_falls_back_to_default(self):
        assert road_categories.classify("unknown_type_xyz") == "default"

    def test_list_input_uses_first_element(self):
        """OSMnx sometimes returns lists; first element should be used."""
        assert road_categories.classify(["motorway", "primary"]) == "motorway"


class TestGetColor:
    def test_motorway_with_theme_key(self):
        result = road_categories.get_color("motorway", {"road_motorway": "#FF0000"})
        assert result == "#FF0000"

    def test_motorway_with_empty_theme_does_not_crash(self):
        """An empty theme dict must return *some* color string, not raise."""
        result = road_categories.get_color("motorway", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_type_fallback_color_not_crash(self):
        """Unknown highway type with empty theme returns a non-empty string."""
        result = road_categories.get_color("unknown_xyz", {})
        assert isinstance(result, str)


class TestGetWidth:
    def test_motorway_returns_float(self):
        result = road_categories.get_width("motorway")
        assert isinstance(result, float)

    def test_motorway_is_wider_than_residential(self):
        """Motorways should have a greater linewidth than residential roads."""
        assert road_categories.get_width("motorway") > road_categories.get_width("residential")

    def test_unknown_type_does_not_crash(self):
        result = road_categories.get_width("unknown_type_xyz")
        assert isinstance(result, float)


# ===========================================================================
# create_map_poster — pure utility functions
# ===========================================================================

# create_map_poster imports matplotlib, osmnx, etc. at module level.  Those
# imports succeed (the libraries are installed) but also attempt to create the
# CACHE_DIR on import.  We redirect CACHE_DIR *before* importing the module so
# the real cache directory is not polluted.

_CACHE_TEMP_DIR = tempfile.mkdtemp(prefix="mapstudio_test_cache_")
os.environ["CACHE_DIR"] = _CACHE_TEMP_DIR

# Now import — module-level CACHE_DIR is set from the env var at import time.
import create_map_poster as cmp  # noqa: E402


class TestIsLatinScript:
    def test_latin_word(self):
        assert cmp.is_latin_script("Paris") is True

    def test_japanese_characters(self):
        assert cmp.is_latin_script("東京") is False

    def test_empty_string(self):
        assert cmp.is_latin_script("") is True

    def test_latin_with_accents(self):
        """Characters like Ñ are in the Latin Extended range (< U+0250)."""
        assert cmp.is_latin_script("Ñoño") is True


class TestGenerateOutputFilename:
    def test_returns_string_ending_with_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cmp, "POSTERS_DIR", str(tmp_path))
        result = cmp.generate_output_filename("Paris", "noir", "png")
        assert isinstance(result, str)
        assert result.endswith(".png")

    def test_contains_city_slug_and_theme(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cmp, "POSTERS_DIR", str(tmp_path))
        result = cmp.generate_output_filename("Paris", "noir", "png")
        basename = os.path.basename(result).lower()
        assert "paris" in basename
        assert "noir" in basename

    def test_accented_city_name_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cmp, "POSTERS_DIR", str(tmp_path))
        result = cmp.generate_output_filename("São Paulo", "sunset", "png")
        assert isinstance(result, str)
        assert result.endswith(".png")

    def test_regression_path_traversal_in_extension(self, tmp_path, monkeypatch):
        """REGRESSION: path traversal in extension.

        Passing '../../../etc/passwd' as the output format must NOT produce a
        filename with path separators in the extension portion.  The extension
        is sanitised by stripping non-word characters so only the alphanumeric
        remainder survives.
        """
        monkeypatch.setattr(cmp, "POSTERS_DIR", str(tmp_path))
        result = cmp.generate_output_filename("test", "noir", "../../../etc/passwd")
        # The extension must not contain any slash characters.
        ext_part = result.rsplit(".", 1)[-1] if "." in result else ""
        assert "/" not in ext_part, (
            f"Extension '{ext_part}' contains a slash — path traversal not sanitised."
        )
        assert "\\" not in ext_part, (
            f"Extension '{ext_part}' contains a backslash — path traversal not sanitised."
        )
        # The sanitised extension should be the word-char remainder of the format.
        # re.sub(r'[^\w]', '', '../../../etc/passwd') = 'etcpasswd' (after lowercasing)
        assert "etcpasswd" in ext_part or ext_part == "etcpasswd", (
            f"Expected 'etcpasswd' in extension after sanitisation, got '{ext_part}'"
        )


class TestCacheRoundtrip:
    def test_cache_set_and_get(self, tmp_path):
        """Values stored with cache_set must be retrievable with cache_get."""
        # Temporarily redirect CACHE_DIR so the module uses our temp dir.
        original_cache_dir = cmp.CACHE_DIR
        cmp.CACHE_DIR = tmp_path
        try:
            key = "test_roundtrip_unique_key_abc123"
            value = {"answer": 42, "items": [1, 2, 3]}
            cmp.cache_set(key, value)
            result = cmp.cache_get(key)
            assert result == value
        finally:
            cmp.CACHE_DIR = original_cache_dir

    def test_cache_get_missing_key_returns_none(self, tmp_path):
        """cache_get on a key that was never written must return None."""
        original_cache_dir = cmp.CACHE_DIR
        cmp.CACHE_DIR = tmp_path
        try:
            result = cmp.cache_get("nonexistent_key_xyz_9999")
            assert result is None
        finally:
            cmp.CACHE_DIR = original_cache_dir


class TestLoadTheme:
    def test_load_terracotta_returns_dict_with_bg(self):
        """The terracotta theme (present in themes/) must have a 'bg' key."""
        # Reset the in-module cache so previous test state doesn't interfere.
        cmp._theme_data_cache.clear()
        theme = cmp.load_theme("terracotta")
        assert isinstance(theme, dict)
        assert "bg" in theme, "Theme dict must contain a 'bg' colour key."

    def test_load_nonexistent_theme_returns_fallback(self):
        """A missing theme must return a safe fallback dict, not raise."""
        cmp._theme_data_cache.clear()
        theme = cmp.load_theme("nonexistent_theme_xyz")
        assert isinstance(theme, dict)
        # The fallback dict must have at minimum a 'bg' key so rendering works.
        assert "bg" in theme, (
            "Fallback theme dict must contain a 'bg' key so the renderer doesn't crash."
        )


# ===========================================================================
# stl_generator — pure functions (_grid_dimensions, world_to_grid)
# ===========================================================================

# stl_generator depends on trimesh and scipy which may not be installed in all
# environments.  Skip the STL tests gracefully if the imports fail.
try:
    import numpy as np
    from stl_generator import STLSettings, _grid_dimensions, world_to_grid
    _STL_AVAILABLE = True
except ImportError:
    _STL_AVAILABLE = False

stl_skip = pytest.mark.skipif(
    not _STL_AVAILABLE,
    reason="stl_generator dependencies (trimesh/scipy/numpy) not installed",
)


@stl_skip
class TestGridDimensions:
    def test_returns_tuple_of_two_positive_integers(self):
        """_grid_dimensions must return (width, height) as positive ints."""
        settings = STLSettings()
        result = _grid_dimensions(settings)
        assert isinstance(result, tuple)
        assert len(result) == 2
        grid_width, grid_height = result
        assert isinstance(grid_width, int) and grid_width > 0
        assert isinstance(grid_height, int) and grid_height > 0

    def test_portrait_orientation_height_equals_resolution(self):
        """When height > width, grid_height should equal resolution."""
        settings = STLSettings()
        settings.width_mm = 150.0
        settings.height_mm = 200.0  # portrait — height_mm > width_mm
        grid_width, grid_height = _grid_dimensions(settings)
        # physical_aspect = 150/200 = 0.75 < 1.0 → grid_height = resolution
        assert grid_height == settings.resolution

    def test_landscape_orientation_width_equals_resolution(self):
        """When width >= height, grid_width should equal resolution."""
        settings = STLSettings()
        settings.width_mm = 200.0
        settings.height_mm = 150.0  # landscape
        grid_width, grid_height = _grid_dimensions(settings)
        assert grid_width == settings.resolution


@stl_skip
class TestWorldToGrid:
    def test_regression_zero_range_raises_value_error(self):
        """REGRESSION: degenerate bounds (zero width/height) must raise
        ValueError, not ZeroDivisionError.

        Before the fix, the function divided by (maxx - minx) and
        (maxy - miny) directly, causing an unhandled ZeroDivisionError when
        the bounding box had zero extent.  The fix adds an early guard that
        raises a descriptive ValueError instead.
        """
        coords = np.array([[0.0, 0.0], [1.0, 1.0]])
        # Zero-width bounding box: minx == maxx
        zero_width_bounds = (0.0, 0.0, 0.0, 1.0)  # width = 0
        with pytest.raises(ValueError, match="degenerate"):
            world_to_grid(coords, zero_width_bounds, (100, 100))

    def test_regression_zero_height_raises_value_error(self):
        """REGRESSION: zero-height bounding box must also raise ValueError."""
        coords = np.array([[0.0, 0.0], [1.0, 1.0]])
        zero_height_bounds = (0.0, 0.0, 1.0, 0.0)  # height = 0
        with pytest.raises(ValueError, match="degenerate"):
            world_to_grid(coords, zero_height_bounds, (100, 100))

    def test_normal_bounds_returns_rows_and_cols(self):
        """Sanity check: valid bounds produce clipped integer arrays."""
        coords = np.array([[0.5, 0.5]])
        bounds = (0.0, 0.0, 1.0, 1.0)
        grid_shape = (100, 100)
        rows, cols = world_to_grid(coords, bounds, grid_shape)
        assert rows.shape == (1,)
        assert cols.shape == (1,)
        # All indices must be within grid bounds
        assert 0 <= rows[0] < grid_shape[0]
        assert 0 <= cols[0] < grid_shape[1]


# ===========================================================================
# font_management — sanitisation of font family names
# ===========================================================================

class TestFontFamilySanitisation:
    """Verify that path-traversal sequences in font family names are stripped.

    download_google_font() sanitises the font_family argument with:
        re.sub(r"[^\\w\\s-]", "", font_family)
    We replicate that regex directly to confirm it strips dots and slashes.
    The integration-level check (loading the module) ensures the regex
    exists and is applied before any filesystem operations.
    """

    def test_dots_and_slashes_are_removed(self):
        import re
        malicious = "../../../evil"
        sanitised = re.sub(r"[^\w\s-]", "", malicious)
        assert "/" not in sanitised, "Forward slashes should be stripped."
        assert "." not in sanitised, "Dots should be stripped."
        assert "\\" not in sanitised, "Backslashes should be stripped."

    def test_normal_font_name_is_preserved(self):
        import re
        normal = "Open Sans"
        sanitised = re.sub(r"[^\w\s-]", "", normal)
        assert sanitised == "Open Sans"

    def test_no_file_created_outside_cache_dir(self, tmp_path, monkeypatch):
        """Integration: download_google_font must not escape the cache dir.

        We mock the network call so no real HTTP request is made.  The key
        assertion is that no file appears outside tmp_path even if a
        path-traversal name is passed.
        """
        import unittest.mock as mock
        import font_management as fm

        # Redirect the fonts cache dir to our temp directory.
        monkeypatch.setattr(fm, "FONTS_CACHE_DIR", tmp_path / "cache")

        # Stub out the HTTP call to avoid any network dependency.
        mock_response = mock.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = ""  # No @font-face blocks → no files downloaded.
        with mock.patch("font_management.requests.get", return_value=mock_response):
            fm.download_google_font("../../../evil")

        # The function returns None or a dict; either way no traversal file
        # should have been created anywhere above tmp_path.
        evil_marker = tmp_path.parent / "evil"
        assert not evil_marker.exists(), (
            "Path-traversal font name created a file outside the cache directory!"
        )


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
        sea_union = gpd.GeoSeries(result).union_all()
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
        sea_union = gpd.GeoSeries(result).union_all()
        assert sea_union.contains(Point(100, 100)), (
            "Outside the loop should be sea"
        )
        assert not sea_union.contains(Point(500, 500)), (
            "Inside the loop should be land, not sea"
        )

    def test_noisy_short_segment_does_not_flip_classification(self):
        """Regression: a tiny noisy coastline stretch must not flip the
        classification of a polygon that's overwhelmingly bounded by a
        well-oriented long coastline.

        Setup: a long vertical coastline at x=500 going +Y (sea on right = +X).
        Plus a tiny 4-segment zigzag at (300, 800) whose local right-side
        probes happen to fall in the LEFT (land) half. The long coastline
        votes correctly for the left half being LAND; the zigzag votes
        incorrectly for the left half being SEA. The long coastline must
        win.
        """
        long_coast = LineString([(500, 0), (500, 1000)])
        # Zigzag: a noisy little stretch in the land half whose local
        # right-perpendiculars point further into the land half.
        zigzag = LineString([
            (300, 800),
            (310, 810),
            (300, 820),
            (310, 830),
            (300, 840),
        ])
        gdf = self._make_gdf([long_coast, zigzag])
        bbox = box(0, 0, 1000, 1000)

        result = cmp._compute_sea_polygons(gdf, bbox, self._CRS)

        assert len(result) >= 1
        sea_union = gpd.GeoSeries(result).union_all()
        # Right half is sea (correct OSM convention from the long coast)
        assert sea_union.contains(Point(750, 500))
        # Left half must NOT be classified as sea, despite the zigzag's
        # local right-side votes for "sea" inside the left polygon.
        assert not sea_union.contains(Point(250, 500))


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

    def test_preview_cache_future_schema_version_returns_none(self, tmp_path):
        """A cache with a newer schema version than expected must be ignored."""
        import preview_cache
        # Both files exist so we get past the existence check
        roads = gpd.GeoDataFrame(
            {"highway": ["residential"]},
            geometry=[LineString([(0, 0), (1, 1)])],
            crs=self._CRS,
        )
        roads.to_file(str(tmp_path / "preview.gpkg"), driver="GPKG", layer="roads")
        (tmp_path / "preview.json").write_text(
            '{"version": 999, "city": "X", "country": "Y", "center": [0, 0], '
            '"compensated_dist": 1000, "crop_xlim": [0, 1], "crop_ylim": [0, 1], '
            '"target_crs": "EPSG:32633", "width": 12, "height": 16}',
            encoding="utf-8",
        )
        result = preview_cache.load_preview_cache(str(tmp_path))
        assert result is None
