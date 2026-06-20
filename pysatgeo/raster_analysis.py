"""Raster analysis, normalization, and clustering helpers."""

import os

from mapclassify import NaturalBreaks
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import rioxarray
from scipy.ndimage import distance_transform_edt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MinMaxScaler
import xarray as xr


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


def distance_matrix(input_raster_path, output_raster_path, target_value=1):
    """Create a distance raster to the nearest target cell value."""
    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1)
        meta = src.meta

    target_cells = raster_data == target_value
    distance = distance_transform_edt(~target_cells)
    meta.update(dtype=rasterio.float32)

    with rasterio.open(output_raster_path, "w", **meta) as dst:
        dst.write(distance.astype(rasterio.float32), 1)

    return output_raster_path


def reclassify_raster(input_raster_path):
    """Reclassify raster values into five equal-interval classes."""
    base, ext = os.path.splitext(input_raster_path)
    output_raster_path = f"{base}_ebreaks_reclassified{ext}"

    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1).astype(float)
        nodata = src.nodata

        mask = np.ones_like(raster_data, dtype=bool)
        if nodata is not None:
            mask &= raster_data != nodata
        mask &= raster_data > 0.0

        valid_data = raster_data[mask]
        min_val = valid_data.min() if valid_data.size > 0 else np.nan
        max_val = raster_data.max()
        interval = (max_val - min_val) / 5
        classification_values = [max_val - i * interval for i in range(5)]

        reclassified_raster = np.copy(raster_data)
        reclassified_raster[mask] = 6 - np.digitize(
            raster_data[mask], classification_values, right=True
        )

        if nodata is not None:
            reclassified_raster[~mask] = nodata

        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=nodata)

    with rasterio.open(output_raster_path, "w", **profile) as dst:
        dst.write(reclassified_raster.astype(rasterio.float32), 1)

    return output_raster_path


def reclassify_raster_nbreaks(input_raster_path, accept_zero_as_min=False):
    """Reclassify raster values using Jenks natural breaks."""
    base, ext = os.path.splitext(input_raster_path)
    output_raster_path = f"{base}_nbreaks_reclassified{ext}"

    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1).astype(float)
        nodata = src.nodata

        mask = np.ones_like(raster_data, dtype=bool)
        if nodata is not None:
            mask &= raster_data != nodata

        if accept_zero_as_min:
            valid_data = raster_data[mask]
        else:
            mask &= raster_data > 0.0
            valid_data = raster_data[mask]

        breaks = NaturalBreaks(valid_data, k=5)
        reclassified_raster = np.copy(raster_data)
        reclassified_raster[mask] = breaks.yb + 1
        reclassified_raster[~mask] = np.nan

        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=np.nan)

    with rasterio.open(output_raster_path, "w", **profile) as dst:
        dst.write(reclassified_raster.astype(rasterio.float32), 1)

    return output_raster_path


def set_nodata_value(input_raster_path, nodata_value):
    """Set the nodata value on all raster bands, in place."""
    gdal = _require_gdal()
    raster = gdal.Open(input_raster_path, gdal.GA_Update)
    if not raster:
        raise IOError("Could not open raster file.")

    try:
        for band_index in range(1, raster.RasterCount + 1):
            band = raster.GetRasterBand(band_index)
            data_type = band.DataType
            if nodata_value < 0 and gdal.GetDataTypeName(data_type).startswith("UInt"):
                raise ValueError(
                    f"The raster data type is {gdal.GetDataTypeName(data_type)}, "
                    "which does not support negative NoData values."
                )
            band.SetNoDataValue(nodata_value)
            band.FlushCache()
    finally:
        raster = None

    return input_raster_path


def normalize_raster(input_tiffs):
    """Normalize raster values to the range [0, 1] using per-file min-max scaling."""
    output_paths = []
    for input_tiff in input_tiffs:
        raster = rioxarray.open_rasterio(input_tiff).astype(np.float32)
        no_data_value = raster.rio.nodata
        data = raster.values
        masked_data = np.ma.masked_equal(data, no_data_value)
        reshaped_data = masked_data.compressed().reshape(-1, 1)

        scaler = MinMaxScaler()
        normalized_data = scaler.fit_transform(reshaped_data)

        normalized_full = np.full(data.shape, no_data_value, dtype=np.float32)
        normalized_full[~masked_data.mask] = normalized_data.flatten()
        raster.values = normalized_full

        base, ext = os.path.splitext(input_tiff)
        output_tiff = f"{base}_normalized{ext}"
        raster.rio.to_raster(output_tiff)
        output_paths.append(output_tiff)

    return output_paths


def normalize_raster_fixed_scale(
    input_raster_path, output_normalized_raster_path, fixed_min, fixed_max
):
    """Normalize raster values using a fixed minimum and maximum range."""
    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1).astype(float)
        nodata = src.nodata
        mask = (
            raster_data != nodata
            if nodata is not None
            else np.ones_like(raster_data, dtype=bool)
        )

        normalized_data = np.copy(raster_data)
        scale_range = fixed_max - fixed_min
        if scale_range != 0:
            normalized_data[mask] = (raster_data[mask] - fixed_min) / scale_range
        else:
            normalized_data[mask] = 0.0

        if nodata is not None:
            normalized_data[~mask] = nodata

        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=nodata)

    with rasterio.open(output_normalized_raster_path, "w", **profile) as dst:
        dst.write(normalized_data.astype(rasterio.float32), 1)

    return output_normalized_raster_path


def invert_raster_values(input_raster_path, output_raster_path):
    """Invert raster values using `-value + max_value`."""
    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1)
        max_value = np.max(raster_data)
        result = (-1 * raster_data) + max_value
        profile = src.profile

    with rasterio.open(output_raster_path, "w", **profile) as dst:
        dst.write(result, 1)

    return output_raster_path


def process_kmeans(input_raster, n_clusters=None, verbose=True):
    """Cluster raster values using KMeans and return labels plus cluster summaries."""
    with rasterio.open(input_raster) as src:
        raster_data = src.read(1)
        raster_meta = src.meta
        nodata_value = src.nodata

    raster_flat = raster_data.flatten()
    raster_valid = raster_flat[raster_flat != nodata_value]
    if np.any(np.isnan(raster_valid)) and verbose:
        print("Warning: NaN values detected in raster_valid. They will be removed.")

    if raster_valid.shape[0] == 0:
        raise ValueError("No valid data points found for clustering.")

    raster_valid = raster_valid.reshape(-1, 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(raster_valid)
    cluster_labels = kmeans.labels_

    cluster_ranges = []
    for cluster in range(n_clusters):
        cluster_values = raster_valid[cluster_labels == cluster]
        if cluster_values.size > 0:
            cluster_mean = cluster_values.mean()
            cluster_count = cluster_values.size
            cluster_ranges.append((cluster + 1, float(cluster_mean), cluster_count))

    clustered_raster = np.full_like(raster_flat, fill_value=nodata_value)
    clustered_raster[raster_flat != nodata_value] = cluster_labels + 1
    clustered_raster = clustered_raster.reshape(raster_data.shape)

    return clustered_raster, raster_meta, cluster_ranges


def relabel_clusters(cluster_ranges):
    """Relabel cluster identifiers by ascending mean value."""
    sorted_means = sorted(cluster_ranges, key=lambda item: item[1])
    return {
        old_cluster_id: new_index + 1
        for new_index, (old_cluster_id, _mean_value, _count) in enumerate(sorted_means)
    }


def process_directory(
    input_directory, output_directory, n_clusters=None, process_single_file=False
):
    """Apply KMeans clustering and relabeling to one raster or a whole directory."""
    os.makedirs(output_directory, exist_ok=True)

    if process_single_file:
        raster_paths = [input_directory] if os.path.isfile(input_directory) else []
    else:
        raster_paths = [
            os.path.join(input_directory, filename)
            for filename in os.listdir(input_directory)
            if filename.endswith(".tiff") or filename.endswith(".tif")
        ]

    if not raster_paths:
        raise ValueError("No valid raster files found to process.")

    output_paths = []
    for input_raster in raster_paths:
        clustered_raster, raster_meta, cluster_ranges = process_kmeans(
            input_raster, n_clusters
        )
        new_labels = relabel_clusters(cluster_ranges)

        relabelled_raster = np.copy(clustered_raster)
        for old_label, new_label in new_labels.items():
            relabelled_raster[clustered_raster == old_label] = new_label

        filename = os.path.basename(input_raster)
        stem, ext = os.path.splitext(filename)
        output_raster = os.path.join(output_directory, f"{stem}_relabeled{ext}")

        xr.DataArray(relabelled_raster, dims=("y", "x")).rio.write_crs(
            raster_meta["crs"], inplace=True
        ).rio.write_transform(raster_meta["transform"], inplace=True).rio.write_nodata(
            raster_meta["nodata"], inplace=True
        ).rio.to_raster(
            output_raster
        )
        output_paths.append(output_raster)

    return output_paths


def convert_raster_to_integers(input_tiff, output_tiff):
    """Round raster values and save them to a new raster."""
    raster = rioxarray.open_rasterio(input_tiff)
    nodata_value = raster.rio.nodata
    float_raster = raster.round()
    int_raster = float_raster.where(float_raster != nodata_value, other=np.nan)
    int_raster = int_raster.where(~np.isnan(int_raster), other=np.nan).astype(
        np.float32
    )
    int_raster.rio.write_nodata(nodata_value, inplace=True)
    int_raster.rio.to_raster(output_tiff)
    return output_tiff


def plot_silhouette_scores(data, k_range=None):
    """Plot silhouette scores for a range of KMeans cluster counts."""
    silhouette_scores = []
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        cluster_labels = kmeans.fit_predict(data)
        score = silhouette_score(data, cluster_labels)
        silhouette_scores.append(score)

    plt.figure()
    plt.plot(k_range, silhouette_scores, "b*-")
    plt.grid(True)
    plt.xlabel("Number of Clusters (K)")
    plt.ylabel("Silhouette Score")
    plt.title("Silhouette Score vs. Number of Clusters")
    plt.show()


def process_raster_for_silhouette(input_raster, k_range=None):
    """Prepare raster values and forward them to the silhouette plotter."""
    raster_data = rioxarray.open_rasterio(input_raster)
    nodata_value = raster_data.rio.nodata
    raster_flat = raster_data.values.flatten()
    data = raster_flat[raster_flat != nodata_value] if nodata_value is not None else raster_flat
    data = data.reshape(-1, 1)
    plot_silhouette_scores(data, k_range=k_range)


def remove_outliers(input_tiff, output_tiff, no_data_value=-9999):
    """Mask raster outliers using the IQR method and write the result."""
    data = rioxarray.open_rasterio(input_tiff)
    q1 = np.percentile(data.where(data != no_data_value, drop=True), 25)
    q3 = np.percentile(data.where(data != no_data_value, drop=True), 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    data_out = data.where((data >= lower_bound) & (data <= upper_bound), np.nan)
    data_out = data_out.fillna(no_data_value)
    data_out.rio.write_nodata(no_data_value, inplace=True)
    data_out.rio.to_raster(output_tiff)
    return {"input_tiff": input_tiff, "output_tiff": output_tiff}
