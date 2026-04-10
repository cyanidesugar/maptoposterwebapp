"""
Road Category Classification

Shared module for classifying OSM highway types into a road hierarchy.
Used by both create_map_poster.py and stl_generator.py.
"""

import logging


logger = logging.getLogger(__name__)

# Fallback colour used when the theme does not define a colour for a category.
_DEFAULT_ROAD_COLOR = "#888888"


# OSM highway type -> category mapping
_HIGHWAY_CATEGORIES: dict[str, str] = {
    "motorway": "motorway",
    "motorway_link": "motorway",
    "trunk": "primary",
    "trunk_link": "primary",
    "primary": "primary",
    "primary_link": "primary",
    "secondary": "secondary",
    "secondary_link": "secondary",
    "tertiary": "tertiary",
    "tertiary_link": "tertiary",
    "residential": "residential",
    "living_street": "residential",
    "unclassified": "residential",
    "service": "residential",
    # Pedestrian / active-travel ways
    "footway": "default",
    "path": "default",
    "steps": "default",
    "corridor": "default",
    "cycleway": "default",
    "track": "default",
    "escape": "default",
    "pedestrian": "default",
}

# Display widths for poster rendering (in matplotlib linewidth units)
ROAD_WIDTHS: dict[str, float] = {
    "motorway": 1.2,
    "primary": 1.0,
    "secondary": 0.8,
    "tertiary": 0.6,
    "residential": 0.4,
    "default": 0.4,
}

# SVG layer names
ROAD_LAYER_NAMES: dict[str, str] = {
    "motorway": "Motorways",
    "primary": "Primary_Roads",
    "secondary": "Secondary_Roads",
    "tertiary": "Tertiary_Roads",
    "residential": "Residential_&_Other",
}

# STL visual widths (base pixels, before road_width_scale)
STL_BASE_WIDTHS: dict[str, float] = {
    "motorway": 4.0,
    "primary": 3.5,
    "secondary": 3.0,
    "tertiary": 2.5,
    "residential": 2.0,
    "default": 2.0,
}


def classify(highway_type: str | list) -> str:
    """
    Classify an OSM highway type into a road category.

    Args:
        highway_type: OSM highway tag value. OSMnx sometimes returns a list
            when multiple highway tags are attached to a single edge; in that
            case the first element is used.

    Returns:
        Category string: 'motorway', 'primary', 'secondary', 'tertiary',
        'residential', or 'default'.
    """
    if isinstance(highway_type, list):
        highway_type = highway_type[0] if highway_type else "unclassified"
    category = _HIGHWAY_CATEGORIES.get(highway_type)
    if category is None:
        logger.debug("Unknown highway type: %s, using default", highway_type)
        return "default"
    return category


def get_width(highway_type: str | list) -> float:
    """Get the poster rendering width for a highway type.

    Args:
        highway_type: OSM highway tag value (string or list — see classify()).
    """
    category = classify(highway_type)
    return ROAD_WIDTHS.get(category, ROAD_WIDTHS["default"])


def get_color(highway_type: str | list, theme: dict[str, str]) -> str:
    """Get the theme colour for a highway type.

    Args:
        highway_type: OSM highway tag value (string or list — see classify()).
        theme: Mapping of theme keys (e.g. 'road_primary') to colour strings.

    Returns:
        Hex colour string. Falls back to the theme's 'road_default' key, then
        to _DEFAULT_ROAD_COLOR if neither is present.
    """
    category = classify(highway_type)
    key = f"road_{category}"
    return theme.get(key, theme.get("road_default", _DEFAULT_ROAD_COLOR))


def get_layer_info(highway_type: str | list) -> tuple[str, str, float]:
    """
    Get SVG layer info for a highway type.

    Args:
        highway_type: OSM highway tag value (string or list — see classify()).

    Returns:
        (category_key, layer_name, width)
    """
    category = classify(highway_type)
    layer_name = ROAD_LAYER_NAMES.get(category, "Residential_&_Other")
    width = ROAD_WIDTHS.get(category, ROAD_WIDTHS["default"])
    return (category, layer_name, width)


def get_stl_width(highway_type: str | list, road_width_scale: float = 1.5) -> float:
    """Get the STL rendering width for a highway type.

    Args:
        highway_type: OSM highway tag value (string or list — see classify()).
        road_width_scale: Multiplier applied to the base STL width.
    """
    category = classify(highway_type)
    base = STL_BASE_WIDTHS.get(category, STL_BASE_WIDTHS["default"])
    return base * road_width_scale


def get_stl_height(highway_type: str | list, road_heights: dict[str, float]) -> float:
    """Get the STL height value for a highway type.

    Args:
        highway_type: OSM highway tag value (string or list — see classify()).
        road_heights: Mapping of category keys to height values.
    """
    category = classify(highway_type)
    return road_heights.get(category, road_heights.get("default", 0.4))
