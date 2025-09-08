"""
NetCDF-related functions for pysatgeo.
"""

import xarray as xr
import pandas as pd
import os

def extract_year_from_filename(filename):
    """Extracts the year from the NetCDF file name."""
    return filename.split('_')[1]

def process_netcdf(netcdf_file, var_name):
    """Processes a NetCDF file and returns a pivoted DataFrame with the specified variable data.

    Parameters:
        netcdf_file (str): Path to the NetCDF file.
        var_name (str): Name of the variable to extract (e.g., 'precip', 'temperature').

    Returns:
        pd.DataFrame: A pivoted DataFrame with the specified variable data.
    """

    combined = xr.open_dataset(netcdf_file)

    # Rename the 'band' dimension to 'time' and swap the dimensions
    combined = combined.rename({"band": "time"}).swap_dims({"time": "time"})

    # Get the 2D spatial grid
    x = combined['x'].values
    y = combined['y'].values

    # Get the list of dates from the time dimension
    dates = pd.to_datetime(combined['time'].values)

    all_data = []

    for i, date in enumerate(dates):
        # Get the data for the current time slice (all pixel values for this date)
        data = combined.isel(time=i)[var_name].values

        # Create a meshgrid for the x and y coordinates
        xx, yy = np.meshgrid(x, y)

        # Flatten the meshgrid and data values to create point geometries
        lat_lon_points = np.column_stack((xx.flatten(), yy.flatten()))
        values = data.flatten()

        for lon, lat, value in zip(lat_lon_points[:, 0], lat_lon_points[:, 1], values):
            all_data.append({'geometry': Point(lon, lat), var_name: value, 'Date': date})

    gdf = gpd.GeoDataFrame(all_data, geometry='geometry')

    gdf['lon'] = gdf.geometry.x
    gdf['lat'] = gdf.geometry.y

    # Pivot the GeoDataFrame by 'Date' using each (lat, lon) pair as a separate column
    pivot_df = gdf.pivot_table(index='Date', columns=['lat', 'lon'], values=var_name, aggfunc='first')

    pivot_df.columns = [f"{var_name} ({lat:.2f}, {lon:.2f})" for lat, lon in pivot_df.columns]

    return pivot_df

def process_all_netcdfs(netcdf_dir, save_dir):
    """Processes all NetCDF files in the specified directory and saves CSVs to the save directory."""
    for netcdf_file in os.listdir(netcdf_dir):
        if netcdf_file.endswith('.nc'):
            year = extract_year_from_filename(netcdf_file)
            
            netcdf_file_path = os.path.join(netcdf_dir, netcdf_file)
            
            pivot_df = process_netcdf(netcdf_file_path)
            
            save_to_csv(pivot_df, year, save_dir)
            
def save_to_csv(pivot_df, year, save_dir, base_filename):
    """Saves the pivoted DataFrame to a CSV file with a customizable base filename.

    Parameters:
        pivot_df (pd.DataFrame): The pivoted DataFrame to save.
        year (int): The year for the output filename.
        save_dir (str): Directory to save the CSV file.
        base_filename (str): Base name for the output file (e.g., 'PDIR', 'temperature').
    """
    os.makedirs(save_dir, exist_ok=True)

    # Construct the output filename using the specified base name
    csv_file = os.path.join(save_dir, f"{base_filename}_{year}_pixel_values.csv")

    # Save the DataFrame to CSV
    pivot_df.to_csv(csv_file, index=True)
    print(f"CSV file saved at: {csv_file}")