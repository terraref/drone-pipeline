#!/usr/bin/env python

'''Extractor for calculating canopy cover by plot plots via a shapefile
'''

import os
import json
import datetime
import subprocess
import requests

from osgeo import gdal, ogr
from numpy import nan, rollaxis
from dbfread import DBF

import pyclowder.datasets as clowder_dataset
from pyclowder.utils import CheckMessage

from terrautils.extractors import build_metadata, file_exists, upload_to_dataset, load_json_file
from terrautils.sensors import STATIONS
from terrautils.spatial import clip_raster

from pipelineutils.extractors import PipelineExtractor
from pipelineutils.metadata import season_experiment_timestamp_from_metadata, \
     pipeline_get_season_experiment_timestamp

import terraref.stereo_rgb

# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'canopybyshape' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['canopybyshape'] = {'template': '{base}/{station}/Level_2/' + \
                                                           '{sensor}/{date}/{filename}',
                                               'pattern': '{sensor}_L2_{station}_{date}{opts}.tif'
                                              }

# TODO: Make this generic
def get_traits_table():
    """Returns the field names and default trait values

    Returns:
        A tuple containing the list of field names and a dictionary of default field values
    """
    # Compiled traits table
    fields = ('local_datetime', 'canopy_cover', 'access_level', 'species', 'site',
              'citation_author', 'citation_year', 'citation_title', 'method')
    traits = {'local_datetime' : '',
              'canopy_cover' : [],
              'access_level': '2',
              'species': 'Unknown',
              'site': [],
              'citation_author': '"Zongyang, Li"',
              'citation_year': '2016',
              'citation_title': 'Maricopa Field Station Data and Metadata',
              'method': 'Canopy Cover Estimation from drone captured RGB images'}

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
    trait_list = [traits['local_datetime'],
                  traits['canopy_cover'],
                  traits['access_level'],
                  traits['species'],
                  traits['site'],
                  traits['citation_author'],
                  traits['citation_year'],
                  traits['citation_title'],
                  traits['method']
                 ]

    return trait_list

# The class for determining canopy cover from shapefile
class CanopyCover(PipelineExtractor):
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
        experiment_filename = os.getenv('EXPERIMENT_FILENAME', 'experiment.json')

        # Add any additional arguments to parser
        self.parser.add_argument('--identify-binary', nargs='?', dest='identify_binary',
                                 default=identify_binary,
                                 help='Identify executable used to for image type capture ' +
                                 '(default=' + identify_binary + ')')

        self.parser.add_argument('--experiment_json_file', nargs='?', dest='experiment_json_file',
                                 default=experiment_filename,
                                 help='Default name of experiment configuration file used to' \
                                      ' provide additional processing information')

        # parse command line and load default logging configuration
        self.setup(sensor='canopyCover')

    @property
    def config_file_name(self):
        """Returns the name of the expected configuration file
        """
        # pylint: disable=line-too-long
        return 'experiment.json' if not self.args.experiment_json_file else self.args.experiment_json_file
        # pylint: enable=line-too-long

    @property
    def dataset_metadata_file_ending(self):
        """ Returns the ending string of a dataset metadata JSON file name
        """
        return '_dataset_metadata.json'

    @property
    def file_infodata_file_ending(self):
        """ Returns the ending string of a file's info JSON file name
        """
        return '_info.json'

    # List of file extensions we will probably see that we don't need to check for being
    # an image type
    @property
    def known_non_image_ext(self):
        """Returns an array of file extensions that we will see that
           are definitely not an image type
        """
        return ["dbf", "json", "prj", "shp", "shx", "txt"]

    # Returns if the mime type of 'image' is found in the text passed in. A reasonable effort is
    # made to identify the section containing the type by looking for the phrase 'Mime', or 'mime',
    # or 'MIME' and using that as the basis for determining the type
    # pylint: disable=no-self-use
    def find_image_mime_type(self, text):
        """Looks for a mime image type in the text passed in.

           It's expected that the mime label may be something other than the string 'Mime type' so
           a proximity search is made for the mime type label followed by 'image/'. If found, True
           is returned and False otherwise

        Args:
            text(str): The text in which to find a MIME type of 'image'

        Returns:
            None is returned if the string is empty or the MIME keyword is not found.
            False is returned if a MIME type of 'image' isn't found
            True is returned upon success
        """
        if not text:
            return None

        # Try to find the beginning and end of the mime type (but not the subtype)
        pos = text.find('Mime')
        if pos < 0:
            pos = text.find('mime')
        if pos < 0:
            pos = text.find('MIME')
        if pos < 0:
            return None

        end_pos = text.find('/', pos)
        if end_pos < 0:
            return False

        # Get the portion of the string containing the possible mime type making sure we have
        # something reasonable
        mime = text[pos : end_pos]
        mime_len = len(mime)
        if (mime_len > 50) or (mime.find('\n') >= 0) or (mime.find('\r') >= 0):
            return False

        # Look for a 'reasonable' image mime type
        if mime.endswith('image'):
            return True

        return False

    # Determines if the file is an image type
    def file_is_image_type(self, resource, filename):
        """Uses the identify application to generate the MIME type of the file and
           looks for an image MIME type

        Args:
            resource(dict): dictionary containing the resources associated with the request
            filename(str): the path to the file to check

        Returns:
            True is returned if the file is a MIME image type
            False is returned upon failure or the file is not a type of image
        """
        # Try to determine the file type from its JSON information (metadata if from Clowder API)
        try:
            infodata_name = filename +  self.file_infodata_file_ending
            if file_exists(infodata_name):
                file_md = load_json_file(infodata_name)
                if file_md:
                    if 'contentType' in file_md:
                        if file_md['contentType'].startswith('image'):
                            return True
        # pylint: disable=broad-except
        except Exception as ex:
            self.log_info(resource, "Exception caught: " + str(ex))
        # pylint: enable=broad-except

        # Try to determine the file type locally
        try:
            is_image_type = self.find_image_mime_type(
                subprocess.check_output(
                    [self.args.identify_binary, "-verbose", filename], stderr=subprocess.STDOUT))

            if not is_image_type is None:
                return is_image_type
        # pylint: disable=broad-except
        except Exception as ex:
            self.log_info(resource, "Exception caught: " + str(ex))
        # pylint: enable=broad-except

        return False

    # Checks if the file has geometry associated with it and returns the bounds
    # pylint: disable=no-self-use
    def image_get_geobounds(self, resource, filename):
        """Uses gdal functionality to retrieve recilinear boundaries

        Args:
            resource(dict): dictionary containing the resources associated with the request
            filename(str): path of the file to get the boundaries from

        Returns:
            The upper-left and calculated lower-right boundaries of the image in a list upon success
            A list of nan is returned if the boundaries can't be determined
        """
        try:
            # TODO: handle non-ortho images
            src = gdal.Open(filename)
            ulx, xres, _, uly, _, yres = src.GetGeoTransform()
            lrx = ulx + (src.RasterXSize * xres)
            lry = uly + (src.RasterYSize * yres)

            return [ulx, uly, lrx, lry]
        # pylint: disable=broad-except
        except Exception as ex:
            self.log_info(resource, "Exception caught: " + str(ex))
        # pylint: enable=broad-except

        return [nan, nan, nan, nan]

    # Get the tuple from the passed in polygon
    def polygon_to_tuples(self, polygon):
        """Convert polygon passed in to
            ( lat (y) min, lat (y) max,
              long (x) min, long (x) max) for geotiff creation

        Args:
            polygon(object) - OGR Polygon (type ogr.wkbPolygon)

        Return:
            A tuple of  (min Y, max Y, min X, max X)
        """
        min_x, min_y, max_x, max_y = None, None, None, None
        try:
            if polygon.GetGeometryType() == ogr.wkbPolygon:
                ring = polygon.GetGeometryRef(0)
                point_count = ring.GetPointCount()
                for point_idx in xrange(point_count):
                    pt_x, pt_y, _ = ring.GetPoint(point_idx)
                    if min_x is None or pt_x < min_x:
                        min_x = pt_x
                    if max_x is None or pt_x > max_x:
                        max_x = pt_x
                    if min_y is None or pt_y < min_y:
                        min_y = pt_y
                    if max_y is None or pt_y > max_y:
                        max_y = pt_y
        # pylint: disable=broad-except
        except Exception as ex:
            self.logger.warn("[polygon_to_tuples] Exception: %s", str(ex))
        # pylint: enable=broad-except

        return (min_y, max_y, min_x, max_x)

    # Look through the file list to find the files we need
    # pylint: disable=no-self-use
    def find_needed_files(self, resource, files, triggering_file):
        """Finds files that are needed for extracting plots from an orthomosaic

        Args:
            resource(dict): dictionary containing the resources associated with the request
            files(list): the list of file to look through and access
            triggering_file(str): optional parameter specifying the file that triggered the
            extraction

        Returns:
            Returns a list containing the shapefile name, its optional associated DBF file,
            and a dict of georeferenced image files (indexed by filename and containing an
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
        # pylint: enable=no-self-use
        shapefile, dbffile = None, None
        imagefiles = {}

        for onefile in files:
            if onefile.endswith(".shp") and shapefile is None:
                shapefile = onefile
                # If we saw a DBF file first we want to make sure it matches the shapefile
                if dbffile:
                    filename_test = os.path.splitext(os.path.basename(dbffile))[0] + ".shp"
                    if not shapefile.endswith(filename_test):
                        # The pre-found dbf file is not a match for the shapefile
                        dbffile = None
            elif onefile.endswith(".dbf"):
                # Create the equivelent name of the shapefile and see if we're a match
                filename_test = os.path.splitext(os.path.basename(onefile))[0] + ".shp"
                # If we haven't seen a shape file, or we're the same name, then we have what we want
                # pylint: disable=line-too-long
                if (not shapefile is None and shapefile.endswith(filename_test)) or (triggering_file is None) or (triggering_file.endswith(filename_test)):
                    dbffile = onefile
                # pylint: enable=line-too-long
            else:
                ext = os.path.splitext(os.path.basename(onefile))[1].lstrip('.')
                if not ext in self.known_non_image_ext:
                    # We either have the triggering TIF file or we look for image files
                    # pylint: disable=line-too-long
                    if ((not triggering_file is None) and triggering_file.endswith(os.path.basename(onefile))) or \
                        ((triggering_file is None) and (self.file_is_image_type(resource, onefile))):
                        # If the file has a geo shape we store it for clipping
                        bounds = self.image_get_geobounds(resource, onefile)
                        if bounds[0] != nan:
                            ring = ogr.Geometry(ogr.wkbLinearRing)
                            ring.AddPoint(bounds[0], bounds[1])     # Upper left
                            ring.AddPoint(bounds[2], bounds[1])     # Upper right
                            ring.AddPoint(bounds[2], bounds[3])     # lower right
                            ring.AddPoint(bounds[0], bounds[3])     # lower left
                            ring.AddPoint(bounds[0], bounds[1])     # Closing the polygon

                            poly = ogr.Geometry(ogr.wkbPolygon)
                            poly.AddGeometry(ring)

                            bounds_tuple = self.polygon_to_tuples(poly)

                            # pylint: disable=line-too-long
                            imagefiles[onefile] = {'bounds' : poly,
                                                   'bounding_tuples' : bounds_tuple
                                                  }
                            # pylint: enable=line-too-long
                    # pylint: enable=line-too-long

        # Return what we've found
        return (shapefile, dbffile, imagefiles)

    # Find pipeline JSON and essential fields
    # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
    def find_pipeline_json(self, resource, files, default_season_name, default_experiment_name,
                           default_timestamp):
        """Attempts to find the file containing the pipeline JSON and load it

        Args:
            resource(dict): dictionary containing the resources associated with the request
            files(list): list of available file paths to look through
            default_season_name(str): value to return for season if JSON not found, or season not
                                      configured
            default_experiment_name(str): value to return for experiment if JSON not found, or
                                          experiment not configured
            default_timestamp(str): value to return for timestamp if JSON not found, or timestamp
                                    not configured

        Returns:
            A list containing the season name, experiment name, timestamp, and JSON is returned.
            The first three may be the default values passed in if a JSON file wasn't found, of
            the fields weren't specified or were invalid. The JSON return value may be None if a
            configuration file wasn't found or pipeline parameters weren't specified. The JSON
            return will also be None if the Terra Ref metadata in the dataset is used to
            determine the values.

        Note:
            A configuration file will override any parameters set in a dataset's metadata
        """
        # Initialize our return variables
        # pylint: disable=line-too-long
        (ret_season, ret_experiment, ret_timestamp) = (default_season_name, default_experiment_name, default_timestamp)
        # pylint: enable=line-too-long
        ret_json = None

        # Find the JSON files
        config_file = None
        dataset_file = None
        target_config_file = self.config_file_name
        target_dataset_file = self.dataset_metadata_file_ending
        for onefile in files:
            if onefile.endswith(target_config_file):
                config_file = onefile
            elif onefile.endswith(target_dataset_file):
                dataset_file = onefile
            if (not config_file is None) and (not dataset_file is None):
                break

        # See if we can find the information we need in the dataset metadata
        if not dataset_file is None:
            # pylint: disable=line-too-long
            (ret_season, ret_experiment, ret_timestamp, ret_json) = season_experiment_timestamp_from_metadata(dataset_file,
                                                                                                              ret_season,
                                                                                                              ret_experiment,
                                                                                                              ret_timestamp,
                                                                                                              resource['dataset_info']['name'])
            # pylint: enable=line-too-long

        # Load the settings JSON file if we found it
        if config_file:
            try:
                ret_json = load_json_file(config_file)

                if 'pipeline' in ret_json:
                    ret_json = ret_json['pipeline']
                else:
                    ret_json = None
            # pylint: disable=broad-except
            except Exception as ex:
                self.log_info(resource, "Exception caught: " + str(ex))
                ret_json = None
            # pylint: enable=broad-except

            # Set variables to return based upon JSON content
            if not ret_json is None:
                # pylint: disable=line-too-long
                (pl_season, pl_experiment, pl_timestamp) = pipeline_get_season_experiment_timestamp(ret_json)
                # pylint: enable=line-too-long
                if not pl_season is None:
                    ret_season = pl_season
                if not pl_experiment is None:
                    ret_experiment = pl_experiment
                if not pl_timestamp is None:
                    ret_timestamp = pl_timestamp

        return (ret_season, ret_experiment, ret_timestamp, ret_json)

    # Make a best effort to get a dataset ID
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
                files = clowder_dataset.get_file_list(connector, host, secret_key, dataset_id)
                have_shapefile = False
                for one_file in files:
                    if one_file['filename'].endswith('.shp'):
                        have_shapefile = True
                        break
                if have_shapefile is True:
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

        # Handle any parameters
        if isinstance(parameters, basestring):
            parameters = json.loads(parameters)
        if isinstance(parameters, unicode):
            parameters = json.loads(str(parameters))

        # Initialize local variables
        dataset_name = parameters["datasetname"]
        season_name, experiment_name = "Unknown Season", "Unknown Experiment"
        datestamp, shape_table, plot_name_idx, shape_rows = None, None, None, None
        config_specie = None

        # Change the base path of files to include the user by tweaking the sensor's value
        _, new_base = self.get_username_with_base_path(host, secret_key, dataset_name,
                                                       self.sensors.base)
        sensor_old_base = self.sensors.base
        self.sensors.base = new_base

        # Find the files we're interested in
        (shapefile, dbffile, imagefiles) = self.find_needed_files(resource,
                                                                  resource['local_paths'],
                                                                  resource['triggering_file'])
        if shapefile is None:
            self.log_skip(resource, "No shapefile found")
            return
        num_image_files = len(imagefiles)
        if num_image_files <= 0:
            self.log_skip(resource, "No image files with geographic boundaries found")
            return
        if num_image_files > 1:
            self.log_info(resource, "Multiple image files were found, only using first found")
            (key, value) = imagefiles.popitem()
            imagefiles = {key : value}

        # Build up a list of image IDs
        image_ids = {}
        if 'files' in resource:
            for one_image in imagefiles:
                image_name = os.path.basename(one_image)
                for res_file in resource['files']:
                    # pylint: disable=line-too-long
                    if ('filename' in res_file) and ('id' in res_file) and (image_name == res_file['filename']):
                    # pylint: enable=line-too-long
                        image_ids[image_name] = res_file['id']

        # Find pipeline JSON and essential fields
        # pylint: disable=line-too-long
        (season_name, experiment_name, datestamp, config_json) = self.find_pipeline_json(resource,
                                                                                         resource['local_paths'],
                                                                                         season_name,
                                                                                         experiment_name,
                                                                                         None)
        # pylint: enable=line-too-long

        if config_json:
            if 'extractors' in config_json:
                extractor_json = config_json['extractors']
                if 'plot_column_name' in extractor_json:
                    plot_name_idx = extractor_json['plot_column_name']
            if 'germplasmSpecies' in config_json:
                config_specie = config_json['germplasmSpecies']

        # If we don't have a valid date from the user yet, check the dataset name for one
        if not datestamp is None:
            try:
                datestamp = self.get_datestamp(datestamp)
            # pylint: disable=broad-except
            except Exception:
                datestamp = None
        if datestamp is None:
            try:
                datestamp = self.get_datestamp(dataset_name)
            # pylint: disable=broad-except
            except Exception:
                datestamp = None
        # Still no datestamp, use today's date
        if datestamp is None:
            datestamp = datetime.datetime.today().strftime('%Y-%m-%d')

        # Check our current local variables
        if dbffile is None:
            self.log_info(resource, "DBF file not found, using default plot naming")
        self.log_info(resource, "Extracting plots using shapefile '" + os.path.basename(shapefile) +
                      "'")

        # Load the shapes and find the plot name column if we have a DBF file
        shape_in = ogr.Open(shapefile)
        layer = shape_in.GetLayer(os.path.split(os.path.splitext(shapefile)[0])[1])
        feature = layer.GetNextFeature()

        if dbffile:
            shape_table = DBF(dbffile, lowernames=True, ignore_missing_memofile=True)
            shape_rows = iter(list(shape_table))

            # Make sure if we have the column name of plot-names specified that it exists in
            # the shapefile
            column_names = shape_table.field_names
            if (not plot_name_idx is None) and (not plot_name_idx in column_names):
                ValueError(resource, "Shapefile data does not have specified plot name" +
                           " column '" + plot_name_idx + "'")

            # Lookup a plot name field to use
            if plot_name_idx is None:
                for one_name in column_names:
                    # pylint: disable=line-too-long
                    if one_name == "observationUnitName":
                        plot_name_idx = one_name
                        break
                    elif (one_name.find('plot') >= 0) and ((one_name.find('name') >= 0) or one_name.find('id')):
                        plot_name_idx = one_name
                        break
                    elif one_name == 'id':
                        plot_name_idx = one_name
                        break
                    # pylint: enable=line-too-long
            if plot_name_idx is None:
                ValueError(resource, "Shapefile data does not have a plot name field '" +
                           os.path.basename(dbffile) + "'")

        # Setup for the extracted plot canopy cover
        sensor_name = "canopybyshape"

        # Create the output files
        base_name = imagefiles.keys()[0]
        rootdir = self.sensors.create_sensor_path(datestamp, sensor=sensor_name, ext=".csv")
        out_csv = os.path.join(os.path.dirname(rootdir),
                               base_name.replace(".tif", "_canopycover_shapefile.csv"))
        out_geo = os.path.join(os.path.dirname(rootdir),
                               base_name.replace(".tif", "_canopycover_geo.csv"))

        self.log_info(resource, "Writing Shapefile CSV to %s" % out_csv)
        csv_file = open(out_csv, 'w')
        (fields, traits) = get_traits_table()
        if not config_specie is None:
            traits['species'] = config_specie
        traits['citation_year'] = datestamp[:4]
        csv_file.write(','.join(map(str, fields)) + '\n')

        self.log_info(resource, "Writing Geostreams CSV to %s" % out_geo)
        geo_file = open(out_geo, 'w')
        geo_file.write(','.join(['site', 'trait', 'lat', 'lon', 'dp_time',
                                 'source', 'value', 'timestamp']) + '\n')

        # Prepare some CSV data
        full_timestamp = datestamp + "T12:00:00-07:00"

        # Loop through each polygon and extract plot level data
        alternate_plot_id = 0
        while feature:

            # Current geometry to extract
            plot_poly = feature.GetGeometryRef()

            # Determie the plot name to use
            plot_name = None
            alternate_plot_id = alternate_plot_id + 1
            if shape_rows and plot_name_idx:
                try:
                    row = next(shape_rows)
                    plot_name = str(row[plot_name_idx])
                except StopIteration:
                    pass
            if not plot_name:
                plot_name = "plot_" + str(alternate_plot_id)

            # Loop through all the images looking for overlap
            for filename in imagefiles:

                # Checking for geographic overlap and skip if there is none
                bounds = imagefiles[filename]['bounds']
                intersection = plot_poly.Intersection(bounds)

                if intersection.GetArea() == 0.0:
                    self.log_info(resource, "Skipping image: "+filename)
                    continue

                self.log_info(resource, "Attempting to clip '" + filename + "' to polygon number " +
                              str(alternate_plot_id))

                # Clip the raster
                bounds_tuple = self.polygon_to_tuples(plot_poly)

                try:
                    cc_val = "NA"

                    clip_pix = clip_raster(filename, bounds_tuple)
                    if clip_pix is None:
                        self.log_error(resource, "Failed to clip image to plot name " + plot_name)
                        continue
                    if len(clip_pix.shape) < 3:
                        self.log_error(resource,
                                       "Unexpected array shape for %s (%s)" % \
                                                                    (plot_name, clip_pix.shape))
                        continue

                    cc_val = terraref.stereo_rgb.calculate_canopycover(rollaxis(clip_pix, 0, 3))

                    # Prepare the data for writing
                    image_clowder_id = ""
                    if filename in image_ids:
                        image_clowder_id = image_ids[filename]
                    centroid = plot_poly.Centroid()

                    # Write the datapoint geographically and otherwise
                    geo_file.write(','.join([plot_name,
                                             'Canopy Cover',
                                             str(centroid.GetX()),
                                             str(centroid.GetY()),
                                             full_timestamp,
                                             host.rstrip('/') + '/files/' + image_clowder_id,
                                             str(cc_val),
                                             datestamp]) + '\n')

                    traits['canopy_cover'] = str(cc_val)
                    traits['site'] = plot_name
                    traits['local_datetime'] = full_timestamp
                    trait_list = generate_traits_list(traits)
                    csv_file.write(','.join(map(str, trait_list)) + '\n')

                # pylint: disable=broad-except
                except Exception as ex:
                    self.log_error(resource, "error generating canopy cover for %s" % plot_name)
                    self.log_error(resource, "    exception: %s" % str(ex))
                    continue
                # pylint: enable=broad-except

            # Get the next shape to extract
            feature = layer.GetNextFeature()

        # All done, close the CSV files
        csv_file.close()
        geo_file.close()

        # Upload this CSV to Clowder
        dataset_id = self.get_dataset_id(host, secret_key, resource, dataset_name)
        try:
            fileid = upload_to_dataset(connector, host, self.clowder_user, self.clowder_pass,
                                       dataset_id, out_csv)
            geoid = upload_to_dataset(connector, host, self.clowder_user, self.clowder_pass,
                                      dataset_id, out_geo)

            # Tell Clowder this is completed so subsequent file updates don't daisy-chain
            self.log_info(resource, "updating dataset metadata")
            content = {"comment": "Calculated from shapefile '" + os.path.basename(shapefile) + "'",
                       "files_created": [fileid, geoid]
                      }
            extractor_md = build_metadata(host, self.extractor_info, dataset_id, content, 'file')
            clowder_dataset.remove_metadata(connector, host, secret_key, dataset_id,
                                            self.extractor_info['name'])
            clowder_dataset.upload_metadata(connector, host, secret_key, dataset_id, extractor_md)
        # pylint: disable=broad-except
        except Exception as ex:
            self.log_error(resource, "Exception updating dataset metadata: " + str(ex))
        # pylint: enable=broad-except

        # Signal end of processing message and restore changed variables
        self.sensors.base = sensor_old_base
        self.end_message(resource)

if __name__ == "__main__":
    # pylint: disable=invalid-name
    extractor = CanopyCover()
    extractor.start()
