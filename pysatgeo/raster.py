"""
Raster-related functions for pysatgeo.
"""

import rasterio
import rioxarray
import numpy as np
import geopandas as gpd
from rasterio.mask import mask
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import os
from mapclassify import NaturalBreaks
import subprocess

def reproject_clip_resample_tiff(input_tiff, output_tiff=None, aoi_shapefile=None, target_srs=None, target_res_x=None, target_res_y=None, resampling_method=None, clip=False, clip_by_extent=False, no_data=None):
    """
    Reprojects, optionally clips, and resamples a TIFF file based on an AOI shapefile.

    :param input_tiff: Path to the input TIFF file
    :param output_tiff: Path for the output TIFF file
    :param aoi_shapefile: Optional path to the AOI shapefile or GeoDataFrame. Required if clip is True.
    :param target_srs: Optional target spatial reference system (ex: 'EPSG:32629')
    :param target_res_x: Optional target resolution in x (meters)
    :param target_res_y: Optional target resolution in y (meters)
    :param resampling_method: Optional resampling method (ex: 'bilinear')
    :param clip: Boolean to determine whether to clip the raster
    :param clip_by_extent: Boolean to determine whether to clip the raster by the extent of the AOI.
    :param no_data: Optional no data value to be set for the output TIFF
    """
    # Check if the output TIFF path is given, otherwise create a new one based on the input TIFF
    if not output_tiff:
        base, ext = os.path.splitext(input_tiff)
        output_tiff = f"{base}_new.tif"

    # Continue with your function implementation
    cmd_reproject = "gdalwarp"

    if target_srs:
        cmd_reproject += f" -t_srs {target_srs}"
    if target_res_x and target_res_y:
        cmd_reproject += f" -tr {target_res_x} {target_res_y}"
    if resampling_method:
        cmd_reproject += f" -r {resampling_method}"
    if clip:
        if aoi_shapefile:
            if clip_by_extent:
                # Extract the extent if it is a GeoDataFrame or load it from a shapefile
                if isinstance(aoi_shapefile, gpd.geodataframe.GeoDataFrame):
                    bounds = aoi_shapefile.total_bounds
                else:
                    aoi_gdf = gpd.read_file(aoi_shapefile)
                    bounds = aoi_gdf.total_bounds
                cmd_reproject += f' -te {bounds[0]} {bounds[1]} {bounds[2]} {bounds[3]}'
            else:
                cmd_reproject += f' -cutline \"{aoi_shapefile}\" -crop_to_cutline'
        else:
            raise ValueError("AOI shapefile must be provided if clip is True")
    if no_data is not None:
        cmd_reproject += f" -dstnodata {no_data}"
    
    cmd_reproject += f" \"{input_tiff}\" \"{output_tiff}\""
    
    os.system(cmd_reproject)
    
""" # Example usage
reproject_clip_resample_tiff(
    input_tiff="path/to/your/input_raster.tif", 
    output_tiff="path/to/your/output_raster.tif", 
    aoi_shapefile="path/to/your/aoi_shapefile.shp", 
    target_srs="EPSG:32629", 
    target_res_x=30, 
    target_res_y=30, 
    resampling_method="bilinear", 
    clip=True,
    clip_by_extent=True,
    no_data=-9999
) """

def align_rasters(rasters, source_path, output_suffix, folder_name='Aligned'):
    """
    Aligns list of rasters to have the same resolution and 
    cell size for pixel-based calculations. Saves aligned rasters in a specified folder.
    
    :param rasters: List of raster paths.
    :type rasters: List
    :param source_path: Path to the source directory of rasters.
    :type source_path: String
    :param output_suffix: The output aligned rasters files suffix with extension.
    :type output_suffix: String
    :param folder_name: Name of the folder to save aligned rasters, defaults to 'Aligned'.
    :type folder_name: String
    :return: True if the process runs and False if the data couldn't be read. 
    :rtype: Boolean
    """
    # Calculate the parent directory of source_path
    parent_dir = os.path.dirname(source_path.rstrip(os.sep))
    
    # Construct the path to the specified folder
    aligned_dir = os.path.join(parent_dir, folder_name)
    
    # Check if the folder exists, if not, create it
    if not os.path.exists(aligned_dir):
        os.makedirs(aligned_dir)
    
    command = ["gdalbuildvrt", "-te"]
    hDataset = gdal.Open(rasters[0], gdal.GA_ReadOnly)
    if hDataset is None:
        return False
    
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null=True)
    if adfGeoTransform is None:
        return False
    
    # Process each raster in the list
    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        vrt_file = os.path.join(aligned_dir, base_filename.replace('.tif', '.vrt'))

        # Calculate the corners of the bounding box for each raster
        dfGeoXUL = adfGeoTransform[0]  # Upper left X
        dfGeoYUL = adfGeoTransform[3]  # Upper left Y
        dfGeoXLR = adfGeoTransform[0] + adfGeoTransform[1] * hDataset.RasterXSize + adfGeoTransform[2] * hDataset.RasterYSize  # Lower right X
        dfGeoYLR = adfGeoTransform[3] + adfGeoTransform[4] * hDataset.RasterXSize + adfGeoTransform[5] * hDataset.RasterYSize  # Lower right Y
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))
        
        # Build and translate VRT to final raster with specified resolution
        subprocess.call(command + [str(dfGeoXUL), str(dfGeoYLR), str(dfGeoXLR),
                                   str(dfGeoYUL), "-q", "-tr", xres, yres,
                                   vrt_file, tif_file])
        
        output_file = os.path.join(aligned_dir, base_filename.replace('.tif', output_suffix))
        cmd = f'gdal_translate -q "{vrt_file}" "{output_file}"'
        subprocess.call(cmd, shell=True)
        os.remove(vrt_file)  # Clean up temporary VRT file
    
    return True

""" # Example usage
rasters = ['path/to/raster1.tif', 'path/to/raster2.tif']
output_suffix = '_aligned.tif'
align_rasters(rasters, '/path/to/source', output_suffix, 'Aligned_8_5') """
    
def align_rasters_in_place(folder_path, output_suffix):
    """
    Aligns all .tiff files in the specified folder to have the same resolution and 
    cell size for pixel-based calculations. Saves aligned rasters in the same folder.
    
    :param folder_path: Path to the folder containing .tiff files.
    :type folder_path: String
    :param output_suffix: The output aligned rasters files suffix with extension.
    :type output_suffix: String
    :return: True if the process runs and False if the data couldn't be read. 
    :rtype: Boolean
    """
    # List all .tiff files in the folder
    rasters = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.tiff') or f.endswith('.tif')]
    
    if not rasters:
        print("No .tiff files found in the specified folder.")
        return False
    
    command = ["gdalbuildvrt", "-te"]
    hDataset = gdal.Open(rasters[0], gdal.GA_ReadOnly)
    if hDataset is None:
        return False
    
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null=True)
    if adfGeoTransform is None:
        return False
    
    # Process each raster in the list
    for tif_file in rasters:
        base_filename = os.path.basename(tif_file)
        vrt_file = os.path.join(folder_path, base_filename.replace('.tif', '.vrt'))

        # Calculate the corners of the bounding box for each raster
        dfGeoXUL = adfGeoTransform[0]  # Upper left X
        dfGeoYUL = adfGeoTransform[3]  # Upper left Y
        dfGeoXLR = adfGeoTransform[0] + adfGeoTransform[1] * hDataset.RasterXSize + adfGeoTransform[2] * hDataset.RasterYSize  # Lower right X
        dfGeoYLR = adfGeoTransform[3] + adfGeoTransform[4] * hDataset.RasterXSize + adfGeoTransform[5] * hDataset.RasterYSize  # Lower right Y
        xres = str(abs(adfGeoTransform[1]))
        yres = str(abs(adfGeoTransform[5]))
        
        # Build and translate VRT to final raster with specified resolution
        subprocess.call(command + [str(dfGeoXUL), str(dfGeoYLR), str(dfGeoXLR),
                                   str(dfGeoYUL), "-q", "-tr", xres, yres,
                                   vrt_file, tif_file])
        
        output_file = os.path.join(folder_path, base_filename.replace('.tif', output_suffix))
        cmd = f'gdal_translate -q "{vrt_file}" "{output_file}"'
        subprocess.call(cmd, shell=True)
        os.remove(vrt_file)  # Clean up temporary VRT file
    
    return True

# Example usage:
# align_rasters_in_place("E:\\Spotlite_JPereira\\Ascendi\\Concessao_Beira_Litoral\\2030\\Aligned", "_aligned.tif")    



def stack_rasters(tiff_files, output_tiff, aoi_shapefile=None, chunk_size=None, operation=None):
    """
    Clips, stacks a list of raster files based on an AOI shapefile, calculates the sum, median, or mean of the stack,
    and saves the resulting raster to a file. Processes data in chunks to reduce memory usage.

    :param tiff_files: List of paths to the input TIFF files
    :param aoi_shapefile: Path to the AOI shapefile (optional, default is None)
    :param output_tiff: Path for the output raster file
    :param operation: Operation to perform on the stack ('mean', 'sum')
    :param chunk_size: Size of chunks for processing (e.g., (500, 500))
    :return: None
    """
    if aoi_shapefile:
        aoi = gpd.read_file(aoi_shapefile)
        polygon_geometry = [aoi.geometry.iloc[0]]
    else:
        polygon_geometry = None

    raster_arrays = []
    no_data_values = []
    scale_factors = []  # List to hold scaling factors

    for tiff in tiff_files:
        ds = gdal.Open(tiff)
        
        # Get the scale
        scale = ds.GetRasterBand(1).GetScale()
        if scale is None:
            scale = 1.0  # Default scale if none is found
        scale_factors.append(scale)

        # Open the raster and convert to float32
        raster = rioxarray.open_rasterio(tiff, chunks=chunk_size).astype('float32')
        print(f"Starting the processing... {tiff}")
        no_data = raster.rio.nodata
        no_data_values.append(no_data)

        # Check if 'time' dimension is present and remove it
        if 'time' in raster.dims:
            raster = raster.squeeze(dim='time', drop=True)

        try:
            if polygon_geometry:
                clipped_raster = raster.rio.clip(polygon_geometry, aoi.crs, drop=True, invert=False)
                # Replace NoData values with np.nan
                clipped_raster = clipped_raster.where(clipped_raster != no_data, other=np.nan)
                raster_arrays.append(clipped_raster)
            else:
                raster_arrays.append(raster.where(raster != no_data, other=np.nan))
        finally:
            # Ensure the file is closed after processing
            raster.close()
            ds = None  

    # Stack the rasters across bands
    stacked_rasters = xr.concat(raster_arrays, dim='band')

    if operation == 'mean':
        # Exclude NoData pixels from the mean calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).mean(dim='band')

        # Adjust the mean raster based on the scale factor
        average_scale = np.mean(scale_factors)
        if average_scale != 1.0:
            result_raster = result_raster * average_scale

    elif operation == 'sum':
        # Exclude NoData pixels from the sum calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).sum(dim='band')

        # Adjust the sum raster based on the scale factor
        total_scale = np.mean(scale_factors)  # You can modify this as needed
        if total_scale != 1.0:
            result_raster = result_raster * total_scale

    else:
        raise ValueError("Invalid operation. Choose 'mean' or 'sum'")

    # Set the CRS of the result raster to match the vector CRS if AOI is provided
    if aoi_shapefile:
        result_raster.rio.write_crs(aoi.crs, inplace=True)

    # Set the NoData value for the result raster to the NoData of the first raster
    result_no_data_value = no_data_values[0]
    result_raster.rio.write_nodata(result_no_data_value, inplace=True)

    # Replace remaining NaN values with NoData in the result
    result_raster = result_raster.where(~np.isnan(result_raster), other=result_no_data_value)
    result_raster.rio.to_raster(output_tiff)
    print(f"Stacked {operation} Raster saved at {output_tiff}")

    return output_tiff

""" # Example usage
tiff_files = [...]  # List of paths to input TIFF files # 

tiff_files = glob.glob(os.path.join(raster_dir, '*.tif'))

output_tiff = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\2023\Rainfall\sum_raster.tif"
aoi_shapefile = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\AOI\CN_A7_A11_A42_expanded_bounds_wgs84.geojson"
chunk_size = (500, 500)  # Adjust based on your system's memory capacity

stack_rasters(tiff_files, aoi_shapefile, output_tiff, chunk_size, operation='sum') """

def merge_tiffs(input_dir, output_tif):
    """
    Merges all TIFF files in a specified directory into a single TIFF file

    :param input_dir: Path to the directory containing the TIFF files.
    :param output_tif: Path for the output merged TIFF file.
    """
    tiff_files = glob.glob(os.path.join(input_dir, '*.tif'))

    if not tiff_files:
        print("No TIFF files found in the directory.")
        return
    
    print(f"Found {len(tiff_files)} TIFF files to merge.")
    
    vrt = gdal.BuildVRT("temp.vrt", tiff_files) 
    gdal.Translate(output_tif, vrt) 
    vrt = None

    print(f"Merge successful. Output saved to {output_tif}")

def clip_rasters_by_extent(input_folder, output_folder, mask_layer_path):
    """
    Clips all rasters in the input folder to the bounding box (extent) of the mask layer
    and saves the output with '_clipped' appended to the filenames.
    
    Args:
        input_folder (str): Path to the folder containing input rasters.
        output_folder (str): Path to the folder to save clipped rasters.
        mask_layer_path (str): Path to the mask layer.
    
    Returns:
        None
    """
    os.makedirs(output_folder, exist_ok=True)
    
    mask_gdf = gpd.read_file(mask_layer_path)
    mask_bounds = mask_gdf.total_bounds
    
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".tif"):
            input_raster_path = os.path.join(input_folder, file_name)
            
            base_name, ext = os.path.splitext(file_name)
            output_raster_path = os.path.join(output_folder, f"{base_name}_clipped{ext}")
            
            raster = rioxarray.open_rasterio(input_raster_path, masked=True)
            
            clipped_raster = raster.rio.clip_box(*mask_bounds)
            
            clipped_raster.rio.to_raster(output_raster_path)
            print(f"Saved clipped raster to: {output_raster_path}")


def clip_raster_with_vector(raster_file, geojson_directory, output_directory):
    """
    Clips a raster with multiple GeoJSON mask layers and saves the output as new TIFF files.

    :param raster_file: Path to the input raster file to be clipped.
    :param geojson_directory: Directory containing the GeoJSON mask files.
    :param output_directory: Directory to save the clipped raster files.
    """
    raster = rioxarray.open_rasterio(raster_file, masked=True)

    for file_name in os.listdir(geojson_directory):
        if file_name.endswith(".geojson"):
            geojson_path = os.path.join(geojson_directory, file_name)
            
            geojson = gpd.read_file(geojson_path)

            geojson = geojson.to_crs(raster.rio.crs)

            clipped_raster = raster.rio.clip(geojson.geometry, geojson.crs, drop=True)

            output_file = os.path.join(output_directory, file_name.replace(".geojson", "_clipped.tif"))

            clipped_raster.rio.to_raster(output_file, driver="GTiff")
            print(f"Clipped raster saved to {output_file}")

def remove_outliers(input_tiff, output_tiff, no_data_value=-9999):

    data = rioxarray.open_rasterio(input_tiff)
    
    # Calculate IQR for outlier detection and ignoring NoData values
    Q1 = np.percentile(data.where(data != no_data_value, drop=True), 25)
    Q3 = np.percentile(data.where(data != no_data_value, drop=True), 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    data_out = data.where((data >= lower_bound) & (data <= upper_bound), np.nan)

    data_out = data_out.fillna(no_data_value)
    
    data_out.rio.write_nodata(no_data_value, inplace=True)
    data_out.rio.to_raster(output_tiff)

    print(f"Outliers removed and output saved as {output_tiff}")

    return {"input_tiff": input_tiff, "output_tiff": output_tiff}

def fill_no_data(input_tiff, output_tiff, max_distance=5, smoothing_iterations=0):
    """
    Apply gdal_fillnodata.py to a TIFF file.
    :param input_tiff: Path to the input TIFF file.
    :param output_tiff: Path to the output TIFF file.
    :param max_distance: Maximum search distance (in pixels) for interpolation.
    :param smoothing_iterations: Number of smoothing iterations to apply.
    """
    # Find the directory containing gdal_fillnodata.py
    gdal_fillnodata_dir = None
    for path_dir in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path_dir, 'gdal_fillnodata.py')):
            gdal_fillnodata_dir = path_dir
            break

    if not gdal_fillnodata_dir:
        print("gdal_fillnodata.py not found in PATH.")
        return

    gdal_fillnodata_script = os.path.join(gdal_fillnodata_dir, 'gdal_fillnodata.py')

    command = [sys.executable, gdal_fillnodata_script, input_tiff, output_tiff]

    if max_distance is not None:
        command.extend(['-md', str(max_distance)])
    if smoothing_iterations is not None:
        command.extend(['-si', str(smoothing_iterations)])

    command.extend(['-of', 'GTiff'])

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(f"FillNoData applied successfully. Output saved to {output_tiff}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error during fillnodata:", e.stderr)

    """    Example Usage  
input_tiff = r"E:\Spotlite_JPereira\Ascendi\Concessao_Pinhal_Interior\Slope_Angle\PI_elevation_1m.tif"
output_tiff = r"E:\Spotlite_JPereira\Ascendi\Concessao_Pinhal_Interior\Slope_Angle\PI_elevation_1m_filled_teste.tif"
fill_no_data(input_tiff, output_tiff)  """

def process_raster_for_silhouette(input_raster, k_range=None):
    
    """Processes a raster file, flattens the data, and applies the silhouette method"""
    
    raster_data = rioxarray.open_rasterio(input_raster)
    nodata_value = raster_data.rio.nodata
    # In rioxarray, use .values.flatten() instead of only .flatten to transform 2D to 1D array
    raster_flat = raster_data.values.flatten()

    if nodata_value is not None:
        data = raster_flat[raster_flat != nodata_value]
    else:
        data = raster_flat

    data = data.reshape(-1, 1)
    
    plot_silhouette_scores(data, k_range=k_range)


def plot_silhouette_scores(data, k_range=None):
   
    """Plots the silhouette scores to help find the optimal number of clusters"""
    
    silhouette_scores = []
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        cluster_labels = kmeans.fit_predict(data)
        
        score = silhouette_score(data, cluster_labels)
        silhouette_scores.append(score)
        # Round scores to three decimal cases
        print(f"Silhouette score for {k} clusters: {score:.3f}")

    plt.figure()
    plt.plot(k_range, silhouette_scores, 'b*-')
    plt.grid(True)
    plt.xlabel('Number of Clusters (K)')
    plt.ylabel('Silhouette Score')
    plt.title('Silhouette Score vs. Number of Clusters')
    plt.show()


def remove_outliers(input_tiff, output_tiff, no_data_value=-9999):

    data = rioxarray.open_rasterio(input_tiff)
    
    # Calculate IQR for outlier detection and ignoring NoData values
    Q1 = np.percentile(data.where(data != no_data_value, drop=True), 25)
    Q3 = np.percentile(data.where(data != no_data_value, drop=True), 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    data_out = data.where((data >= lower_bound) & (data <= upper_bound), np.nan)

    data_out = data_out.fillna(no_data_value)
    
    data_out.rio.write_nodata(no_data_value, inplace=True)
    data_out.rio.to_raster(output_tiff)

    print(f"Outliers removed and output saved as {output_tiff}")

    return {"input_tiff": input_tiff, "output_tiff": output_tiff}

def process_kmeans(input_raster, n_clusters=None):
    
    """Processes a single raster file and applies K-means clustering.
    Use plot_silhouette_scores and process_raster_for_silhouette to define n_clusters
    """
    
    with rasterio.open(input_raster) as src:
        raster_data = src.read(1)  
        raster_meta = src.meta  
        nodata_value = src.nodata

    # Prepare the data (flatten the 2D raster into a 1D array)
    raster_flat = raster_data.flatten()
    raster_valid = raster_flat[raster_flat != nodata_value]  # Remove NoData values

    if np.any(np.isnan(raster_valid)):
        print("Warning: NaN values detected in raster_valid. They will be removed.")
    
    # Apply K-means clustering
    raster_valid = raster_valid.reshape(-1, 1)  # Reshape to 2D (required by KMeans)

    # Only fit KMeans if there are valid data points
    if raster_valid.shape[0] == 0:
        raise ValueError("No valid data points found for clustering.")

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(raster_valid)

    # Get the cluster labels
    cluster_labels = kmeans.labels_

    # Prepare to extract cluster value ranges
    cluster_ranges = []
    
    for cluster in range(n_clusters):
        # Get the values for this cluster
        cluster_values = raster_valid[cluster_labels == cluster]
        if cluster_values.size > 0:
            cluster_min = cluster_values.min()
            cluster_max = cluster_values.max()
            cluster_count = cluster_values.size
            cluster_ranges.append((cluster + 1, cluster_min, cluster_max, cluster_count))

    print("Cluster value ranges:")
    for old_cluster, min_val, max_val, count in cluster_ranges:
        print(f"Cluster {old_cluster}: Min = {min_val}, Max = {max_val}, Count = {count}")

    # Reassign cluster labels to the original raster shape
    clustered_raster = np.full_like(raster_flat, fill_value=nodata_value)
    clustered_raster[raster_flat != nodata_value] = cluster_labels + 1
    clustered_raster = clustered_raster.reshape(raster_data.shape)

    return clustered_raster, raster_meta, cluster_ranges 

def convert_hgt_to_tiff(hgt_file, tiff_file):

    dataset = gdal.Open(hgt_file)

    # Check if the dataset was successfully opened
    if not dataset:
        print(f"Failed to open file {hgt_file}")
        return

    # Convert to TIFF
    driver = gdal.GetDriverByName('GTiff')
    driver.CreateCopy(tiff_file, dataset)

    # Close the dataset
    dataset = None

    print(f"File converted and saved as {tiff_file}")
    

def calculate_slope(input_dem, output_slope):
    """
    Calculates Slope based on a Digital Elevation Model

    :param input_dem: Path to the input DEM Raster file.
    :param output_slope: Path for the output Slope Raster file.
    :output_slope is represented in degrees (º)
    """
    
    cmd = f"gdaldem slope \"{input_dem}\" \"{output_slope}\" -compute_edges"
    os.system(cmd)

    return {"input_dem": input_dem, "output_slope": output_slope}

# Example usage
""" calculate_slope(
    input_dem ="path/to/input.tif",
    output_slope ="path/to/output.tif"
) """


def calculate_aspect(input_dem, output_aspect):
    """
    Calculates Aspect based on a Digital Elevation Model

    :param input_dem: Path to the input DEM Raster file
    :param output_aspect: Path for the output Aspect Raster file
    """
    
    cmd = f"gdaldem aspect \"{input_dem}\" \"{output_aspect}\" -compute_edges"
    os.system(cmd)

    return {"output_aspect": output_aspect}

# Example usage
""" calculate_aspect(
    input_dem ="path/to/input.tif",
    output_aspect ="path/to/output.tif"
) """

def stack_rasters(tiff_files, output_tiff, aoi_shapefile=None, chunk_size=None, operation=None):
    """
    Clips, stacks a list of raster files based on an AOI shapefile, calculates the sum, median, or mean of the stack,
    and saves the resulting raster to a file. Processes data in chunks to reduce memory usage.

    :param tiff_files: List of paths to the input TIFF files
    :param aoi_shapefile: Path to the AOI shapefile (optional, default is None)
    :param output_tiff: Path for the output raster file
    :param operation: Operation to perform on the stack ('mean', 'sum')
    :param chunk_size: Size of chunks for processing (e.g., (500, 500))
    :return: None
    """
    if aoi_shapefile:
        aoi = gpd.read_file(aoi_shapefile)
        polygon_geometry = [aoi.geometry.iloc[0]]
    else:
        polygon_geometry = None

    raster_arrays = []
    no_data_values = []
    scale_factors = []  # List to hold scaling factors

    for tiff in tiff_files:
        ds = gdal.Open(tiff)
        
        # Get the scale
        scale = ds.GetRasterBand(1).GetScale()
        if scale is None:
            scale = 1.0  # Default scale if none is found
        scale_factors.append(scale)

        # Open the raster and convert to float32
        raster = rioxarray.open_rasterio(tiff, chunks=chunk_size).astype('float32')
        print(f"Starting the processing... {tiff}")
        no_data = raster.rio.nodata
        no_data_values.append(no_data)

        # Check if 'time' dimension is present and remove it
        if 'time' in raster.dims:
            raster = raster.squeeze(dim='time', drop=True)

        try:
            if polygon_geometry:
                clipped_raster = raster.rio.clip(polygon_geometry, aoi.crs, drop=True, invert=False)
                # Replace NoData values with np.nan
                clipped_raster = clipped_raster.where(clipped_raster != no_data, other=np.nan)
                raster_arrays.append(clipped_raster)
            else:
                raster_arrays.append(raster.where(raster != no_data, other=np.nan))
        finally:
            # Ensure the file is closed after processing
            raster.close()
            ds = None  

    # Stack the rasters across bands
    stacked_rasters = xr.concat(raster_arrays, dim='band')

    if operation == 'mean':
        # Exclude NoData pixels from the mean calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).mean(dim='band')

        # Adjust the mean raster based on the scale factor
        average_scale = np.mean(scale_factors)
        if average_scale != 1.0:
            result_raster = result_raster * average_scale

    elif operation == 'sum':
        # Exclude NoData pixels from the sum calculation
        result_raster = stacked_rasters.where(~np.isnan(stacked_rasters)).sum(dim='band')

        # Adjust the sum raster based on the scale factor
        total_scale = np.mean(scale_factors)  # You can modify this as needed
        if total_scale != 1.0:
            result_raster = result_raster * total_scale

    else:
        raise ValueError("Invalid operation. Choose 'mean' or 'sum'")

    # Set the CRS of the result raster to match the vector CRS if AOI is provided
    if aoi_shapefile:
        result_raster.rio.write_crs(aoi.crs, inplace=True)

    # Set the NoData value for the result raster to the NoData of the first raster
    result_no_data_value = no_data_values[0]
    result_raster.rio.write_nodata(result_no_data_value, inplace=True)

    # Replace remaining NaN values with NoData in the result
    result_raster = result_raster.where(~np.isnan(result_raster), other=result_no_data_value)
    result_raster.rio.to_raster(output_tiff)
    print(f"Stacked {operation} Raster saved at {output_tiff}")

    return output_tiff

""" # Example usage
tiff_files = [...]  # List of paths to input TIFF files # 

tiff_files = glob.glob(os.path.join(raster_dir, '*.tif'))

output_tiff = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\2023\Rainfall\sum_raster.tif"
aoi_shapefile = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\AOI\CN_A7_A11_A42_expanded_bounds_wgs84.geojson"
chunk_size = (500, 500)  # Adjust based on your system's memory capacity

stack_rasters(tiff_files, aoi_shapefile, output_tiff, chunk_size, operation='sum') """

def ssm_nan_fix(raster_dir):
    """
    Fixes SSM data by replacing values above 200 with 255, then divide by 2 (scale factor of 0.5)
    except for the values that were set as 255.

    :param raster_dir: Path of the main directory where files of each subdirectory are already unzipped.
    """

    for filename in os.listdir(raster_dir):
        if filename.endswith('.tiff'):
            tiff_path = os.path.join(raster_dir, filename)
            
            # Open the TIFF file
            dataset = gdal.Open(tiff_path, gdal.GA_Update)
            
            if dataset is not None:
                # Read the raster data as a numpy array
                raster_array = dataset.ReadAsArray()
                
                # Set values above 200 as 255
                raster_array[raster_array > 200] = 255
                
                # Convert the array to float
                raster_array = raster_array.astype(float)
                
                # Divide values that are not equal to 255 by 2
                raster_array[raster_array != 255] /= 2
                
                # Write the modified array back to the TIFF file
                dataset.GetRasterBand(1).WriteArray(raster_array)
                
                # Close the dataset
                dataset = None
            else:
                print(f"Failed to open {tiff_path}")

    print("Processing complete.")
    
    
    """     Example Usage  
    raster_dir = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\2023\SSM\SSM_1km_2023"
 
    ssm_nan_fix(raster_dir)  """  
    

def assign_crs(input_tiffs, crs):
    """
    Assigns a specified CRS to a single TIFF file or a list of TIFF files, saves them with a new filename that includes the CRS suffix, and then replaces the original files.

    :param input_tiffs: A single path to a TIFF file or a list of paths to TIFF files.
    :param crs: CRS to assign (e.g., 4326 for 'EPSG:4326').
    """
    # Ensure input_tiffs is a list even if a single file path is provided
    if not isinstance(input_tiffs, list):
        input_tiffs = [input_tiffs]
    
    for tiff in input_tiffs:
        with rasterio.open(tiff) as src:
            profile = src.profile
            profile.update(crs=CRS.from_epsg(crs))

            # Read data from the source TIFF
            data = src.read(1)  # Assuming it's a single band raster

            # Construct new filename with CRS suffix
            output_file = os.path.splitext(tiff)[0] + '_epsg' + str(crs) + '.tif'

            # Write out the new TIFF with the updated CRS
            with rasterio.open(output_file, 'w', **profile) as dst:
                dst.write(data, 1)

        # Replace the original file with the new file
        os.remove(tiff)
        os.rename(output_file, tiff)

""" # Example Usage for a single file
assign_crs('path_to_your_single_tiff_file.tif', 4326)

# Example Usage for multiple files
assign_crs(['path_to_your_first_tiff_file.tif', 'path_to_your_second_tiff_file.tif'], 4326)
 """

def clip_raster_all_pixels(raster_path, vector_path, output_path, all_touched=True):
    
    """
    Clips a raster file with a vector but including all the pixels that have at least one intersection with the raster.
    
    :param raster_path: Path to the input raster file.
    :param vector_path: Path to the vector mask layer.
    :output_path: Path to the output clipped file.
    :all_touched = True: Parameter to set the clipping to the maximum extent.
    """
    
    # Read the vector data
    vector_data = gpd.read_file(vector_path)

    # Read the raster data
    with rasterio.open(raster_path) as src:
        # Clip the raster with the vector data
        out_image, out_transform = mask(src, vector_data.geometry, crop=True, all_touched=all_touched)
        
        # Copy the metadata
        out_meta = src.meta.copy()

    # Update the metadata to have the new shape
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    # Write the clipped raster to a new file
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)
    

        
""" # Example usage
raster_path = 'path_to_your_raster.tif'
vector_path = 'path_to_your_vector.shp'
output_path = 'path_to_output_raster.tif'

clip_raster_all_pixels(raster_path, vector_path, output_path) """

def split_raster_bands(file_path, directory_path):
    """
    Splits the bands of a multi-band raster file into individual single-band raster files.

    :param file_path: Path to the input multi-band raster file.
    :param directory_path: Directory where the output single-band raster files will be saved.
    """
    
    # Set the "no data" value to 0 in the main input raster
    with rasterio.open(file_path, 'r+') as src:
        src.nodata = 0

        # Iterate through each band and export as single-band TIFF
        for band_idx in range(1, src.count + 1):
            with rasterio.open(file_path, 'r') as src_band:
                # Read the band data for the current band
                band_data = src_band.read(band_idx)

                # Create the output TIFF file name (e.g., file_B1.tif, file_B2.tif, etc.)
                output_tiff_name = f"{os.path.basename(file_path).split('.')[0]}_B{band_idx}.tif"
                output_tiff_path = os.path.join(directory_path, output_tiff_name)

                # Create a new raster dataset for the current band
                profile = src_band.profile
                profile.update(
                    count=1,  # Set the count to 1 to create a single-band TIFF
                    dtype=rasterio.float64  # Adjust the data type as needed
                )

                with rasterio.open(output_tiff_path, 'w', **profile) as dst:
                    dst.write(band_data, 1)

                # Print a message indicating the export is complete for each band
                print(f"Exported {output_tiff_name}")

    # Print a final message
    print("All bands exported.")
    
    
    """ # Example usage
file_path = 'E:\\Spotlite_JPereira\\E-REDES\\Bruno\\spot_cutted.tif'
directory_path = r"E:\Spotlite_JPereira\E-REDES\Bruno"

split_raster_bands(file_path, directory_path) """

def subset_raster_into_parts(input_raster, num_parts):
    """
    Divide a raster file into X equal parts.
    :param input_raster: Path to the input raster file.
    :param num_parts: Number of parts to divide the raster into.
    """
    # Open the input raster
    src_ds = gdal.Open(input_raster)
    if src_ds is None:
        print(f"Failed to open raster file: {input_raster}")
        return

    # Get raster dimensions
    width = src_ds.RasterXSize
    height = src_ds.RasterYSize

    # Calculate the size of each part
    part_height = height // num_parts

    output_files = []
    
    for i in range(num_parts):
        # Calculate the coordinates for the subset
        ulx = 0               # Upper left x
        uly = i * part_height # Upper left y
        lrx = width           # Lower right x
        lry = (i + 1) * part_height if i < num_parts - 1 else height # Lower right y

        # Create output filename
        output_file = f"{os.path.splitext(input_raster)[0]}_part_{i + 1}.tif"
        output_files.append(output_file)

        # Subset the raster using gdal.Translate
        gdal.Translate(output_file, src_ds, srcWin=[ulx, uly, lrx - ulx, lry - uly], format='GTiff')
        print(f"Created subset: {output_file}")

    # Close the dataset
    src_ds = None

    return output_files

# Example Usage

"""
subset_raster_into_parts(
    input_raster="path/to/input1.tif",
    num_parts=8
)
"""

def polygonize_raster(input_tiff, output_vector=None, layer_name='layer', output_format='Parquet'):
    """
    Apply gdal_polygonize.py to a TIFF file and automatically set the output vector file extension.
    
    :param input_tiff: Path to the input TIFF file.
    :param output_vector: Path to the output vector file (automatically generated if not provided).
    :param layer_name: Name of the layer to create in the output file.
    :param output_format: Format of the output file (e.g., 'GPKG', 'Parquet', 'GeoJSON').
    """
    
    # Determine file extension based on the format
    format_extensions = {
        'GPKG': '.gpkg',
        'GeoJSON': '.geojson',
        'Parquet': '.parquet',
        'Shapefile': '.shp'
    }

    # Automatically generate output vector file name if not provided
    if output_vector is None:
        base_name, _ = os.path.splitext(input_tiff)
        output_vector = base_name + format_extensions.get(output_format, '.gpkg')  # Default to GPKG if format is unknown

    # Find the path to the gdal_polygonize.py script
    gdal_polygonize_dir = None
    for path_dir in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path_dir, 'gdal_polygonize.py')):
            gdal_polygonize_dir = path_dir
            break

    if not gdal_polygonize_dir:
        print("gdal_polygonize.py not found in PATH.")
        return

    gdal_polygonize_script = os.path.join(gdal_polygonize_dir, 'gdal_polygonize.py')

    # Construct the command to run gdal_polygonize.py
    command = [sys.executable, gdal_polygonize_script, input_tiff, '-f', output_format, output_vector, layer_name]

    # Run the command and handle output
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(f"Polygonization applied successfully. Output saved to {output_vector}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error during polygonization:", e.stderr)

# Example Usage

"""
polygonize_raster(
    input_tiff="path/to/input1.tif",
    output_vector= "path/to/input1.gpkg" , go to ffsm_first_run_data_prep.ipynb if list needed
    layer_name = string
)
"""

def distance_matrix(input_raster_path, output_raster_path, target_value=1):
    """
    Create a distance matrix from a raster by calculating the distance from each cell to the nearest target cell.

    :param input_raster_path: Path to the input GeoTIFF raster file.
    :param output_raster_path: Path for the output distance raster file.
    :param target_value: The target cell value for which to calculate distances (default is 1).
    """
    
    with rasterio.open(input_raster_path) as src:
        raster_data = src.read(1)
        meta = src.meta

        # Define your target cells
        target_cells = (raster_data == target_value)

        # Calculate the distance from each cell to the nearest target cell
        distance = distance_transform_edt(~target_cells)

        # Update metadata for the output raster
        meta.update(dtype=rasterio.float32)

        with rasterio.open(output_raster_path, 'w', **meta) as dst:
            dst.write(distance, 1)

"""     # Example usage
    create_distance_matrix(
    input_raster_path = "/path/to/input.tif", 
    output_raster_path = "/path/to/output.tif", 
    target_value = 1
) """

def reclassify_raster(input_raster_path):
    base, ext = os.path.splitext(input_raster_path)
    output_raster_path = f"{base}_ebreaks_reclassified{ext}"
    
    with rasterio.open(input_raster_path) as src:
        # Read the first band
        raster_data = src.read(1).astype(float)  # Cast raster data to float

        # Identify the 'no data' value from the source
        nodata = src.nodata

        # Exclude 'no data' value and zeros to find the actual minimum value
        mask = np.ones_like(raster_data, dtype=bool)
        if nodata is not None:
            mask &= (raster_data != nodata)
        mask &= (raster_data > 0.0)
        
        valid_data = raster_data[mask]
        min_val = valid_data.min() if valid_data.size > 0 else np.nan

        # Find maximum values
        max_val = raster_data.max()

        # Calculate interval
        interval = (max_val - min_val) / 5

        # Define the classification ranges in reverse order
        classification_values = [max_val - i * interval for i in range(5)]

        # Reclassify the raster
        reclassified_raster = np.copy(raster_data)
        reclassified_raster[mask] = 6 - np.digitize(raster_data[mask], classification_values, right=True)

        # Retain the original 'no data' value
        if nodata is not None:
            reclassified_raster[~mask] = nodata

        # Adjust the profile for a single band and write the output
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=nodata)

        with rasterio.open(output_raster_path, 'w', **profile) as dst:
            dst.write(reclassified_raster.astype(rasterio.float32), 1)

    print(f"Reclassified raster written to: {output_raster_path}")


"""     # Example usage
    reclassify_raster(
    input_raster_path = "/path/to/input.tif"
) """

def reclassify_raster_nbreaks(input_raster_path, accept_zero_as_min=False):
    base, ext = os.path.splitext(input_raster_path)
    output_raster_path = f"{base}_nbreaks_reclassified{ext}"
    
    with rasterio.open(input_raster_path) as src:
        # Read the first band
        raster_data = src.read(1).astype(float)  # Cast raster data to float

        # Identify the 'no data' value from the source
        nodata = src.nodata

        # Exclude 'no data' value to find the actual minimum value
        mask = np.ones_like(raster_data, dtype=bool)
        if nodata is not None:
            mask &= (raster_data != nodata)
        
        # Optionally include 0.0 in valid data
        if accept_zero_as_min:
            valid_data = raster_data[mask]  # Include all non-nodata values
        else:
            mask &= (raster_data > 0.0)
            valid_data = raster_data[mask]  # Exclude 0.0

        min_val = valid_data.min() if valid_data.size > 0 else np.nan

        # Find maximum values
        max_val = raster_data.max()

        # Calculate the number of classes (adjust this as needed)
        num_classes = 5

        # Use Jenks Natural Breaks classification
        breaks = NaturalBreaks(valid_data, k=num_classes)

        # Reclassify the raster based on breaks
        reclassified_raster = np.copy(raster_data)
        reclassified_raster[mask] = breaks.yb + 1  # Add 1 to make classes start from 1

        # Set 'no data' and zero areas to NaN
        reclassified_raster[~mask] = np.nan

        # Adjust the profile for a single band and write the output
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=np.nan)

        with rasterio.open(output_raster_path, 'w', **profile) as dst:
            dst.write(reclassified_raster.astype(rasterio.float32), 1)

    print(f"Natural Breaks reclassified raster written to: {output_raster_path}")

"""     # Example usage
    reclassify_raster_nbreaks(
    input_raster_path = "/path/to/input.tif"
) """


def set_nodata_value(input_raster_path, nodata_value):
    """
    Set the NoData value of a raster and overwrite the input file.

    Parameters:
    input_raster_path (str): Path to the raster file.
    nodata_value (numeric): The value to be set as NoData.
    """
    try:
        # Open the input raster in update mode
        raster = gdal.Open(input_raster_path, gdal.GA_Update)

        if not raster:
            raise IOError("Could not open raster file.")

        # Set the NoData value for each band
        for i in range(1, raster.RasterCount + 1):
            band = raster.GetRasterBand(i)
            data_type = band.DataType
            # Ensure the data type supports negative values if nodata_value is negative
            if nodata_value < 0 and gdal.GetDataTypeName(data_type).startswith('UInt'):
                raise ValueError(f"The raster data type is {gdal.GetDataTypeName(data_type)}, which does not support negative NoData values.")
            band.SetNoDataValue(nodata_value)
            band.FlushCache()  # Ensure changes are written immediately

        print(f"NoData value set to {nodata_value} successfully in {input_raster_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the raster file to ensure changes are saved
        raster = None
        
"""     # Example usage
   set_nodata_value(
    input_raster_path = "/path/to/input.tif"
    nodata_value = -9999
) """

def normalize_raster(input_tiffs):
    """
    Normalize a list of raster files using Min-Max scaling and save each as a new TIFF file
    with '_normalized' suffix added to the original filename.

    :param input_tiffs: List of paths to the input TIFF files
    :return: None
    """
    for input_tiff in input_tiffs:
        print(f"Processing {input_tiff}...")

        # Load the TIFF file and convert to float32
        raster = rioxarray.open_rasterio(input_tiff).astype(np.float32)

        # Get the NoData value
        no_data_value = raster.rio.nodata

        # Get the data as a NumPy array and mask NoData values
        data = raster.values
        masked_data = np.ma.masked_equal(data, no_data_value)

        # Reshape the data for MinMaxScaler (1D array)
        reshaped_data = masked_data.compressed().reshape(-1, 1)

        # Initialize the scaler
        scaler = MinMaxScaler()

        # Fit and transform the data
        normalized_data = scaler.fit_transform(reshaped_data)

        # Create an array for the normalized values
        normalized_full = np.full(data.shape, no_data_value, dtype=np.float32)  # Start with NoData values
        normalized_full[~masked_data.mask] = normalized_data.flatten()  # Fill in normalized values

        # Update the raster data with normalized values directly
        raster.values = normalized_full

        # Generate output file path with '_normalized' suffix
        base, ext = os.path.splitext(input_tiff)
        output_tiff = f"{base}_normalized{ext}"

        # Save the normalized raster to a new TIFF file
        raster.rio.to_raster(output_tiff)

        print(f"Normalized raster saved at {output_tiff}")

""" # Example usage
input_tiff = r"D:\Geospatial_Pessoal\FFSM\Fatores_Condicionantes\Rainfall\PDIR_2024-10-21011811pm\PDIR_2023_sum_32629.tif"
output_tiff = r"D:\Geospatial_Pessoal\FFSM\Fatores_Condicionantes\Rainfall\PDIR_2024-10-21011811pm\PDIR_2023_normalized.tif"

normalize_raster(input_tiff, output_tiff) """

def normalize_raster_fixed_scale(input_raster_path, output_normalized_raster_path, fixed_min, fixed_max):
    # Use the provided fixed minimum and maximum values
    fixed_min_value = fixed_min
    fixed_max_value = fixed_max

    with rasterio.open(input_raster_path) as src:
        # Read the first band and cast raster data to float
        raster_data = src.read(1).astype(float)

        # Identify the 'no data' value from the source
        nodata = src.nodata

        # Create a mask to exclude 'no data' value only
        mask = raster_data != nodata if nodata is not None else np.ones_like(raster_data, dtype=bool)

        # Normalize the raster values to the range [0, 1] based on the fixed scale
        normalized_data = np.copy(raster_data)
        scale_range = fixed_max_value - fixed_min_value  # Calculate the range of the scale
        if scale_range != 0:  # Avoid division by zero
            normalized_data[mask] = (raster_data[mask] - fixed_min_value) / scale_range
        else:
            # Handle case where scale range is zero (unlikely in this scenario)
            normalized_data[mask] = 0.0

        # Set 'no data' areas to original nodata value
        if nodata is not None:
            normalized_data[~mask] = nodata

        # Adjust the profile for a single band and write the output
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=nodata)

        with rasterio.open(output_normalized_raster_path, 'w', **profile) as dst:
            dst.write(normalized_data.astype(rasterio.float32), 1)

    # Print the input raster path and the fixed scale values
    print(f"Input Raster: {input_raster_path}")
    print(f"Fixed Minimum Value: {fixed_min_value}")
    print(f"Fixed Maximum Value: {fixed_max_value}")

    # Print the normalized data statistics (excluding NoData values)
    print(f"Normalized Data Min (excluding NoData): {normalized_data[mask].min()}")
    print(f"Normalized Data Max (excluding NoData): {normalized_data[mask].max()}")

""" # Example usage
input_raster_path = "path_to_your_input_raster.tiff"
output_normalized_raster_path = "path_to_your_output_normalized_raster.tiff"
fixed_min = 1.0
fixed_max = 5.0
normalize_raster(input_raster_path, output_normalized_raster_path, fixed_min, fixed_max) """


def relabel_clusters(cluster_ranges):
    """
    Relabels clusters based on their weighted mean values from cluster ranges.
    
    Args:
        cluster_ranges (list): A list of tuples containing (old_cluster_id, min_value, max_value, count)
    
    Returns:
        dict: A mapping from old cluster IDs to new cluster IDs based on sorted weighted mean values
    """
    
    # Calculate the mean and weighted mean for each cluster
    weighted_means = []
    means = []  # To store means for printing later
    for old_cluster_id, min_value, max_value, count in cluster_ranges:
        mean_value = (min_value + max_value) / 2  # Calculate mean of the range
        weighted_mean = mean_value * count  # Weight mean by the count
        means.append((old_cluster_id, mean_value, min_value, max_value, count))  # Store means for printing
        weighted_means.append((old_cluster_id, weighted_mean, min_value, max_value, count))
    
    # Print the means before relabeling
    print("Means for each cluster before relabeling:")
    for (old_cluster_id, mean_value, min_value, max_value, count) in means:
        print(f"Old Cluster {old_cluster_id}: Mean = {mean_value}, Min = {min_value}, Max = {max_value}, Count = {count}")
    
    # Sort clusters by their means (not weighted means for relabeling)
    sorted_means = sorted(means, key=lambda x: x[1])  # Sort by mean value
    
    # Create a new mapping from old cluster IDs to new cluster IDs
    new_labels = {}
    for new_index, (old_cluster_id, mean_value, min_value, max_value, count) in enumerate(sorted_means):
        new_cluster_id = new_index + 1  # New cluster IDs start from 1
        new_labels[old_cluster_id] = new_cluster_id  # Map old cluster ID to new cluster ID
        
    print("\nCluster value ranges and reordering based on means:")
    for (old_cluster_id, mean_value, min_value, max_value, count) in sorted_means:
        new_cluster_id = new_labels[old_cluster_id]  # Get the new cluster ID
        print(f"Old Cluster {old_cluster_id}: Min = {min_value}, Max = {max_value}, Count = {count} -> New Cluster {new_cluster_id}")

    return new_labels

def process_directory(input_directory, output_directory, n_clusters=None, process_single_file=False):
    """
    Processes all TIFF files in a directory or a single file if specified.
    """
        
    os.makedirs(output_directory, exist_ok=True)

    if process_single_file:
        if os.path.isfile(input_directory):
            print(f"Processing single file: {input_directory}")
            clustered_raster, raster_meta, cluster_ranges = process_kmeans(input_directory, n_clusters)

            # Relabel the clusters
            new_labels = relabel_clusters(cluster_ranges)

            # Create a relabelled raster using the new_labels mapping
            relabelled_raster = np.copy(clustered_raster)
            for old_label, new_label in new_labels.items():
                relabelled_raster[clustered_raster == old_label] = new_label

            new_output_raster = os.path.join(output_directory, os.path.basename(input_directory).replace('.tiff', '_relabelled.tiff'))

            # Use rioxarray to save the raster
            xr.DataArray(relabelled_raster, dims=("y", "x")) \
                .rio.write_crs(raster_meta['crs'], inplace=True) \
                .rio.write_transform(raster_meta['transform'], inplace=True) \
                .rio.write_nodata(raster_meta['nodata'], inplace=True) \
                .rio.to_raster(new_output_raster)

            print(f"Relabeling output saved at {new_output_raster}")
        else:
            print(f"Error: {input_directory} is not a valid file.")
    else:
        for filename in os.listdir(input_directory):
            if filename.endswith('.tiff') or filename.endswith('.tif'):
                input_raster = os.path.join(input_directory, filename)
                print(f"Processing {input_raster}")

                # Process the raster
                clustered_raster, raster_meta, cluster_ranges = process_kmeans(input_raster, n_clusters)

                # Relabel the clusters
                new_labels = relabel_clusters(cluster_ranges)

                # Create a relabelled raster using the new_labels mapping
                relabelled_raster = np.copy(clustered_raster)
                for old_label, new_label in new_labels.items():
                    relabelled_raster[clustered_raster == old_label] = new_label

                new_output_raster = os.path.join(output_directory, filename.replace('.tiff', '_relabeled.tiff'))

                xr.DataArray(relabelled_raster, dims=("y", "x")) \
                    .rio.write_crs(raster_meta['crs'], inplace=True) \
                    .rio.write_transform(raster_meta['transform'], inplace=True) \
                    .rio.write_nodata(raster_meta['nodata'], inplace=True) \
                    .rio.to_raster(new_output_raster)

                print(f"Relabeling output saved at {new_output_raster}")

def convert_raster_to_integers(input_tiff, output_tiff):
    """
    Converts raster values to integers and saves the output, preserving native NoData values.

    :param input_tiff: Path for the input raster file
    :param output_tiff: Path for the output raster file
    :return: None
    """
    raster = rioxarray.open_rasterio(input_tiff)

    # Get the native NoData value
    nodata_value = raster.rio.nodata

    float_raster = raster.round()

    # Preserve native NoData values
    int_raster = float_raster.where(float_raster != nodata_value, other=np.nan)

    # Convert to int32, ensuring NoData remains as np.nan
    int_raster = int_raster.where(~np.isnan(int_raster), other=np.nan).astype(np.float32)

    # Write the native NoData value to the raster metadata
    int_raster.rio.write_nodata(nodata_value, inplace=True)

    int_raster.rio.to_raster(output_tiff)

    print(f"Raster with integer dataype saved at {output_tiff}")

def clip_raster_by_masks(input_raster_path, mask_input, output_folder):
    """
    Clips one or more raster files by one or more mask layers (either a single file or all files in a folder).
    Saves the clipped rasters with filenames indicating the mask used.
    
    Args:
        input_raster_path (str): Path to a single raster file or a folder containing multiple raster files.
        mask_input (str): Path to a single mask file or folder containing multiple mask layers.
        output_folder (str): Path to the folder to save clipped rasters.
    
    Returns:
        None
    """
    os.makedirs(output_folder, exist_ok=True)
    
    if os.path.isdir(input_raster_path):
        raster_files = [f for f in os.listdir(input_raster_path) if f.endswith((".tif", ".tiff"))]
    elif os.path.isfile(input_raster_path) and input_raster_path.endswith((".tif", ".tiff")):
        raster_files = [os.path.basename(input_raster_path)]
    else:
        print("Error: Invalid raster input. Please provide either a folder or a valid raster file.")
        return
    
    if os.path.isdir(mask_input):
        mask_files = [f for f in os.listdir(mask_input) if f.endswith((".shp", ".geojson"))]
    elif os.path.isfile(mask_input) and mask_input.endswith((".shp", ".geojson")):
        mask_files = [os.path.basename(mask_input)]
    else:
        print("Error: Invalid mask input. Please provide either a folder or a valid mask file.")
        return

    for raster_file in raster_files:
        raster_path = os.path.join(input_raster_path, raster_file) if os.path.isdir(input_raster_path) else input_raster_path
        input_raster_name = os.path.splitext(raster_file)[0]
        
        for mask_file in mask_files:
            mask_path = os.path.join(mask_input, mask_file) if os.path.isdir(mask_input) else mask_input
            mask_name = os.path.splitext(os.path.basename(mask_file))[0]
            
            mask_gdf = gpd.read_file(mask_path)
            raster = rxr.open_rasterio(raster_path, masked=True)
            
            clipped_raster = raster.rio.clip(mask_gdf.geometry, mask_gdf.crs, drop=True)
            
            # Generate output path
            output_file_name = f"{input_raster_name}_clipped_by_{mask_name}.tif"
            output_raster_path = os.path.join(output_folder, output_file_name)
            
            # Save clipped raster
            clipped_raster.rio.to_raster(output_raster_path)
            print(f"Saved clipped raster to: {output_raster_path}")


def clip_raster_to_reference_extent(ground_truth_path, prediction_path):
    """Clips the ground truth raster to the extent of the predicted raster and ensures matching size."""
    
    with rasterio.open(prediction_path) as pred_src:
        pred_extent = pred_src.bounds  
        pred_box = box(*pred_extent) 
    
    with rasterio.open(ground_truth_path, 'r+') as gt_src:  
        ground_truth, _ = mask(gt_src, [pred_box], crop=True)
        
        # Get the dimensions of the predicted raster
        pred_width = pred_src.width
        pred_height = pred_src.height

        # Ensure that the ground truth raster has the same dimensions as the predicted raster
        if ground_truth.shape[1] != pred_height or ground_truth.shape[2] != pred_width:
            # Resize the ground truth to match the predicted raster size
            ground_truth_resized = np.resize(ground_truth, (ground_truth.shape[0], pred_height, pred_width))
        else:
            ground_truth_resized = ground_truth

        # Update the metadata for the clipped ground truth
        clipped_gt_meta = gt_src.meta.copy()
        clipped_gt_meta.update({
            'height': ground_truth_resized.shape[1], 
            'width': ground_truth_resized.shape[2],  
            'transform': pred_src.transform  
        })

        with rasterio.open(ground_truth_path, 'w', **clipped_gt_meta) as out_src:
            out_src.write(ground_truth_resized)

    print(f"Ground truth raster clipped and saved to {ground_truth_path}")

    return ground_truth_resized, clipped_gt_meta