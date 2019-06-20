"""Test cases for the Clowder interface
"""

import os
import uuid
import unittest
import datetime
import time
import logging

import pipelineutils.pipelineutils.pipelineutils as pu

# Define constants
USERNAME = os.getenv("TEST_CLOWDER_USERNAME", "test@example.com")
PASSWORD = os.getenv("TEST_CLOWDER_PASSWORD", "testPassword")
CLOWDER_URI = os.getenv("CLOWDER_HOST_URI", "http://localhost:9000")

FILE_WAIT_SLEEP_SECONDS = 5
FILE_WAIT_TIMEOUT_SECONDS = 5 * 60

# Configure logging
logging.basicConfig(level=logging.INFO)

def _wait_for_file(api_key, ds_id, filename):
    """Waits for the specified file to show up in the dataset
    Args:
        api_key(str): the API key to use
        ds_id(str): the dataset ID to look in
        filename(str): the name of the file to look for
    Return:
        True is returned if the file is found before timeout
    """
    file_found = False
    start_ts = datetime.datetime.now()
    cur_ts = start_ts
    while (cur_ts - start_ts).total_seconds() < FILE_WAIT_TIMEOUT_SECONDS and not file_found:
        url = "%s/api/datasets/%s/files?key=%s" % (CLOWDER_URI, ds_id, api_key)

        try:
            result_json = pu.__local__.get(url)
            # Try to find the filename
            if not result_json is None:
                for one_file in result_json:
                    if 'filename' in one_file and one_file['filename'] == filename:
                        file_found = True
        except Exception as ex:
            print("Exception was caught waiting for a file: " + str(ex))
            print("    Continuing to wait for the file \"" + filename + "\"")

        time.sleep(FILE_WAIT_SLEEP_SECONDS)

    return file_found

# pylint: disable=too-many-public-methods
class ClowderTestCase(unittest.TestCase):
    """Testing the clowder connections
    """
    
    def setup(self):    # pylint: disable=no-self-use
        """Test preparation for every unit test
        """
        print("Accessing Clowder instance at: '" + CLOWDER_URI + "'")
        print("Clowder credentials: '" + USERNAME + "/[hiddden]'")
    
    def teardown(self): # pylint: disable=no-self-use
        """Test cleanup for every unit test
        """
        # Nothing to tear down
        
    def _get_test_api_key(self):
        """Helper method for fetching an API key from Clowder
        """
        api_key = None
        try:
            api_key = pu.__local__.get_api_key(CLOWDER_URI, USERNAME, PASSWORD)
        except Exception as ex:
            print("Exception was caught getting API key: ", str(ex))
        finally:
            self.assertIsNotNone(api_key, "No api key was returned from clowder instance")
        return api_key
        
    def test_get_api_key(self):
        """Unit test for getting an API key from Clowder
        """
        api_key = None
        try:
            api_key = pu.__local__.get_api_key(CLOWDER_URI, USERNAME, PASSWORD)
        except Exception as ex:
            print("Exception was caught: ", str(ex))
        finally:
            self.assertIsNotNone(api_key, "No api key was returned from clowder instance")
        print("test_get_api_key passed: " + api_key)

    def test_find_extractor_name(self):
        """Unit test for finding an extractor name in Clowder
        """
        test_name = os.getenv("TEST_EXTRACTOR_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_EXTRACTOR_NAME")

        try:
            ex_name = pu.__local__.find_extractor_name(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding extractor name: ", str(ex))
        finally:
            self.assertIsNotNone(ex_name, "Extractor name '" + test_name + "' was not found")
            
        print("test_find_extractor_name for '" + test_name + "' passed: " + ex_name)

    def test_failure_find_extractor_name(self):
        """Unit test for finding an extractor name in Clowder
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create extractor name for failure test")

        try:
            ex_name = pu.__local__.find_extractor_name(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding extractor name: ", str(ex))
        finally:
            self.assertIsNone(ex_name, "Extractor name '" + test_name + "' was found but should not have been")
            
        print("test_failure_find_extractor_name for '" + test_name + "' passed")
        
    def test_get_dataset_id(self):
        """Unit test for returning the ID of a dataset
        """
        test_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
            
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + test_name + "' was not found")
            
        print("test_get_dataset_id for '" + test_name + "' passed: " + ds_id)
        
    def test_failure_get_dataset_id(self):
        """Unit test for returning the ID of a dataset
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create dataset name for failure test")
            
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNone(ds_id, "Dataset ID for dataset '" + test_name + "' was found but should not have been")
            
        print("test_failure_get_dataset_id for '" + test_name + "' passed")

    def test_get_space_id(self):
        """Unit test for returning the ID of a space
        """
        test_name = os.getenv("TEST_SPACE_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_SPACE_NAME")
            
        try:
            space_id = pu.__local__.get_space_id(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding space id ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "Space ID for space '" + test_name + "' was not found")
            
        print("test_get_space_id for '" + test_name + "' passed: " + space_id)
        
    def test_failure_get_space_id(self):
        """Unit test for returning the ID of a space
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create a space name for failure test")
            
        try:
            space_id = pu.__local__.get_space_id(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught finding space id ", str(ex))
        finally:
            self.assertIsNone(space_id, "Space ID for space '" + test_name + "' was found but should not have been")
            
        print("test_failure_get_space_id for '" + test_name + "' passed by not finding a space")
        
    def test_create_space(self):
        """Unit test for creating a space in Clowder
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to generate a space name for testing space creation")
            
        try:
            space_id = pu.__local__.create_space(CLOWDER_URI, self._get_test_api_key(), test_name)
        except Exception as ex:
            print("Exception was caught creating a space ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "A space named '" + test_name + "' was not created")
            
        print("test_create_space for '" + test_name + "' passed: " + space_id)

    def test_prepare_space_1(self):
        """Test space preparation with space_must_exist = None and existing space
        """
        test_name = os.getenv("TEST_SPACE_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_SPACE_NAME")
        
        space_must_exist = None
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "The existing space '" + test_name +
                                 "' was not prepared: space_must_exist=" + str(space_must_exist))
            
        print("test_prepare_space_1 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passed: " + space_id)

    def test_prepare_space_2(self):
        """Test space preparation with space_must_exist = None and non-existing space
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create a space name for testing space preparation")
        
        space_must_exist = None
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "The new space '" + test_name + "' was not prepared: space_must_exist=" +
                                 str(space_must_exist))
            
        print("test_prepare_space_2 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passed: " + space_id)

    def test_prepare_space_3(self):
        """Test space preparation with space_must_exist = True and existing space
        """
        test_name = os.getenv("TEST_SPACE_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_SPACE_NAME")
        
        space_must_exist = True
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "The existing space '" + test_name +
                                 "' was not prepared: space_must_exist=" + str(space_must_exist))
            
        print("test_prepare_space_3 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passed: " + space_id)

    def test_prepare_space_4(self):
        """Test space preparation with space_must_exist = True and non-existing space
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create a space name for testing space preparation")
        
        space_must_exist = True
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNone(space_id, "The new space '" + test_name + "' was not prepared: space_must_exist=" +
                              str(space_must_exist))
            
        print("test_prepare_space_4 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passed by not preparing a space")

    def test_prepare_space_5(self):
        """Test space preparation with space_must_exist = False and non-existing space
        """
        test_name = str(uuid.uuid4())
        self.assertIsNotNone(test_name, "Unable to create a space name for testing space preparation")
        
        space_must_exist = False
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNotNone(space_id, "The new space '" + test_name + "' was not prepared: space_must_exist=" +
                                 str(space_must_exist))
            
        print("test_prepare_space_5 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passed: " + space_id)

    def test_prepare_space_6(self):
        """Test space preparation with space_must_exist = False and existing space
        """
        test_name = os.getenv("TEST_SPACE_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_SPACE_NAME")
        
        space_must_exist = False
        try:
            space_id = pu.__local__.prepare_space(CLOWDER_URI, self._get_test_api_key(), test_name, space_must_exist)
        except Exception as ex:
            print("Exception was caught testing space preparation ", str(ex))
        finally:
            self.assertIsNone(space_id, "The existing space '" + test_name + "' was not prepared: space_must_exist=" +
                              str(space_must_exist))
            
        print("test_prepare_space_6 for '" + test_name + "' with space_must_exist=" + str(space_must_exist) +
              " passsed by not preparing a space")

    def test_upload_as_file(self):
        """Tests uploading a string as a file
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to create a temporary filename for uploading")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")
        
        file_content = "This is a test string"
        try:
            file_id = pu.__local__.upload_as_file(CLOWDER_URI, api_key, ds_id, test_name, file_content)
        except Exception as ex:
            print("Exception was caught testing string-as-file upload ", str(ex))
        finally:
            self.assertIsNotNone(file_id, "The file '" + test_name + "' was not uploaded to dataset '" + ds_name + "'")

        print("test_upload_as_file for '" + test_name + "' passed: " + file_id)

    def test_upload_file(self):
        """Tests uploading a file from disk
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to create a temporary filename for uploading")
        file_name = os.getenv("TEST_FILE_UPLOAD_PATH")
        self.assertIsNotNone(file_name, "Unable to find a configured environment variable of TEST_FILE_UPLOAD_PATH")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()

        # Ensure the file exists
        self.assertTrue(os.path.isfile(file_name), "File specified for upload test was not found: '" +
                        test_name + "'")
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id for file upload test ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")
        
        try:
            file_id = pu.__local__.upload_file(CLOWDER_URI, api_key, ds_id, test_name, file_name)
        except Exception as ex:
            print("Exception was caught testing file upload ", str(ex))
        finally:
            self.assertIsNotNone(file_id, "The file '" + test_name + "' was not uploaded to dataset '" + ds_name + "'")

        print("test_upload_file for '" + test_name + "' passed: " + file_id)

    def test_remove_file_by_id(self):
        """Tests removing a file by file ID
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to create a temporary filename for uploading")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")
        
        file_content = "This is a test string"
        try:
            file_id = pu.__local__.upload_as_file(CLOWDER_URI, api_key, ds_id, test_name, file_content)
        except Exception as ex:
            print("Exception was caught file upload for testing file removal ", str(ex))
        finally:
            self.assertIsNotNone(file_id, "The file '" + test_name + "' was not uploaded to dataset '" + ds_name + "'")

        # Wait for the file to show up
        self.assertTrue(_wait_for_file(api_key, ds_id, test_name))

        try:
            file_removed = pu.__local__.remove_file_by_id(CLOWDER_URI, api_key, file_id)
        except Exception as ex:
            print("Exception was caught file removing ", str(ex))
        finally:
            self.assertTrue(file_removed, "The file '" + test_name + "' was removed from dataset '" + ds_name + "'")

        print("test_remove_file_by_id for '" + test_name + "' passed: " + file_id)
        
    def test_checked_remove_file_1(self):
        """Checks for a non-existing file's existance before trying to remove it
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to create a temporary filename for testing checked file removal")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")

        try:
            file_removed = pu.__local__.checked_remove_file(CLOWDER_URI, api_key, ds_id, test_name)
        except Exception as ex:
            print("Exception was caught file removing ", str(ex))
        finally:
            self.assertFalse(file_removed, "The file '" + test_name + "' was removed from dataset '" + ds_name + "'")

        print("test_checked_remove_file_1 for '" + test_name + "' passed by not removing a non-existant file")

    def test_checked_remove_file_2(self):
        """Checks for an existing file's existance before trying to remove it
        """
        test_name = uuid.uuid4().hex
        self.assertIsNotNone(test_name, "Unable to create a temporary filename for testing checked file removal")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")
        
        file_content = "This is a test string"
        try:
            file_id = pu.__local__.upload_as_file(CLOWDER_URI, api_key, ds_id, test_name, file_content)
        except Exception as ex:
            print("Exception was caught file upload for testing file removal ", str(ex))
        finally:
            self.assertIsNotNone(file_id, "The file '" + test_name + "' was not uploaded to dataset '" +
                                 ds_name + "'")

        # Wait for the file to show up
        self.assertTrue(_wait_for_file(api_key, ds_id, test_name))

        try:
            file_removed = pu.__local__.checked_remove_file(CLOWDER_URI, api_key, ds_id, test_name)
        except Exception as ex:
            print("Exception was caught file removing ", str(ex))
        finally:
            self.assertTrue(file_removed, "The file '" + test_name + "' was not removed from dataset '" +
                            ds_name + "'")

        print("test_checked_remove_file_2 for '" + test_name + "' passed by removing existing file")
        
    def test_start_extractor(self):
        """Tests sending a command to start an extractor
        """
        test_name = os.getenv("TEST_EXTRACTOR_FULL_NAME")
        self.assertIsNotNone(test_name, "Unable to find a configured environment variable of TEST_EXTRACTOR_FULL_NAME")
        ds_name = os.getenv("TEST_DATASET_NAME")
        self.assertIsNotNone(ds_name, "Unable to find a configured environment variable of TEST_DATASET_NAME")
        api_key = self._get_test_api_key()
        
        try:
            ds_id = pu.__local__.get_dataset_id(CLOWDER_URI, api_key, ds_name)
        except Exception as ex:
            print("Exception was caught finding dataset id ", str(ex))
        finally:
            self.assertIsNotNone(ds_id, "Dataset ID for dataset '" + ds_name + "' was not found")
            
        try:
            extractor_started = pu.__local__.start_extractor(CLOWDER_URI, self._get_test_api_key(), ds_id, test_name)
        except Exception as ex:
            print("Exception was caught starting extractor", str(ex))
        finally:
            self.assertTrue(extractor_started, "Extractor '" + test_name + "' was not started")
            
        print("test_start_extractor for '" + test_name + "' passed")
        
        
    def test_prepare_experiment(self):
        """Testing preparing experiment data
        """
        study = str(uuid.uuid4())
        season = str(uuid.uuid4())
        timestamp = str(uuid.uuid4())
        
        try:
            experiment = pu.prepare_experiment(study, season, timestamp)
        except Exception as ex:
            print("Exception was caught preparing experiment data", str(ex))
        finally:
            self.assertIsNotNone(experiment, "Experiment data was not prepared")
            self.assertEqual(experiment['studyName'], study, "Experiment name is not correct")
            self.assertEqual(experiment['season'], season, "Experiment season is not correct")
            self.assertEqual(experiment['observationTimestamp'], timestamp, "Experiment timestamp is not correct")

        print("test_prepare_experiment passed")
