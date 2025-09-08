"""
LiDAR LAS/LAZ processing for pysatgeo.
"""

import laspy
import os
import glob
import subprocess


def convert_las_to_laz(input_directory):
    """
    Converts a las file to a laz file
    :param input_file: Path to the input .las file.
    """
    
    file_pattern = "*.las"

        # Iterate over each LAS file in the directory
    for las_file in glob.glob(os.path.join(input_directory, file_pattern)):
        # Construct the output filename
        base_name = os.path.splitext(os.path.basename(las_file))[0]
        output_file = os.path.join(input_directory, f"{base_name}.laz")

        # Decimate original laz files to decrease resolution and size
        laszip_command = [
            "laszip64", "-i", las_file, "-o", output_file
        ]

        subprocess.run(laszip_command)

    print(f"Las to Laz conversion completed!  in {input_directory}")
    
    """    Example Usage  
input_directory_parte = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\Dados_Fornecidos\ANT_LiDar\ANT_Parte_1"
 
convert_las_to_laz(input_directory_parte)  """

def convert_laz_to_copc(input_file):
    """
    Converts a LAZ file to a COPC LAZ file
    :param input_file: Path to the input LAZ file. This should be the full path to the file, ensuring it exists and is accessible.
    """
    # Construct the output filename with a '.copc.laz' extension
    output_file = f"{os.path.splitext(input_file)[0]}.copc.laz"

    # Construct and run the lascopcindex command
    command = ['lascopcindex64', '-i', input_file, '-o', output_file]

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        output_dir = os.path.dirname(output_file)
        output_filename = os.path.basename(output_file)
        print(f"Conversion successful: {output_filename} saved in directory {output_dir}")
    except subprocess.CalledProcessError as e:
        print("Error during conversion:", e.stderr)

""" Example usage
input_file = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\Dados_Fornecidos\ANT_LiDar\ANT_Parte_1\CN_Parte1_Merged.laz"

convert_laz_to_copc(input_file)
"""



def thin_laz_files(input_directory, step_size):
    # Pattern to match all LAZ files
    file_pattern = "*.laz"

        # Iterate over each LAZ file in the directory
    for laz_file in glob.glob(os.path.join(input_directory, file_pattern)):
        # Construct the output filename
        base_name = os.path.splitext(os.path.basename(laz_file))[0]
        output_file = os.path.join(input_directory, f"{base_name}_thinned.laz")

        # Decimate original laz files to decrease resolution and size
        lasthin_command = [
            "lasthin", "-i", laz_file, "-o", output_file, "-step", str(step_size)
        ]

        subprocess.run(lasthin_command)

    print(f"Decimation completed in {input_directory}")
    
    """    Example Usage  
input_directory_parte_1 = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\Dados_Fornecidos\ANT_LiDar\ANT_Parte_1"
 
thin_laz_files(input_directory_parte_1, 1.0)  """  

def find_and_merge_thinned_files(input_directories, output_file):
    thinned_files = []
    # Pattern to match all thinned LAZ files
    thinned_file_pattern = "*_thinned.laz"

    # Finding thinned files in each input directory
    for directory in input_directories:
        thinned_files += glob.glob(os.path.join(directory, thinned_file_pattern))

    # Check if there are thinned files to merge
    if not thinned_files:
        print("No thinned files found to merge.")
        return

    # Determine the common directory for the thinned files
    common_directory = os.path.commonpath(thinned_files)

    # Convert absolute paths to relative paths based on the common directory
    relative_thinned_files = [os.path.relpath(f, common_directory) for f in thinned_files]

    # Store the original working directory
    original_directory = os.getcwd()
    try:
        # Change the current working directory to the common directory
        os.chdir(common_directory)

        # Merge thinned files to a single one
        lasmerge_command = ["lasmerge", "-i"] + relative_thinned_files + ["-o", os.path.basename(output_file)]
        
        # Print the command to debug
        print("Running command:", ' '.join(lasmerge_command))

        subprocess.run(lasmerge_command, check=True)  # Use check=True to raise an error if the command fails
        print("Merging completed! Output file:", output_file)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Change back to the original directory
        os.chdir(original_directory)
    
"""    Example Usage  
    merged_output_file_1 = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\Dados_Fornecidos\ANT_LiDar\ANT_Parte_1\CN_Parte1_Merged.laz"
    input_directory_parte_1 = r"E:\Spotlite_JPereira\Ascendi\Concessao_Norte\Dados_Fornecidos\ANT_LiDar\ANT_Parte_1"
    
    find_and_merge_thinned_files([input_directory_parte_1], merged_output_file_1)
  """  

def filter_laz(input_file, classification_label=2):
    """
    Filters a LAZ file using PDAL Wrench commands.
    
    :param input_file: Path to the input LAZ file. This should be the full path to the file, ensuring it exists and is accessible.
    :param classification_label: The classification label to filter on. Default is 2.
    """
    # Construct the output filename with a '_filtered_label_2.laz' extension
    output_file = f"{os.path.splitext(input_file)[0]}_filtered_label_{classification_label}.laz"

    command = [
        'pdal_wrench', 'translate',
        f'--input={input_file}',
        f'--output={output_file}',
        f'--filter=Classification == {classification_label}',
        '--threads=16'
    ]

    try:
        # Run the command with Popen to get real-time output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in process.stdout:
            print(line, end='')  # Print each line from stdout

        return_code = process.wait()
        
        if return_code == 0:
            output_dir = os.path.dirname(output_file)
            output_filename = os.path.basename(output_file)
            print(f"\nFiltering successful: {output_filename} saved in directory {output_dir}")
        else:
            print("\nError during filtering.")
            print("Return code:", return_code)

    except Exception as e:
        print("An unexpected error occurred:", str(e))

def laz_to_dem(input_file, output_file=None, resolution=1, tile_size=1000, threads=16):
    """
    Converts a LAZ file to a DEM using PDAL Wrench commands.
    
    :param input_file: Path to the input LAZ file. This should be the full path to the file, ensuring it exists and is accessible.
    :param output_file: Optional. Path to the output TIFF file. If not specified, defaults to a name derived from the input file.
    :param resolution: Optional. Resolution of the output DEM in meters. Default is 1 meter.
    :param tile_size: Optional. Size of the tiles for processing. Default is 1000.
    :param threads: Optional. Number of threads to use for processing. Default is 16.
    """
    if output_file is None:
        output_file = f"{os.path.splitext(input_file)[0]}_{resolution}m.tiff"

    command = [
        'pdal_wrench', 'to_raster',
        f'--output={output_file}',
        f'--resolution={resolution}',
        f'--tile-size={tile_size}',
        f'--threads={threads}',
        '--attribute=Z',
        f'--input={input_file}',
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in process.stdout:
            print(line, end='')  # Print each line from stdout

        # Wait for the process to complete
        return_code = process.wait()
        
        if return_code == 0:
            output_dir = os.path.dirname(output_file)
            output_filename = os.path.basename(output_file)
            print(f"\nConversion successful: {output_filename} saved in directory {output_dir}")
        else:
            print("\nError during conversion.")
            print("Return code:", return_code)

    except Exception as e:
        print("An unexpected error occurred:", str(e))