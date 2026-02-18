#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

# Force UTF-8 encoding for Windows console (only if stdout has a buffer attribute)
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass  # Already redirected or wrapped
"""
City Map Poster Generator

This module generates beautiful, minimalist map posters for any city in the world.
It fetches OpenStreetMap data using OSMnx, applies customizable themes, and creates
high-quality poster-ready images with roads, water features, and parks.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast
import xml.etree.ElementTree as ET

# Workaround for PyInstaller: Mock package metadata if not available
if getattr(sys, 'frozen', False):
    # Running as exe - mock metadata to prevent errors
    try:
        import importlib.metadata as metadata
        original_version = metadata.version

        def version_with_fallback(package_name: str) -> str:
            try:
                return original_version(package_name)
            except Exception:
                return "1.0.0"

        metadata.version = version_with_fallback
    except Exception:
        pass

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from geopandas import GeoDataFrame
from geopy.geocoders import Nominatim
from lat_lon_parser import parse
from font_management import load_fonts
from matplotlib.font_manager import FontProperties
from networkx import MultiDiGraph
from shapely.geometry import Point
from tqdm import tqdm

import road_categories

# --- Logging setup ---
logger = logging.getLogger("maptoposter")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# STL generation support (optional - will fail gracefully if not available)
try:
    from stl_generator import generate_stl, STLSettings
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    logger.info("STL generation not available - install trimesh and scipy for 3D printing support")


class CacheError(Exception):
    """Raised when a cache operation fails."""
    pass


CACHE_DIR_PATH = os.environ.get("CACHE_DIR", "cache")
CACHE_DIR = Path(CACHE_DIR_PATH)
CACHE_DIR.mkdir(exist_ok=True)

# Determine the correct base path (works for both script and EXE)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

THEMES_DIR = os.path.join(BASE_DIR, "themes")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
POSTERS_DIR = os.path.join(BASE_DIR, "posters")

FONTS = load_fonts()

# --- Module-level caches ---
_themes_cache: Optional[list[str]] = None
_theme_data_cache: dict[str, dict] = {}


def _cache_path(key: str) -> str:
    """Generate a safe cache file path from a cache key using a hash."""
    safe = hashlib.sha256(key.encode()).hexdigest()[:32]
    return os.path.join(CACHE_DIR, f"{safe}.json")


def cache_get(key: str) -> Any:
    """
    Retrieve a cached object by key.

    Returns:
        Cached object if found, None otherwise

    Raises:
        CacheError: If cache read operation fails
    """
    try:
        path = _cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Incompatible old cache file (e.g. pickle), remove it
        try:
            os.remove(path)
        except OSError:
            pass
        return None
    except Exception as e:
        raise CacheError(f"Cache read failed: {e}") from e


def cache_set(key: str, value: Any) -> None:
    """
    Store a JSON-serializable object in the cache.

    Raises:
        CacheError: If cache write operation fails
    """
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        path = _cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f)
    except Exception as e:
        raise CacheError(f"Cache write failed: {e}") from e


def is_latin_script(text: str) -> bool:
    """
    Check if text is primarily Latin script.
    Used to determine if letter-spacing should be applied to city names.
    """
    if not text:
        return True

    latin_count = 0
    total_alpha = 0

    for char in text:
        if char.isalpha():
            total_alpha += 1
            if ord(char) < 0x250:
                latin_count += 1

    if total_alpha == 0:
        return True

    return (latin_count / total_alpha) > 0.8


def generate_output_filename(city: str, theme_name: str, output_format: str) -> str:
    """Generate unique output filename with city, theme, and datetime."""
    os.makedirs(POSTERS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(" ", "_")
    ext = output_format.lower()
    filename = f"{city_slug}_{theme_name}_{timestamp}.{ext}"
    return os.path.join(POSTERS_DIR, filename)


def get_available_themes() -> list[str]:
    """
    Scans the themes directory and returns a list of available theme names.
    Results are cached after the first call.
    """
    global _themes_cache
    if _themes_cache is not None:
        return _themes_cache

    logger.debug("Looking for themes in: %s", THEMES_DIR)

    if not os.path.exists(THEMES_DIR):
        logger.warning("Themes directory not found, creating: %s", THEMES_DIR)
        os.makedirs(THEMES_DIR)
        return []

    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith(".json"):
            theme_name = file[:-5]
            themes.append(theme_name)

    logger.debug("Total themes found: %d", len(themes))
    _themes_cache = themes
    return themes


def load_theme(theme_name: str = "terracotta") -> dict[str, str]:
    """Load theme from JSON file in themes directory. Results are cached."""
    if theme_name in _theme_data_cache:
        return _theme_data_cache[theme_name]

    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")

    if not os.path.exists(theme_file):
        logger.warning("Theme file '%s' not found. Using default terracotta theme.", theme_file)
        return {
            "name": "Terracotta",
            "description": "Mediterranean warmth - burnt orange and clay tones on cream",
            "bg": "#F5EDE4",
            "text": "#8B4513",
            "gradient_color": "#F5EDE4",
            "water": "#A8C4C4",
            "parks": "#E8E0D0",
            "road_motorway": "#A0522D",
            "road_primary": "#B8653A",
            "road_secondary": "#C9846A",
            "road_tertiary": "#D9A08A",
            "road_residential": "#E5C4B0",
            "road_default": "#D9A08A",
        }

    with open(theme_file, "r") as f:
        theme = json.load(f)
        logger.info("Loaded theme: %s", theme.get('name', theme_name))
        if "description" in theme:
            logger.info("  %s", theme['description'])
        _theme_data_cache[theme_name] = theme
        return theme


def create_gradient_fade(
    ax: plt.Axes,
    color: str,
    location: str = "bottom",
    zorder: int = 10,
) -> None:
    """Creates a fade effect at the top or bottom of the map."""
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))

    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]

    if location == "bottom":
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 0.75
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]

    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end

    ax.imshow(
        gradient,
        extent=[xlim[0], xlim[1], y_bottom, y_top],
        aspect="auto",
        cmap=custom_cmap,
        zorder=zorder,
        origin="lower",
    )


def get_edge_colors_by_type(g: MultiDiGraph, theme: dict[str, str]) -> list[str]:
    """Assigns colors to edges based on road type hierarchy using shared road_categories."""
    return [
        road_categories.get_color(data.get('highway', 'unclassified'), theme)
        for _u, _v, data in g.edges(data=True)
    ]


def get_edge_widths_by_type(g: MultiDiGraph) -> list[float]:
    """Assigns line widths to edges based on road type using shared road_categories."""
    return [
        road_categories.get_width(data.get('highway', 'unclassified'))
        for _u, _v, data in g.edges(data=True)
    ]


def get_coordinates(city: str, country: str) -> tuple[float, float]:
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    cache_key = f"coords_{city.lower()}_{country.lower()}"
    cached = cache_get(cache_key)
    if cached:
        logger.info("Using cached coordinates for %s, %s", city, country)
        return tuple(cached)

    logger.info("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster", timeout=10)

    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)

    try:
        location = geolocator.geocode(f"{city}, {country}")
    except Exception as e:
        raise ValueError(f"Geocoding failed for {city}, {country}: {e}") from e

    if asyncio.iscoroutine(location):
        try:
            location = asyncio.run(location)
        except RuntimeError as exc:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError(
                    "Geocoder returned a coroutine while an event loop is already running. "
                    "Run this script in a synchronous environment."
                ) from exc
            location = loop.run_until_complete(location)

    if location:
        addr = getattr(location, "address", None)
        if addr:
            logger.info("Found: %s", addr)
        else:
            logger.info("Found location (address not available)")
        logger.info("Coordinates: %s, %s", location.latitude, location.longitude)
        try:
            cache_set(cache_key, [location.latitude, location.longitude])
        except CacheError as e:
            logger.warning("Could not cache coordinates: %s", e)
        return (location.latitude, location.longitude)

    raise ValueError(f"Could not find coordinates for {city}, {country}")


def validate_coordinates(lat: float, lon: float) -> None:
    """Validate that coordinates are within valid ranges."""
    if not -90 <= lat <= 90:
        raise ValueError(f"Latitude {lat} out of range. Must be between -90 and 90.")
    if not -180 <= lon <= 180:
        raise ValueError(f"Longitude {lon} out of range. Must be between -180 and 180.")


def get_crop_limits(
    g_proj: MultiDiGraph,
    center_lat_lon: tuple[float, float],
    fig: plt.Figure,
    dist: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Crop inward to preserve aspect ratio while guaranteeing
    full coverage of the requested radius.
    """
    lat, lon = center_lat_lon

    center = (
        ox.projection.project_geometry(
            Point(lon, lat),
            crs="EPSG:4326",
            to_crs=g_proj.graph["crs"]
        )[0]
    )
    center_x, center_y = center.x, center.y

    fig_width, fig_height = fig.get_size_inches()
    aspect = fig_width / fig_height

    half_x = dist
    half_y = dist

    if aspect > 1:
        half_y = half_x / aspect
    else:
        half_x = half_y * aspect

    return (
        (center_x - half_x, center_x + half_x),
        (center_y - half_y, center_y + half_y),
    )


def fetch_graph(
    point: tuple[float, float],
    dist: float,
    network_type: str = "all",
) -> Optional[MultiDiGraph]:
    """
    Fetch street network graph from OpenStreetMap.

    Args:
        point: (latitude, longitude) tuple for center point
        dist: Distance in meters from center point
        network_type: OSMnx network type ('drive', 'walk', 'bike', or 'all')
    """
    try:
        g = ox.graph_from_point(
            point, dist=dist, dist_type='bbox',
            network_type=network_type, truncate_by_edge=True,
        )
        time.sleep(0.5)
        return g
    except Exception as e:
        logger.error("OSMnx error while fetching graph: %s", e)
        return None


def fetch_features(
    point: tuple[float, float],
    dist: float,
    tags: dict[str, str],
    name: str,
) -> Optional[GeoDataFrame]:
    """
    Fetch geographic features (water, parks, etc.) from OpenStreetMap.
    """
    lat, lon = point

    # Note: GeoDataFrames are not JSON-serializable, so we rely on OSMnx caching.
    try:
        data = ox.features_from_point(point, tags=tags, dist=dist)
        time.sleep(0.3)
        return data
    except Exception as e:
        logger.error("OSMnx error while fetching %s: %s", name, e)
        return None


def organize_svg_layers(svg_path: str) -> None:
    """
    Post-process SVG to organize road lines into layers by width.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = {'svg': 'http://www.w3.org/2000/svg'}
    paths = root.findall('.//svg:path', ns)

    layers: dict[str, dict] = {
        'motorway': {'name': 'Motorways', 'width': 1.2, 'paths': []},
        'primary': {'name': 'Primary_Roads', 'width': 1.0, 'paths': []},
        'secondary': {'name': 'Secondary_Roads', 'width': 0.8, 'paths': []},
        'tertiary': {'name': 'Tertiary_Roads', 'width': 0.6, 'paths': []},
        'residential': {'name': 'Residential_&_Other', 'width': 0.4, 'paths': []},
    }

    for path in paths:
        style = path.get('style', '')
        if 'stroke-width' in style:
            for part in style.split(';'):
                if 'stroke-width' in part:
                    try:
                        width = float(part.split(':')[1].strip())
                        if width >= 1.15:
                            layers['motorway']['paths'].append(path)
                        elif width >= 0.9:
                            layers['primary']['paths'].append(path)
                        elif width >= 0.7:
                            layers['secondary']['paths'].append(path)
                        elif width >= 0.5:
                            layers['tertiary']['paths'].append(path)
                        else:
                            layers['residential']['paths'].append(path)
                    except (ValueError, IndexError):
                        pass

    g_elements = root.findall('.//svg:g', ns)
    if g_elements:
        parent = root
        insert_index = list(parent).index(g_elements[0])

        for layer_key in ['residential', 'tertiary', 'secondary', 'primary', 'motorway']:
            layer = layers[layer_key]
            if layer['paths']:
                layer_group = ET.Element('{http://www.w3.org/2000/svg}g')
                layer_group.set('id', f"layer_{layer_key}_{layer['name']}_width_{layer['width']}")

                for path in layer['paths']:
                    for elem in root.iter():
                        if path in list(elem):
                            elem.remove(path)
                            break
                    layer_group.append(path)

                parent.insert(insert_index, layer_group)

    tree.write(svg_path, encoding='utf-8', xml_declaration=True)
    logger.info("SVG layers organized in %s", svg_path)


# --- Rendering sub-functions (refactored from monolithic create_poster) ---

def _project_features(
    features: Optional[GeoDataFrame],
    g_proj: MultiDiGraph,
) -> Optional[GeoDataFrame]:
    """Filter to polygons and project features to match graph CRS."""
    if features is None or features.empty:
        return None
    polys = features[features.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if polys.empty:
        return None
    try:
        return ox.projection.project_gdf(polys)
    except Exception:
        return polys.to_crs(g_proj.graph['crs'])


def _render_water(
    ax: plt.Axes,
    water_polys: Optional[GeoDataFrame],
    theme: dict[str, str],
) -> None:
    """Render water polygons on the map axes."""
    if water_polys is not None and not water_polys.empty:
        water_polys.plot(ax=ax, facecolor=theme['water'], edgecolor='none', zorder=0.5)


def _render_parks(
    ax: plt.Axes,
    parks_polys: Optional[GeoDataFrame],
    theme: dict[str, str],
) -> None:
    """Render park polygons on the map axes."""
    if parks_polys is not None and not parks_polys.empty:
        parks_polys.plot(ax=ax, facecolor=theme['parks'], edgecolor='none', zorder=0.8)


def _render_roads(
    ax: plt.Axes,
    g_proj: MultiDiGraph,
    theme: dict[str, str],
) -> None:
    """Render road network on the map axes."""
    edge_colors = get_edge_colors_by_type(g_proj, theme)
    edge_widths = get_edge_widths_by_type(g_proj)
    ox.plot_graph(
        g_proj, ax=ax, bgcolor=theme['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False,
        close=False,
    )


def _render_text(
    ax: plt.Axes,
    display_city: str,
    display_country: str,
    point: tuple[float, float],
    theme: dict[str, str],
    font_family: str,
    width: float,
    height: float,
    city_font_size: Optional[float],
    country_font_size: Optional[float],
    coords_font_size: Optional[float],
) -> None:
    """Render all text elements (city, country, coordinates, divider) on the poster."""
    scale_factor = min(height, width) / 12.0

    BASE_MAIN = city_font_size if city_font_size is not None else 60
    BASE_SUB = country_font_size if country_font_size is not None else 30
    BASE_COORDS = coords_font_size if coords_font_size is not None else 22

    font_main = FontProperties(family=font_family, weight="bold", size=BASE_MAIN * scale_factor)
    font_sub = FontProperties(family=font_family, weight="normal", size=BASE_SUB * scale_factor)
    font_coords = FontProperties(family=font_family, weight="normal", size=BASE_COORDS * scale_factor)

    # Format city name based on script type
    if is_latin_script(display_city):
        spaced_city = "  ".join(list(display_city.upper()))
    else:
        spaced_city = display_city

    # Dynamically adjust font size for long city names
    base_adjusted_main = BASE_MAIN * scale_factor
    city_char_count = len(display_city)
    if city_char_count > 10:
        length_factor = 10 / city_char_count
        adjusted_font_size = max(base_adjusted_main * length_factor, 10 * scale_factor)
    else:
        adjusted_font_size = base_adjusted_main

    font_main_adjusted = FontProperties(
        family=font_family,
        weight="bold",
        size=adjusted_font_size,
    )

    # Dynamic text positioning
    fig_height_pts = height * 72
    city_line_height = (adjusted_font_size * 1.8) / fig_height_pts
    country_line_height = (BASE_SUB * scale_factor * 1.8) / fig_height_pts
    coords_line_height = (BASE_COORDS * scale_factor * 1.8) / fig_height_pts
    divider_gap = (8 * scale_factor) / fig_height_pts
    city_country_gap = 0.3
    base_bottom = 0.03

    coords_y = base_bottom + coords_line_height * 0.5
    divider_y = coords_y + coords_line_height * 0.5 + divider_gap
    country_y = divider_y + divider_gap + country_line_height * 0.5
    city_y = country_y + country_line_height * city_country_gap + city_line_height * city_country_gap

    ax.text(
        0.5, city_y, spaced_city,
        transform=ax.transAxes, color=theme["text"],
        ha="center", fontproperties=font_main_adjusted, zorder=11,
    )

    ax.text(
        0.5, country_y, display_country.upper(),
        transform=ax.transAxes, color=theme["text"],
        ha="center", fontproperties=font_sub, zorder=11,
    )

    lat, lon = point
    if lat >= 0:
        coords_str = f"{lat:.4f}\u00b0 N / {abs(lon):.4f}\u00b0 {'E' if lon >= 0 else 'W'}"
    else:
        coords_str = f"{abs(lat):.4f}\u00b0 S / {abs(lon):.4f}\u00b0 {'E' if lon >= 0 else 'W'}"

    ax.text(
        0.5, coords_y, coords_str,
        transform=ax.transAxes, color=theme["text"], alpha=0.7,
        ha="center", fontproperties=font_coords, zorder=11,
    )

    ax.plot(
        [0.4, 0.6], [divider_y, divider_y],
        transform=ax.transAxes, color=theme["text"],
        linewidth=1 * scale_factor, zorder=11,
    )


def create_poster(
    city: str,
    country: str,
    point: tuple[float, float],
    dist: int,
    output_file: str,
    output_format: str,
    width: float = 12,
    height: float = 16,
    country_label: Optional[str] = None,
    display_city: Optional[str] = None,
    display_country: Optional[str] = None,
    fonts: Optional[dict] = None,
    svg_layers: bool = False,
    stl_settings: Any = None,
    city_font_size: Optional[float] = None,
    country_font_size: Optional[float] = None,
    coords_font_size: Optional[float] = None,
    show_text: bool = True,
    no_roads: bool = False,
    no_water: bool = False,
    no_parks: bool = False,
    font_family: str = "sans-serif",
    theme: Optional[dict[str, str]] = None,
    network_type: str = "all",
) -> None:
    """
    Generate a complete map poster with roads, water, parks, and typography.

    Args:
        city: City name for display on poster
        country: Country name for display on poster
        point: (latitude, longitude) tuple for map center
        dist: Map radius in meters
        output_file: Path where poster will be saved
        output_format: File format ('png', 'svg', 'pdf', or 'stl')
        width: Poster width in inches (default: 12)
        height: Poster height in inches (default: 16)
        country_label: Optional override for country text on poster
        display_city: Custom display name for city
        display_country: Custom display name for country
        fonts: Custom font dictionary
        svg_layers: If True and format is SVG, organize roads into layers by width
        stl_settings: STLSettings object for STL output
        city_font_size: Custom font size for city name
        country_font_size: Custom font size for country name
        coords_font_size: Custom font size for coordinates text
        show_text: If False, hide all text labels from the poster
        no_roads: If True, hide roads
        no_water: If True, hide water features
        no_parks: If True, hide park features
        font_family: Font family name for text rendering
        theme: Theme dictionary (required)
        network_type: OSMnx network type ('drive', 'walk', 'bike', or 'all')

    Raises:
        RuntimeError: If street network data cannot be retrieved
    """
    if theme is None:
        raise ValueError("Theme must be provided to create_poster()")

    display_city = display_city or country_label or city
    display_country = display_country or country

    logger.info("Generating map for %s, %s...", city, country)

    # Progress bar for data fetching
    with tqdm(
        total=3,
        desc="Fetching map data",
        unit="step",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
    ) as pbar:
        pbar.set_description("Downloading street network")
        compensated_dist = dist * (max(height, width) / min(height, width)) / 4
        g = fetch_graph(point, compensated_dist, network_type=network_type)
        if g is None:
            raise RuntimeError("Failed to retrieve street network data.")
        pbar.update(1)

        pbar.set_description("Downloading water features")
        water = fetch_features(
            point, compensated_dist,
            tags={"natural": "water", "waterway": "riverbank"},
            name="water",
        )
        pbar.update(1)

        pbar.set_description("Downloading parks/green spaces")
        parks = fetch_features(
            point, compensated_dist,
            tags={"leisure": "park", "landuse": "grass"},
            name="parks",
        )
        pbar.update(1)

    logger.info("All data retrieved successfully!")

    # Setup Plot
    logger.info("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=theme["bg"])
    ax.set_facecolor(theme["bg"])
    ax.set_position((0.0, 0.0, 1.0, 1.0))

    g_proj = ox.project_graph(g)

    # Render layers
    water_polys = _project_features(water, g_proj)
    parks_polys = _project_features(parks, g_proj)

    if not no_water:
        _render_water(ax, water_polys, theme)

    if not no_parks:
        _render_parks(ax, parks_polys, theme)

    # Determine cropping limits
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)

    if not no_roads:
        logger.info("Applying road hierarchy colors...")
        _render_roads(ax, g_proj, theme)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)

    # Gradients
    create_gradient_fade(ax, theme['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, theme['gradient_color'], location='top', zorder=10)

    # Typography
    if show_text:
        _render_text(
            ax, display_city, display_country, point, theme,
            font_family, width, height,
            city_font_size, country_font_size, coords_font_size,
        )

    # Save
    logger.info("Saving to %s...", output_file)

    fmt = output_format.lower()

    if fmt == "stl":
        if not STL_AVAILABLE:
            raise RuntimeError(
                "STL generation requires additional libraries. "
                "Install with: pip install trimesh scipy"
            )
        if stl_settings is None:
            stl_settings = STLSettings()
            stl_settings.width_mm = width * 25.4
            stl_settings.height_mm = height * 25.4

        minx, maxx = crop_xlim
        miny, maxy = crop_ylim
        bounds = (minx, miny, maxx, maxy)

        generate_stl(
            g_proj,
            water_polys if water_polys is not None else None,
            parks_polys if parks_polys is not None else None,
            bounds, output_file, stl_settings,
        )
    else:
        save_kwargs: dict[str, Any] = dict(
            facecolor=theme["bg"],
            bbox_inches="tight",
            pad_inches=0.05,
        )
        if fmt == "png":
            save_kwargs["dpi"] = 300

        plt.savefig(output_file, format=fmt, **save_kwargs)
        plt.close()

        if svg_layers and fmt == "svg":
            logger.info("Organizing SVG into layers by road type...")
            organize_svg_layers(output_file)

        logger.info("Done! Poster saved as %s", output_file)


def print_examples() -> None:
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000

  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000

  # Radial patterns
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream -d 10000

  # Organic old cities
  python create_map_poster.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000
  python create_map_poster.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000

  # SVG with plotter-friendly layers
  python create_map_poster.py -c "Berlin" -C "Germany" -f svg --svg-layers -d 10000

  # STL for 3D printing
  python create_map_poster.py -c "Paris" -C "France" -f stl -d 10000 -W 6 -H 8

  # List themes
  python create_map_poster.py --list-themes

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)
""")


def list_themes() -> None:
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return

    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_data = load_theme(theme_name)
        display_name = theme_data.get('name', theme_name)
        description = theme_data.get('description', '')
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city "New York" --country "USA" -lat 40.776676 -long -73.971321 --theme neon_cyberpunk
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster.py --city Berlin --country Germany -f svg --svg-layers
  python create_map_poster.py --list-themes
        """,
    )

    parser.add_argument("--city", "-c", type=str, help="City name")
    parser.add_argument("--country", "-C", type=str, help="Country name")
    parser.add_argument(
        "--latitude", "-lat", dest="latitude", type=str,
        help="Override latitude center point",
    )
    parser.add_argument(
        "--longitude", "-long", dest="longitude", type=str,
        help="Override longitude center point",
    )
    parser.add_argument(
        "--country-label", dest="country_label", type=str,
        help="Override country text displayed on poster",
    )
    parser.add_argument(
        "--theme", "-t", type=str, default="terracotta",
        help="Theme name (default: terracotta)",
    )
    parser.add_argument(
        "--all-themes", "--All-themes", dest="all_themes", action="store_true",
        help="Generate posters for all themes",
    )
    parser.add_argument(
        "--distance", "-d", type=int, default=18000,
        help="Map radius in meters (default: 18000)",
    )
    parser.add_argument(
        "--network-type", type=str, default="drive",
        choices=["drive", "all", "walk", "bike"],
        help="Type of street network to download (default: drive)",
    )
    parser.add_argument(
        "--width", "-W", type=float, default=12,
        help="Image width in inches (default: 12, max: 20)",
    )
    parser.add_argument(
        "--height", "-H", type=float, default=16,
        help="Image height in inches (default: 16, max: 20)",
    )
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="Output resolution in DPI (default: 300)",
    )
    parser.add_argument("--list-themes", action="store_true", help="List all available themes")
    parser.add_argument(
        "--display-city", "-dc", type=str,
        help="Custom display name for city (for i18n support)",
    )
    parser.add_argument(
        "--display-country", "-dC", type=str,
        help="Custom display name for country (for i18n support)",
    )
    parser.add_argument(
        "--font-family", type=str,
        help='Google Fonts family name (e.g., "Noto Sans JP", "Open Sans").',
    )
    parser.add_argument(
        "--format", "-f", default="png",
        choices=["png", "svg", "pdf", "stl"],
        help="Output format for the poster (default: png)",
    )
    parser.add_argument(
        "--svg-layers", action="store_true",
        help="Organize SVG output into layers by road type (SVG format only)",
    )
    parser.add_argument("--stl-base-thickness", type=float, default=3.0)
    parser.add_argument("--stl-max-height", type=float, default=2.5)
    parser.add_argument("--stl-resolution", type=int, default=800)
    parser.add_argument("--stl-invert", action="store_true")
    parser.add_argument("--stl-smoothing", type=float, default=1.0)
    parser.add_argument("--stl-width", type=float)
    parser.add_argument("--stl-height", type=float)

    parser.add_argument("--city-font-size", type=float, default=None)
    parser.add_argument("--country-font-size", type=float, default=None)
    parser.add_argument("--coords-font-size", type=float, default=None)
    parser.add_argument("--no-text", action="store_true",
                       help="Hide all text labels")
    parser.add_argument('--no-roads', action='store_true',
                       help='Hide roads/streets from the map')
    parser.add_argument('--no-water', action='store_true',
                       help='Hide water bodies from the map')
    parser.add_argument('--no-parks', action='store_true',
                       help='Hide parks/green spaces from the map')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable debug logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # If no arguments provided, show examples
    if len(sys.argv) == 1:
        print_examples()
        sys.exit(0)

    if args.list_themes:
        list_themes()
        sys.exit(0)

    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        sys.exit(1)

    # Enforce maximum dimensions
    if args.width > 20:
        logger.warning("Width %s exceeds maximum 20. Clamping.", args.width)
        args.width = 20.0
    if args.height > 20:
        logger.warning("Height %s exceeds maximum 20. Clamping.", args.height)
        args.height = 20.0

    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        sys.exit(1)

    if args.all_themes:
        themes_to_generate = available_themes
    else:
        if args.theme not in available_themes:
            print(f"Error: Theme '{args.theme}' not found.")
            print(f"Available themes: {', '.join(available_themes)}")
            sys.exit(1)
        themes_to_generate = [args.theme]

    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)

    custom_fonts = None
    if args.font_family:
        custom_fonts = load_fonts(getattr(args, "font_family", None))

    try:
        if args.latitude and args.longitude:
            lat = parse(args.latitude)
            lon = parse(args.longitude)
            validate_coordinates(lat, lon)
            coords = (lat, lon)
            logger.info("Coordinates: %s, %s", lat, lon)
        else:
            coords = get_coordinates(args.city, args.country)

        font_family = args.font_family if args.font_family else "sans-serif"

        for theme_name in themes_to_generate:
            current_theme = load_theme(theme_name)
            output_file = generate_output_filename(args.city, theme_name, args.format)

            stl_settings = None
            if args.format == "stl":
                if STL_AVAILABLE:
                    stl_settings = STLSettings()
                    if args.stl_width and args.stl_height:
                        stl_settings.width_mm = args.stl_width
                        stl_settings.height_mm = args.stl_height
                    else:
                        stl_settings.width_mm = args.width * 25.4
                        stl_settings.height_mm = args.height * 25.4
                    stl_settings.base_thickness = args.stl_base_thickness
                    stl_settings.max_relief_height = args.stl_max_height
                    stl_settings.resolution = args.stl_resolution
                    stl_settings.invert = args.stl_invert
                    stl_settings.smoothing = args.stl_smoothing
                else:
                    print("[ERROR] STL generation requires: pip install trimesh scipy")
                    sys.exit(1)

            create_poster(
                args.city,
                args.country,
                coords,
                args.distance,
                output_file,
                args.format,
                args.width,
                args.height,
                display_city=args.display_city,
                display_country=args.display_country,
                fonts=custom_fonts,
                svg_layers=args.svg_layers,
                stl_settings=stl_settings,
                city_font_size=args.city_font_size,
                country_font_size=args.country_font_size,
                coords_font_size=args.coords_font_size,
                show_text=not args.no_text,
                no_roads=args.no_roads,
                no_water=args.no_water,
                no_parks=args.no_parks,
                font_family=font_family,
                theme=current_theme,
                network_type=args.network_type,
            )

        print("\n" + "=" * 50)
        print("[OK] Poster generation complete!")
        print("=" * 50)

    except Exception as e:
        logger.error("Error: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
