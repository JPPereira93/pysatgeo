"""
Vector-related functions for pysatgeo.
"""

import geopandas as gpd
import os
import rasterio


def _read_vector(vector_path):
    """Read a vector file based on its extension."""
    extension = os.path.splitext(vector_path)[1].lower()
    if extension == ".parquet":
        return gpd.read_parquet(vector_path)
    if extension in {".geojson", ".gpkg", ".shp"}:
        return gpd.read_file(vector_path)
    raise ValueError(f"Unsupported vector format: {extension}")


def _write_vector(gdf, output_path):
    """Write a vector file based on its extension."""
    extension = os.path.splitext(output_path)[1].lower()
    if extension == ".parquet":
        gdf.to_parquet(output_path)
        return
    if extension == ".geojson":
        gdf.to_file(output_path, driver="GeoJSON")
        return
    if extension == ".gpkg":
        gdf.to_file(output_path, driver="GPKG")
        return
    if extension == ".shp":
        gdf.to_file(output_path)
        return
    raise ValueError(f"Unsupported output vector format: {extension}")


def assign_crs_to_vector(input_geojson_path, output_geojson_path, crs_epsg):
    """
    Assign a CRS to a vector file and export it.

    Parameters:
    - input_geojson_path (str): Path to the input vector file
    - output_geojson_path (str): Path to save the output vector with the assigned crs
    - crs_epsg (int): EPSG code of the CRS to assign (e.g: 4326)
    """
    
    gdf = _read_vector(input_geojson_path)
    gdf.set_crs(epsg=crs_epsg, inplace=True, allow_override=True)
    _write_vector(gdf, output_geojson_path)

    print(f"Output saved to: {output_geojson_path}")
    return output_geojson_path


def convert_geojson_to_geoparquet(input_folder, output_folder):
    """
    Converts all GeoJSON files in a folder to GeoParquet format.

    Parameters:
        input_folder (str): Path to the folder containing GeoJSON files.
        output_folder (str): Path to the folder to save GeoParquet files.

    Returns:
        None
    """
    os.makedirs(output_folder, exist_ok=True)

    geojson_files = [f for f in os.listdir(input_folder) if f.endswith(".geojson")]

    if not geojson_files:
        print("No GeoJSON files found in the input folder.")
        return

    for geojson_file in geojson_files:
        input_path = os.path.join(input_folder, geojson_file)
        output_path = os.path.join(output_folder, f"{os.path.splitext(geojson_file)[0]}.parquet")
        
        try:
            gdf = gpd.read_file(input_path)
            
            gdf.to_parquet(output_path)
            
            print(f"Converted: {geojson_file} -> {os.path.basename(output_path)}")
        except Exception as e:
            print(f"Error processing {geojson_file}: {e}")

    print("\nConversion complete!")


def shift_vector_to_raster_reference(vector_path, raster_path, output_vector_path):
    """
    Shifts the extent of a vector file to match the extent of a raster file.

    Parameters:
    - vector_path (str): Path to the input vector file (GeoJSON, Shapefile, GeoParquet, etc.)
    - raster_path (str): Path to the raster file (GeoTIFF, etc.)
    - output_vector_path (str): Path to save the output vector file with shifted extent

    Returns:
    - None
    """
    with rasterio.open(raster_path) as src:
        raster_bounds = src.bounds  # (min_x, min_y, max_x, max_y)
        raster_crs = src.crs

    vector_gdf = _read_vector(vector_path)
    if vector_gdf.crs is not None and raster_crs is not None and vector_gdf.crs != raster_crs:
        vector_gdf = vector_gdf.to_crs(raster_crs)

    vector_bounds = vector_gdf.total_bounds  # (min_x, min_y, max_x, max_y)

    x_offset = raster_bounds[0] - vector_bounds[0]  # Difference in X (min_x)
    y_offset = raster_bounds[1] - vector_bounds[1]  # Difference in Y (min_y)

    print(f"X offset (m) is: {x_offset}")
    print(f"Y offset (m) is: {y_offset}")
    
    vector_gdf['geometry'] = vector_gdf['geometry'].translate(xoff=x_offset, yoff=y_offset)

    _write_vector(vector_gdf, output_vector_path)

    print(f"Shifted vector saved to: {output_vector_path}")
    return output_vector_path

