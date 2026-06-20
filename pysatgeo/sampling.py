"""Sampling and point-generation helpers."""

import geopandas as gpd
import numpy as np
import rasterio
import shapely.geometry as sg


def get_raster_values(input_raster_path, input_points):
    """Sample raster values at point geometries from a GeoDataFrame."""
    with rasterio.open(input_raster_path) as raster:
        return [
            value[0]
            for _, row in input_points.iterrows()
            for value in raster.sample([(row.geometry.x, row.geometry.y)])
        ]


def generate_points_within_polygon(polygon, spacing, crs="EPSG:32629"):
    """Generate regularly spaced points inside a polygon."""
    minx, miny, maxx, maxy = polygon.bounds
    x_coords = np.arange(minx, maxx, spacing)
    y_coords = np.arange(miny, maxy, spacing)
    points = [sg.Point(x, y) for x in x_coords for y in y_coords]
    points_within_polygon = [point for point in points if polygon.contains(point)]

    points_gdf = gpd.GeoDataFrame(geometry=points_within_polygon, crs=crs)
    points_gdf["fire_ocurrence"] = 1
    return points_gdf


def generate_points_outside_polygons(
    fire_polygons, existing_points_gdf, boundary_gdf, spacing=500
):
    """Generate random points outside buffered polygons but within a boundary."""
    buffered_polygons = fire_polygons.geometry.buffer(spacing)
    combined_buffered_area = buffered_polygons.union_all()
    boundary_polygon = boundary_gdf.geometry.union_all()
    minx, miny, maxx, maxy = boundary_polygon.bounds

    outside_points = []
    target_count = len(existing_points_gdf)
    while len(outside_points) < target_count:
        x = np.random.uniform(minx, maxx)
        y = np.random.uniform(miny, maxy)
        point = sg.Point(x, y)

        if not combined_buffered_area.contains(point) and boundary_polygon.contains(
            point
        ):
            outside_points.append(point)

    points_gdf = gpd.GeoDataFrame(geometry=outside_points, crs=fire_polygons.crs)
    points_gdf["fire_ocurrence"] = 0
    return points_gdf
