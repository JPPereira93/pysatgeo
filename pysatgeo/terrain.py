"""Terrain and DEM-related utilities."""

import os
import subprocess
import sys

import geopandas as gpd


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


def idw_interpolation(input_geojson, output_raster, zfield, aoi_path):
    """Perform IDW interpolation on point data clipped to an AOI extent."""
    gdal = _require_gdal()
    aoi = gpd.read_file(aoi_path)
    aoi_bounds = aoi.total_bounds
    gdal.Grid(
        output_raster,
        input_geojson,
        zfield=zfield,
        algorithm="invdist",
        outputBounds=aoi_bounds,
    )
    return output_raster


def convert_hgt_to_tiff(hgt_file, tiff_file):
    """Convert an HGT raster into GeoTIFF format."""
    gdal = _require_gdal()
    dataset = gdal.Open(hgt_file)
    if dataset is None:
        raise ValueError(f"Failed to open file {hgt_file}")

    driver = gdal.GetDriverByName("GTiff")
    driver.CreateCopy(tiff_file, dataset)
    dataset = None
    return tiff_file


def calculate_slope(input_dem, output_slope):
    """Calculate a slope raster from a DEM using gdaldem."""
    subprocess.run(
        ["gdaldem", "slope", input_dem, output_slope, "-compute_edges"], check=True
    )
    return {"input_dem": input_dem, "output_slope": output_slope}


def calculate_aspect(input_dem, output_aspect):
    """Calculate an aspect raster from a DEM using gdaldem."""
    subprocess.run(
        ["gdaldem", "aspect", input_dem, output_aspect, "-compute_edges"], check=True
    )
    return {"input_dem": input_dem, "output_aspect": output_aspect}


def fill_no_data(input_tiff, output_tiff, max_distance=5, smoothing_iterations=0):
    """Fill raster nodata cells using gdal_fillnodata.py."""
    gdal_fillnodata_script = None
    for path_dir in os.environ["PATH"].split(os.pathsep):
        candidate = os.path.join(path_dir, "gdal_fillnodata.py")
        if os.path.exists(candidate):
            gdal_fillnodata_script = candidate
            break

    if not gdal_fillnodata_script:
        raise FileNotFoundError("gdal_fillnodata.py not found in PATH")

    command = [sys.executable, gdal_fillnodata_script, input_tiff, output_tiff]
    if max_distance is not None:
        command.extend(["-md", str(max_distance)])
    if smoothing_iterations is not None:
        command.extend(["-si", str(smoothing_iterations)])
    command.extend(["-of", "GTiff"])

    subprocess.run(command, check=True, text=True, capture_output=True)
    return output_tiff
