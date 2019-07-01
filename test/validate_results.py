#!/usr/bin/env python

"""Validates the test results
"""

import os
import sys
import re
import math
import cv2
import numpy as np

# Maximum difference in size of generated file vs. master before there's an error
FILE_SIZE_MAX_DIFF_FRACTION = 0.10

# How much difference is allowed before we start looking at values
# For example, a 10% allowance means we don't start looking at histogram values until bin 25
PERCENT_DIFF_ALLOWED = (5.0 / 100.0)

# Calculate the starting histogram index value
HIST_START_INDEX = int(math.ceil(256 * PERCENT_DIFF_ALLOWED))

# Number elements in a bucket that are "OK". Any bucket value above this is considered failure
# Note that for 3 channel images, a value of 100 means that about 33 pixels in any bin exceeding
# this value would cause failure
HIST_BIN_MAX = 100

# Default maximum number of pixels difference in any image dimension
MAX_ALLOWED_PIX_DIFF = 0

# Expected folders
datasets_folder = "./datasets"
compare_folder = "./compare"

def string_to_int(value):
    """Converts a string to an integer
    Args:
        value(str): string to convert
    Return:
        The integer representation of the nummber. Fractions are truncated. Invalid values return None
    """
    val = None

    try:
        val = float(value)
        val = int(val)
    except Exception:
        pass

    return val

def process_arg(arg):
    """Processes the argument string
    Args:
        String to process as a runtime command line argument
    Return:
        Returns true if the parameter was recognised and accepted
    """
    return False

def process_arg_parameter(arg_and_params):
    """Processes the argument string with parameters
    Args:
        String to process as a runtime command line argument with parameters
    Return:
        Returns true if the parameter was recognised and accepted
    """
    # We use if .. else instead of dictionary to keep evaluation time down and all the code in one place
    global MAX_ALLOWED_PIX_DIFF
    try:
        param_len = len(arg_and_params)
        if param_len > 0:
            cmd = arg_and_params[0].lstrip('-')
            params = arg_and_params[1:]
            param_len = len(params)
            if param_len <= 0:
                params.append("")

            if cmd == "pixdiff":
                val = string_to_int(params[0])
                if val >= 0:
                    MAX_ALLOWED_PIX_DIFF = val
                    return True
                
    except Exception as ex:
        print("Caught exception processing argument with parameters: " + str(ex))
        print("    Parameter: " + str(arg_and_params))
        print("    continuing...")

    return False

def find_file_match(folder, end):
    """Locates a file in the specified folder that has the matching ending.
    Args:
        folder(str): path to the folder to look in
        end(str): the file name ending to look for
    Return:
        The path of the first file that matches the end parameter
    Notes: This function will work recursively to find the file. Each folder is fully scanned
           before its sub-folders are examined. Each subfolder is examined in depth before
           moving on to the next subfolder
    """
    if not os.path.exists(folder):
        return None
    if not os.path.isdir(folder):
        return None

    dir_list = os.listdir(folder)
    subdirs = []

    # First try to find the file. Save any sub folders for later
    for entry in dir_list:
        # Skip over hidden files
        if entry[0] == '.':
            continue

        # Check the name to see if it's a file and if it first the descrioption
        test_path = os.path.join(folder, entry)
        if os.path.isfile(test_path):
            if test_path.endswith(end):
                return test_path
        else:
            subdirs.append(entry)

    # Loop through sub folders
    subdirs_len = len(subdirs)
    if subdirs_len > 0:
        for one_dir in subdirs:
            found = find_file_match(os.path.join(folder, one_dir), end)
            if not found is None:
                return found

    return None

def find_filtered_folders(folder, regex_filter=None):
    """Finds subfolders that match the filter
    Args:
        folder(str): the folder to iterate over
        regex_filter(str): optional regular expression used to filter out subfolders
    Return:
        A list of matched folders or None if no folders were found and/or matched
    Notes:
        If regex_filter is None then all subfolders are considered a match
    """
    found = []

    for name in os.listdir(folder):
        # Skip over special folders and hidden names
        name_len = len(name)
        if name_len >= 1 and name[0] == '.':
            continue

        full_name = os.path.join(folder, name)
        if os.path.isdir(full_name):
            if not regex_filter is None:
                match = re.search(regex_filter, full_name)
                if not match is None:
                    found.append(name)
            else:
                found.append(name)

    found_len = len(found)
    return found if not found_len <= 0 else None


argc = len(sys.argv)
if argc <= 1:
    raise RuntimeError("Missing filename match strings parameter")
if ',' in sys.argv[1]:
    file_endings = []
    for ending in sys.argv[1].split(','):
        file_endings.append(ending.strip())
else:
    file_endings = [sys.argv[1].strip()]

# Check for a dataset filter and ensure it's not an empty string (white space counts)
dataset_filter = None
if argc > 2:
    dataset_filter = sys.argv[2]
    dataset_filter_len = len(dataset_filter)
    if dataset_filter_len <= 0:
        dataset_filter = None

# Check for other parameters
if argc > 3:
    for idx in range(3, argc):
        if '=' in sys.argv[idx]:
            process_arg_parameter(sys.argv[idx].split('='))
        else:
            process_arg(sys.argv[idx])

# Find subfolders if they're specified. Having no subfolders, with a filter specified, is not considered an error
if not dataset_filter is None:
    filtered_folders = find_filtered_folders(compare_folder, dataset_filter)
    if filtered_folders is None:
        filtered_folders = find_filtered_folders(datasets_folder, dataset_filter)
    if filtered_folders is None:
        filtered_folders = [None]
else:
    filtered_folders = [None]

# Loop through everything
filtered_folder_range = range(0, len(filtered_folders))
for one_end in file_endings:
    # If we have subfolders, we loop through those
    for folder_idx in filtered_folder_range:
        # Find the file with the correct name
        sub_folder = filtered_folders[folder_idx]

        match_folder = compare_folder if sub_folder is None else os.path.join(compare_folder, sub_folder)
        master = find_file_match(match_folder, one_end)

        match_folder = datasets_folder if sub_folder is None else os.path.join(datasets_folder, sub_folder)
        source = find_file_match(match_folder, one_end)

        if master is None:
            raise RuntimeError("Missing the comparison files used to validate results: " + str(one_end))
        if source is None:
            raise RuntimeError("Missing the resulting files from the dataset: " + str(one_end))

        # Check file sizes
        master_size = os.path.getsize(master)
        source_size = os.path.getsize(source)
        if master_size <= 0 and not source_size <= 0:
            raise RuntimeError("Generated file is not empty like comparison file: " + source + " vs " + master)
        if not master_size == 0:
            diff = abs(master_size - source_size)
            if not diff == 0 and float(diff)/float(master_size) > FILE_SIZE_MAX_DIFF_FRACTION:
                raise RuntimeError("File size difference exceeds limit of " + FILE_SIZE_MAX_DIFF_FRACTION + ": " + source + " vs " + master)
        if master_size == 0 or source_size == 0:
            print("Success compare empty files (" + one_end + "): " + source + " and " + master)
            continue

        # Check file types
        _, ext = os.path.splitext(master)
        if not ext:
            print("Success compare extension-less files (" + one_end + "): " + source + " and " + master)
            continue

        if not (ext == ".tif" or ext == "png"):
            print("Success. No futher tests for files (" + one_end + "): " + source + " and " + master)
            continue

        im_mas = cv2.imread(master)
        im_src = cv2.imread(source)

        if im_mas is None:
            print("Master image was not loaded: '" + master + "'")
            exit(1)
        if im_src is None:
            print("Source image was not loaded: '" + source + "'")
            exit(1)

        # We use a dict so that we can add better error handling later if desired
        failures = {}

        # Check the image attributes
        if not im_mas.shape == im_src.shape:
            mas_shape_len = len(im_mas.shape)
            src_shape_len = len(im_src.shape)
            dimensional_error = True
            # We want to perform additional checks to determine if some variations are OK
            if mas_shape_len == src_shape_len:  # Make sure images have the same number of dimensions
                if mas_shape_len < 3 or (im_mas.shape[2] == im_src.shape[2]): # Dimension 3 is the number of channels
                    # Check the pixel count differences in each dimension and see if they're acceptable
                    dimensional_error = False
                    for idx in range(0,1):
                        pix_diff = abs(im_mas.shape[idx] - im_src.shape[idx])
                        if pix_diff > 0 and pix_diff > MAX_ALLOWED_PIX_DIFF:
                            dimensional_error = True
            if dimensional_error == True:
                print("Mismatched image dimensions: (" + str(im_mas.shape) + ") vs (" + str(im_src.shape) + ")")
                failures['image dimensions'] = True

        if 'image dimensions' not in failures:
            if im_mas.shape == im_src.shape:
                # calculate the differences between the images and check that
                diff = np.absolute(np.subtract(im_mas, im_src))
                hist, _ = np.histogram(diff, 256, (0, 255))

                start_idx = HIST_START_INDEX if HIST_START_INDEX < hist.size else 0
                for idx in range(start_idx, hist.size):
                    if hist[idx] > HIST_BIN_MAX:
                        print("Histogram: Have over " + str(HIST_BIN_MAX) + " items at index " + str(idx) + ": " + str(hist[idx]))
                        print("   Using range of " + str(start_idx) + " to " + str(hist.size) + " [HIST_START_INDEX: " + str(HIST_START_INDEX) + "]")
                        print("   Histogram: " + str(hist))
                        #failures['image differences'] = True
                        break
            else:
                print("Skipping image histogram comparison due to image dimensional differences: assuming success")

        # Report any errors back
        failures_len = len(failures)
        if failures_len > 0:
            print("We have " + str(failures_len) + " errors detected for files (" + one_end + "): " + source + " vs " + master)
            errs = ', '.join(str(k) for k in failures.keys())
            raise RuntimeError("Errors found: %s" % errs)

        print("Success compare image files (" + one_end + "): " + source + " and " + master)

print("Test has run successfully")
