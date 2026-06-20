#!/usr/bin/env python

"""Tests for `pysatgeo` package."""


import importlib

import geopandas as gpd
import pytest
from shapely.geometry import Point

import pysatgeo


def test_package_has_version():
    assert isinstance(pysatgeo.__version__, str)
    assert pysatgeo.__version__


def test_raster_module_imports():
    raster = importlib.import_module("pysatgeo.raster")
    assert hasattr(raster, "stack_rasters")


def test_vector_module_imports():
    vector = importlib.import_module("pysatgeo.vector")
    assert hasattr(vector, "assign_crs_to_vector")


def test_reproject_clip_resample_tiff_requires_input():
    from pysatgeo.raster import reproject_clip_resample_tiff

    with pytest.raises(ValueError, match="input_tiff must be provided"):
        reproject_clip_resample_tiff()


def test_stack_rasters_requires_files(tmp_path):
    from pysatgeo.raster import stack_rasters

    output_path = tmp_path / "out.tif"

    with pytest.raises(ValueError, match="tiff_files must contain at least one raster path"):
        stack_rasters([], str(output_path), operation="sum")


def test_assign_crs_to_vector_writes_output(tmp_path):
    from pysatgeo.vector import assign_crs_to_vector

    input_path = tmp_path / "input.geojson"
    output_path = tmp_path / "output.geojson"

    gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    gdf.to_file(input_path, driver="GeoJSON")

    result = assign_crs_to_vector(str(input_path), str(output_path), 4326)

    saved = gpd.read_file(output_path)

    assert result == str(output_path)
    assert output_path.exists()
    assert saved.crs.to_epsg() == 4326
