"""
Vector-related functions for pysatgeo.
"""

import geopandas as gpd
from shapely.geometry import Point, Polygon
import os

def assign_crs_to_vector(input_geojson_path, output_geojson_path, crs_epsg):
    """
    Assign a CRS to a GeoJSON file and export

    Parameters:
    - input_geojson_path (str): Path to the input geojson
    - output_geojson_path (str): Path to save the output geojson with the assigned crs
    - crs_epsg (int): EPSG code of the CRS to assign (e.g: 4326)
    """
    
    gdf = gpd.read_file(input_geojson_path)
    gdf.set_crs(epsg=crs_epsg, inplace=True, allow_override=True)
    gdf.to_file(output_geojson_path, driver="GeoJSON")

    print(f"Output saved to: {output_geojson_path}")

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

    vector_gdf = gpd.read_parquet(vector_path)

    vector_bounds = vector_gdf.total_bounds  # (min_x, min_y, max_x, max_y)

    x_offset = raster_bounds[0] - vector_bounds[0]  # Difference in X (min_x)
    y_offset = raster_bounds[1] - vector_bounds[1]  # Difference in Y (min_y)

    print(f"X offset (m) is: {x_offset}")
    print(f"Y offset (m) is: {y_offset}")
    
    vector_gdf['geometry'] = vector_gdf['geometry'].translate(xoff=x_offset, yoff=y_offset)

    vector_gdf.to_parquet(output_vector_path)

    print(f"Shifted vector saved to: {output_vector_path}")

def clip_vector_with_masks(input_vector_path, mask_folder, output_folder):
    """
    Clips a single vector file using multiple mask layers in a folder.

    Parameters:
        input_vector_path (str): Path to the input vector file (GeoParquet, GeoPackage, GeoJSON, Shapefile, etc.).
        mask_folder (str): Path to the folder containing mask layers (GeoParquet, GeoPackage, GeoJSON, Shapefile, etc.).
        output_folder (str): Path to the folder to save the clipped vector files.

    Returns:
        None
    """
    os.makedirs(output_folder, exist_ok=True)

    valid_extensions = [".parquet", ".geojson", ".gpkg", ".shp"]

    mask_files = [f for f in os.listdir(mask_folder) if os.path.splitext(f)[1].lower() in valid_extensions]

    if not mask_files:
        print("No valid mask files found in the mask folder.")
        return

    _, vector_extension = os.path.splitext(input_vector_path)
    if vector_extension.lower() == ".parquet":
        input_gdf = gpd.read_parquet(input_vector_path)
    elif vector_extension.lower() in [".geojson", ".gpkg", ".shp"]:
        input_gdf = gpd.read_file(input_vector_path)
    else:
        raise ValueError(f"Unsupported input vector format: {vector_extension}")

    for mask_file in mask_files:
        mask_path = os.path.join(mask_folder, mask_file)
        _, mask_extension = os.path.splitext(mask_file)

        try:
            if mask_extension.lower() == ".parquet":
                mask_gdf = gpd.read_parquet(mask_path)
            elif mask_extension.lower() in [".geojson", ".gpkg", ".shp"]:
                mask_gdf = gpd.read_file(mask_path)
            else:
                raise ValueError(f"Unsupported mask file format: {mask_extension}")

            clipped_gdf = gpd.clip(input_gdf, mask_gdf)

            output_name = f"{os.path.splitext(mask_file)[0]}_clipped{vector_extension}"
            output_path = os.path.join(output_folder, output_name)

            if vector_extension.lower() == ".parquet":
                clipped_gdf.to_parquet(output_path)
            elif vector_extension.lower() in [".geojson", ".gpkg", ".shp"]:
                clipped_gdf.to_file(output_path, driver="GeoJSON" if vector_extension.lower() == ".geojson" else None)
            else:
                raise ValueError(f"Unsupported output vector format: {vector_extension}")

            print(f"Saved clipped vector: {output_name}")

        except Exception as e:
            print(f"Error processing mask {mask_file}: {e}")

def dissolve_vector(input_vector, output_vector, dissolve_field=None):
    """
    Dissolve features in a vector file (GeoPackage or GeoParquet) based on a given field.

    :param input_vector: Path to the input vector file (GeoPackage or GeoParquet).
    :param output_vector: Path for the output dissolved vector file (GeoPackage or GeoParquet).
    :param dissolve_field: The field to dissolve on. If None, dissolve all features into one.
    """
    
    # Determine the input and output formats based on file extensions
    input_ext = os.path.splitext(input_vector)[-1].lower()
    output_ext = os.path.splitext(output_vector)[-1].lower()

    # Read the input file based on its extension
    if input_ext == '.gpkg':
        gdf = gpd.read_file(input_vector)
    elif input_ext == '.parquet':
        gdf = gpd.read_parquet(input_vector)
    else:
        raise ValueError(f"Unsupported input file format: {input_ext}")

    # Perform dissolve operation
    if dissolve_field:
        dissolved_gdf = gdf.dissolve(by=dissolve_field)
    else:
        dissolved_gdf = gdf.dissolve()

    # Write the dissolved GeoDataFrame based on the output extension
    if output_ext == '.gpkg':
        dissolved_gdf.to_file(output_vector, driver='GPKG')
    elif output_ext == '.parquet':
        dissolved_gdf.to_parquet(output_vector)
    else:
        raise ValueError(f"Unsupported output file format: {output_ext}")

    print(f"Dissolved vector file created: {output_vector}")

# Example Usage

"""
dissolve_vector(
    input_vector = "path/to/input1.gpkg",
    output_vector = "path/to/output1.gpkg",
    dissolve_field ="DN"
)

"""

def rasterize(target_resolution, input_directory, no_data_value, field_name=None):
    """
    Rasterizes all GeoJSON files in a directory, saving the output as TIFF files with the same name.
    
    :param target_resolution: Target resolution for the output raster.
    :param input_directory: Directory containing the input GeoJSON files.
    :param no_data_value: The no-data value to set for the output raster.
    :param field_name: Name of the field in the GeoJSON to use for rasterization. If None, default behavior is applied.
    """
    for file_name in os.listdir(input_directory):
        if file_name.endswith(".geojson"):
            input_geojson = os.path.join(input_directory, file_name)
            
            output_tif = os.path.join(input_directory, file_name.replace(".geojson", ".tif"))
            
            cmd = f"gdal_rasterize -tr {target_resolution} {target_resolution} -of GTiff"
            
            if field_name:
                cmd += f" -a {field_name}"
            else:
                cmd += " -burn 1"
            
            cmd += f" -a_nodata {no_data_value}"
            cmd += f" \"{input_geojson}\" \"{output_tif}\""
            
            # Execute the command
            os.system(cmd)
 
""" # Example usage
rasterize(
    target_resolution=30,
    input_directory=/path/to/geojson_folder
    no_data_value = -9999
    field_name="CURRENT_AGE"
) """


def generate_points_within_polygon(polygon, spacing):
    """
    Generate points within a polygon at specified spacing and label them with 'fire_ocurrence' = 1.
    
    :param polygon: Shapely polygon to generate points within.
    :param spacing: Distance between points.
    :return: GeoDataFrame containing points within the polygon.
    """
    minx, miny, maxx, maxy = polygon.bounds
    
    # Generate grid of points
    x_coords = np.arange(minx, maxx, spacing)
    y_coords = np.arange(miny, maxy, spacing)
    points = [sg.Point(x, y) for x in x_coords for y in y_coords]
    
    # Filter points to keep only those within the polygon
    points_within_polygon = [point for point in points if polygon.contains(point)]
    
    points_gdf = gpd.GeoDataFrame(geometry=points_within_polygon, crs="EPSG:32629") 
    
    # Points in "unsafe zone"
    points_gdf['fire_ocurrence'] = 1
    
    return points_gdf

def generate_points_outside_polygons(fire_polygons, existing_points_gdf, boundary_gdf, spacing=500):
    """
    Generate points outside the fire polygons at least 'spacing' distance away,
    while ensuring points are within the specified boundary.
    
    :param fire_polygons: GeoDataFrame of fire polygons.
    :param existing_points_gdf: GeoDataFrame of existing points to match the count.
    :param boundary_gdf: GeoDataFrame of the boundary to restrict point generation.
    :param spacing: Minimum distance from the fire polygons.
    :return: GeoDataFrame of points outside the fire polygons and within the boundary.
    """

    # Create a buffered area around each fire polygon
    buffered_polygons = fire_polygons.geometry.buffer(spacing)
    combined_buffered_area = buffered_polygons.union_all()
    
    boundary_polygon = boundary_gdf.geometry.union_all()
    minx, miny, maxx, maxy = boundary_polygon.bounds

    # Number of points to generate
    n_points = len(existing_points_gdf)

    # Initialize storage for generated points
    outside_points = []
    
    # Randomly sample points outside the combined buffered area
    while len(outside_points) < n_points:
        x = np.random.uniform(minx, maxx)
        y = np.random.uniform(miny, maxy)
        point = sg.Point(x, y)
        
        # Add the point if it's outside the buffered area and within the boundary
        if not combined_buffered_area.contains(point) and boundary_polygon.contains(point):
            outside_points.append(point)

    points_gdf = gpd.GeoDataFrame(geometry=outside_points, crs=fire_polygons.crs)
    
    # Points in "safe zone"
    points_gdf['fire_ocurrence'] = 0
    return points_gdf

def idw_interpolation(input_geojson, output_raster, zfield, aoi_path):
    """
    Performs IDW interpolation on point data.

    :param input_geojson: Path to the input GeoJSON file with point data
    :param output_raster: Path for the output raster file
    :param zfield: Field name in the GeoJSON file to use for interpolation
    :param aoi_path: Path to the AOI GeoJSON file
    """
    aoi = gpd.read_file(aoi_path)
    aoi_bounds = aoi.total_bounds
    
    # Perform IDW interpolation
    gdal.Grid(output_raster, input_geojson, zfield=zfield, algorithm="invdist", outputBounds=aoi_bounds)
    
# Example usage
""" idw_interpolation(
    input_geojson="path/to/input.geojson",
    output_raster="path/to/output.tif",
    zfield="Cumulative-Precipitation",
    aoi_path="path/to/aoi.geojson"
) """

def convert_pk_to_string(pk_string):
    """
    Function to convert "PK" to a formatted string
    :param pk_string: String column type.
    :type pk_string: string in a geodataframe,
    """

    if '+' in pk_string:
        # Remove any '+' characters and convert to an integer
        pk_integer = int(pk_string.replace('+', ''))
        # Format the integer as a string with leading zeros
        pk_formatted = f"{pk_integer:04d}"
    else:
        # If there's no '+', assume it's already an integer and format it with leading zeros
        pk_formatted = f"{int(pk_string):04d}"
    return pk_formatted


""" # Example usage
    gdf['PK'] = gdf['PK'].apply(convert_pk_to_string) """
    