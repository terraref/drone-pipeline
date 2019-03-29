#!/usr/bin/env python

'''Extractor for clipping images to plots via a shapefile
'''

import os
import json
import logging
import datetime
import subprocess

from osgeo import gdal, ogr
from numpy import nan
from dbfread import DBF

from pyclowder.utils import CheckMessage
from pyclowder.files import upload_to_dataset
from pyclowder.datasets import upload_metadata, remove_metadata
from terrautils.extractors import build_metadata, build_dataset_hierarchy_crawl, file_exists, \
     check_file_in_dataset, load_json_file
from terrautils.sensors import STATIONS
from terrautils.spatial import clip_raster
from pipelineutils.extractors import PipelineExtractor
from pipelineutils.metadata import season_experiment_timestamp_from_metadata, \
     pipeline_get_season_experiment_timestamp


# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'clipbyshape' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['clipbyshape'] = {'display': 'Plot Clipper',
                                             'template': '{base}/{station}/Level_2_Plots/' + \
                                                         '{sensor}/{date}/{timestamp}/{filename}'
                                            }

# The class for clipping images by shape
class ClipByShape(PipelineExtractor):
    """Extractor for clipping georeferenced images to plot boundaries via a shape file

       The extractor creates datasets of images for each plot and uploads them to Clowder
    """
    def __init__(self):
        """Initialization of class instance.

           We use the identify application to identify the mime type of files and then
           determine if they are georeferenced using the osgeo package
        """
        super(ClipByShape, self).__init__()

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
        self.setup(sensor='clipbyshape')

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
        if mime.endwith('image'):
            return True

        return False

    # Determines if the file is an image type
    def file_is_image_type(self, filename):
        """Uses the identify application to generate the MIME type of the file and
           looks for an image MIME type

        Args:
            filename(str): the path to the file to check

        Returns:
            True is returned if the file is a MIME image type
            False is returned upon failure or the file is not a type of image
        """
        # Try to determine the file type locally
        try:
            is_image_type = self.find_image_mime_type(
                subprocess.check_output(
                    [self.args.image_binary, "-verbose", filename], stderr=subprocess.STDOUT))

            if not is_image_type is None:
                return is_image_type
        # pylint: disable=broad-except
        except Exception:
            pass
        # pylint: enable=broad-except

        return False

    # Checks if the file has geometry associated with it and returns the bounds
    # pylint: disable=no-self-use
    def image_get_geobounds(self, filename):
        """Uses gdal functionality to retrieve recilinear boundaries

        Args:
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
        except Exception:
            pass

        return [nan, nan, nan, nan]

    # Look through the file list to find the files we need
    # pylint: disable=no-self-use
    def find_needed_files(self, files, triggering_file=None):
        """Finds files that are needed for extracting plots from an orthomosaic

        Args:
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
        imagefiles = []

        for onefile in files:
            if onefile.endswith(".shp"):
                # We give priority to the shapefile that triggered the extraction over any other
                # shapefiles that may exist
                if triggering_file is None or triggering_file.endswith(onefile):
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
            elif self.file_is_image_type(onefile):
                # If the file has a geo shape we store it for clipping
                bounds = self.image_get_geobounds(onefile)
                if bounds[0] != nan:
                    ring = ogr.Geometry(ogr.wkbLinearRing)
                    ring.AddPoint(bounds[0], bounds[1])     # Upper left
                    ring.AddPoint(bounds[2], bounds[1])     # Upper right
                    ring.AddPoint(bounds[2], bounds[3])     # lower right
                    ring.AddPoint(bounds[0], bounds[3])     # lower left
                    ring.AddPoint(bounds[0], bounds[1])     # Closing the polygon

                    poly = ogr.Geometry(ogr.wkbPolygon)
                    poly.AddGeometry(ring)

                    # pylint: disable=line-too-long
                    imagefiles[onefile] = {'bounds' : poly,
                                           'bounding_tuples' : (bounds[1], bounds[3], bounds[0], bounds[2]) # Ymin, Ymax, Xmin, Xmax
                                          }
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
            except Exception:
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
        if resource['triggering_file'] is None or resource['triggering_file'].endswith(".shp"):
            logging.debug("Shapefile file uploaded")
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

        # Array containing the links to uploaded files
        uploaded_file_ids = []

        # Find the files we're interested in
        (shapefile, dbffile, imagefiles) = self.find_needed_files(resource['local_paths'],
                                                                  resource['triggering_file'])
        if shapefile is None:
            self.log_skip(resource, "No shapefile found")
            return
        num_image_files = len(imagefiles)
        if num_image_files <= 0:
            self.log_skip(resource, "No image files with geographic boundaries found")
            return

        # Find pipeline JSON and essential fields
        # pylint: disable=line-too-long
        (season_name, experiment_name, datestamp, config_json) = self.find_pipeline_json(resource,
                                                                                         resource['local_paths'],
                                                                                         season_name,
                                                                                         experiment_name,
                                                                                         None)
        # pylint: enable=line-too-long

        if 'extractors' in config_json:
            extractor_json = config_json['extractors']
            if 'plot_column_name' in extractor_json:
                plot_name_idx = extractor_json['plot_column_name']

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

        # Check our current status
        if dbffile is None:
            self.log_info(resource, "DBF file not found, using default plot naming")
        self.log_info(resource, "Extracting plots using shapefile '" + os.path.basename(shapefile) +
                      "'")

        # Load the shapes and find the plot name column if we have a DBF file
        shape_in = ogr.Open(shapefile)
        layer = shape_in.GetLayer(os.path.split(os.path.splitext(shapefile)[0])[1])
        poly = layer.GetNextFeature()

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

        # Setup for the extracted plot images
        sensor_name = "rgb_geotiff"
        plot_display_name = self.sensors.get_display_name(sensor=sensor_name) + " (By Plot)"

        # Loop through each polygon and extract plot level data
        alternate_plot_id = 0
        while poly:

            # Determie the plot name to use
            plot_name = None
            alternate_plot_id = alternate_plot_id + 1
            if shape_rows and plot_name_idx:
                try:
                    row = next(shape_rows)
                    plot_name = row[plot_name_idx]
                except StopIteration:
                    pass
            if not plot_name:
                plot_name = "plot_" + str(alternate_plot_id)

            # Determine output dataset name
            leaf_dataset = plot_display_name + ' - ' + plot_name + " - " + datestamp.split("__")[0]
            self.log_info(resource, "Hierarchy: %s / %s / %s / %s / %s / %s / %s" %
                          (season_name, experiment_name, plot_display_name,
                           datestamp[:4], datestamp[5:7], datestamp[8:10], leaf_dataset))

            # Create the dataset, even if we have no data to put in it, so that the caller knows
            # it was addressed
            target_dsid = build_dataset_hierarchy_crawl(host, secret_key,
                                                        self.clowder_user,
                                                        self.clowder_pass,
                                                        self.clowderspace,
                                                        season_name,
                                                        experiment_name,
                                                        plot_display_name,
                                                        datestamp[:4],
                                                        datestamp[5:7],
                                                        datestamp[8:10],
                                                        leaf_ds_name=leaf_dataset)

            # Loop through all the images looking for overlap
            for filename in imagefiles:

                # Checking for geographic overlap and skip if there is none
                bounds = imagefiles[filename]['bounds']
                intersection = poly.Intersection(bounds)
                if intersection.GetArea() <= 0:
                    continue

                # Determine where we're putting the clipped file on disk and determine overwrite
                # pylint: disable=unexpected-keyword-arg
                out_file = self.sensors.create_sensor_path(datestamp, filename=filename,
                                                           plot=plot_name, subsensor=sensor_name)
                if (file_exists(out_file) and not self.overwrite):
                    # The file exists and don't want to overwrite it
                    continue

                self.log_info(resource, "Attempting to clip '" + filename + "' to polygon number " +
                              str(alternate_plot_id))

                # Create destination folder on disk if we haven't done that already
                if not os.path.exists(os.path.dirname(out_file)):
                    os.makedirs(os.path.dirname(out_file))

                # Clip the raster
                clip_raster(filename, imagefiles[filename]['bounding_tuples'], out_path=out_file)

                # Upload the clipped image to the dataset
                found_in_dest = check_file_in_dataset(connector, host, secret_key, target_dsid,
                                                      out_file, remove=self.overwrite)
                if not found_in_dest or self.overwrite:
                    fileid = upload_to_dataset(connector, host, secret_key, target_dsid, out_file)
                    uploaded_file_ids.append(host + ("" if host.endswith("/") else "/") +
                                             "files/" + fileid)

                self.created += 1
                self.bytes += os.path.getsize(out_file)

            # Get the next shape to extract
            poly = layer.GetNextFeature()

        # Tell Clowder this is completed so subsequent file updates don't daisy-chain
        extractor_md = build_metadata(host, self.extractor_info, resource['id'], {
            "files_created": uploaded_file_ids
        }, 'dataset')
        self.log_info(resource, "Uploading shapefile plot extractor metadata to Level_2 dataset")
        remove_metadata(connector, host, secret_key, resource['id'], self.extractor_info['name'])
        upload_metadata(connector, host, secret_key, resource['id'], extractor_md)

        self.end_message(resource)

if __name__ == "__main__":
    # pylint: disable=invalid-name
    extractor = ClipByShape()
    extractor.start()
