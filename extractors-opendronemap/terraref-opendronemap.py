#!/usr/bin/env python

# pylint: disable=invalid-name
# pylint: disable=missing-docstring

import os
import subprocess
import tempfile
import json
import gzip
import shutil
import logging
import re

from pyclowder.files import upload_metadata
from terrautils.extractors import TerrarefExtractor, build_metadata, \
     build_dataset_hierarchy_crawl, upload_to_dataset, file_exists, \
     check_file_in_dataset
from terrautils.sensors import Sensors, STATIONS

from opendm import config

from opendrone_stitch import OpenDroneMapStitch

# We need to add other sensor types for OpenDroneMap generated files before anything happens
# The Sensor() class initialization defaults the sensor dictionary and we can't override
# without many code changes
if 'ua-mac' in STATIONS:
    if 'laz' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['laz'] = {'display': 'Compressed point cloud',
                                     'template': '{base}/{station}/Level_2/' + \
                                                 '{sensor}/{date}/{filename}',
                                     'pattern': '{sensor}_L2_{station}_{date}{opts}.laz'
                                    }
    if 'shp' not in STATIONS['ua-mac']:
        STATIONS['ua-mac']['shp'] = {'display': 'Shapefile',
                                     'template': '{base}/{station}/Level_2/' + \
                                                 '{sensor}/{date}/{filename}',
                                     'pattern': '{sensor}_L2_{station}_{date}{opts}.shp'
                                    }


# Deletes a folder tree and ensures the top level folder is deleted as well
# pylint: disable=broad-except
def check_delete_folder(folder):
    """Deletes a folder tree and ensures the top level folder is removes as well
    """
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
            # If the top level folder is still around, delete it explicitly
            if os.path.exists(folder):
                os.rmdir(folder)
        except Exception as ex:
            logging.debug("Execption deleting folder %s", folder)
            logging.debug("  %s", ex.message)


# Class for performing a full field mosaic stitching using Clowder's opendronemap extractor
# This class is mostly a wrapper around the OpenDroneMapStitch extractor
class ODMFullFieldStitcher(TerrarefExtractor, OpenDroneMapStitch):
    """Runs OpenDroneMap (ODM) extractor in the TerraRef environment

    The Clowder ODM extractor uploads the generated files into the source dataset.
    For the TerraRef environment, each sensor type needs to get placed into its own dataset. This
    default behavior requires that we store the information of the files to be uploaded for later
    processing. Another wrinkle is that not all types of file are necessarily uploaded. This means
    that we can't create the datasets until we are sure the files of the correct type are being
    uploaded. For example, the LAZ file may not be uploaded.
    """

    # Initialization of instance
    def __init__(self):
        """Initialization of instance
        """
        super(ODMFullFieldStitcher, self).__init__()

        # Array of files to upload once processing is done
        self.files_to_upload = None
        self.sensor_maps = None
        self.sensor_dsid_map = None
        self.cache_folder = None

    # Property definitions
    @property
    def date_format_regex(self):
        """Returns array of regex expressions for different date formats
        """
        # We lead with the best formatting to use, add on the catch-all
        return [r'(\d{4}(/|-){1}\d{1,2}(/|-){1}\d{1,2})',
                r'(\d{1,2}(/|-){1}\d{1,2}(/|-){1}\d{4})']

    @property
    def filename_sensor_maps(self):
        """Returns array of file name endings and thier associated sensor types
        """
        # Filename/extension mappings for derived types that are not included in the
        # default RGB sensor mapping
        return {'.laz':'laz', '.shp':'shp', '.dbf':'shp', '.shx':'shp',
                'proj.txt':'shp', '.prj':'shp', '.json':'shp', '.geojson':'shp'}

    # Called by OpenDroneMapStitch during the __init__ call
    # So we override it to make sure things happen the way we want them to
    # pylint: disable=arguments-differ
    def dosetup(self, odm_args):
        """Performs setup of our instances by defaulting our sensor
        """
        # parse command line and load default logging configuration
        TerrarefExtractor.setup(self, sensor='rgb_fullfield')
        OpenDroneMapStitch.dosetup(self, odm_args)

    # Called to see if we want the message
    # Hand it through to the OpenDroneMapStitch since it knows what it wants
    # pylint: disable=too-many-arguments
    def check_message(self, connector, host, secret_key, resource, parameters):
        """Explicitly calls through to our OpenDroneMapStitch parent instance
        """
        return OpenDroneMapStitch.check_message(self, connector, host, secret_key,
                                                resource, parameters)

    # We override the file uploads method to handle later
    # pylint: disable=line-too-long
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=unused-argument
    def upload_file(self, file_path, source_file_name, dest_file_name, connector, host, secret_key, dataset_id, compress):
        """Override from parent ODM Extractor instance for uploading a file

        We expect to see the name of the main orthophoto (Ortho Mosiac) file. We ignore it
        when we see it since we're handling it later. We need to move the original files
        since they get cleaned up after ODM is done processing

        Args:
            file_path(str): the path to the source file
            source_file_name(str): the name of the source file to upload
            dest_file_name(str): the file name that the file should be uploaded as
            connector(obj): the message queue connector instance
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            dataset_id(str): [Ignored] the dataset the file is to be uploaded to
            compress(bool): If set to true the file is compressed before uploading

        Notes:
            We push information on the file upload onto a list. If the file matches
            an alternate sensor, we map it to that new sensor type.
        """

        # Make a copy of the file
        src_path = os.path.join(file_path, source_file_name)
        cache_path = os.path.join(self.cache_folder, source_file_name)
        os.rename(src_path, cache_path)

        # Handle extensions/sensors
        new_sensor = None
        for m in self.filename_sensor_maps:
            if source_file_name.endswith(m):
                new_sensor = self.filename_sensor_maps[m]
                break

        # Setup the correct path information based upon found sensor type
        if not new_sensor:
            self.files_to_upload.append({"source_path":self.cache_folder, "source_name":source_file_name, "dest_path":self.cache_folder,
                                         "dest_name":dest_file_name, "compress":compress})
        elif new_sensor in self.sensor_maps:
            si = self.sensor_maps[new_sensor]
            # We need to keep the original filename extension but update the file name itself
            if 'name' in si:
                src_ext = os.path.splitext(si['name'])[1]
                dest_ext = os.path.splitext(dest_file_name)[1]
                new_dest_file_name = si['name'].replace(src_ext, dest_ext)
            else:
                new_dest_file_name = dest_file_name
            self.files_to_upload.append({"source_path":self.cache_folder, "source_name":source_file_name,
                                         "dest_path":si["dir"], "dest_name":new_dest_file_name,
                                         "compress":compress, "sensor":new_sensor})
        else:
            # Not found
            raise Exception("%s sensor path was not found" % new_sensor)

    # Performs the actual upload to the dataset
    # pylint: disable=too-many-locals
    def perform_uploads(self, connector, host, secret_key, resource, default_dsid, content, season_name, experiment_name, timestamp):
        """Perform the uploading of all the files we're put onto the upload list

        Args:
            connector(obj): the message queue connector instance
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            default_dsid(str): the default dataset to load files to
            content(str): content information for the files we're uploading
            season_name(str): the name of the season
            experiment_name(str): the name of the experiment
            timestamp(str): the timestamp string associated with the source dataset

        Notes:
            We loop through the files, compressing, and remapping the names as needed.
            If the sensor associated with the file is missing, we upload the file to
            the default dataset. Otherwise, we use the dataset associated with the sensor
            and create the dataset if necessary
        """
        for one_file in self.files_to_upload:
            sourcefile = os.path.join(one_file["source_path"], one_file["source_name"])

            # Make sure we have the original file and then compress it if needed, or remane is
            if os.path.isfile(sourcefile):
                # make sure we have the full destination path
                if not os.path.exists(one_file["dest_path"]):
                    os.makedirs(one_file["dest_path"])

                resultfile = os.path.join(one_file["dest_path"], one_file["dest_name"])
                if one_file["compress"]:
                    resultfile = resultfile + ".zip"
                    with open(sourcefile, 'rb') as f_in:
                        with gzip.open(resultfile, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                elif not sourcefile == resultfile:
                    shutil.move(sourcefile, resultfile)

                # Find or create the target dataset for this entry if it doesn't exist
                cur_dataset_id = default_dsid
                if "sensor" in one_file:
                    sensor_type = one_file["sensor"]
                    if sensor_type in self.sensor_dsid_map:
                        cur_dataset_id = self.sensor_dsid_map[sensor_type]
                    else:
                        new_sensor = Sensors(base=self.sensors.base, station=self.sensors.station, sensor=sensor_type)

                        new_dsid = build_dataset_hierarchy_crawl(host, secret_key, self.clowder_user, self.clowder_pass, self.clowderspace,
                                                                 season_name, experiment_name, new_sensor.get_display_name(),
                                                                 timestamp[:4], timestamp[5:7], timestamp[8:10],
                                                                 leaf_ds_name=new_sensor.get_display_name() + ' - ' + timestamp)

                        self.sensor_dsid_map[sensor_type] = new_dsid
                        cur_dataset_id = new_dsid

                # Check if file already exists in the dataset
                file_in_dataset = check_file_in_dataset(connector, host, secret_key, cur_dataset_id, resultfile, remove=False)

                # If the files is already in the dataset, determine if we need to delete it first
                if self.overwrite and file_in_dataset:
                    # Delete the file from the dataset before uploading the new copy
                    self.log_info(resource, "Removing existing file in dataset " + resultfile)
                    check_file_in_dataset(connector, host, secret_key, cur_dataset_id, resultfile, remove=True)
                elif not self.overwrite and file_in_dataset:
                    # We won't overwrite an existing file
                    self.log_skip(resource, "Not overwriting existing file in dataset " + resultfile)
                    continue

                # Upload the file to the dataset
                dsid = upload_to_dataset(connector, host, self.clowder_user, self.clowder_pass, cur_dataset_id, resultfile)

                # Generate our metadata
                meta = build_metadata(host, self.extractor_info, dsid, content, 'file')

                # Upload the meadata to the dataset
                upload_metadata(connector, host, secret_key, dsid, meta)

                self.created += 1
                self.bytes += os.path.getsize(resultfile)
            else:
                raise Exception("%s was not found" % sourcefile)

    # Extract the timestamp
    # pylint: disable=too-many-nested-blocks
    def get_timestamp(self, dataset_name, resource):
        """Extracts the timestamp from the dataset name

        Returns:
            The extracted timestamp as YYYY-MM-DD. Throws an exception if the timestamp isn't found

        Notes:
            This function only cares about if the timestamp looks correct. It doesn't
            figure out if month and date are correct. The string is reformatted if
            the year is in the wrong spot
        """

        formats = self.date_format_regex

        # If there's a date in the dataset name it will be what we use
        dataset_len = len(dataset_name)
        if dataset_name and isinstance(dataset_name, basestring) and dataset_len > 0:
            for part in dataset_name.split(" - "):
                for f in formats:
                    r = re.search(f, part)
                    if r:
                        date = r.group(0)
                        if not '-' in date[:4]:
                            return date
                        else:
                            split_date = date.split("-")
                            if len(split_date) == 3:
                                return date[2] + "-" + date[1] + "-" + date[0]

        self.log_error(resource, "A date is not recognised as part of the name of the dataset")
        raise RuntimeError("Invalid dataset name. Needs to include a date such as 'My dataset - YYYY-MM-DD - more text'")

    # We have a message to process
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def process_message(self, connector, host, secret_key, resource, parameters):
        """Process the message requesting the ODM extractor to run

        Args:
            connector(obj): the message queue connector instance
            host(str): the URI of the host making the connection
            secret_key(str): used with the host API
            resource(dict): dictionary containing the resources associated with the request
            parameters(json): json object of the triggering message contents
        """

        # Start of message processing
        super(ODMFullFieldStitcher, self).start_message(resource)

        # Handle any parameters
        if isinstance(parameters, basestring):
            parameters = json.loads(parameters)
        if isinstance(parameters, unicode):
            parameters = json.loads(str(parameters))
        #if 'parameters' in parameters:
        #    parameters = parameters['parameters']

        # Array of files to upload once processing is done
        self.files_to_upload = []

        # Our cache of files to upload
        self.cache_folder = tempfile.mkdtemp()

        # We are only handling one sensor type here. ODM generates additional sensor outputs
        # that may not be available for upload; we handle those as we see them in upload_file() above
        sensor_type = "rgb"

        # Initialize local variables
        dataset_name = parameters["datasetname"]
        scan_name = parameters["scan_type"] if "scan_type" in parameters else ""
        season_name, experiment_name = "Unknown Season", "Unknown Experiment"

        # Look over file metadata to get the best timestamp
        timestamp = self.get_timestamp(dataset_name, resource)

        # Generate the file names
        out_tif_full = self.sensors.get_sensor_path(timestamp, opts=[sensor_type, scan_name]).replace(" ", "_")
        out_tif_thumb = out_tif_full.replace(".tif", "_thumb.tif")
        out_tif_medium = out_tif_full.replace(".tif", "_10pct.tif")
        out_png = out_tif_medium.replace(".tif", ".png")
        out_dir = os.path.dirname(out_tif_full)

        # Generate dictionary of sensor output folders and file names
        sensor_maps = {sensor_type: {"dir" : out_dir, "name" : os.path.basename(out_tif_full)}}
        fsm = self.filename_sensor_maps
        for one_map in fsm:
            cur_sensor = fsm[one_map]
            if not cur_sensor in sensor_maps:
                sensor_path = self.sensors.get_sensor_path(timestamp, sensor=cur_sensor, opts=[cur_sensor, scan_name]).replace(" ", "_")
                sensor_maps[cur_sensor] = {"dir" : os.path.dirname(sensor_path), "name" : os.path.basename(sensor_path)}
        self.sensor_maps = sensor_maps

        # Only generate what we need to by checking files on disk
        thumb_exists, med_exists, full_exists, png_exists, only_png = False, False, False, False, False

        if file_exists(out_tif_thumb):
            thumb_exists = True
        if file_exists(out_tif_medium):
            med_exists = True
        if file_exists(out_tif_full):
            full_exists = True
        if file_exists(out_png):
            png_exists = True
        if thumb_exists and med_exists and full_exists and not self.overwrite:
            if  png_exists:
                self.log_skip(resource, "all outputs already exist")
                return
            else:
                self.log_info(resource, "all outputs already exist (10% PNG thumbnail must still be generated)")
                only_png = True

        # If we need the whole set of files, create them
        if not only_png:
            # Override the output file name. We don't save anything here because we'll override it the next time through
            self.args.orthophotoname = os.path.splitext(os.path.basename(out_tif_full))[0]

            # Run the stitch process
            OpenDroneMapStitch.process_message(self, connector, host, secret_key, resource, parameters)

            # Look up the name of the full sized orthomosaic
            basename = os.path.basename(out_tif_full)
            srcname = None
            for f in self.files_to_upload:
                if f["dest_name"] == basename:
                    srcname = os.path.join(self.cache_folder, f["source_name"])
                    break

            # Generate other file sizes from the original orthomosaic
            if srcname and not file_exists(out_tif_medium):
                self.log_info(resource, "Converting orthomosaic to %s..." % out_tif_medium)
                outname = os.path.join(self.cache_folder, os.path.basename(out_tif_medium))
                cmd = "gdal_translate -outsize %s%% %s%% %s %s" % (10, 10, srcname, outname)
                subprocess.call(cmd, shell=True)

            if srcname and not file_exists(out_tif_thumb):
                self.log_info(resource, "Converting orthomosaic to %s..." % out_tif_thumb)
                outname = os.path.join(self.cache_folder, os.path.basename(out_tif_thumb))
                cmd = "gdal_translate -outsize %s%% %s%% %s %s" % (2, 2, srcname, outname)
                subprocess.call(cmd, shell=True)

        # We're here due to possibly needing the PNG Thumbnail
        srcname = os.path.join(self.cache_folder, os.path.basename(out_tif_medium))
        if (only_png or not png_exists) and file_exists(srcname):
            # Create PNG thumbnail
            self.log_info(resource, "Converting 10pct to %s..." % out_png)
            outname = os.path.join(self.cache_folder, os.path.basename(out_png))
            cmd = "gdal_translate -of PNG %s %s" % (srcname, outname)
            subprocess.call(cmd, shell=True)

        # Get dataset ID or create it, creating parent collections as needed
        target_dsid = build_dataset_hierarchy_crawl(host, secret_key, self.clowder_user, self.clowder_pass, self.clowderspace,
                                                    season_name, experiment_name, self.sensors.get_display_name(),
                                                    timestamp[:4], timestamp[5:7], timestamp[8:10],
                                                    leaf_ds_name=self.sensors.get_display_name() + ' - ' + timestamp)

        # Store our dataset mappings for possible later use
        self.sensor_dsid_map = {sensor_type : target_dsid}

        # Upload full field image to Clowder
        file_ids = []
        if "files" in resource:
            for one_file in resource["files"]:
                file_ids.append(one_file.get("id", ""))
        content = {
            "comment": "This stitched file is computed using OpenDroneMap. Change the parameters in extractors-opendronemap.txt to change the results.",
            "file_ids": ", ".join(file_ids)
        }

        # If we newly created these files, upload to Clowder
        file_name = os.path.basename(out_tif_thumb)
        file_path = os.path.join(self.cache_folder, file_name)
        if file_exists(file_path) and not thumb_exists:
            self.files_to_upload.append({"source_path":self.cache_folder, "source_name":file_name, "dest_path":out_dir,
                                         "dest_name":file_name, "compress":False})

        file_name = os.path.basename(out_tif_medium)
        file_path = os.path.join(self.cache_folder, file_name)
        if file_exists(file_path) and not med_exists:
            self.files_to_upload.append({"source_path":self.cache_folder, "source_name":file_name, "dest_path":out_dir,
                                         "dest_name":file_name, "compress":False})

        file_name = os.path.basename(out_png)
        file_path = os.path.join(self.cache_folder, file_name)
        if file_exists(file_path) and not png_exists:
            self.files_to_upload.append({"source_path":self.cache_folder, "source_name":file_name, "dest_path":out_dir,
                                         "dest_name":file_name, "compress":False})

        # The main orthomosaic is already getting uploaded, but we must make sure its path is correct
        srcname = os.path.basename(out_tif_full).lower()
        for one_file in self.files_to_upload:
            file_name = os.path.basename(one_file["dest_name"]).lower()
            if file_name == srcname:
                one_file["dest_path"] = os.path.dirname(out_tif_full)
                break

        # This function uploads the files into their appropriate datasets
        self.perform_uploads(connector, host, secret_key, resource, target_dsid, content, season_name, experiment_name, timestamp)

        # Cleanup the all destination folders skipping over ones that are in our "base" path (we want to keep those)
        base = self.sensors.base
        if not self.cache_folder.startswith(base):
            check_delete_folder(self.cache_folder)
        for sp in self.sensor_maps:
            if not self.sensor_maps[sp]["dir"].startswith(base):
                check_delete_folder(self.sensor_maps[sp]["dir"])

        # We are done
        self.end_message(resource)

if __name__ == "__main__":
    args = config.config()
    args.project_path = tempfile.mkdtemp()

    extractor = ODMFullFieldStitcher()
    extractor.dosetup(args)
    extractor.start()
