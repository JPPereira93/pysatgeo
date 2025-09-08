"""
Download-related utilities for pysatgeo.
"""

import requests
import zipfile
import os
import time

def download_file(url, save_dir):
    local_filename = os.path.join(save_dir, url.split('/')[-1])
    # Download the file in chunks and save it
    with requests.get(url, stream=True) as r:
        r.raise_for_status()  # Check if the request was successful
        total_size = int(r.headers.get('content-length', 0))  # Total file size
        downloaded_size = 0
        
        start_time = time.time()  # Start time for speed calculation
        
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk) 
                    
                    # Calculate elapsed time and download speed
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0: 
                        speed = (downloaded_size / (1024 * 1024)) / elapsed_time  
                        # Speed in MB/s
                        print(f"\rDownloading {local_filename}... {downloaded_size / (1024 * 1024):.2f} MB of {total_size / (1024 * 1024):.2f} MB at {speed:.2f} MB/s", end='')
        
        print(f"\nDownloaded {local_filename} successfully.")
    return local_filename

def download_soil_moisture(manifest_url, year, save_directory):
    # Download the manifest file
    response = requests.get(manifest_url)
    if response.status_code == 200:
        # Parse the manifest content, each line is a different URL
        urls = response.text.splitlines() 
        
        # Filter URLs by the specified year
        filtered_urls = [url for url in urls if f'/{year}/' in url]
        
        if not filtered_urls:
            print(f"No files found for the year {year}.")
            return

        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        total_files = len(filtered_urls)
        for i, file_url in enumerate(filtered_urls):
            print(f"Downloading file {i + 1}/{total_files}: {file_url}")
            try:
                download_file(file_url, save_directory)
                print(f"Downloaded {file_url} successfully.")
                print(f"{total_files - (i + 1)} files remaining to download.")
            except Exception as e:
                print(f"Failed to download {file_url}: {e}")
    else:
        print(f"Failed to fetch the manifest file: {response.status_code}")

def extract_files_ssm(input_dir):
    """
    Unzips the files corresponding to the SSM (without the noise band) inside the sub directories inside the main folder
    Build new folders in every subfolder with only the date of the file.
    
    :param input_dir: Path of the main directory where download files from SSM and LST are located
    """
    
    for subdir in os.listdir(input_dir):
        if subdir.startswith('SSM1km_'):
            for file in os.listdir(os.path.join(input_dir, subdir)):
                if file.startswith('c_gls_SSM1km_') and file.endswith('.zip'):
                    zip_file_path = os.path.join(input_dir, subdir, file)
                    extract_dir = os.path.join(input_dir, subdir)
                    tiff_file_exists = any(f.endswith('.tiff') for f in os.listdir(extract_dir))
                    if not tiff_file_exists:
                        shutil.unpack_archive(zip_file_path, extract_dir=extract_dir)
                        
    """     Example Usage  
    input_dir = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\2023\SSM"
 
    extract_files_ssm_lst(input_dir) """

def folder_stack_ssm(input_dir):
    """
    Copies tiffs files and place it into the main input directory.
    Deletes no data files (because of no satellite passages in that date) and finally copies all tiffs in main folder 
    into a single folder with the name of first four characters of a single filename.

    :param input_dir: Path of the main directory where files of each sub directory are already unzipped.
    """
    
    for folder in os.listdir(input_dir):
        if folder.startswith('SSM1km'):
            # get the date from the folder name
            date = folder.split('_')[1][:8]
            # build the new folder name with the shortened date
            new_folder_name = f'SSM1km_{date}_CEURO_S1CSAR_V1.1.1'
            # build the paths for the old and new folders
            old_folder_path = os.path.join(input_dir, folder)
            new_folder_path = os.path.join(input_dir, new_folder_name)
            # rename the folder
            try:
                os.rename(old_folder_path, new_folder_path)
            except FileNotFoundError:
                print(f"Error: Folder {old_folder_path} not found.")

    # copy the .tiff file inside the subdirectory, rename it, and place it in the path
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".tiff"):
                if "c_gls_SSM1km" in file:
                    src_path = os.path.join(root, file)
                    date = file.split("_")[3][:8]
                    dst_filename = "SSM_1km_" + date + ".tiff"
                    dst_path = os.path.join(input_dir, dst_filename)
                    shutil.copy(src_path, dst_path)

    # loop over the files in the directory
    for file_name in os.listdir(input_dir):
        # get the full file path
        file_path = os.path.join(input_dir, file_name)
        # check if the file is a TIFF file and has a size less than or equal to 13 KB = NO DATA
        if file_name.endswith(".tiff") and os.path.getsize(file_path) <= 13*1024:
            # Delete the file
            os.remove(file_path)
            
    # Iterate over the files in the input directory
    for file_name in os.listdir(input_dir):
        # Check if the file is a TIFF file
        if file_name.endswith(".tiff"):
            # Extract the year from the file name
            year = file_name.split("_")[2][:4]
            # Create the destination folder name based on the year
            dest_folder_name = f'SSM_1km_{year}'
            dest_folder_path = os.path.join(input_dir, dest_folder_name)

            # Create the destination folder if it doesn't exist
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)

            # Construct the source and destination file paths
            src_file_path = os.path.join(input_dir, file_name)
            dst_file_path = os.path.join(dest_folder_path, file_name)

            # Move the file to the destination folder
            shutil.move(src_file_path, dst_file_path)

    # Delete the folders that start with 'SSM1km' in the specified directory
    for folder in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, folder)
        if os.path.isdir(folder_path) and folder.startswith('SSM1km'):
            shutil.rmtree(folder_path)
    
    """     Example Usage  
    input_dir = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\2023\SSM"
 
    folder_stack_ssm_lst(input_dir)   """        