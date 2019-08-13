#!/usr/bin/env python

'''Extractor for calculating canopy cover by plot plots
'''

import os
import json
import logging
import math
import random
import time
import requests
import osr
import numpy as np
import gdal

from osgeo import ogr

import pyclowder.datasets as clowder_dataset
from pyclowder.utils import CheckMessage

from terrautils.extractors import TerrarefExtractor, build_metadata, confirm_clowder_info, \
     timestamp_to_terraref
from terrautils.sensors import STATIONS
from terrautils.imagefile import file_is_image_type, image_get_geobounds, get_epsg

# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'canopybyshape' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['canopybyshape'] = {'template': '{base}/{station}/Level_3/' + \
                                                           '{sensor}/{date}/{timestamp}/{filename}',
                                               'pattern': '{sensor}_L3_{station}_{date}{opts}.csv',
                                              }

# Number of tries to open a CSV file before we give up
MAX_CSV_FILE_OPEN_TRIES = 10

# Maximum number of seconds a single wait for file open can take
MAX_FILE_OPEN_SLEEP_SEC = 30

# Array of trait names that should have array values associated with them
TRAIT_NAME_ARRAY_VALUE = ['canopy_cover', 'site']

# Mapping of default trait names to fixecd values
TRAIT_NAME_MAP = {
    'access_level': '2',
    'species': 'Unknown',
    'citation_author': '"Zongyang, Li"',
    'citation_year': '2016',
    'citation_title': 'Maricopa Field Station Data and Metadata',
    'method': 'Canopy Cover Estimation from RGB images'
}

RANDOM_GENERATOR = None

def _get_plot_name(name):
    """Looks in the parameter and returns a plot name.

       Expects the plot name to be identified by having "By Plot" embedded in the name.
       The plot name is then surrounded by " - " characters. That valus is then returned.

    Args:
        name(iterable or string): An array/list of names or a single name string

    Return:
        Returns the found plot name or an empty string.
    """
    if isinstance(name, str):
        name = [name]

    plot_signature = "by plot"
    plot_separator = " - "
    # Loop through looking for a plot identifier (case insensitive)
    for one_name in name:
        low_name = one_name.lower()
        if plot_signature in low_name:
            parts = low_name.split(plot_separator)
            parts_len = len(parts)
            if parts_len > 1:
                return parts[1]

    return ""

def _get_open_backoff(prev=None):
    """Returns the number of seconds to backoff from opening a file

    Args:
        prev(int or float): the previous return value from this function

    Return:
        Returns the number of seconds (including fractional seconds) to wait

    Note that the return value is deterministic, and always the same, when None is
    passed in
    """
    # pylint: disable=global-statement
    global RANDOM_GENERATOR
    global MAX_FILE_OPEN_SLEEP_SEC

    # Simple case
    if prev is None:
        return 1

    # Get a random number generator
    if RANDOM_GENERATOR is None:
        try:
            RANDOM_GENERATOR = random.SystemRandom()
        finally:
            # Set this so we don't try again
            RANDOM_GENERATOR = 0

    # Get a random number
    if RANDOM_GENERATOR:
        multiplier = RANDOM_GENERATOR.random()
    else:
        multiplier = random.random()

    # Calculate how long to sleep
    sleep = math.trunc(float(prev) * multiplier * 100) / 10.0
    if sleep > MAX_FILE_OPEN_SLEEP_SEC:
        sleep = max(0.1, math.trunc(multiplier * 100) / 10)

    return sleep

def get_fields():
    """Returns the supported field names as a list
    """
    return ('local_datetime', 'canopy_cover', 'access_level', 'species', 'site',
            'citation_author', 'citation_year', 'citation_title', 'method')

def get_default_trait(trait_name):
    """Returns the default value for the trait name
    Args:
       trait_name(str): the name of the trait to return the default value for
    Return:
        If the default value for a trait is configured, that value is returned. Otherwise
        an empty string is returned.
    """
    # pylint: disable=global-statement
    global TRAIT_NAME_ARRAY_VALUE
    global TRAIT_NAME_MAP

    if trait_name in TRAIT_NAME_ARRAY_VALUE:
        return []
    elif trait_name in TRAIT_NAME_MAP:
        return TRAIT_NAME_MAP[trait_name]
    return ""

def get_traits_table():
    """Returns the field names and default trait values

    Returns:
        A tuple containing the list of field names and a dictionary of default field values
    """
    # Compiled traits table
    fields = get_fields()
    traits = {}
    for field_name in fields:
        traits[field_name] = get_default_trait(field_name)

    return (fields, traits)

# TODO: Keep these in terrautils.bety instead
def generate_traits_list(traits):
    """Returns an array of trait values

    Args:
        traits(dict): contains the set of trait values to return

    Return:
        Returns an array of trait values taken from the traits parameter
    """
    # compose the summary traits
    fields = get_fields()
    trait_list = []
    for field_name in fields:
        if field_name in traits:
            trait_list.append(traits[field_name])
        else:
            trait_list.append(get_default_trait(field_name))

    return trait_list

def calculate_canopycover_masked(pxarray):
    """Return greenness percentage of given numpy array of pixels.

    Args:
      pxarray (numpy array): rgb image

    Return:
      (float): greenness percentage
    """

    # For masked images, all nonzero pixels are considered canopy
    nz = count_nonzero(pxarray)
    ratio = nz/float(pxarray.size)
    # Scale ratio from 0-1 to 0-100
    ratio *= 100.0

    return ratio

# The class for determining canopy cover from an RGB image
class CanopyCover(TerrarefExtractor):
    """Extractor for clipping georeferenced images to plot boundaries via a shape file

       The extractor creates datasets of images for each plot and uploads them to Clowder
    """
    def __init__(self):
        """Initialization of class instance.

           We use the identify application to identify the mime type of files and then
           determine if they are georeferenced using the osgeo package
        """
        super(CanopyCover, self).__init__()

        # Our default values
        identify_binary = os.getenv('IDENTIFY_BINARY', '/usr/bin/identify')

        # Add any additional arguments to parser
        self.parser.add_argument('--identify-binary', nargs='?', dest='identify_binary',
                                 default=identify_binary,
                                 help='Identify executable used to for image type capture ' +
                                 '(default=' + identify_binary + ')')

        # parse command line and load default logging configuration
        self.setup(sensor='canopyCover')

    # List of file extensions we will probably see that we don't need to check for being
    # an image type
    @property
    def known_non_image_ext(self):
        """Returns an array of file extensions that we will see that
           are definitely not an image type
        """
        return ["dbf", "json", "prj", "shp", "shx", "txt"]

    # Look through the file list to find the files we need
    # pylint: disable=too-many-locals,too-many-nested-blocks
    def find_image_files(self, files):
        """Finds files that are needed for extracting plots from an orthomosaic

        Args:
            files(list): the list of file to look through and access

        Returns:
            Returns a dict of georeferenced image files (indexed by filename and containing an
            object with the calculated image bounds as an ogr polygon and a list of the
            bounds as a tuple)

            The bounds are assumed to be rectilinear with the upper-left corner directly
            pulled from the file and the lower-right corner calculated based upon the geometry
            information stored in the file.

            The polygon points start at the upper left corner and proceed clockwise around the
            boundary. The returned polygon is closed: the first and last point are the same.

            The bounds tuple contains the min and max Y point values, followed by the min and
            max X point values.
        """
        imagefiles = {}

        for onefile in files:
            ext = os.path.splitext(os.path.basename(onefile))[1].lstrip('.')
            if not ext in self.known_non_image_ext:
                if file_is_image_type(self.args.identify_binary, onefile,
                                      onefile + self.file_infodata_file_ending):
                    # If the file has a geo shape we store it for clipping
                    bounds = image_get_geobounds(onefile)
                    epsg = get_epsg(onefile)
                    if bounds[0] != np.nan:
                        ring = ogr.Geometry(ogr.wkbLinearRing)
                        ring.AddPoint(bounds[2], bounds[1])     # Upper left
                        ring.AddPoint(bounds[3], bounds[1])     # Upper right
                        ring.AddPoint(bounds[3], bounds[0])     # lower right
                        ring.AddPoint(bounds[2], bounds[0])     # lower left
                        ring.AddPoint(bounds[2], bounds[1])     # Closing the polygon

                        poly = ogr.Geometry(ogr.wkbPolygon)
                        poly.AddGeometry(ring)

                        ref_sys = osr.SpatialReference()
                        if ref_sys.ImportFromEPSG(int(epsg)) != ogr.OGRERR_NONE:
                            logging.error("Failed to import EPSG %s for image file %s",
                                          str(epsg), onefile)
                        else:
                            poly.AssignSpatialReference(ref_sys)

                        imagefiles[onefile] = {'bounds' : poly}

        # Return what we've found
        return imagefiles

    # Make a best effort to get a dataset ID
    # pylint: disable=no-self-use
    def get_dataset_id(self, host, key, resource, dataset_name=None):
        """Makes a best effort attempt to get a dataset ID

        Args:
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            resource(dict): dictionary containing the resources associated with the request
            dataset_name(str): optional parameter containing the dataset name of interest

        Return:
            The found dataset ID or None

        Note:
            The resource parameter is investigated first for a dataset ID. Note that if found,
            this dataset ID may not represent the dataset_name (if specified).

            If the resource parameter is not specified, or doesn't have the expected elements
            then a dataset lookup is performed
        """
        # First check to see if the ID is provided
        if resource and 'type' in resource:
            if resource['type'] == 'dataset':
                return resource['id']
            elif resource['type'] == 'file':
                if ('parent' in resource) and ('id' in resource['parent']):
                    return resource['parent']['id']

        # Look through all the datasets we can retrieve to find the ID
        if dataset_name:
            url = '%s/api/datasets/sorted' % (host)
            params = {"key" : key, "limit" : 50000}
            headers = {'content-type': 'application/json'}

            response = requests.get(url, headers=headers, params=params, verify=False)
            response.raise_for_status()
            datasets = response.json()

            for one_ds in datasets:
                if 'name' in one_ds and 'id' in one_ds:
                    if one_ds['name'] == dataset_name:
                        return one_ds['id']

        return None

    def write_csv_file(self, resource, filename, header, data):
        """Attempts to write out the data to the specified file. Will write the
           header information if it's the first call to write to the file.

           If the file is not available, it waits as configured until it becomes
           available, or returns an error.

           Args:
                resource(dict): dictionary containing the resources associated with the request
                filename(str): path to the file to write to
                header(str): Optional CSV formatted header to write to the file; can be set to None
                data(str): CSV formatted data to write to the file

            Return:
                Returns True if the file was written to and False otherwise
        """
        # pylint: disable=global-statement
        global MAX_CSV_FILE_OPEN_TRIES

        if not resource or not filename or not data:
            self.log_error(resource, "Empty parameter passed to write_geo_csv")
            return False

        csv_file = None
        backoff_secs = None
        for tries in range(0, MAX_CSV_FILE_OPEN_TRIES):
            try:
                csv_file = open(filename, 'w+')
            except Exception as ex:     # pylint: disable=broad-except
                pass

            # If we can't open the file, back off and try again (unless it's our last try)
            if tries < MAX_CSV_FILE_OPEN_TRIES - 1:
                backoff_secs = _get_open_backoff(backoff_secs)
                self.log_info(resource, "Sleeping for " + str(backoff_secs) + \
                                                " seconds before trying to open CSV file again")
                time.sleep(backoff_secs)

        if not csv_file:
            self.log_error(resource, "Unable to open CSV file for writing: '" + filename + "'")
            self.log_error(resource, "Exception: " + str(ex))
            return False

        wrote_file = False
        try:
            # Check if we need to write a header
            if os.fstat(csv_file.fileno()).st_size <= 0:
                csv_file.write(header)

            # Write out data
            csv_file.write(data)

            wrote_file = True
        except Exception as ex:     # pylint: disable=broad-except
            self.log_error(resource, "Exception while writing CSV file: '" + filename + "'")
            self.log_error(resource, "Exception: " + str(ex))
        finally:
            csv_file.close()

        # Return whether or not we wrote to the file
        return wrote_file

    # Entry point for checking how message should be handled
    # pylint: disable=too-many-arguments
    def check_message(self, connector, host, secret_key, resource, parameters):
        """Determines if we want to handle the received message

        Args:
            connector(obj): the message queue connector instance
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            resource(dict): dictionary containing the resources associated with the request
            parameters(json): json object of the triggering message contents
        """
        self.start_check(resource)

        if (resource['triggering_file'] is None) or (resource['triggering_file'].endswith(".tif")):
            dataset_id = None
            if resource['type'] == 'dataset':
                dataset_id = resource['id']
            elif resource['type'] == 'file':
                if ('parent' in resource) and ('id' in resource['parent']):
                    dataset_id = resource['parent']['id']
            if dataset_id:
                return CheckMessage.download

        return CheckMessage.ignore

    # Entry point for processing messages
    # pylint: disable=too-many-arguments, too-many-branches, too-many-statements, too-many-locals
    def process_message(self, connector, host, secret_key, resource, parameters):
        """Performs plot level image extraction

        Args:
            connector(obj): the message queue connector instance
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            resource(dict): dictionary containing the resources associated with the request
            parameters(json): json object of the triggering message contents
        """
        self.start_message(resource)
        super(CanopyCover, self).process_message(connector, host, secret_key, resource, parameters)

        # Handle any parameters
        if isinstance(parameters, basestring):
            parameters = json.loads(parameters)
        elif isinstance(parameters, unicode):
            parameters = json.loads(parameters.decode("utf-8", errors="replace"))

        # Initialize local variables
        dataset_name = parameters["datasetname"]
        experiment_name = "Unknown Experiment"
        datestamp = None
        citation_auth_override, citation_title_override, citation_year_override = None, None, None
        config_specie = None

        # Find the files we're interested in
        imagefiles = self.find_image_files(resource['local_paths'])
        num_image_files = len(imagefiles)
        if num_image_files <= 0:
            self.log_skip(resource, "No image files with geographic boundaries found")
            return
        if num_image_files > 1:
            self.log_info(resource, "Multiple image files were found, only using first found")
            (key, value) = imagefiles.popitem()
            imagefiles = {key : value}

        # Get the best username, password, and space
        old_un, old_pw, old_space = (self.clowder_user, self.clowder_pass, self.clowderspace)
        self.clowder_user, self.clowder_pass, self.clowderspace = self.get_clowder_context()

        # Ensure that the clowder information is valid
        if not confirm_clowder_info(host, secret_key, self.clowderspace, self.clowder_user,
                                    self.clowder_pass):
            self.log_error(resource, "Clowder configuration is invalid. Not processing " +\
                                     "request")
            self.clowder_user, self.clowder_pass, self.clowderspace = (old_un, old_pw, old_space)
            self.end_message(resource)
            return

        # Change the base path of files to include the user by tweaking the sensor's value
        sensor_old_base = None
        if self.get_terraref_metadata is None:
            _, new_base = self.get_username_with_base_path(host, secret_key, resource['id'],
                                                           self.sensors.base)
            sensor_old_base = self.sensors.base
            self.sensors.base = new_base

        try:
            # Get the best timestamp
            datestamp = self.find_datestamp(dataset_name)
            timestamp = timestamp_to_terraref(self.find_timestamp(resource['dataset_info']['name']))
            _, experiment_name, _ = self.get_season_and_experiment(timestamp, self.sensor_name)

            # Build up a list of image IDs
            image_ids = {}
            if 'files' in resource:
                for one_image in imagefiles:
                    image_name = os.path.basename(one_image)
                    for res_file in resource['files']:
                        if ('filename' in res_file) and ('id' in res_file) and \
                                                            (image_name == res_file['filename']):
                            image_ids[image_name] = res_file['id']

            if self.experiment_metadata:
                if 'extractors' in self.experiment_metadata:
                    extractor_json = self.experiment_metadata['extractors']
                    if 'canopyCover' in extractor_json:
                        if 'citationAuthor' in extractor_json['canopyCover']:
                            citation_auth_override = extractor_json['canopyCover']['citationAuthor']
                        if 'citationYear' in extractor_json['canopyCover']:
                            citation_year_override = extractor_json['canopyCover']['citationYear']
                        if 'citationTitle' in extractor_json['canopyCover']:
                            citation_title_override = extractor_json['canopyCover']['citationTitle']

                if 'germplasmName' in self.experiment_metadata:
                    config_specie = self.experiment_metadata['germplasmName']

            # Setup for the extracted plot canopy cover
            sensor_name = "canopybyshape"

            # Create the output files
            rootdir = self.sensors.create_sensor_path(timestamp, sensor=sensor_name, ext=".csv",
                                                      opts=[experiment_name])
            out_csv = os.path.splitext(rootdir)[0] + "_canopycover.csv"
            out_geo = os.path.splitext(rootdir)[0] + "_canopycover_geo.csv"

            self.log_info(resource, "Writing Shapefile CSV to %s" % out_csv)
            #csv_file = open(out_csv, 'w')
            (fields, traits) = get_traits_table()
            #csv_file.write(','.join(map(str, fields)) + '\n')

            self.log_info(resource, "Writing Geostreams CSV to %s" % out_geo)
            #geo_file = open(out_geo, 'w')
            #geo_file.write(','.join(['site', 'trait', 'lat', 'lon', 'dp_time',
            #                         'source', 'value', 'timestamp']) + '\n')

            # Setup default trait values
            if not config_specie is None:
                traits['species'] = config_specie
            if not citation_auth_override is None:
                traits['citation_author'] = citation_auth_override
            if not citation_title_override is None:
                traits['citation_title'] = citation_title_override
            if not citation_year_override is None:
                traits['citation_year'] = citation_year_override
            else:
                traits['citation_year'] = datestamp[:4]

            # Loop through all the images (of which there should be one - see above)
            for filename in imagefiles:

                try:
                    cc_val = ""

                    # Load the pixels
                    clip_pix = np.array(gdal.Open(filename).ReadAsArray())

                    # Get additional, necessary data
                    centroid = imagefiles[filename]["bounds"].Centroid()
                    plot_name = _get_plot_name([resource['dataset_info']['name'], dataset_name])

                    cc_val = calculate_canopycover_masked(np.rollaxis(clip_pix, 0, 3))

                    # Prepare the data for writing
                    image_clowder_id = ""
                    image_name = os.path.basename(filename)
                    if image_name in image_ids:
                        image_clowder_id = image_ids[image_name]

                    # Write the datapoint geographically and otherwise
                    csv_data = ','.join([plot_name,
                                         'Canopy Cover',
                                         str(centroid.GetX()),
                                         str(centroid.GetY()),
                                         timestamp,
                                         host.rstrip('/') + '/files/' + image_clowder_id,
                                         str(cc_val),
                                         datestamp])
                    csv_header = ','.join(['site', 'trait', 'lat', 'lon', 'dp_time',
                                           'source', 'value', 'timestamp'])
                    self.write_csv_file(resource, out_geo, csv_header, csv_data)
#                    geo_file.write(','.join([plot_name,
#                                             'Canopy Cover',
#                                             str(centroid.GetX()),
#                                             str(centroid.GetY()),
#                                             timestamp,
#                                             host.rstrip('/') + '/files/' + image_clowder_id,
#                                             str(cc_val),
#                                             datestamp]) + '\n')

                    traits['canopy_cover'] = str(cc_val)
                    traits['site'] = plot_name
                    traits['local_datetime'] = timestamp
                    trait_list = generate_traits_list(traits)
                    csv_data = ','.join(map(str, trait_list))
                    csv_header = ','.join(map(str, fields))
                    self.write_csv_file(resource, out_csv, csv_header, csv_data)
#                    csv_file.write(','.join(map(str, trait_list)) + '\n')

                except Exception as ex:     # pylint: disable=broad-except
                    self.log_error(resource, "error generating canopy cover for %s" % plot_name)
                    self.log_error(resource, "    exception: %s" % str(ex))
                    continue

            # All done, close the CSV files
            #csv_file.close()
            #geo_file.close()

            # Update this dataset with the extractor info
            dataset_id = self.get_dataset_id(host, secret_key, resource, dataset_name)
            try:
                # Tell Clowder this is completed so subsequent file updates don't daisy-chain
                self.log_info(resource, "updating dataset metadata")
                content = {"comment": "Calculated greenness index",
                           "greenness value": cc_val
                          }
                extractor_md = build_metadata(host, self.extractor_info, dataset_id, content,
                                              'dataset')
                clowder_dataset.remove_metadata(connector, host, secret_key, dataset_id,
                                                self.extractor_info['name'])
                clowder_dataset.upload_metadata(connector, host, secret_key, dataset_id,
                                                extractor_md)

            except Exception as ex:     # pylint: disable=broad-except
                self.log_error(resource, "Exception updating dataset metadata: " + str(ex))
        finally:
            # Signal end of processing message and restore changed variables. Be sure to restore
            # changed variables above with early returns
            if not sensor_old_base is None:
                self.sensors.base = sensor_old_base

            self.clowder_user, self.clowder_pass, self.clowderspace = (old_un, old_pw, old_space)
            self.end_message(resource)

if __name__ == "__main__":
    # pylint: disable=invalid-name
    extractor = CanopyCover()
    extractor.start()
