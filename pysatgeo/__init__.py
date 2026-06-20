"""Top-level package for pysatgeo.

The public API is exposed lazily so `import pysatgeo` stays lightweight,
while functions remain available as `pysatgeo.some_function(...)`.
"""

from importlib import import_module

__author__ = "Joao Pereira"
__email__ = "joaopmpereira93@gmail.com"
__version__ = "1.0.0"

_MODULE_EXPORTS = {
    "gee": {
        "split_region",
        "addNDVI_ee",
        "apply_cloud_masks_ee",
        "apply_scale_factor_ee",
        "export_tiled_mosaic",
    },
    "netcdf": {
        "extract_year_from_filename",
        "process_netcdf",
        "process_all_netcdfs",
        "save_to_csv",
    },
    "ranking": {
        "normalize_custom_ranking",
        "create_ahp_matrix",
        "calculate_ahp_weights",
    },
    "raster": {
        "reproject_clip_resample_tiff",
        "align_rasters",
        "align_rasters_in_place",
        "stack_rasters",
        "ssm_nan_fix",
        "assign_crs",
        "clip_raster_all_pixels",
        "split_raster_bands",
        "merge_tiffs",
        "subset_raster_into_parts",
        "polygonize_raster",
        "clip_rasters_by_extent",
        "clip_raster_with_vector",
        "clip_raster_by_masks",
        "clip_raster_to_reference_extent",
    },
    "raster_analysis": {
        "distance_matrix",
        "reclassify_raster",
        "reclassify_raster_nbreaks",
        "set_nodata_value",
        "normalize_raster",
        "normalize_raster_fixed_scale",
        "invert_raster_values",
        "process_kmeans",
        "relabel_clusters",
        "process_directory",
        "convert_raster_to_integers",
        "plot_silhouette_scores",
        "process_raster_for_silhouette",
        "remove_outliers",
    },
    "sampling": {
        "get_raster_values",
        "generate_points_within_polygon",
        "generate_points_outside_polygons",
    },
    "styles": {
        "parse_qml_colors",
    },
    "terrain": {
        "idw_interpolation",
        "convert_hgt_to_tiff",
        "calculate_slope",
        "calculate_aspect",
        "fill_no_data",
    },
    "vector": {
        "assign_crs_to_vector",
        "convert_geojson_to_geoparquet",
        "shift_vector_to_raster_reference",
        "rasterize",
        "convert_pk_to_string",
        "merge_vector_files",
        "merge_geoparquet_files",
        "dissolve_vector",
        "clip_vector_with_masks",
        "convert_and_buffer_vectors",
        "convert_epsg_vectors",
    },
}

_MODULE_NAMES = tuple(_MODULE_EXPORTS)
_NAME_TO_MODULE = {
    export_name: module_name
    for module_name, export_names in _MODULE_EXPORTS.items()
    for export_name in export_names
}

__all__ = [
    "__author__",
    "__email__",
    "__version__",
    *_MODULE_NAMES,
    *sorted(_NAME_TO_MODULE),
]


def __getattr__(name):
    """Resolve modules and public functions lazily."""
    if name in _MODULE_NAMES:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module

    module_name = _NAME_TO_MODULE.get(name)
    if module_name is not None:
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Return the names available from the public package namespace."""
    return sorted(__all__)
