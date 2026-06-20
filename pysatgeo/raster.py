"""
Raster-related functions for pysatgeo.
"""

import rioxarray
import numpy as np
import geopandas as gpd
import os
import subprocess
import xarray as xr


def _output_path_with_suffix(input_path, suffix):
    """Return a new raster path using the original stem and the provided suffix."""
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return f"{stem}{suffix}"


def _run_command(command):
    """Run a GDAL command and fail loudly when it does not succeed."""
    subprocess.run(command, check=True)


def _require_gdal():
    """Import GDAL only when a function actually needs the Python bindings."""
    try:
        from osgeo import gdal
    except ImportError as exc:
        raise ImportError(
            "GDAL Python bindings are required for this function. "
            "Install GDAL in the current environment."
        ) from exc
    return gdal


def reproject_clip_resample_tiff(input_tiff=None, output_tiff=None, aoi_shapefile=None, target_srs=None, target_res_x=None, target_res_y=None, resampling_method=None, clip=False, clip_by_extent=False, no_data=None):
    """
    Reprojects, optionally clips, and resamples a TIFF file based on an AOI shapefile.

    :param input_tiff: Path to the input TIFF file
    :param output_tiff: Path for the output TIFF file
    :param aoi_shapefile: Optional path to the AOI shapefile or GeoDataFrame. Required if clip is True.
    :param target_srs: Optional target spatial reference system (ex: 'EPSG:32629')
    :param target_res_x: Optional target resolution in x (meters)
    :param target_res_y: Optional target resolution in y (meters)
    :param resampling_method: Optional resampling method (ex: 'bilinear')
    :param clip: Boolean to determine whether to clip the raster
    :param clip_by_extent: Boolean to determine whether to clip the raster by the extent of the AOI.
    :param no_data: Optional no data value to be set for the output TIFF
    """
    if not input_tiff:
        raise ValueError("input_tiff must be provided")

    # Check if the output TIFF path is given, otherwise create a new one based on the input TIFF
    if not output_tiff:
        base, ext = os.path.splitext(input_tiff)
        output_tiff = f"{base}_new.tif"

    cmd_reproject = ["gdalwarp"]

    if target_srs:
        cmd_reproject.extend(["-t_srs", str(target_srs)])
    if target_res_x and target_res_y:
        cmd_reproject.extend(["-tr", str(target_res_x), str(target_res_y)])
    if resampling_method:
        cmd_reproject.extend(["-r", str(resampling_method)])
    if clip:
        if aoi_shapefile:
            if clip_by_extent:
                # Extract the extent if it is a GeoDataFrame or load it from a shapefile
                if isinstance(aoi_shapefile, gpd.geodataframe.GeoDataFrame):
                    bounds = aoi_shapefile.total_bounds
                else:
                    aoi_gdf = gpd.read_file(aoi_shapefile)
                    bounds = aoi_gdf.total_bounds
                cmd_reproject.extend(["-te", *(str(value) for value in bounds)])
            else:
                if isinstance(aoi_shapefile, gpd.geodataframe.GeoDataFrame):
                    raise TypeError(
                        "aoi_shapefile must be a file path when clip_by_extent is False"
                    )
                cmd_reproject.extend(["-cutline", aoi_shapefile, "-crop_to_cutline"])
        else:
            raise ValueError("AOI shapefile must be provided if clip is True")
    if no_data is not None:
        cmd_reproject.extend(["-dstnodata", str(no_data)])

    cmd_reproject.extend([input_tiff, output_tiff])

    _run_command(cmd_reproject)
    return output_tiff

# Example usage:
# reproject_clip_resample_tiff(
#     input_tiff="path/to/your/input_raster.tif",
#     output_tiff="path/to/your/output_raster.tif",
#     aoi_shapefile="path/to/your/aoi_shapefile.shp",
#     target_srs="EPSG:32629",
#     target_res_x=30,
#     target_res_y=30,
#     resampling_method="bilinear",
#     clip=True,
#     clip_by_extent=True,
#     no_data=-9999,
# )


def align_rasters(rasters, source_path, output_suffix, folder_name='Aligned'):
    """
    Aligns list of rasters to have the same resolution and 
    cell size for pixel-based calculations. Saves aligned rasters in a specified folder.
    
    :param rasters: List of raster paths.
    :type rasters: List
    :param source_path: Path to the source directory of rasters.
    :type source_path: String
    :param output_suffix: The output aligned rasters files suffix with extension.
    :type output_suffix: String
    :param folder_name: Name of the folder to save aligned rasters, defaults to 'Aligned'.
    :type folder_name: String
    :return: True if the process runs and False if the data couldn't be read. 
    :rtype: Boolean
    """
    if not rasters:
        return False

    gdal = _require_gdal()

    # Calculate the parent directory of source_path
    parent_dir = os.path.dirname(source_path.rstrip(os.sep))
    
    # Construct the path to the specified folder
    aligned_dir = os.path.join(parent_dir, folder_name)
    
    # Check if the folder exists, if not, create it
    os.makedirs(aligned_dir, exist_ok=True)
    
    command = ["gdalbuildvrt", "-te"]
    hDataset = gdal.Open(rasters[0], gdal.GA_ReadOnly)
    if hDataset is None:
        return False
    
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null=True)
    if adfGeoTransform is None:
        return False
    
    # Process each raster in the list
    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        raster_stem = os.path.splitext(base_filename)[0]
        vrt_file = os.path.join(aligned_dir, f"{raster_stem}.vrt")

        # Calculate the corners of the bounding box for each raster
        dfGeoXUL = adfGeoTransform[0]  # Upper left X
        dfGeoYUL = adfGeoTransform[3]  # Upper left Y
        dfGeoXLR = adfGeoTransform[0] + adfGeoTransform[1] * hDataset.RasterXSize + adfGeoTransform[2] * hDataset.RasterYSize  # Lower right X
        dfGeoYLR = adfGeoTransform[3] + adfGeoTransform[4] * hDataset.RasterXSize + adfGeoTransform[5] * hDataset.RasterYSize  # Lower right Y
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))
        
        # Build and translate VRT to final raster with specified resolution
        _run_command(
            command
            + [
                str(dfGeoXUL),
                str(dfGeoYLR),
                str(dfGeoXLR),
                str(dfGeoYUL),
                "-q",
                "-tr",
                xres,
                yres,
                vrt_file,
                tif_file,
            ]
        )
        
        output_file = os.path.join(
            aligned_dir, _output_path_with_suffix(base_filename, output_suffix)
        )
        _run_command(["gdal_translate", "-q", vrt_file, output_file])
        os.remove(vrt_file)  # Clean up temporary VRT file
    
    return True

# Example usage:
# rasters = ["path/to/raster1.tif", "path/to/raster2.tif"]
# output_suffix = "_aligned.tif"
# align_rasters(rasters, "/path/to/source", output_suffix, "Aligned_8_5")

    
def align_rasters_in_place(folder_path, output_suffix):
    """
    Aligns all .tiff files in the specified folder to have the same resolution and 
    cell size for pixel-based calculations. Saves aligned rasters in the same folder.
    
    :param folder_path: Path to the folder containing .tiff files.
    :type folder_path: String
    :param output_suffix: The output aligned rasters files suffix with extension.
    :type output_suffix: String
    :return: True if the process runs and False if the data couldn't be read. 
    :rtype: Boolean
    """
    # List all .tiff files in the folder
    rasters = [
        os.path.join(folder_path, filename)
        for filename in os.listdir(folder_path)
        if filename.endswith(".tiff") or filename.endswith(".tif")
    ]
    
    if not rasters:
        print("No .tiff files found in the specified folder.")
        return False

    gdal = _require_gdal()
    
    command = ["gdalbuildvrt", "-te"]
    hDataset = gdal.Open(rasters[0], gdal.GA_ReadOnly)
    if hDataset is None:
        return False
    
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null=True)
    if adfGeoTransform is None:
        return False
    
    # Process each raster in the list
    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        raster_stem = os.path.splitext(base_filename)[0]
        vrt_file = os.path.join(folder_path, f"{raster_stem}.vrt")

        # Calculate the corners of the bounding box for each raster
        dfGeoXUL = adfGeoTransform[0]  # Upper left X
        dfGeoYUL = adfGeoTransform[3]  # Upper left Y
        dfGeoXLR = adfGeoTransform[0] + adfGeoTransform[1] * hDataset.RasterXSize + adfGeoTransform[2] * hDataset.RasterYSize  # Lower right X
        dfGeoYLR = adfGeoTransform[3] + adfGeoTransform[4] * hDataset.RasterXSize + adfGeoTransform[5] * hDataset.RasterYSize  # Lower right Y
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))
        
        # Build and translate VRT to final raster with specified resolution
        _run_command(
            command
            + [
                str(dfGeoXUL),
                str(dfGeoYLR),
                str(dfGeoXLR),
                str(dfGeoYUL),
                "-q",
                "-tr",
                xres,
                yres,
                vrt_file,
                tif_file,
            ]
        )
        
        output_file = os.path.join(
            folder_path, _output_path_with_suffix(base_filename, output_suffix)
        )
        _run_command(["gdal_translate", "-q", vrt_file, output_file])
        os.remove(vrt_file)  # Clean up temporary VRT file
    
    return True

# Example usage:
# align_rasters_in_place("E:\\Spotlite_JPereira\\Ascendi\\Concessao_Beira_Litoral\\2030\\Aligned", "_aligned.tif")    



def stack_rasters(tiff_files, output_tiff, aoi_shapefile=None, chunk_size=None, operation=None):
    """
    Clips, stacks a list of raster files based on an AOI shapefile, calculates the sum, median, or mean of the stack,
    and saves the resulting raster to a file. Processes data in chunks to reduce memory usage.

    :param tiff_files: List of paths to the input TIFF files
    :param aoi_shapefile: Path to the AOI shapefile (optional, default is None)
    :param output_tiff: Path for the output raster file
    :param operation: Operation to perform on the stack ('mean', 'sum')
    :param chunk_size: Size of chunks for processing (e.g., (500, 500))
    :return: None
    """
    if not tiff_files:
        raise ValueError("tiff_files must contain at least one raster path")

    if operation not in {"mean", "sum"}:
        raise ValueError("Invalid operation. Choose 'mean' or 'sum'")

    gdal = _require_gdal()

    if aoi_shapefile:
        aoi = gpd.read_file(aoi_shapefile)
        polygon_geometry = [aoi.geometry.iloc[0]]
    else:
        polygon_geometry = None

    raster_arrays = []
    no_data_values = []
    scale_factors = []  # List to hold scaling factors

    for tiff in tiff_files:
        ds = gdal.Open(tiff)
        if ds is None:
            raise ValueError(f"Could not open raster: {tiff}")
        
        # Get the scale
        scale = ds.GetRasterBand(1).GetScale()
        if scale is None:
            scale = 1.0  # Default scale if none is found
        scale_factors.append(scale)

        # Open the raster and convert to float32
        raster = rioxarray.open_rasterio(tiff, chunks=chunk_size).astype('float32')
        print(f"Starting the processing... {tiff}")
        no_data = raster.rio.nodata
        no_data_values.append(no_data)

        # Check if 'time' dimension is present and remove it
        if 'time' in raster.dims:
            raster = raster.squeeze(dim='time', drop=True)

        try:
            if polygon_geometry:
                processed_raster = raster.rio.clip(
                    polygon_geometry, aoi.crs, drop=True, invert=False
                )
            else:
                processed_raster = raster

            if no_data is not None:
                processed_raster = processed_raster.where(
                    processed_raster != no_data, other=np.nan
                )

            raster_arrays.append(processed_raster.load())
        finally:
            # Ensure the file is closed after processing
            raster.close()
            ds = None  

    # Stack the rasters across bands
    stacked_rasters = xr.concat(raster_arrays, dim='band')

    if operation == 'mean':
        # Exclude NoData pixels from the mean calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).mean(dim='band')

        # Adjust the mean raster based on the scale factor
        average_scale = np.mean(scale_factors)
        if average_scale != 1.0:
            result_raster = result_raster * average_scale

    elif operation == 'sum':
        # Exclude NoData pixels from the sum calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).sum(dim='band')

        # Adjust the sum raster based on the scale factor
        total_scale = np.mean(scale_factors)  # You can modify this as needed
        if total_scale != 1.0:
            result_raster = result_raster * total_scale

    # Set the CRS of the result raster to match the vector CRS if AOI is provided
    if aoi_shapefile:
        result_raster.rio.write_crs(aoi.crs, inplace=True)

    # Set the NoData value for the result raster to the NoData of the first raster
    result_no_data_value = no_data_values[0]
    result_raster.rio.write_nodata(result_no_data_value, inplace=True)

    # Replace remaining NaN values with NoData in the result
    result_raster = result_raster.where(~np.isnan(result_raster), other=result_no_data_value)
    result_raster.rio.to_raster(output_tiff)
    print(f"Stacked {operation} Raster saved at {output_tiff}")

    return output_tiff

# Example usage:
# tiff_files = [...]
# output_tiff = "path/to/sum_raster.tif"
# aoi_shapefile = "path/to/aoi.geojson"
# chunk_size = (500, 500)
# stack_rasters(tiff_files, output_tiff, aoi_shapefile, chunk_size, operation="sum")

