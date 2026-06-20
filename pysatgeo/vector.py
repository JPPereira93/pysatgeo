"""Vector processing utilities for pysatgeo."""

import glob
import os
import pandas as pd
import subprocess

import geopandas as gpd
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
    """Assign a CRS to a vector dataset and export the result."""
    gdf = _read_vector(input_geojson_path)
    gdf.set_crs(epsg=crs_epsg, inplace=True, allow_override=True)
    _write_vector(gdf, output_geojson_path)

    print(f"Output saved to: {output_geojson_path}")
    return output_geojson_path


def convert_geojson_to_geoparquet(input_folder, output_folder):
    """Convert every GeoJSON file in a folder into GeoParquet format."""
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
    """Shift a vector layer so its lower-left corner matches a raster extent."""
    with rasterio.open(raster_path) as src:
        raster_bounds = src.bounds
        raster_crs = src.crs

    vector_gdf = _read_vector(vector_path)
    if vector_gdf.crs is not None and raster_crs is not None and vector_gdf.crs != raster_crs:
        vector_gdf = vector_gdf.to_crs(raster_crs)

    vector_bounds = vector_gdf.total_bounds

    x_offset = raster_bounds[0] - vector_bounds[0]
    y_offset = raster_bounds[1] - vector_bounds[1]

    print(f"X offset (m) is: {x_offset}")
    print(f"Y offset (m) is: {y_offset}")
    
    vector_gdf["geometry"] = vector_gdf["geometry"].translate(
        xoff=x_offset, yoff=y_offset
    )

    _write_vector(vector_gdf, output_vector_path)

    print(f"Shifted vector saved to: {output_vector_path}")
    return output_vector_path


def rasterize(target_resolution, input_directory, no_data_value, field_name=None):
    """Rasterize GeoJSON files in a directory into GeoTIFF files."""
    for file_name in os.listdir(input_directory):
        if file_name.endswith(".geojson"):
            input_geojson = os.path.join(input_directory, file_name)
            output_tif = os.path.join(
                input_directory, file_name.replace(".geojson", ".tif")
            )

            command = [
                "gdal_rasterize",
                "-tr",
                str(target_resolution),
                str(target_resolution),
                "-of",
                "GTiff",
            ]

            if field_name:
                command.extend(["-a", field_name])
            else:
                command.extend(["-burn", "1"])

            command.extend(
                ["-a_nodata", str(no_data_value), input_geojson, output_tif]
            )
            subprocess.run(command, check=True)


def convert_pk_to_string(pk_string):
    """Convert a PK string like `12+3` into a zero-padded numeric string."""
    if "+" in pk_string:
        pk_integer = int(pk_string.replace("+", ""))
        return f"{pk_integer:04d}"
    return f"{int(pk_string):04d}"


def merge_vector_files(vector_dir):
    """Merge supported vector files in a directory using `ogrmerge.py`."""
    input_vectors = (
        glob.glob(os.path.join(vector_dir, "*.gpkg"))
        + glob.glob(os.path.join(vector_dir, "*.geojson"))
        + glob.glob(os.path.join(vector_dir, "*.shp"))
    )

    if not input_vectors:
        return None

    base_name, ext = os.path.splitext(os.path.basename(input_vectors[0]))
    output_format_map = {
        ".gpkg": "GPKG",
        ".geojson": "GeoJSON",
        ".shp": "ESRI Shapefile",
    }
    output_format = output_format_map.get(ext.lower(), "GPKG")
    output_file = os.path.join(vector_dir, f"{base_name}_merged{ext}")
    merge_command = ["ogrmerge.py", "-single", "-f", output_format, "-o", output_file]
    merge_command.extend(input_vectors)
    subprocess.run(merge_command, check=True)
    return output_file


def merge_geoparquet_files(vector_dir):
    """Merge all GeoParquet files in a directory into one file."""
    input_parquets = glob.glob(os.path.join(vector_dir, "*.parquet"))
    if not input_parquets:
        return None

    geodataframes = [gpd.read_parquet(path) for path in input_parquets]
    merged_gdf = gpd.GeoDataFrame(pd.concat(geodataframes, ignore_index=True))

    base_filename = os.path.basename(input_parquets[0])
    base_name, ext = os.path.splitext(base_filename)
    if "_" in base_name:
        base_name = "_".join(base_name.split("_")[:-1]) + "_merged"
    else:
        base_name += "_merged"

    output_file = os.path.join(vector_dir, f"{base_name}{ext}")
    merged_gdf.to_parquet(output_file)
    return output_file


def dissolve_vector(input_vector, output_vector, dissolve_field=None):
    """Dissolve features from a vector dataset into a new output layer."""
    gdf = _read_vector(input_vector)
    dissolved_gdf = gdf.dissolve(by=dissolve_field) if dissolve_field else gdf.dissolve()
    _write_vector(dissolved_gdf, output_vector)
    return output_vector


def clip_vector_with_masks(input_vector_path, mask_folder, output_folder):
    """Clip a vector dataset with every supported mask found in a folder."""
    os.makedirs(output_folder, exist_ok=True)
    valid_extensions = [".parquet", ".geojson", ".gpkg", ".shp"]
    mask_files = [
        file_name
        for file_name in os.listdir(mask_folder)
        if os.path.splitext(file_name)[1].lower() in valid_extensions
    ]
    if not mask_files:
        return []

    input_gdf = _read_vector(input_vector_path)
    vector_extension = os.path.splitext(input_vector_path)[1].lower()
    outputs = []

    for mask_file in mask_files:
        mask_path = os.path.join(mask_folder, mask_file)
        mask_gdf = _read_vector(mask_path)
        clipped_gdf = gpd.clip(input_gdf, mask_gdf)

        output_name = f"{os.path.splitext(mask_file)[0]}_clipped{vector_extension}"
        output_path = os.path.join(output_folder, output_name)
        _write_vector(clipped_gdf, output_path)
        outputs.append(output_path)

    return outputs


def convert_and_buffer_vectors(input_folder, output_folder, target_epsg, buffer_distance=None):
    """Reproject, dissolve, and optionally buffer vector files in a directory."""
    os.makedirs(output_folder, exist_ok=True)
    outputs = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith((".shp", ".geojson")):
            input_path = os.path.join(input_folder, file_name)
            gdf = gpd.read_file(input_path).to_crs(epsg=target_epsg).dissolve()

            if buffer_distance is not None:
                gdf["geometry"] = gdf.buffer(buffer_distance)

            base_name, ext = os.path.splitext(file_name)
            parts = base_name.split("_")
            if parts[-1].isdigit() and len(parts[-1]) == 4:
                parts.pop()

            output_base = "_".join(parts) + f"_{target_epsg}"
            output_path = os.path.join(output_folder, f"{output_base}_buffered{ext}")
            gdf.to_file(output_path)
            outputs.append(output_path)

    return outputs


def convert_epsg_vectors(input_folder, output_folder, target_epsg):
    """Reproject and dissolve vector files in a directory."""
    os.makedirs(output_folder, exist_ok=True)
    outputs = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith((".shp", ".geojson")):
            input_path = os.path.join(input_folder, file_name)
            gdf = gpd.read_file(input_path).to_crs(epsg=target_epsg).dissolve()

            base_name, ext = os.path.splitext(file_name)
            parts = base_name.split("_")
            if parts[-1].isdigit() and len(parts[-1]) == 4:
                parts.pop()

            output_base = "_".join(parts) + f"_{target_epsg}"
            output_path = os.path.join(output_folder, f"{output_base}{ext}")
            gdf.to_file(output_path)
            outputs.append(output_path)

    return outputs

