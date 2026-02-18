"""
Simple latitude/longitude parser

Parses coordinate strings in various formats to decimal degrees.
"""


def parse(coord_str: str) -> float:
    """
    Parse a coordinate string to decimal degrees.

    Supports formats:
    - Decimal: "40.7128" or "-74.0060"
    - With symbols: "40.7128N" or "74.0060W"
    - With degree symbol: "40.7128°N"

    Args:
        coord_str: String representation of coordinate

    Returns:
        Coordinate in decimal degrees

    Raises:
        ValueError: If string cannot be parsed
    """
    if coord_str is None:
        raise ValueError("Coordinate string cannot be None")

    coord_str = str(coord_str).strip().upper()

    is_negative = 'S' in coord_str or 'W' in coord_str

    # Remove all non-numeric characters except decimal point and minus
    cleaned = ''
    for char in coord_str:
        if char.isdigit() or char == '.' or char == '-':
            cleaned += char

    if not cleaned:
        raise ValueError(f"Could not parse coordinate: {coord_str}")

    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"Could not parse coordinate: {coord_str}")

    if is_negative and value > 0:
        value = -value

    return value
