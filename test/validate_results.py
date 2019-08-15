#!/usr/bin/env python

"""Validates the test results
"""

import os
import sys
import re
import tempfile
import shutil
import subprocess
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

# Number elements in a bucket that are "OK". Any bucket value above this is considered failure.
# This value is used with the total number of pixels to determine success. The value is the
# decimal representation of the percent
MAX_HISTOGRAM_DIFF_PCT = 0.03

# Default maximum number of pixels difference in any image dimension
MAX_ALLOWED_PIX_DIFF = 0

# Maximum allowed calculated differences between images (0.0 - 1.0)
# For example, the max histogram value divided by the total number of pixels < MAX_IMAGE_DIFF_PCT
MAX_IMAGE_DIFF_PCT = 0.001

# Maximum allowed cumulative calculated differences between images (0.0 - 1.0)
# For example, the sum of histogram values divided by the total number of pixels < MAX_IMAGE_SUM_DIFF_PCT
MAX_IMAGE_SUM_DIFF_PCT = 0.04

# Tiff Clipping Tuple: (min Y, max Y, min X, max X)
TIFF_CLIP_TUPLE = None

# Expected folders
datasets_folder = "./datasets"
compare_folder = "./compare"

def _clip_raster(src, dest):
    """Clips a geo located raster image file
    Args:
        src(str): The source raster file
        dest(str): The name of the file for the clipped image
    Return:
        True is returned if the raster was successfully clipped and False if not
    """
    # Check if we should have been called at all
    if TIFF_CLIP_TUPLE is None:
        return False

    cmd = 'gdal_translate -projwin %s %s %s %s "%s" "%s"' % \
              (TIFF_CLIP_TUPLE[2], TIFF_CLIP_TUPLE[1], TIFF_CLIP_TUPLE[3], TIFF_CLIP_TUPLE[0], src, dest)
    print("Clipping: " + cmd)
    subprocess.call(cmd, shell=True, stdout=open(os.devnull, 'wb'))
    return True


def string_to_int(value):
    """Converts a string to an integer
    Args:
        value(str): string to convert
    Return:
        The integer representation of the nummber. Fractions are truncated. Invalid values return None
    """
    ival = None

    try:
        ival = float(value)
        ival = int(ival)
    except Exception:
        pass

    return ival

def process_arg(arg):
    """Processes the argument string
    Args:
        String to process as a runtime command line argument
    Return:
        Returns true if the argument was recognised and accepted
    """
    return False

def process_arg_parameter(arg_and_params):
    """Processes the argument string with parameters
    Args:
        String to process as a runtime command line argument with parameters
    Return:
        Returns true if the argument and parameter was recognised and accepted
    """
    # We use if .. else instead of dictionary to keep evaluation time down and all the code in one place
    global MAX_ALLOWED_PIX_DIFF
    global TIFF_CLIP_TUPLE
    global MAX_IMAGE_DIFF_PCT
    global MAX_IMAGE_SUM_DIFF_PCT

    try:
        # Fix up argument and parameter
        param_len = len(arg_and_params)
        if param_len > 0:
            cmd = arg_and_params[0].lstrip('-')
            params = arg_and_params[1:]
            param_len = len(params)
            if param_len <= 0:
                params.append("")

            # Handle each argument
            if cmd == "pixdiff":
                diff_val = string_to_int(params[0])
                if diff_val >= 0:
                    MAX_ALLOWED_PIX_DIFF = diff_val
                    return True
            elif cmd == "geotiffclip":
                bounds = params[0].split(',')
                bounds_len = len(bounds)
                if bounds_len == 4:
                    min_x = min(bounds[0], bounds[2])
                    min_y = min(bounds[1], bounds[3])
                    max_x = max(bounds[0], bounds[2])
                    max_y = max(bounds[1], bounds[3])
                    TIFF_CLIP_TUPLE = (min_y, max_y, min_x, max_x)
                    print("Clip Tuple: " + str(TIFF_CLIP_TUPLE))
                    return True
            elif cmd == "bychannel":
                limits = params[0].split(',')
                limits_len = len(limits)
                if limits_len >= 1:
                    MAX_IMAGE_DIFF_PCT = float(limits[0]) / 100.0
                    print("Max image diff: " + str(MAX_IMAGE_DIFF_PCT))
                if limits_len >= 2:
                    MAX_IMAGE_SUM_DIFF_PCT = float(limits[1]) / 100.0
                    print("Max image sum diff: " + str(MAX_IMAGE_SUM_DIFF_PCT))

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

def _extract_image(img, x_off, y_off, max_x, max_y):
    """Returns a subsection of the image
    Args:
        img(numpy array): the source image (with 2 or 3 size dimensions)
        x_off(int): the starting X clip position (0th index of image)
        y_off(int): the starting Y clip position (1st index of image)
        max_x(int): the X size of extract (0th index of image)
        max_y(int): the Y size of extract (1st index of image)
    Return:
        The extracted portion of the image. If the requested extraction doesn't fit
        within the bounds of the image in any direction, the original image is returned.
    """
    dims = len(img.shape)

    # Return original if we can't fulfill the request for a dimension
    print("Extract: params: " + str(img.shape) + " " + str(x_off) + " " + str(y_off) + " " + str(max_x) + " " + str(max_y))
    if max_x == img.shape[0] and max_y == img.shape[1]:
        print("Extract:     Returning original, exact match")
        return img

    # Check if we need to clip the image from the origin because it's inherently too large
    if x_off + max_x > img.shape[0] or y_off + max_y > img.shape[1]:
        x_start = 0 if x_off + max_x > img.shape[0] else x_off
        y_start = 0 if y_off + max_y > img.shape[1] else y_off
        x_end = x_start + max_x
        y_end = y_start + max_y
        print("Extract:     Returning original, clipped: " + str(x_start) + "," + str(y_start) + " " + str(x_end) + "," + str(y_end))
        if dims == 2:
            return img[x_start:x_end, y_start:y_end]
        return img[x_start:x_end, y_start:y_end, :]

    # Return same type of image
    dims = len(img.shape)
    if dims == 2:
        return img[x_off:max_x+x_off, y_off:max_y+y_off]

    return img[x_off:max_x+x_off, y_off:max_y+y_off, :]


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

        # Get the file extention to use as file type
        _, ext = os.path.splitext(master)

        # If we have a tif file and we're asked to clip it
        comp_dir = None
        comp_master = master
        comp_source = source
        if ext == ".tif" and not TIFF_CLIP_TUPLE is None:
            comp_dir = tempfile.mkdtemp()
            comp_master = os.path.join(comp_dir, os.path.basename(master))
            print("Clipping: "+master+" to "+comp_master)
            _clip_raster(master, comp_master)
            comp_source = os.path.join(comp_dir, os.path.basename(source))
            print("Clipping: "+source+" to "+comp_source)
            _clip_raster(source, comp_source)

        # Check file sizes
        master_size = os.path.getsize(comp_master)
        source_size = os.path.getsize(comp_source)
        if master_size <= 0:
            if source_size <= 0:
                print("Success compare empty files (" + one_end + "): " + source + " and " + master)
                continue
            else:
                raise RuntimeError("Generated file is not empty like comparison file: " + source + " vs " + master)
        diff = abs(master_size - source_size)
        if not diff == 0 and float(diff)/float(master_size) > FILE_SIZE_MAX_DIFF_FRACTION:
            print("File size difference exceeds allowance of " + str(FILE_SIZE_MAX_DIFF_FRACTION) + ": " + str(master_size) + " vs " +
                  str(source_size) + " (old vs new) for files " + master + " and " + source)
            raise RuntimeError("File size difference exceeds limit of " + str(FILE_SIZE_MAX_DIFF_FRACTION) + ": " + source + " vs " + master)

        # Check file types
        if not ext:
            print("Success compare extension-less files (" + one_end + "): " + source + " and " + master)
            continue
        if not (ext == ".tif" or ext == "png"):
            print("Success. No futher tests for files (" + one_end + "): " + source + " and " + master)
            continue

        im_mas = cv2.imread(comp_master)
        im_src = cv2.imread(comp_source)

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
                    for idx in range(0, 1):
                        pix_diff = abs(im_mas.shape[idx] - im_src.shape[idx])
                        if pix_diff > 0 and pix_diff > MAX_ALLOWED_PIX_DIFF:
                            dimensional_error = True
            if dimensional_error is True:
                print("Mismatched image dimensions: (" + str(im_mas.shape) + ") vs (" + str(im_src.shape) + ")")
                failures['image dimensions'] = True

        if 'image dimensions' not in failures:
            diff_x = abs(im_mas.shape[0] - im_src.shape[0])
            diff_y = abs(im_mas.shape[1] - im_src.shape[1])
            size_x = min(im_mas.shape[0], im_src.shape[0])
            size_y = min(im_mas.shape[1], im_src.shape[1])
            print("Image size differences: (" + str(diff_x) + ", " + str(diff_y) + ")")
            print("Image min dimensions: (" + str(size_x) + ", " + str(size_y) + ")")
            if diff_x <= 1 and diff_y <= 1:
                matching_images = False
                max_histogram_diff = int(size_x * size_y * MAX_HISTOGRAM_DIFF_PCT)
                for x_off in range(0, diff_x + 1):
                    for y_off in range(0, diff_y + 1):
                        # Get any subset of the images we need to check
                        if not diff_x == 0 or not diff_y == 0:
                            print("Cropping images: ("+str(x_off)+", "+str(y_off)+") ("+str(size_x)+", "+str(size_y)+")")
                            check_mas = _extract_image(im_mas, x_off, y_off, size_x, size_y)
                            check_src = _extract_image(im_src, x_off, y_off, size_x, size_y)
                            print("    crop result: "+str(check_mas.shape)+" "+str(check_src.shape))
                        else:
                            print("Comparing original images")
                            check_mas = im_mas
                            check_src = im_src

                        found_mismatch = False
                        total_pixels = float(check_mas.shape[0] * check_mas.shape[1])
                        for channel in range(0, 3):
                            print("Working on channel "+str(channel))

                            # Check the normalized average pixel value
                            master_chan_avg = float(np.sum(check_mas[:, :, channel])) / total_pixels
                            source_chan_avg = float(np.sum(check_src[:, :, channel])) / total_pixels
                            pct_master = master_chan_avg / (master_chan_avg + source_chan_avg)
                            pct_source = source_chan_avg / (master_chan_avg + source_chan_avg)
                            print("  Average pixel value difference: " + str(abs(pct_master - pct_source)))
                            if abs(pct_master - pct_source) >= MAX_IMAGE_DIFF_PCT:
                                print("  Average pixel value differences exceed threshold")
                                print("    Avg: " + str(master_chan_avg) + " vs " + str(source_chan_avg))
                                print("    Values: " + str(pct_master) + " - " + str(pct_source) + \
                                                                    " >= " + str(MAX_IMAGE_DIFF_PCT))
                                found_mismatch = True
                                break

                            # Check the normalized counts of pixel intensity
                            master_hist, _ = np.histogram(check_mas[:, :, channel], 256, (0, 255))
                            source_hist, _ = np.histogram(check_src[:, :, channel], 256, (0, 255))
                            subsample_master = np.sum(master_hist[25:230])
                            subsample_source = np.sum(source_hist[25:230])
                            pct_master = float(subsample_master) / float(np.sum(master_hist))
                            pct_source = float(subsample_source) / float(np.sum(source_hist))
                            print("  Percentage histogram intensity difference: " + str(abs(pct_master - pct_source)))
                            if abs(pct_master - pct_source) >= MAX_IMAGE_DIFF_PCT:
                                print("  Percentage differences between histograms of intensity exceeds threshold")
                                print("    Values: " + str(pct_master) + " - " + str(pct_source) + \
                                                                    " >= " + str(MAX_IMAGE_DIFF_PCT))
                                found_mismatch = True
                                break

                            # Perform a maximum value of histogram difference comparison
                            diff = np.absolute(np.subtract(master_hist, source_hist))
                            maxval = 0
                            for val in diff:
                                maxval = max(maxval, val)
                            print("  Pixel intensity difference of maximum percent: " + str(float(maxval) / total_pixels))
                            if float(maxval) / total_pixels >= MAX_IMAGE_DIFF_PCT:
                                found_mismatch = True
                                print("  Pixel intensity difference maximum (by count) exceeds threshold")
                                print("    Values: " + str(maxval) + " / " + str(total_pixels) + \
                                                                    " >= " + str(MAX_IMAGE_DIFF_PCT))
                                break

                            # Check that the total histogram differences are within range
                            total_diff = np.sum(diff)
                            print("  Pixel intensity difference sum percent: " + str(float(total_diff) / total_pixels))
                            if float(total_diff) / total_pixels >= MAX_IMAGE_SUM_DIFF_PCT:
                                found_mismatch = True
                                print("  Pixel intensity difference sum total (by count) exceeds threshold")
                                print("    Values: " + str(total_diff) + " / " + str(total_pixels) + \
                                                                    " >= " + str(MAX_IMAGE_DIFF_PCT))
                                break

                        if not found_mismatch:
                            matching_images = True

                if not matching_images:
                    print("FAILURE: Failed to match images")
                    #failures['image differences'] = True
            else:
                print("Skipping image histogram comparison due to image dimensional differences: assuming success: " + source + " vs " + master)
                print("    Image dimensions: (" + str(im_mas.shape) + ") vs (" + str(im_src.shape) + ")")

        # Report any errors back
        failures_len = len(failures)
        if failures_len > 0:
            print("We have " + str(failures_len) + " errors detected for files (" + one_end + "): " + source + " vs " + master)
            errs = ', '.join(str(k) for k in failures.keys())
            raise RuntimeError("Errors found: %s" % errs)

        print("Success compare image files (" + one_end + "): " + source + " and " + master)

        # Perform cleanup
        if not comp_dir is None:
            print("Removing temporary folder: "+comp_dir)
            shutil.rmtree(comp_dir)

print("Test has run successfully")
