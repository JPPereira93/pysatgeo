# Installation

## PyPI Install

To install the latest published release:

```powershell
pip install pysatgeo
```

## Conda Environment For Geospatial Work

Because geospatial dependencies can be tricky, especially on Windows, Conda is
often the most reliable setup:

```powershell
conda create -n pysatgeo python=3.11 -y
conda activate pysatgeo
conda install -c conda-forge geopandas rasterio rioxarray gdal pyarrow shapely xarray scikit-learn matplotlib mapclassify scipy pytest -y
pip install pysatgeo
```

## Install From Source

If you are working on the repository itself:

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
