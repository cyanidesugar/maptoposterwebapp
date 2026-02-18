"""
STL Generator for 3D Printable Map Reliefs

Converts 2D map data into 3D relief STL files suitable for FDM printing.
Uses heightmap rasterization to avoid topology issues.
"""

import logging
from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter
import trimesh
from geopandas import GeoDataFrame
from networkx import MultiDiGraph

import road_categories

logger = logging.getLogger("maptoposter")


class STLSettings:
    """Settings for STL generation."""
    def __init__(self) -> None:
        self.width_mm: float = 150.0
        self.height_mm: float = 200.0
        self.base_thickness: float = 3.0
        self.max_relief_height: float = 2.5
        self.invert: bool = False

        self.road_heights: dict[str, float] = {
            'motorway': 1.0,
            'primary': 0.85,
            'secondary': 0.70,
            'tertiary': 0.55,
            'residential': 0.40,
            'default': 0.40,
        }

        self.water_height: float = -0.2
        self.park_height: float = 0.15
        self.resolution: int = 800
        self.smoothing: float = 1.0
        self.road_width_scale: float = 1.5
        self.add_border: bool = True
        self.border_width: float = 5.0


def _grid_dimensions(settings: STLSettings) -> tuple[int, int]:
    """Calculate grid dimensions from settings, preserving physical aspect ratio."""
    physical_aspect = settings.width_mm / settings.height_mm
    if physical_aspect >= 1.0:
        grid_width = settings.resolution
        grid_height = int(settings.resolution / physical_aspect)
    else:
        grid_height = settings.resolution
        grid_width = int(settings.resolution * physical_aspect)
    return grid_height, grid_width


def world_to_grid(
    coords: np.ndarray,
    bounds: tuple[float, float, float, float],
    grid_shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Convert world coordinates to grid pixel coordinates."""
    minx, miny, maxx, maxy = bounds
    width = maxx - minx
    height = maxy - miny

    grid_height, grid_width = grid_shape

    norm_x = (coords[:, 0] - minx) / width
    norm_y = (coords[:, 1] - miny) / height

    cols = (norm_x * (grid_width - 1)).astype(int)
    rows = ((1 - norm_y) * (grid_height - 1)).astype(int)

    cols = np.clip(cols, 0, grid_width - 1)
    rows = np.clip(rows, 0, grid_height - 1)

    return rows, cols


def draw_thick_line(
    grid: np.ndarray,
    x0: int, y0: int,
    x1: int, y1: int,
    value: float,
    thickness: int,
) -> None:
    """Draw a thick line on a grid using Bresenham's algorithm."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    half_thick = thickness // 2

    while True:
        for i in range(-half_thick, half_thick + 1):
            for j in range(-half_thick, half_thick + 1):
                y_pos = y0 + i
                x_pos = x0 + j
                if 0 <= y_pos < grid.shape[0] and 0 <= x_pos < grid.shape[1]:
                    grid[y_pos, x_pos] = max(grid[y_pos, x_pos], value)

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def rasterize_roads(
    graph: MultiDiGraph,
    bounds: tuple[float, float, float, float],
    settings: STLSettings,
) -> np.ndarray:
    """Rasterize road network to heightmap grid."""
    grid_height, grid_width = _grid_dimensions(settings)
    grid = np.zeros((grid_height, grid_width), dtype=np.float32)

    logger.info("  Grid size: %dx%d pixels", grid_width, grid_height)
    logger.info("  Rasterizing %d road segments...", len(graph.edges()))

    for u, v, data in graph.edges(data=True):
        if 'geometry' in data:
            coords = np.array(data['geometry'].coords)
        else:
            u_pos = (graph.nodes[u]['x'], graph.nodes[u]['y'])
            v_pos = (graph.nodes[v]['x'], graph.nodes[v]['y'])
            coords = np.array([u_pos, v_pos])

        highway = data.get('highway', 'unclassified')
        height_value = road_categories.get_stl_height(highway, settings.road_heights)
        line_width = road_categories.get_stl_width(highway, settings.road_width_scale)

        rows, cols = world_to_grid(coords, bounds, (grid_height, grid_width))

        for i in range(len(rows) - 1):
            draw_thick_line(
                grid,
                cols[i], rows[i],
                cols[i + 1], rows[i + 1],
                height_value,
                int(line_width),
            )

    return grid


def rasterize_polygons(
    gdf: Optional[GeoDataFrame],
    bounds: tuple[float, float, float, float],
    settings: STLSettings,
    height_value: float,
) -> np.ndarray:
    """Rasterize polygon features (water, parks) to grid."""
    grid_height, grid_width = _grid_dimensions(settings)
    grid = np.zeros((grid_height, grid_width), dtype=np.float32)

    if gdf is None or gdf.empty:
        return grid

    poly_gdf = gdf[gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if poly_gdf.empty:
        return grid

    logger.info("  Rasterizing %d polygon features...", len(poly_gdf))

    for idx, row in poly_gdf.iterrows():
        geom = row.geometry

        if geom.geom_type == 'Polygon':
            polygons = [geom]
        else:
            polygons = list(geom.geoms)

        for poly in polygons:
            coords = np.array(poly.exterior.coords)
            if len(coords) < 3:
                continue

            rows, cols = world_to_grid(coords, bounds, (grid_height, grid_width))

            for i in range(len(rows) - 1):
                draw_thick_line(
                    grid,
                    cols[i], rows[i],
                    cols[i + 1], rows[i + 1],
                    height_value,
                    thickness=2,
                )

            if len(rows) >= 3:
                center_row = int(np.mean(rows))
                center_col = int(np.mean(cols))
                if 0 <= center_row < grid_height and 0 <= center_col < grid_width:
                    grid[center_row, center_col] = height_value

    return grid


def heightmap_to_mesh(heightmap: np.ndarray, settings: STLSettings) -> trimesh.Trimesh:
    """Convert heightmap to 3D mesh."""
    height, width = heightmap.shape
    physical_width = settings.width_mm
    physical_height = settings.height_mm

    logger.info("  Converting heightmap to mesh...")
    logger.info("  Physical size: %.0fmm x %.0fmm", physical_width, physical_height)

    vertices = []
    pixel_width = physical_width / width
    pixel_height = physical_height / height

    for row in range(height):
        for col in range(width):
            x = col * pixel_width
            y = row * pixel_height
            if settings.invert:
                z = settings.base_thickness - (heightmap[row, col] * settings.max_relief_height)
            else:
                z = settings.base_thickness + (heightmap[row, col] * settings.max_relief_height)
            vertices.append([x, y, z])

    vertices = np.array(vertices)

    faces = []
    for row in range(height - 1):
        for col in range(width - 1):
            v0 = row * width + col
            v1 = row * width + (col + 1)
            v2 = (row + 1) * width + col
            v3 = (row + 1) * width + (col + 1)
            faces.append([v0, v2, v1])
            faces.append([v1, v2, v3])

    faces = np.array(faces)

    top_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    base_vertices = vertices.copy()
    base_vertices[:, 2] = 0
    base_faces = faces[:, [0, 2, 1]]
    base_mesh = trimesh.Trimesh(vertices=base_vertices, faces=base_faces)

    side_meshes = []

    # Build side walls
    wall_configs = [
        # (start_vertex_fn, face_winding)
        # Front wall (row = 0)
        (lambda col: col, lambda col: col + 1, np.array([[0, 2, 1], [1, 2, 3]])),
        # Back wall (row = height-1)
        (lambda col: (height - 1) * width + col,
         lambda col: (height - 1) * width + (col + 1),
         np.array([[0, 1, 2], [1, 3, 2]])),
    ]

    for v0_fn, v1_fn, winding in wall_configs:
        for col in range(width - 1):
            v0_idx = v0_fn(col)
            v1_idx = v1_fn(col)
            wall_verts = np.array([
                vertices[v0_idx], vertices[v1_idx],
                base_vertices[v0_idx], base_vertices[v1_idx],
            ])
            side_meshes.append(trimesh.Trimesh(vertices=wall_verts, faces=winding))

    # Left wall (col = 0)
    for row in range(height - 1):
        v0_idx = row * width
        v1_idx = (row + 1) * width
        wall_verts = np.array([
            vertices[v0_idx], vertices[v1_idx],
            base_vertices[v0_idx], base_vertices[v1_idx],
        ])
        side_meshes.append(trimesh.Trimesh(
            vertices=wall_verts, faces=np.array([[0, 1, 2], [1, 3, 2]])))

    # Right wall (col = width-1)
    for row in range(height - 1):
        v0_idx = row * width + (width - 1)
        v1_idx = (row + 1) * width + (width - 1)
        wall_verts = np.array([
            vertices[v0_idx], vertices[v1_idx],
            base_vertices[v0_idx], base_vertices[v1_idx],
        ])
        side_meshes.append(trimesh.Trimesh(
            vertices=wall_verts, faces=np.array([[0, 2, 1], [1, 2, 3]])))

    logger.info("  Combining %d mesh components...", 2 + len(side_meshes))
    all_meshes = [top_mesh, base_mesh] + side_meshes
    final_mesh = trimesh.util.concatenate(all_meshes)

    logger.info("  Cleaning up mesh...")
    final_mesh.merge_vertices()
    final_mesh.process()

    return final_mesh


def generate_stl(
    graph: MultiDiGraph,
    water: Optional[GeoDataFrame],
    parks: Optional[GeoDataFrame],
    bounds: tuple[float, float, float, float],
    output_file: str,
    settings: Optional[STLSettings] = None,
) -> str:
    """Generate STL file from map data."""
    if settings is None:
        settings = STLSettings()

    logger.info("\n" + "=" * 50)
    logger.info("Generating 3D STL Relief")
    logger.info("=" * 50)

    logger.info("\n[1/5] Rasterizing road network...")
    road_grid = rasterize_roads(graph, bounds, settings)

    if water is not None and not water.empty:
        logger.info("\n[2/5] Rasterizing water features...")
        water_grid = rasterize_polygons(water, bounds, settings, settings.water_height)
        road_grid = np.maximum(road_grid, water_grid)
    else:
        logger.info("\n[2/5] No water features to rasterize")

    if parks is not None and not parks.empty:
        logger.info("\n[3/5] Rasterizing park features...")
        park_grid = rasterize_polygons(parks, bounds, settings, settings.park_height)
        mask = road_grid == 0
        road_grid[mask] = np.maximum(road_grid[mask], park_grid[mask])
    else:
        logger.info("\n[3/5] No park features to rasterize")

    if settings.smoothing > 0:
        logger.info("\n[4/5] Smoothing heightmap (sigma=%.1f)...", settings.smoothing)
        road_grid = gaussian_filter(road_grid, sigma=settings.smoothing)
    else:
        logger.info("\n[4/5] Skipping smoothing")

    if road_grid.max() > 0:
        road_grid = road_grid / road_grid.max()

    logger.info("\n[5/5] Generating 3D mesh...")
    mesh = heightmap_to_mesh(road_grid, settings)

    logger.info("Exporting STL to: %s", output_file)
    mesh.export(output_file)

    logger.info("\n" + "=" * 50)
    logger.info("STL Generation Complete!")
    logger.info("=" * 50)
    logger.info("Vertices: %s", f"{len(mesh.vertices):,}")
    logger.info("Faces: %s", f"{len(mesh.faces):,}")
    logger.info("Volume: %.2f mm3", mesh.volume)
    logger.info("Is watertight: %s", mesh.is_watertight)

    if not mesh.is_watertight:
        logger.warning("Mesh is not watertight - may need repair in slicer")

    return output_file
