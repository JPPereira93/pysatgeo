# pysatgeo

[![PyPI version](https://img.shields.io/pypi/v/pysatgeo.svg)](https://pypi.org/project/pysatgeo/)
[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/pysatgeo.svg)](https://anaconda.org/conda-forge/pysatgeo)

`pysatgeo` is a small Python package for raster and vector geospatial
processing.

The project started as a learning repo for packaging, CI, and geospatial
utilities. It has now been trimmed down to a smaller set of maintained modules
with clearer imports, better tests, and lighter docs.

## Current Scope

The package is organized into a few focused modules:

- `raster`: reprojection, clipping, stacking, alignment, polygonizing
- `vector`: CRS assignment, format conversion, clipping, dissolve
- `raster_analysis`: normalization, reclassification, clustering
- `terrain`: DEM-related helpers such as slope and aspect
- `sampling`: point generation and raster sampling
- `ranking`: simple AHP-style ranking helpers
- `styles`, `netcdf`, and `gee`: smaller utility modules

## Project Status

This package is still modest, but it is much more coherent than the original
experimental repo.

- Public imports are available from `pysatgeo` itself.
- Top-level imports are resolved lazily to keep `import pysatgeo` lightweight.
- Core behavior is covered by automated tests.
- Old experimental modules that were not maintained or documented have been removed.

## Installation

If you want to install the published package as a normal dependency:

```powershell
pip install pysatgeo
```

Because the package depends on GDAL, `rasterio`, and `geopandas`, a Conda
environment is usually the easiest setup, especially on Windows.

Example:

```powershell
conda create -n pysatgeo python=3.11 -y
conda activate pysatgeo
conda install -c conda-forge geopandas rasterio rioxarray gdal pyarrow shapely xarray scikit-learn matplotlib mapclassify scipy pytest -y
pip install pysatgeo
```

If you want the latest GitHub code without a local clone:

```powershell
pip install git+https://github.com/JPPereira93/pysatgeo.git
```

If you are working from this repository:

```powershell
pip install -r requirements.txt
pip install -e .
```

## Quick Start

Import the package directly:

```python
import pysatgeo
```

Use functions from the top level:

```python
import pysatgeo

pysatgeo.reproject_clip_resample_tiff(...)
pysatgeo.assign_crs_to_vector(...)
```

Module-level imports still work too:

```python
from pysatgeo.raster import reproject_clip_resample_tiff
from pysatgeo.vector import assign_crs_to_vector
```

## Development

Run the test suite from the repository root:

```powershell
conda run -n pysatgeo pytest -q
```

The current test suite covers:

- top-level package import behavior
- raster and vector validation paths
- raster sampling and analysis helpers
- ranking helpers
- NetCDF and style parsing utilities

## Documentation

Project documentation lives in the `docs/` folder and is published at:

<https://JPPereira93.github.io/pysatgeo>

The most useful pages are:

- `docs/usage.md` for quick examples
- `docs/installation.md` for environment setup
- the API Reference pages for module docs

## License

MIT License
