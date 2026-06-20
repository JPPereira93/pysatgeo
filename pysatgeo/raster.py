"""Raster processing utilities for pysatgeo."""

import os
import glob
import subprocess
import sys

import geopandas as gpd
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from rasterio.crs import CRS
from rasterio.mask import mask
from shapely.geometry import box


def _output_path_with_suffix(input_path, suffix):
    """Return a new raster path using the original stem and the provided suffix."""
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return f"{stem}{suffix}"


def _run_command(command):
    """Run a GDAL command and fail loudly when it does not succeed."""
    subprocess.run(command, check=True)


def _find_script_on_path(script_name):
    """Return the first matching GDAL helper script found on PATH."""
    for path_dir in os.environ["PATH"].split(os.pathsep):
        candidate = os.path.join(path_dir, script_name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"{script_name} not found in PATH")


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


def reproject_clip_resample_tiff(
    input_tiff=None,
    output_tiff=None,
    aoi_shapefile=None,
    target_srs=None,
    target_res_x=None,
    target_res_y=None,
    resampling_method=None,
    clip=False,
    clip_by_extent=False,
    no_data=None,
):
    """Reproject, optionally clip, and resample a raster with `gdalwarp`."""
    if not input_tiff:
        raise ValueError("input_tiff must be provided")

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
        if aoi_shapefile is not None:
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


def align_rasters(rasters, source_path, output_suffix, folder_name="Aligned"):
    """Align raster files to the grid of the first raster and save them together."""
    if not rasters:
        return False

    gdal = _require_gdal()
    parent_dir = os.path.dirname(source_path.rstrip(os.sep))
    aligned_dir = os.path.join(parent_dir, folder_name)
    os.makedirs(aligned_dir, exist_ok=True)

    command = ["gdalbuildvrt", "-te"]
    hDataset = gdal.Open(rasters[0], gdal.GA_ReadOnly)
    if hDataset is None:
        return False
    
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null=True)
    if adfGeoTransform is None:
        return False

    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        raster_stem = os.path.splitext(base_filename)[0]
        vrt_file = os.path.join(aligned_dir, f"{raster_stem}.vrt")

        dfGeoXUL = adfGeoTransform[0]
        dfGeoYUL = adfGeoTransform[3]
        dfGeoXLR = (
            adfGeoTransform[0]
            + adfGeoTransform[1] * hDataset.RasterXSize
            + adfGeoTransform[2] * hDataset.RasterYSize
        )
        dfGeoYLR = (
            adfGeoTransform[3]
            + adfGeoTransform[4] * hDataset.RasterXSize
            + adfGeoTransform[5] * hDataset.RasterYSize
        )
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))

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
        os.remove(vrt_file)

    return True


def align_rasters_in_place(folder_path, output_suffix):
    """Align all TIFF files in a folder and write the outputs beside the inputs."""
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

    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        raster_stem = os.path.splitext(base_filename)[0]
        vrt_file = os.path.join(folder_path, f"{raster_stem}.vrt")

        dfGeoXUL = adfGeoTransform[0]
        dfGeoYUL = adfGeoTransform[3]
        dfGeoXLR = (
            adfGeoTransform[0]
            + adfGeoTransform[1] * hDataset.RasterXSize
            + adfGeoTransform[2] * hDataset.RasterYSize
        )
        dfGeoYLR = (
            adfGeoTransform[3]
            + adfGeoTransform[4] * hDataset.RasterXSize
            + adfGeoTransform[5] * hDataset.RasterYSize
        )
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))

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
        os.remove(vrt_file)

    return True


def stack_rasters(
    tiff_files, output_tiff, aoi_shapefile=None, chunk_size=None, operation=None
):
    """Clip and stack rasters, then aggregate them with a mean or sum."""
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
    scale_factors = []

    for tiff in tiff_files:
        ds = gdal.Open(tiff)
        if ds is None:
            raise ValueError(f"Could not open raster: {tiff}")

        scale = ds.GetRasterBand(1).GetScale()
        if scale is None:
            scale = 1.0
        scale_factors.append(scale)

        raster = rioxarray.open_rasterio(tiff, chunks=chunk_size).astype("float32")
        print(f"Starting the processing... {tiff}")
        no_data = raster.rio.nodata
        no_data_values.append(no_data)

        if "time" in raster.dims:
            raster = raster.squeeze(dim="time", drop=True)

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
            raster.close()
            ds = None

    stacked_rasters = xr.concat(raster_arrays, dim="band")

    if operation == "mean":
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).mean(
            dim="band"
        )

        average_scale = np.mean(scale_factors)
        if average_scale != 1.0:
            result_raster = result_raster * average_scale

    elif operation == "sum":
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).sum(
            dim="band"
        )

        total_scale = np.mean(scale_factors)
        if total_scale != 1.0:
            result_raster = result_raster * total_scale

    if aoi_shapefile:
        result_raster.rio.write_crs(aoi.crs, inplace=True)

    result_no_data_value = no_data_values[0]
    result_raster.rio.write_nodata(result_no_data_value, inplace=True)

    result_raster = result_raster.where(
        ~np.isnan(result_raster), other=result_no_data_value
    )
    result_raster.rio.to_raster(output_tiff)
    print(f"Stacked {operation} Raster saved at {output_tiff}")

    return output_tiff


def ssm_nan_fix(raster_dir):
    """Fix SSM rasters by capping values and applying the expected scale factor."""
    gdal = _require_gdal()

    for filename in os.listdir(raster_dir):
        if filename.endswith(".tiff"):
            tiff_path = os.path.join(raster_dir, filename)
            dataset = gdal.Open(tiff_path, gdal.GA_Update)
            if dataset is None:
                continue

            raster_array = dataset.ReadAsArray()
            raster_array[raster_array > 200] = 255
            raster_array = raster_array.astype(float)
            raster_array[raster_array != 255] /= 2
            dataset.GetRasterBand(1).WriteArray(raster_array)
            dataset = None

    return True


def assign_crs(input_tiffs, crs):
    """Assign a CRS to one raster path or a list of raster paths."""
    if not isinstance(input_tiffs, list):
        input_tiffs = [input_tiffs]

    outputs = []
    for tiff in input_tiffs:
        with rasterio.open(tiff) as src:
            profile = src.profile
            profile.update(crs=CRS.from_epsg(crs))
            data = src.read(1)
            output_file = os.path.splitext(tiff)[0] + f"_epsg{crs}.tif"

            with rasterio.open(output_file, "w", **profile) as dst:
                dst.write(data, 1)

        os.remove(tiff)
        os.rename(output_file, tiff)
        outputs.append(tiff)

    return outputs


def clip_raster_all_pixels(raster_path, vector_path, output_path, all_touched=True):
    """Clip a raster while including every pixel touched by the mask geometry."""
    vector_data = gpd.read_file(vector_path)

    with rasterio.open(raster_path) as src:
        out_image, out_transform = mask(
            src, vector_data.geometry, crop=True, all_touched=all_touched
        )
        out_meta = src.meta.copy()

    out_meta.update(
        {
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        }
    )

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)

    return output_path


def split_raster_bands(file_path, directory_path):
    """Split a multiband raster into separate single-band rasters."""
    output_paths = []
    with rasterio.open(file_path, "r+") as src:
        src.nodata = 0
        for band_idx in range(1, src.count + 1):
            band_data = src.read(band_idx)
            output_tiff_name = (
                f"{os.path.splitext(os.path.basename(file_path))[0]}_B{band_idx}.tif"
            )
            output_tiff_path = os.path.join(directory_path, output_tiff_name)

            profile = src.profile
            profile.update(count=1, dtype=rasterio.float64)

            with rasterio.open(output_tiff_path, "w", **profile) as dst:
                dst.write(band_data, 1)

            output_paths.append(output_tiff_path)

    return output_paths


def merge_tiffs(input_dir, output_tif):
    """Merge all TIFF files in a directory into one output raster."""
    gdal = _require_gdal()
    tiff_files = glob.glob(os.path.join(input_dir, "*.tif"))
    if not tiff_files:
        return None

    vrt = gdal.BuildVRT("temp.vrt", tiff_files)
    gdal.Translate(output_tif, vrt)
    vrt = None
    return output_tif


def subset_raster_into_parts(input_raster, num_parts):
    """Divide a raster into vertically stacked equal parts."""
    gdal = _require_gdal()
    src_ds = gdal.Open(input_raster)
    if src_ds is None:
        raise ValueError(f"Failed to open raster file: {input_raster}")

    width = src_ds.RasterXSize
    height = src_ds.RasterYSize
    part_height = height // num_parts
    output_files = []

    for i in range(num_parts):
        ulx = 0
        uly = i * part_height
        lrx = width
        lry = (i + 1) * part_height if i < num_parts - 1 else height
        output_file = f"{os.path.splitext(input_raster)[0]}_part_{i + 1}.tif"
        output_files.append(output_file)
        gdal.Translate(
            output_file,
            src_ds,
            srcWin=[ulx, uly, lrx - ulx, lry - uly],
            format="GTiff",
        )

    src_ds = None
    return output_files


def polygonize_raster(
    input_tiff, output_vector=None, layer_name="layer", output_format="Parquet"
):
    """Polygonize a raster and write the features to a vector dataset."""
    format_extensions = {
        "GPKG": ".gpkg",
        "GeoJSON": ".geojson",
        "Parquet": ".parquet",
        "Shapefile": ".shp",
    }

    if output_vector is None:
        base_name, _ = os.path.splitext(input_tiff)
        output_vector = base_name + format_extensions.get(output_format, ".gpkg")

    gdal_polygonize_script = _find_script_on_path("gdal_polygonize.py")

    command = [
        sys.executable,
        gdal_polygonize_script,
        input_tiff,
        "-f",
        output_format,
        output_vector,
        layer_name,
    ]
    subprocess.run(command, check=True, text=True, capture_output=True)
    return output_vector


def clip_rasters_by_extent(input_folder, output_folder, mask_layer_path):
    """Clip all rasters in a folder to the bounding box of a mask layer."""
    os.makedirs(output_folder, exist_ok=True)
    mask_bounds = gpd.read_file(mask_layer_path).total_bounds
    output_paths = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".tif"):
            input_raster_path = os.path.join(input_folder, file_name)
            base_name, ext = os.path.splitext(file_name)
            output_raster_path = os.path.join(output_folder, f"{base_name}_clipped{ext}")

            raster = rioxarray.open_rasterio(input_raster_path, masked=True)
            clipped_raster = raster.rio.clip_box(*mask_bounds)
            clipped_raster.rio.to_raster(output_raster_path)
            output_paths.append(output_raster_path)

    return output_paths


def clip_raster_with_vector(raster_file, geojson_directory, output_directory):
    """Clip one raster by every GeoJSON mask file in a directory."""
    raster = rioxarray.open_rasterio(raster_file, masked=True)
    output_paths = []

    for file_name in os.listdir(geojson_directory):
        if file_name.endswith(".geojson"):
            geojson_path = os.path.join(geojson_directory, file_name)
            geojson = gpd.read_file(geojson_path).to_crs(raster.rio.crs)
            clipped_raster = raster.rio.clip(geojson.geometry, geojson.crs, drop=True)

            output_file = os.path.join(
                output_directory, file_name.replace(".geojson", "_clipped.tif")
            )
            clipped_raster.rio.to_raster(output_file, driver="GTiff")
            output_paths.append(output_file)

    return output_paths


def clip_raster_by_masks(input_raster_path, mask_input, output_folder):
    """Clip one or many rasters by one or many mask layers."""
    os.makedirs(output_folder, exist_ok=True)

    if os.path.isdir(input_raster_path):
        raster_files = [
            file_name
            for file_name in os.listdir(input_raster_path)
            if file_name.endswith((".tif", ".tiff"))
        ]
    elif os.path.isfile(input_raster_path) and input_raster_path.endswith(
        (".tif", ".tiff")
    ):
        raster_files = [os.path.basename(input_raster_path)]
    else:
        raise ValueError("Invalid raster input.")

    if os.path.isdir(mask_input):
        mask_files = [
            file_name
            for file_name in os.listdir(mask_input)
            if file_name.endswith((".shp", ".geojson"))
        ]
    elif os.path.isfile(mask_input) and mask_input.endswith((".shp", ".geojson")):
        mask_files = [os.path.basename(mask_input)]
    else:
        raise ValueError("Invalid mask input.")

    output_paths = []
    for raster_file in raster_files:
        raster_path = (
            os.path.join(input_raster_path, raster_file)
            if os.path.isdir(input_raster_path)
            else input_raster_path
        )
        input_raster_name = os.path.splitext(raster_file)[0]

        for mask_file in mask_files:
            mask_path = (
                os.path.join(mask_input, mask_file)
                if os.path.isdir(mask_input)
                else mask_input
            )
            mask_name = os.path.splitext(os.path.basename(mask_file))[0]

            mask_gdf = gpd.read_file(mask_path)
            raster = rioxarray.open_rasterio(raster_path, masked=True)
            clipped_raster = raster.rio.clip(mask_gdf.geometry, mask_gdf.crs, drop=True)

            output_file_name = f"{input_raster_name}_clipped_by_{mask_name}.tif"
            output_raster_path = os.path.join(output_folder, output_file_name)
            clipped_raster.rio.to_raster(output_raster_path)
            output_paths.append(output_raster_path)

    return output_paths


def clip_raster_to_reference_extent(ground_truth_path, prediction_path):
    """Clip one raster to another raster's extent and dimensions."""
    with rasterio.open(prediction_path) as pred_src:
        pred_extent = pred_src.bounds
        pred_box = box(*pred_extent)
        pred_width = pred_src.width
        pred_height = pred_src.height
        pred_transform = pred_src.transform

    with rasterio.open(ground_truth_path, "r+") as gt_src:
        ground_truth, _ = mask(gt_src, [pred_box], crop=True)
        if ground_truth.shape[1] != pred_height or ground_truth.shape[2] != pred_width:
            ground_truth_resized = np.resize(
                ground_truth, (ground_truth.shape[0], pred_height, pred_width)
            )
        else:
            ground_truth_resized = ground_truth

        clipped_gt_meta = gt_src.meta.copy()
        clipped_gt_meta.update(
            {
                "height": ground_truth_resized.shape[1],
                "width": ground_truth_resized.shape[2],
                "transform": pred_transform,
            }
        )

    with rasterio.open(ground_truth_path, "w", **clipped_gt_meta) as out_src:
        out_src.write(ground_truth_resized)

    return ground_truth_resized, clipped_gt_meta

