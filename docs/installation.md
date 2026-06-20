# Installation

## Install As A Normal Package

If you just want to use `pysatgeo` in a project, and not develop the repo
itself, install it from PyPI:

```powershell
pip install pysatgeo
```

That installs the latest published version like any other Python dependency.

## Install In A Geospatial Conda Environment

If you are on Windows or want the safest setup for GDAL-based libraries, create
the environment first and then install the published package into it:

```powershell
conda create -n pysatgeo python=3.11 -y
conda activate pysatgeo
conda install -c conda-forge geopandas rasterio rioxarray gdal pyarrow shapely xarray scikit-learn matplotlib mapclassify scipy pytest -y
pip install pysatgeo
```

This is still a normal package install. The only difference is that the
underlying geospatial dependencies come from Conda.

## Install The Latest Unreleased GitHub Version

If you want the current GitHub code without cloning the repo locally:

```powershell
pip install git+https://github.com/JPPereira93/pysatgeo.git
```

## Install From Source For Development

Only use this if you are working on the repository itself and want local edits
to affect the installed package:

```powershell
git clone https://github.com/JPPereira93/pysatgeo.git
cd pysatgeo
pip install -r requirements.txt
pip install -e .
```

## Development Extras

To build docs, run checks, or work on the package locally:

```powershell
pip install -r requirements_dev.txt
```
