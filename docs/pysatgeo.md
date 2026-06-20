# pysatgeo package

The top-level `pysatgeo` package exposes:

- package metadata such as `__version__`
- public processing functions re-exported lazily from the submodules
- the submodules themselves

This means both styles are valid:

```python
import pysatgeo

pysatgeo.reproject_clip_resample_tiff(...)
pysatgeo.assign_crs_to_vector(...)
```

```python
from pysatgeo.raster import reproject_clip_resample_tiff
from pysatgeo.vector import assign_crs_to_vector
```

The module pages are still useful when you want to browse functions by topic:

- `pysatgeo.raster`
- `pysatgeo.vector`
- `pysatgeo.raster_analysis`
- `pysatgeo.terrain`
- `pysatgeo.sampling`
- `pysatgeo.ranking`
- `pysatgeo.gee`
- `pysatgeo.netcdf`

This lazy export design keeps `import pysatgeo` lightweight while preserving
the more convenient top-level API.
