#!/usr/bin/env python

"""Tests for the `pysatgeo` package."""

import importlib

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, Polygon

import pysatgeo


def _write_test_raster(path, data, crs="EPSG:4326", nodata=None):
    """Write a small single-band raster for tests."""
    height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=from_origin(0, float(height), 1, 1),
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)


def test_package_has_version():
    assert isinstance(pysatgeo.__version__, str)
    assert pysatgeo.__version__


def test_top_level_exports_are_available():
    assert callable(pysatgeo.reproject_clip_resample_tiff)
    assert callable(pysatgeo.assign_crs_to_vector)
    assert callable(pysatgeo.normalize_custom_ranking)


def test_raster_module_imports():
    raster = importlib.import_module("pysatgeo.raster")
    assert hasattr(raster, "stack_rasters")


def test_vector_module_imports():
    vector = importlib.import_module("pysatgeo.vector")
    assert hasattr(vector, "assign_crs_to_vector")


def test_reproject_clip_resample_tiff_requires_input():
    with pytest.raises(ValueError, match="input_tiff must be provided"):
        pysatgeo.reproject_clip_resample_tiff()


def test_reproject_clip_resample_tiff_requires_aoi_when_clip_enabled():
    with pytest.raises(ValueError, match="AOI shapefile must be provided if clip is True"):
        pysatgeo.reproject_clip_resample_tiff(
            input_tiff="input.tif",
            output_tiff="output.tif",
            clip=True,
        )


def test_reproject_clip_resample_tiff_builds_extent_command(monkeypatch):
    captured = {}
    aoi = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )

    def fake_run(command):
        captured["command"] = command

    monkeypatch.setattr("pysatgeo.raster._run_command", fake_run)

    result = pysatgeo.reproject_clip_resample_tiff(
        input_tiff="input.tif",
        output_tiff="output.tif",
        aoi_shapefile=aoi,
        clip=True,
        clip_by_extent=True,
        target_srs="EPSG:4326",
        target_res_x=10,
        target_res_y=20,
        resampling_method="bilinear",
        no_data=-9999,
    )

    assert result == "output.tif"
    assert captured["command"][0] == "gdalwarp"
    assert "-te" in captured["command"]
    assert "-t_srs" in captured["command"]
    assert "-tr" in captured["command"]
    assert "-dstnodata" in captured["command"]


def test_stack_rasters_requires_files(tmp_path):
    output_path = tmp_path / "out.tif"

    with pytest.raises(ValueError, match="tiff_files must contain at least one raster path"):
        pysatgeo.stack_rasters([], str(output_path), operation="sum")


def test_stack_rasters_rejects_invalid_operation(tmp_path):
    output_path = tmp_path / "out.tif"

    with pytest.raises(ValueError, match="Invalid operation"):
        pysatgeo.stack_rasters(["a.tif"], str(output_path), operation="median")


def test_assign_crs_to_vector_writes_output(tmp_path):
    input_path = tmp_path / "input.geojson"
    output_path = tmp_path / "output.geojson"

    gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    gdf.to_file(input_path, driver="GeoJSON")

    result = pysatgeo.assign_crs_to_vector(str(input_path), str(output_path), 4326)

    saved = gpd.read_file(output_path)

    assert result == str(output_path)
    assert output_path.exists()
    assert saved.crs.to_epsg() == 4326


def test_convert_geojson_to_geoparquet_creates_output(tmp_path):
    input_dir = tmp_path / "geojson"
    output_dir = tmp_path / "parquet"
    input_dir.mkdir()

    input_path = input_dir / "sample.geojson"
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    gdf.to_file(input_path, driver="GeoJSON")

    pysatgeo.convert_geojson_to_geoparquet(str(input_dir), str(output_dir))

    output_path = output_dir / "sample.parquet"
    saved = gpd.read_parquet(output_path)
    assert output_path.exists()
    assert len(saved) == 2


def test_shift_vector_to_raster_reference_writes_shifted_geometry(tmp_path):
    vector_path = tmp_path / "input.geojson"
    output_path = tmp_path / "shifted.geojson"
    raster_path = tmp_path / "reference.tif"

    gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    gdf.to_file(vector_path, driver="GeoJSON")

    _write_test_raster(raster_path, np.array([[1]], dtype=np.uint8))

    result = pysatgeo.shift_vector_to_raster_reference(
        str(vector_path), str(raster_path), str(output_path)
    )
    shifted = gpd.read_file(output_path)

    assert result == str(output_path)
    assert shifted.geometry.iloc[0].x == pytest.approx(0.0)
    assert shifted.geometry.iloc[0].y == pytest.approx(0.0)


def test_dissolve_vector_writes_single_feature(tmp_path):
    input_path = tmp_path / "input.geojson"
    output_path = tmp_path / "dissolved.geojson"

    gdf = gpd.GeoDataFrame(
        {"group": ["a", "a"]},
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        ],
        crs="EPSG:4326",
    )
    gdf.to_file(input_path, driver="GeoJSON")

    result = pysatgeo.dissolve_vector(str(input_path), str(output_path))
    dissolved = gpd.read_file(output_path)

    assert result == str(output_path)
    assert len(dissolved) == 1


def test_convert_pk_to_string_formats_values():
    assert pysatgeo.convert_pk_to_string("12+3") == "0123"
    assert pysatgeo.convert_pk_to_string("45") == "0045"


def test_generate_points_within_polygon_creates_flagged_points():
    polygon = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)])

    points = pysatgeo.generate_points_within_polygon(polygon, spacing=1, crs="EPSG:4326")

    assert not points.empty
    assert set(points["fire_ocurrence"]) == {1}
    assert all(polygon.contains(point) for point in points.geometry)


def test_generate_points_outside_polygons_respects_boundary_and_count():
    np.random.seed(0)

    fire_polygons = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(4, 4), (6, 4), (6, 6), (4, 6)])],
        crs="EPSG:3857",
    )
    existing_points = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:3857",
    )
    boundary = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
        crs="EPSG:3857",
    )

    points = pysatgeo.generate_points_outside_polygons(
        fire_polygons,
        existing_points,
        boundary,
        spacing=1,
    )

    buffered = fire_polygons.geometry.buffer(1).union_all()
    boundary_polygon = boundary.geometry.union_all()

    assert len(points) == len(existing_points)
    assert set(points["fire_ocurrence"]) == {0}
    assert all(boundary_polygon.contains(point) for point in points.geometry)
    assert all(not buffered.contains(point) for point in points.geometry)


def test_get_raster_values_samples_expected_cells(tmp_path):
    raster_path = tmp_path / "values.tif"
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    _write_test_raster(raster_path, data)

    points = gpd.GeoDataFrame(
        geometry=[Point(0.5, 1.5), Point(1.5, 0.5)],
        crs="EPSG:4326",
    )

    values = pysatgeo.get_raster_values(str(raster_path), points)
    assert values == [1.0, 4.0]


def test_distance_matrix_writes_output(tmp_path):
    input_raster = tmp_path / "input.tif"
    output_raster = tmp_path / "distance.tif"
    _write_test_raster(input_raster, np.array([[0, 1], [0, 0]], dtype=np.uint8))

    result = pysatgeo.distance_matrix(str(input_raster), str(output_raster), target_value=1)

    with rasterio.open(output_raster) as src:
        distance = src.read(1)

    assert result == str(output_raster)
    assert output_raster.exists()
    assert distance[0, 1] == pytest.approx(0.0)


def test_normalize_custom_ranking_returns_scaled_values():
    normalized = pysatgeo.normalize_custom_ranking(
        {"risk": 1, "slope": 3, "water": 5},
        max_rank=5,
    )

    assert normalized["risk"] == 1
    assert normalized["water"] == 9
    assert normalized["slope"] > normalized["risk"]


def test_normalize_custom_ranking_rejects_invalid_max_rank():
    with pytest.raises(ValueError, match="max_rank must be greater than 1"):
        pysatgeo.normalize_custom_ranking({"risk": 1}, max_rank=1)


def test_create_ahp_matrix_builds_expected_ratios():
    matrix = pysatgeo.create_ahp_matrix({"risk": 9, "water": 3})

    assert matrix.loc["risk", "risk"] == 1.0
    assert matrix.loc["risk", "water"] == pytest.approx(3.0)
    assert matrix.loc["water", "risk"] == pytest.approx(1 / 3)


def test_calculate_ahp_weights_sum_to_one_hundred():
    matrix = pysatgeo.create_ahp_matrix({"risk": 9, "water": 3, "road": 1})
    weights = pysatgeo.calculate_ahp_weights(matrix)

    assert weights.sum() == pytest.approx(100.0)
    assert weights["risk"] > weights["water"] > weights["road"]


def test_parse_qml_colors_extracts_rgba_values(tmp_path):
    qml_path = tmp_path / "style.qml"
    qml_path.write_text(
        """
<qgis>
  <pipe>
    <rasterrenderer>
      <rastershader>
        <colorrampshader>
          <item color="#ff0000" />
          <item color="#00ff00" />
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
  </pipe>
</qgis>
""".strip(),
        encoding="utf-8",
    )

    colors = pysatgeo.parse_qml_colors(str(qml_path))

    assert colors == [(1.0, 0.0, 0.0, 1), (0.0, 1.0, 0.0, 1)]


def test_extract_year_from_filename_returns_middle_token():
    assert pysatgeo.extract_year_from_filename("chirps_2024_daily.nc") == "2024"


def test_save_to_csv_writes_expected_file(tmp_path):
    save_dir = tmp_path / "csv"
    frame = pd.DataFrame({"value": [1, 2]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))

    result = pysatgeo.save_to_csv(frame, "2024", str(save_dir), "precip")

    saved = pd.read_csv(result)
    assert result.endswith("precip_2024_pixel_values.csv")
    assert len(saved) == 2
