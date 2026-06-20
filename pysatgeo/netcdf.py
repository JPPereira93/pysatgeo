"""NetCDF extraction and tabular export utilities."""

import os

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point


def extract_year_from_filename(filename):
    """Extract the year token from a NetCDF file name."""
    return filename.split("_")[1]


def process_netcdf(netcdf_file, var_name):
    """Convert one NetCDF variable into a date-indexed pixel-value table."""
    with xr.open_dataset(netcdf_file) as dataset:
        combined = dataset.rename({"band": "time"}).swap_dims({"time": "time"})
        x_coords = combined["x"].values
        y_coords = combined["y"].values
        dates = pd.to_datetime(combined["time"].values)

        all_data = []
        xx, yy = np.meshgrid(x_coords, y_coords)

        for time_index, date in enumerate(dates):
            values = combined.isel(time=time_index)[var_name].values.flatten()
            coordinates = np.column_stack((xx.flatten(), yy.flatten()))

            for lon, lat, value in zip(
                coordinates[:, 0], coordinates[:, 1], values
            ):
                all_data.append(
                    {"geometry": Point(lon, lat), var_name: value, "Date": date}
                )

    gdf = gpd.GeoDataFrame(all_data, geometry="geometry")
    gdf["lon"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y

    pivot_df = gdf.pivot_table(
        index="Date",
        columns=["lat", "lon"],
        values=var_name,
        aggfunc="first",
    )
    pivot_df.columns = [
        f"{var_name} ({lat:.2f}, {lon:.2f})" for lat, lon in pivot_df.columns
    ]
    return pivot_df


def process_all_netcdfs(netcdf_dir, save_dir, var_name, base_filename=None):
    """Process all NetCDF files in a folder and export one CSV per file."""
    output_paths = []
    output_prefix = base_filename or var_name

    for netcdf_file in os.listdir(netcdf_dir):
        if netcdf_file.endswith(".nc"):
            year = extract_year_from_filename(netcdf_file)
            netcdf_file_path = os.path.join(netcdf_dir, netcdf_file)
            pivot_df = process_netcdf(netcdf_file_path, var_name)
            output_paths.append(
                save_to_csv(pivot_df, year, save_dir, output_prefix)
            )

    return output_paths


def save_to_csv(pivot_df, year, save_dir, base_filename):
    """Write a processed NetCDF table to CSV and return the output path."""
    os.makedirs(save_dir, exist_ok=True)
    csv_file = os.path.join(save_dir, f"{base_filename}_{year}_pixel_values.csv")
    pivot_df.to_csv(csv_file, index=True)
    print(f"CSV file saved at: {csv_file}")
    return csv_file
