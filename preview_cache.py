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
    # Use "preview.tmp.gpkg" / "preview.tmp.json" (extension preserved) rather
    # than "preview.gpkg.tmp" / "preview.json.tmp" to avoid pyogrio's warning
    # about a non-conformant GPKG file extension during the atomic-write window.
    gpkg_tmp = os.path.join(cache_dir, "preview.tmp.gpkg")
    json_tmp = os.path.join(cache_dir, "preview.tmp.json")

    # Remove any stale tmp from a previous failed write
    for stale in (gpkg_tmp, gpkg_path + ".tmp", json_path + ".tmp"):
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass

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
