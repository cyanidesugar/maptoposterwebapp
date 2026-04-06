"""
Simple latitude/longitude parser

Parses coordinate strings in various formats to decimal degrees.
"""


def parse(coord_str: str) -> float:
    """
    Parse a coordinate string to decimal degrees.

    Supports formats:
    - Plain decimal: "40.7128" or "-74.0060"
    - With cardinal direction: "40.7128N" or "74.0060W"
    - With degree symbol and cardinal: "40.7128°N"

    Note: Only decimal-degree input is supported. DMS formats such as
    "40°42'51.7\"N" are not parsed. The degree symbol (°) is stripped
    as a non-numeric character; the numeric portion must already be in
    decimal degrees.

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

    # Remove all non-numeric characters except decimal point and minus,
    # using a list comprehension to avoid O(n²) string concatenation.
    cleaned = ''.join(
        char for char in coord_str
        if char.isdigit() or char == '.' or char == '-'
    )

    if not cleaned:
        raise ValueError(f"Could not parse coordinate: {coord_str}")

    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"Could not parse coordinate: {coord_str}")

    # Determine sign from cardinal direction OR from a leading minus sign.
    # Using abs() before applying the sign prevents double-negation when
    # both are present (e.g. "-40.7128S" must still be negative, not positive).
    is_negative = value < 0 or 'S' in coord_str or 'W' in coord_str
    return -abs(value) if is_negative else abs(value)
