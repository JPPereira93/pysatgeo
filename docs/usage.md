# Usage

`pysatgeo` now exposes its public functions from the top-level package.

This means:

- `import pysatgeo` works
- package metadata like `pysatgeo.__version__` works
- public functions can be called directly as `pysatgeo.some_function(...)`
- module imports such as `pysatgeo.raster` and `pysatgeo.vector` still work too

## Basic Import

```python
import pysatgeo

print(pysatgeo.__version__)
```

## Use Functions From The Top Level

```python
import pysatgeo

pysatgeo.reproject_clip_resample_tiff(...)
pysatgeo.stack_rasters(...)
pysatgeo.assign_crs_to_vector(...)
```

## Module Imports Still Work

```python
from pysatgeo.raster import reproject_clip_resample_tiff, stack_rasters
from pysatgeo.vector import assign_crs_to_vector
```

## Raster Example

Reproject, clip, and resample a raster:

```python
import pysatgeo

output_raster = pysatgeo.reproject_clip_resample_tiff(
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
import pysatgeo

pysatgeo.stack_rasters(
    tiff_files=["raster_1.tif", "raster_2.tif"],
    output_tiff="stacked_sum.tif",
    operation="sum",
)
```

## Vector Example

Assign a CRS to a vector dataset:

```python
import pysatgeo

pysatgeo.assign_crs_to_vector(
    input_geojson_path="input.geojson",
    output_geojson_path="output.geojson",
    crs_epsg=4326,
)
```

Shift a vector layer to a raster reference:

```python
import pysatgeo

pysatgeo.shift_vector_to_raster_reference(
    vector_path="roads.geojson",
    raster_path="reference.tif",
    output_vector_path="roads_shifted.geojson",
)
```

## Current Recommendation

Use whichever style feels clearer in your codebase:

- `import pysatgeo` if you want one package entry point
- `from pysatgeo.raster import ...` if you want module-level clarity

For learning and notebooks, `import pysatgeo` is usually the nicest experience now.
