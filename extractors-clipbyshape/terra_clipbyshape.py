#!/usr/bin/env python

'''Extractor for clipping images to plots via a shapefile
'''

import os
import json
import logging
import osr
import unicodedata

from osgeo import ogr
from numpy import nan
from dbfread import DBF

import pyclowder.datasets as clowder_dataset
import pyclowder.files as clowder_file
from pyclowder.utils import CheckMessage

from terrautils.extractors import TerrarefExtractor, build_metadata, confirm_clowder_info, \
     build_dataset_hierarchy_crawl, file_exists, upload_to_dataset, check_file_in_dataset, \
     timestamp_to_terraref
from terrautils.sensors import STATIONS
from terrautils.spatial import clip_raster
from terrautils.imagefile import file_is_image_type, image_get_geobounds, \
     polygon_to_tuples_transform, get_epsg

# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'clipbyshape' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['clipbyshape'] = {'display': 'Shapefile Plot Clipper',
                                             'template': '{base}/{station}/Level_2_Plots/' + \
                                                         '{sensor}/{date}/{timestamp}/{plot}/{filename}'
                                            }

def find_all_plot_names(plot_name, column_names):
    """Returns whether or not all the plot names are found in
       the list of column names.
    Args:
        plot_name(str or list): the plot column name to look for, or an array of plot column names
        column_names(list): a list of names to look through for matches
    Return:
        Returns True if the plot names are all found in the column names list
    """
    if not plot_name:
        return False

    found_all = True
    if isinstance(plot_name, list):
        for one_idx in plot_name:
            if not one_idx in column_names:
                found_all = False
                break
    elif not plot_name in column_names:
        found_all = False
    else:
        found_all = False

    return found_all

def get_plot_name(name_idx, data):
    """Returns the plot name taken from the data parameter
    Args:
        name_idx(str or list): the plot column name to look for, or an array of plot names
        data(obj): index-able object containing the values that make up the plot name
    Return:
        Returns the found plot name or None if not found
    Note:
        If the plot name consists of more than one index, the values are concatenated
        to make up the returned plot name. Indexes that are missing in the data are
        ignored. If the data doesn't contain any of the indexes, None is returned
    """
    plot_name = ""

    if isinstance(name_idx, list):
        for idx in name_idx:
            if idx in data:
                plot_name += str(data[idx]) + "_"
        plot_name = plot_name.rstrip("_")
    elif name_idx in data:
        plot_name = str(data[name_idx])

    if plot_name == "":
        plot_name = None

    return plot_name

# The class for clipping images by shape
class ClipByShape(TerrarefExtractor):
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

        # Add any additional arguments to parser
        self.parser.add_argument('--identify-binary', nargs='?', dest='identify_binary',
                                 default=identify_binary,
                                 help='Identify executable used to for image type capture ' +
                                 '(default=' + identify_binary + ')')

        # parse command line and load default logging configuration
        self.setup(sensor='clipbyshape')

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
    def find_shape_image_files(self, files, triggering_file):
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
        shapefile, shxfile, dbffile = None, None, None
        imagefiles = {}

        for onefile in files:
            if onefile.endswith(".shp") and shapefile is None:
                # We give priority to the shapefile that triggered the extraction over any other
                # shapefiles that may exist
                if triggering_file is None or triggering_file.endswith(onefile):
                    shapefile = onefile

                    filename_test = os.path.splitext(shapefile)[0] + ".shx"
                    if os.path.isfile(filename_test):
                        shxfile = filename_test

                    filename_test = os.path.splitext(shapefile)[0] + ".dbf"
                    if os.path.isfile(filename_test):
                        dbffile = filename_test
            else:
                ext = os.path.splitext(os.path.basename(onefile))[1].lstrip('.')
                if not ext in self.known_non_image_ext:
                    if file_is_image_type(self.args.identify_binary, onefile,
                                          onefile + self.file_infodata_file_ending):
                        # If the file has a geo shape we store it for clipping
                        bounds = image_get_geobounds(onefile)
                        epsg = get_epsg(onefile)
                        if bounds[0] != nan:
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
        return (shapefile, shxfile, dbffile, imagefiles)

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
        super(ClipByShape, self).process_message(connector, host, secret_key, resource,
                                                 parameters)

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
        # pylint: disable=line-too-long
        (shapefile, shxfile, dbffile, imagefiles) = self.find_shape_image_files(resource['local_paths'],
                                                                                resource['triggering_file'])
        # pylint: enable=line-too-long
        if shapefile is None:
            self.log_skip(resource, "No shapefile found")
            return
        if shxfile is None:
            self.log_skip(resource, "No SHX file found")
            return
        num_image_files = len(imagefiles)
        if num_image_files <= 0:
            self.log_skip(resource, "No image files with geographic boundaries found")
            return

        # Get the best username, password, and space
        old_un, old_pw, old_space = (self.clowder_user, self.clowder_pass, self.clowderspace)
        self.clowder_user, self.clowder_pass, self.clowderspace = \
                                                    self.get_clowder_context(host, secret_key)

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
            # Build up a list of image IDs
            image_ids = {}
            if 'files' in resource:
                for one_image in imagefiles:
                    image_name = os.path.basename(one_image)
                    for res_file in resource['files']:
                        if ('filename' in res_file) and ('id' in res_file) and \
                                                            (image_name == res_file['filename']):
                            image_ids[image_name] = res_file['id']

            # Get timestamps. Also get season and experiment information for Clowder collections
            datestamp = self.find_datestamp(dataset_name)
            timestamp = timestamp_to_terraref(self.find_timestamp(dataset_name))
            (season_name, experiment_name, _) = self.get_season_and_experiment(datestamp,
                                                                               self.sensor_name)

            if self.experiment_metadata:
                if 'extractors' in self.experiment_metadata:
                    extractor_json = self.experiment_metadata['extractors']
                    if 'shapefile' in extractor_json:
                        if 'plot_column_name' in extractor_json['shapefile']:
                            plot_name_idx = extractor_json['shapefile']['plot_column_name']

            # Check our current local variables
            if dbffile is None:
                self.log_info(resource, "DBF file not found, using default plot naming")
            self.log_info(resource, "Extracting plots using shapefile '" + \
                                                        os.path.basename(shapefile) + "'")

            # Load the shapes and find the plot name column if we have a DBF file
            shape_in = ogr.Open(shapefile)
            layer_name = os.path.split(os.path.splitext(shapefile)[0])[1]
            if isinstance(layer_name, unicode):
                layer_name = layer_name.encode('ascii','ignore')
            layer = shape_in.GetLayer(layer_name)
            feature = layer.GetNextFeature()
            layer_ref = layer.GetSpatialRef()

            if dbffile:
                shape_table = DBF(dbffile, lowernames=True, ignore_missing_memofile=True)
                shape_rows = iter(list(shape_table))

                # Make sure if we have the column name of plot-names specified that it exists in
                # the shapefile
                column_names = shape_table.field_names
                if not plot_name_idx is None:
                    if not find_all_plot_names(plot_name_idx, column_names):
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
            plot_display_name = self.sensors.get_display_name(sensor=self.sensor_name) + \
                                                                                    " (By Plot)"

            # Loop through each polygon and extract plot level data
            alternate_plot_id = 0
            while feature:
                # Current geometry to extract
                plot_poly = feature.GetGeometryRef()
                if layer_ref:
                    plot_poly.AssignSpatialReference(layer_ref)
                plot_spatial_ref = plot_poly.GetSpatialReference()

                # Determie the plot name to use
                plot_name = None
                alternate_plot_id = alternate_plot_id + 1
                if shape_rows and plot_name_idx:
                    try:
                        row = next(shape_rows)
                        plot_name = get_plot_name(plot_name_idx, row)
                    except StopIteration:
                        pass
                if not plot_name:
                    plot_name = "plot_" + str(alternate_plot_id)

                # Determine output dataset name
                leaf_dataset = plot_display_name + ' - ' + plot_name + " - " + datestamp
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

                    # Get the bounds. We also get the reference systems in case we need to convert
                    # between them
                    bounds = imagefiles[filename]['bounds']
                    bounds_spatial_ref = bounds.GetSpatialReference()

                    # Checking for geographic overlap and skip if there is none
                    if not bounds_spatial_ref.IsSame(plot_spatial_ref):
                        # We need to convert coordinate system before an intersection
                        transform = osr.CoordinateTransformation(bounds_spatial_ref,
                                                                 plot_spatial_ref)
                        new_bounds = bounds.Clone()
                        if new_bounds:
                            new_bounds.Transform(transform)
                            intersection = plot_poly.Intersection(new_bounds)
                            new_bounds = None
                    else:
                        # Same coordinate system. Simple intersection
                        intersection = plot_poly.Intersection(bounds)

                    if intersection.GetArea() == 0.0:
                        self.log_info(resource, "Skipping image: "+filename)
                        continue

                    self.log_info(resource, "Attempting to clip '" + filename +
                                  "' to polygon number " + str(alternate_plot_id))

                    # Determine where we're putting the clipped file on disk and determine overwrite
                    # pylint: disable=unexpected-keyword-arg
                    out_file = self.sensors.create_sensor_path(timestamp,
                                                               filename=os.path.basename(filename),
                                                               plot=plot_name,
                                                               subsensor=self.sensor_name)
                    if (file_exists(out_file) and not self.overwrite_ok):
                        # The file exists and don't want to overwrite it
                        self.logger.warn("Skipping existing output file: %s", out_file)
                        continue

                    self.log_info(resource, "Attempting to clip '" + filename +
                                  "' to polygon number " + str(alternate_plot_id))

                    # Create destination folder on disk if we haven't done that already
                    if not os.path.exists(os.path.dirname(out_file)):
                        os.makedirs(os.path.dirname(out_file))

                    # Clip the raster
                    bounds_tuple = polygon_to_tuples_transform(plot_poly, bounds_spatial_ref)

                    clip_pix = clip_raster(filename, bounds_tuple, out_path=out_file)
                    if clip_pix is None:
                        self.log_error(resource, "Failed to clip image to plot name " + plot_name)
                        continue

                    # Upload the clipped image to the dataset
                    found_in_dest = check_file_in_dataset(connector, host, secret_key, target_dsid,
                                                          out_file, remove=self.overwrite_ok)
                    if not found_in_dest or self.overwrite_ok:
                        image_name = os.path.basename(filename)
                        content = {
                            "comment": "Clipped from shapefile " + os.path.basename(shapefile),
                            "imageName": image_name
                        }
                        if image_name in image_ids:
                            content['imageID'] = image_ids[image_name]

                        fileid = upload_to_dataset(connector, host, self.clowder_user,
                                                   self.clowder_pass, target_dsid, out_file)
                        uploaded_file_ids.append(fileid)

                        # Generate our metadata
                        meta = build_metadata(host, self.extractor_info, fileid, content, 'file')
                        clowder_file.upload_metadata(connector, host, secret_key, fileid, meta)
                    else:
                        self.logger.warn("Skipping existing file in dataset: %s", out_file)

                    self.created += 1
                    self.bytes += os.path.getsize(out_file)

                # Get the next shape to extract
                feature = layer.GetNextFeature()

            # Tell Clowder this is completed so subsequent file updates don't daisy-chain
            id_len = len(uploaded_file_ids)
            if id_len > 0 or self.created > 0:
                extractor_md = build_metadata(host, self.extractor_info, resource['id'], {
                    "files_created": uploaded_file_ids
                }, 'dataset')
                self.log_info(resource,
                              "Uploading shapefile plot extractor metadata to Level_2 dataset: "
                              + str(extractor_md))
                clowder_dataset.remove_metadata(connector, host, secret_key, resource['id'],
                                                self.extractor_info['name'])
                clowder_dataset.upload_metadata(connector, host, secret_key, resource['id'],
                                                extractor_md)
            else:
                self.logger.warn("Skipping dataset metadata updating since no files were loaded")

        finally:
            # Signal end of processing message and restore changed variables. Be sure to restore
            # changed variables above with early returns
            if not sensor_old_base is None:
                self.sensors.base = sensor_old_base

            self.clowder_user, self.clowder_pass, self.clowderspace = (old_un, old_pw, old_space)
            self.end_message(resource)

if __name__ == "__main__":
    # pylint: disable=invalid-name
    extractor = ClipByShape()
    extractor.start()
