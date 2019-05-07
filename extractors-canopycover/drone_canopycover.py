#!/usr/bin/env python

'''Extractor for calculating canopy cover by plot plots via a shapefile
'''

import os
import json
import logging
import requests
import osr

from osgeo import ogr
from numpy import nan, rollaxis
from dbfread import DBF

import pyclowder.datasets as clowder_dataset
from pyclowder.utils import CheckMessage

from terrautils.extractors import TerrarefExtractor, build_metadata, confirm_clowder_info, \
     upload_to_dataset, timestamp_to_terraref
from terrautils.sensors import STATIONS
from terrautils.spatial import clip_raster
from terrautils.imagefile import file_is_image_type, image_get_geobounds, \
     polygon_to_tuples_transform, get_epsg

import terraref.stereo_rgb

# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'canopybyshape' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['canopybyshape'] = {'template': '{base}/{station}/Level_2/' + \
                                                           '{sensor}/{date}/{timestamp}/{filename}',
                                               'pattern': '{sensor}_L3_{station}_{date}{opts}.csv',
                                              }

# Array of trait names that should have array values associated with them
TRAIT_NAME_ARRAY_VALUE = ['canopy_cover', 'site']

# Mapping of default trait names to fixecd values
TRAIT_NAME_MAP = {
    'access_level': '2',
    'species': 'Unknown',
    'citation_author': '"Zongyang, Li; Schnaufer, Christophe"',
    'citation_year': '2016; 2019',
    'citation_title': 'Maricopa Field Station Data and Metadata',
    'method': 'Canopy Cover Estimation from RGB image using plot shapefile'
}

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

# The class for determining canopy cover from shapefile
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
        TerrarefExtractor.process_message(self, connector, host, secret_key, resource, parameters)

        # Handle any parameters
        if isinstance(parameters, basestring):
            parameters = json.loads(parameters)
        if isinstance(parameters, unicode):
            parameters = json.loads(str(parameters))

        # Initialize local variables
        dataset_name = parameters["datasetname"]
        datestamp, shape_table, plot_name_idx, shape_rows = None, None, None, None
        citation_auth_override, citation_title_override, citation_year_override = None, None, None
        config_specie = None

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
            # Build up a list of image IDs
            image_ids = {}
            if 'files' in resource:
                for one_image in imagefiles:
                    image_name = os.path.basename(one_image)
                    for res_file in resource['files']:
                        if ('filename' in res_file) and ('id' in res_file) and \
                                                            (image_name == res_file['filename']):
                            image_ids[image_name] = res_file['id']

            # Get timestamps
            datestamp = self.find_datestamp(dataset_name)
            timestamp = timestamp_to_terraref(self.find_timestamp(dataset_name))

            if self.experiment_metadata:
                # pylint: disable=line-too-long
                if 'extractors' in self.experiment_metadata:
                    extractor_json = self.experiment_metadata['extractors']
                    if 'shapefile' in extractor_json:
                        if 'plot_column_name' in extractor_json['shapefile']:
                            plot_name_idx = extractor_json['shapefile']['plot_column_name']
                    if 'canopyCover' in extractor_json:
                        if 'citationAuthor' in extractor_json['canopyCover']:
                            citation_auth_override = extractor_json['canopyCover']['citationAuthor']
                        if 'citationYear' in extractor_json['canopyCover']:
                            citation_year_override = extractor_json['canopyCover']['citationYear']
                        if 'citationTitle' in extractor_json['canopyCover']:
                            citation_title_override = extractor_json['canopyCover']['citationTitle']
                # pylint: enable=line-too-long
                if 'germplasmName' in self.experiment_metadata:
                    config_specie = self.experiment_metadata['germplasmName']

            # Check our current local variables
            if dbffile is None:
                self.log_info(resource, "DBF file not found, using default plot naming")
            self.log_info(resource, "Extracting plots using shapefile '" + \
                                                        os.path.basename(shapefile) + "'")

            # Load the shapes and find the plot name column if we have a DBF file
            shape_in = ogr.Open(shapefile)
            layer = shape_in.GetLayer(os.path.split(os.path.splitext(shapefile)[0])[1])
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

            # Setup for the extracted plot canopy cover
            sensor_name = "canopybyshape"

            # Create the output files
            base_name = os.path.basename(imagefiles.keys()[0])
            rootdir = self.sensors.create_sensor_path(timestamp, sensor=sensor_name, ext=".csv")
            out_csv = os.path.join(os.path.dirname(rootdir),
                                   base_name.replace(".tif", "_canopycover_shapefile.csv"))
            out_geo = os.path.join(os.path.dirname(rootdir),
                                   base_name.replace(".tif", "_canopycover_geo.csv"))

            self.log_info(resource, "Writing Shapefile CSV to %s" % out_csv)
            csv_file = open(out_csv, 'w')
            (fields, traits) = get_traits_table()
            csv_file.write(','.join(map(str, fields)) + '\n')

            self.log_info(resource, "Writing Geostreams CSV to %s" % out_geo)
            geo_file = open(out_geo, 'w')
            geo_file.write(','.join(['site', 'trait', 'lat', 'lon', 'dp_time',
                                     'source', 'value', 'timestamp']) + '\n')

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

                    # Clip the raster
                    bounds_tuple = polygon_to_tuples_transform(plot_poly, bounds_spatial_ref)

                    try:
                        cc_val = "NA"

                        clip_pix = clip_raster(filename, bounds_tuple)
                        if clip_pix is None:
                            self.log_error(resource, "Failed to clip image to plot name " +
                                           plot_name)
                            continue
                        if len(clip_pix.shape) < 3:
                            self.log_error(resource,
                                           "Unexpected array shape for %s (%s)" % \
                                                                        (plot_name, clip_pix.shape))
                            continue

                        cc_val = terraref.stereo_rgb.calculate_canopycover(rollaxis(clip_pix, 0, 3))

                        # Prepare the data for writing
                        image_clowder_id = ""
                        image_name = os.path.basename(filename)
                        if image_name in image_ids:
                            image_clowder_id = image_ids[image_name]
                        centroid = plot_poly.Centroid()

                        # Write the datapoint geographically and otherwise
                        geo_file.write(','.join([plot_name,
                                                 'Canopy Cover',
                                                 str(centroid.GetX()),
                                                 str(centroid.GetY()),
                                                 timestamp,
                                                 host.rstrip('/') + '/files/' + image_clowder_id,
                                                 str(cc_val),
                                                 datestamp]) + '\n')

                        traits['canopy_cover'] = str(cc_val)
                        traits['site'] = plot_name
                        traits['local_datetime'] = timestamp
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
                content = {"comment": "Calculated from shapefile '" + os.path.basename(shapefile) \
                           + "'",
                           "files_created": [fileid, geoid]
                          }
                extractor_md = build_metadata(host, self.extractor_info, dataset_id, content,
                                              'file')
                clowder_dataset.remove_metadata(connector, host, secret_key, dataset_id,
                                                self.extractor_info['name'])
                clowder_dataset.upload_metadata(connector, host, secret_key, dataset_id,
                                                extractor_md)
            # pylint: disable=broad-except
            except Exception as ex:
                self.log_error(resource, "Exception updating dataset metadata: " + str(ex))
            # pylint: enable=broad-except
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
