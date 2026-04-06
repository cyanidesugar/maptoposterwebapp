"""
Font Management Module
Handles font loading, Google Fonts integration, and caching.
"""

import logging
import os
import requests
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("maptoposter")

FONTS_DIR = "fonts"
FONTS_CACHE_DIR = Path(FONTS_DIR) / "cache"

# Module-level timeout (seconds) for all HTTP requests made by this module.
# Change this single constant to adjust the network timeout everywhere.
_DOWNLOAD_TIMEOUT = 10


def download_google_font(font_family: str, weights: list | None = None) -> Optional[dict]:
    """
    Download a font family from Google Fonts and cache it locally.
    Returns dict with font paths for different weights, or None if download fails.

    :param font_family: Google Fonts family name (e.g., 'Noto Sans JP', 'Open Sans')
    :param weights: List of font weights to download (300=light, 400=regular, 700=bold)
    :return: Dict with 'light', 'regular', 'bold' keys mapping to font file paths
    """
    if weights is None:
        weights = [300, 400, 700]

    # Create fonts cache directory
    FONTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Normalize font family name for file paths.
    # Sanitise first to prevent path traversal: keep only word chars, spaces, hyphens.
    font_family_clean = re.sub(r"[^\w\s-]", "", font_family)
    font_name_safe = font_family_clean.replace(" ", "_").lower()

    font_files = {}

    try:
        # Google Fonts API endpoint - request all weights at once
        weights_str = ";".join(map(str, weights))
        api_url = "https://fonts.googleapis.com/css2"

        # Use requests library for cleaner HTTP handling
        params = {"family": f"{font_family}:wght@{weights_str}"}
        headers = {
            "User-Agent": "Mozilla/5.0"  # Get .woff2 files (better compression)
        }

        # Fetch CSS file
        response = requests.get(api_url, params=params, headers=headers, timeout=_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        css_content = response.text

        # Parse CSS to extract weight-specific URLs
        # Google Fonts CSS has @font-face blocks with font-weight and src: url()
        weight_url_map = {}

        # Split CSS into font-face blocks
        font_face_blocks = re.split(r"@font-face\s*\{", css_content)

        for block in font_face_blocks[1:]:  # Skip first empty split
            # Extract font-weight
            weight_match = re.search(r"font-weight:\s*(\d+)", block)
            if not weight_match:
                continue

            weight = int(weight_match.group(1))

            # Extract URL restricted to fonts.gstatic.com (prefer woff2, fallback to ttf)
            url_match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.(?:woff2|ttf))\)", block)
            if url_match:
                weight_url_map[weight] = url_match.group(1)

        # Map weights to our keys
        weight_map = {300: "light", 400: "regular", 700: "bold"}

        # Download each weight
        for weight in weights:
            weight_key = weight_map.get(weight, "regular")

            # Find URL for this weight
            weight_url = weight_url_map.get(weight)

            # If exact weight not found, try to find closest
            if not weight_url and weight_url_map:
                # Find closest weight
                closest_weight = min(
                    weight_url_map.keys(), key=lambda x: abs(x - weight)
                )
                weight_url = weight_url_map[closest_weight]
                logger.warning(
                    "Using weight %s for %s (requested %s not available)",
                    closest_weight, weight_key, weight,
                )

            if weight_url:
                # Determine file extension
                file_ext = "woff2" if weight_url.endswith(".woff2") else "ttf"

                # Download font file
                font_filename = f"{font_name_safe}_{weight_key}.{file_ext}"
                font_path = FONTS_CACHE_DIR / font_filename

                if not font_path.exists():
                    logger.info("Downloading %s %s (%s)...", font_family, weight_key, weight)
                    try:
                        font_response = requests.get(weight_url, timeout=_DOWNLOAD_TIMEOUT)
                        font_response.raise_for_status()
                        font_path.write_bytes(font_response.content)
                    except Exception as e:
                        logger.warning("Failed to download %s: %s", weight_key, e)
                        continue
                else:
                    logger.info("Using cached %s %s", font_family, weight_key)

                font_files[weight_key] = str(font_path)

        # Ensure we have at least regular weight
        if "regular" not in font_files and font_files:
            # Use first available as regular (safe iteration avoids IndexError)
            first_key = next(iter(font_files), None)
            if first_key is None:
                return None
            font_files["regular"] = font_files[first_key]
            logger.info("Using %s weight as regular", first_key)

        # If we don't have all three weights, duplicate available ones
        if "bold" not in font_files and "regular" in font_files:
            font_files["bold"] = font_files["regular"]
            logger.info("Using regular weight as bold")
        if "light" not in font_files and "regular" in font_files:
            font_files["light"] = font_files["regular"]
            logger.info("Using regular weight as light")

        return font_files if font_files else None

    except Exception as e:
        logger.warning("Error downloading Google Font '%s': %s", font_family, e)
        return None


def load_fonts(font_family: Optional[str] = None) -> Optional[dict]:
    """
    Load fonts from local directory or download from Google Fonts.
    Returns dict with font paths for different weights.

    :param font_family: Google Fonts family name (e.g., 'Noto Sans JP', 'Open Sans').
                       If None, uses local Roboto fonts.
    :return: Dict with 'bold', 'regular', 'light' keys mapping to font file paths,
             or None if all loading methods fail
    """
    # If custom font family specified, try to download from Google Fonts
    if font_family and font_family.lower() != "roboto":
        logger.info("Loading Google Font: %s", font_family)
        fonts = download_google_font(font_family)
        if fonts:
            logger.info("Font '%s' loaded from Google Fonts", font_family)
            return fonts
        else:
            # Google Fonts download failed - try system fonts
            logger.info("'%s' not available on Google Fonts, checking system fonts...", font_family)

            # Try to find the font in system fonts using matplotlib.
            # NOTE: fm.fontManager.ttflist can be slow on systems with
            # network-mounted font directories as it scans all font paths.
            try:
                import matplotlib.font_manager as fm

                # Search for the font in system fonts
                available_fonts = [f.name for f in fm.fontManager.ttflist]

                if font_family in available_fonts:
                    logger.info("Using system font '%s'", font_family)
                    # Return None to signal: use matplotlib's default font matching
                    # The create_map_poster script will handle this with font_family parameter
                    return None
                else:
                    logger.warning("'%s' not found in system fonts", font_family)
                    close_matches = [f for f in available_fonts if font_family.lower() in f.lower()]
                    if close_matches:
                        logger.info("Similar fonts available: %s", ", ".join(close_matches[:3]))
            except ImportError:
                # matplotlib is not installed; cannot scan system fonts.
                logger.error(
                    "matplotlib is not installed — cannot scan system fonts for '%s'",
                    font_family,
                )
                raise
            except Exception as e:
                logger.warning("Could not check system fonts: %s", e)

            logger.info("Falling back to local Roboto fonts")

    # Default: Load local Roboto fonts
    fonts = {
        "bold": os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
        "regular": os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
        "light": os.path.join(FONTS_DIR, "Roboto-Light.ttf"),
    }

    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            logger.warning("Font not found: %s", path)
            return None

    return fonts
