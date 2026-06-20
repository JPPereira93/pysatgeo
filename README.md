# pysatgeo

[![PyPI version](https://img.shields.io/pypi/v/pysatgeo.svg)](https://pypi.org/project/pysatgeo/)
[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/pysatgeo.svg)](https://anaconda.org/conda-forge/pysatgeo)

`pysatgeo` is a small Python package for raster and vector geospatial processing.

The project started as a learning repo for packaging, CI, and geospatial utilities. It is now being cleaned up into a more maintainable library with basic tests and a smaller, clearer API surface.

## Current Scope

The package currently focuses on a small set of raster and vector helpers:

- raster reprojection, clipping, and resampling
- raster alignment to a common grid
- raster stacking with `mean` or `sum`
- assigning CRS information to vector files
- shifting a vector layer to match a raster reference extent
- converting GeoJSON files to GeoParquet

## Project Status

This package is still evolving.

- Core packaging and import behavior have been cleaned up.
- Basic automated tests are in place.
- The API is still being narrowed and standardized.
- Some geospatial workflows are more mature than others.

## Installation

Because this package depends on geospatial libraries such as GDAL, `rasterio`, and `geopandas`, a Conda environment is usually the easiest setup, especially on Windows.

Example with Conda:

```powershell
conda create -n pysatgeo python=3.11 -y
conda activate pysatgeo
conda install -c conda-forge geopandas rasterio rioxarray gdal pyarrow shapely xarray scikit-learn matplotlib mapclassify pytest -y
pip install -e .
```

If you already have a working Python environment with GDAL-compatible geospatial packages, you can also install the project with:

```powershell
pip install -r requirements.txt
pip install -e .
```

## Quick Start

Import modules directly:

```python
from pysatgeo.raster import reproject_clip_resample_tiff, stack_rasters
from pysatgeo.vector import assign_crs_to_vector
```

### Raster Example

Reproject, clip, and resample a raster:

```python
from pysatgeo.raster import reproject_clip_resample_tiff

reproject_clip_resample_tiff(
    input_tiff="input.tif",
    output_tiff="output.tif",
    aoi_shapefile="aoi.geojson",
    target_srs="EPSG:32629",
    target_res_x=30,
    target_res_y=30,
    resampling_method="bilinear",
    clip=True,
    clip_by_extent=True,
    no_data=-9999,
)
```

Stack multiple rasters:

```python
from pysatgeo.raster import stack_rasters

stack_rasters(
    tiff_files=["raster_1.tif", "raster_2.tif"],
    output_tiff="stacked_sum.tif",
    operation="sum",
)
```

### Vector Example

Assign a CRS to a vector file:

```python
from pysatgeo.vector import assign_crs_to_vector

assign_crs_to_vector(
    input_geojson_path="input.geojson",
    output_geojson_path="output.geojson",
    crs_epsg=4326,
)
```

## Development

Run the test suite from the repository root:

```powershell
pytest -v
```

The current tests cover:

- package metadata import
- raster and vector module import
- basic validation errors
- a simple vector CRS workflow

## Documentation

Project documentation lives in the `docs/` folder and is published at:

<https://JPPereira93.github.io/pysatgeo>

## License

MIT License
