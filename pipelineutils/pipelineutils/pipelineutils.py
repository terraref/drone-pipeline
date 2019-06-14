"""Utility functions and classes for accessing the drone pipeline
"""

import io
import os
import logging
import tempfile
import shutil
import json
import requests

# Definitions
YAML_INDENT = "    "
YAML_INDENT2 = YAML_INDENT + YAML_INDENT

class __local__():
    """Class instance wrapping local functions
    """
    def __init__(self):
        """Initialize class instance.
        """

    @staticmethod
    def get(url: str, args=None, result_key: str = None, result_index: int = None):
        """Makes a GET request
        Args:
            url(string): the url to call
            args: arguments to pass to the call
            result_key(string): optional key to look up in the results
            result_index(int): optional index to return the result_key value from, for indexable results
        Return:
            If no result_key or result_index is specified, the JSON returned from the call.
            If only the result_key is specified, the value of that key in the JSON returned from the call.
            If both result_key and result_index is specified, the JSON is indexed at the value specified in
            result_index and the value associated with the result_key at that index is returned.
            None is returned if the parsed JSON returned from the call has a length of zero.
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            No checks are made to the args parameter for validity to the GET call
        """
        request = lambda: __local__.make_call("GET", url, args, result_key, result_index)
        return request()

    @staticmethod
    def post(url: str, args=None, result_key: str = None, result_index: int = None):
        """Makes a POST request
        Args:
            url(string): the url to call
            args: arguments to pass to the call
            result_key(string): optional key to look up in the results
            result_index(int): optional index to return the result_key value from, for indexable results
        Return:
            If no result_key or result_index is specified, the JSON returned from the call.
            If only the result_key is specified, the value of that key in the JSON returned from the call.
            If both result_key and result_index is specified, the JSON is indexed at the value specified in
            result_index and the value associated with the result_key at that index is returned.
            None is returned if the parsed JSON returned from the call has a length of zero.
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            No checks are made to the args parameter for validity to the POST call
        """
        request = lambda: __local__.make_call("POST", url, args, result_key, result_index)
        return request()

    @staticmethod
    def delete(url: str, args=None, result_key: str = None, result_index: int = None):
        """Makes a DELETE request
        Args:
            url(string): the url to call
            args: arguments to pass to the call
            result_key(string): optional key to look up in the results
            result_index(int): optional index to return the result_key value from, for indexable results
        Return:
            If no result_key or result_index is specified, the JSON returned from the call.
            If only the result_key is specified, the value of that key in the JSON returned from the call.
            If both result_key and result_index is specified, the JSON is indexed at the value specified in
            result_index and the value associated with the result_key at that index is returned.
            None is returned if the parsed JSON returned from the call has a length of zero.
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            No checks are made to the args parameter for validity to the DELETE call
        """
        request = lambda: __local__.make_call("DELETE", url, args, result_key, result_index)
        return request()

    @staticmethod
    def make_call(method: str, url: str, args=None, result_key: str = None, result_index: int = None):
        """Makes a generic HTTP request
        Args:
            method(string): the method to use when making the call
            url(string): the url to call
            args: arguments to pass to the call
            result_key(string): optional key to look up in the results
            result_index(int): optional index to return the result_key value from, for indexable results
        Return:
            If no result_key or result_index is specified, the JSON returned from the call.
            If only the result_key is specified, the value of that key in the JSON returned from the call.
            If both result_key and result_index is specified, the JSON is indexed at the value specified in
            result_index and the value associated with the result_key at that index is returned.
            None is returned if the parsed JSON returned from the call has a length of zero.
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            No checks are made to the args parameter for validity to the method requested
        """
        if not args is None:
            result = requests.request(method, url, *args)
        else:
            result = requests.request(method, url)
        result.raise_for_status()

        result_json = result.json()
        json_len = len(result_json)
        if json_len > 0:
            if not result_key is None:
                if not result_index is None:
                    try:
                        _ = iter(result_json)
                        return result_json[result_index][result_key]
                    except Exception:
                        pass
                return result_json[result_key]
            return result_json

        return None

    @staticmethod
    def get_api_key(clowder_url: str, username: str, password: str) -> str:
        """Returns an API key for the specified user
        Args:
            clowder_url(string): the Clowder URL (make sure it's not the API url)
            username(string): name of Clowder user
            password(string): password associated with Clowder user
        Return:
            A found API key or None if one isn't found
        """
        # Get a key
        url = "%s/api/users/keys" % (clowder_url)
        get_args = {"headers":{"Accept": "application/json"},
                    "auth": (username, password)
                   }

        result_key = __local__.get(url, get_args, result_key="key", result_index=0)
        if result_key is None:
            logging.warning("Unable to find an API key for user %s", username)

        return result_key

    @staticmethod
    def find_extractor_name(clowder_api_url: str, api_key: str, extractor_name: str) -> str:
        """Looks up the Clowder registered extractor associated with the extractor name
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            extractor_name(string): part of the extractor name to match
        Return:
            The name of the associated Clowder extractor or None if one isn't found.
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            The first match found is the one that's returned
        """
        url = "%s/extractors?key=%s" % (clowder_api_url, api_key)
        get_args = {"headers": {"Accept": "application/json"}}

        result_json = __local__.get(url, get_args)
        if not result_json is None:
            for ex in result_json:
                if 'name' in ex and extractor_name in ex['name']:
                    return ex['name']

        logging.warning("Unable to find an extractor matching \"%s\"", extractor_name)
        return None

    @staticmethod
    def get_dataset_id(clowder_api_url: str, api_key: str, dataset_name: str) -> str:
        """Retrieves the ID of a dataset by name
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_name(string): the name of the dataset to get the ID of
        Return:
            The ID of the dataset or None if the dataset is not found or there was a problem
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        """

        # Look up the dataset
        url = "%s/api/datasets?key=%s&title=%s&exact=true" % (clowder_api_url, api_key, str(dataset_name))

        result_id = __local__.get(url, result_key='id', result_index=0)
        if result_id is None:
            logging.warning("Unable to find the ID for the dataset \"%s\"", dataset_name)

        return result_id

    @staticmethod
    def get_space_id(clowder_api_url: str, api_key: str, space_name: str) -> str:
        """Looks up and returns the ID associated with the Clowder space named
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            space_name(string): the name of the space to fetch the ID of
        Return:
            Returns the ID if the space was found. None is returned otherwise
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        """

        # Make the call to get the ID
        url = "%s/spaces?key=%s&title=%s&exact=true" % (clowder_api_url, api_key, str(space_name))

        result_id = __local__.get(url)
        if result_id is None:
            logging.warning("Unable to find the ID for the space \"%s\"", space_name)
            
        return result_id

    @staticmethod
    def create_space(clowder_api_url: str, api_key: str, space_name: str) -> str:
        """Creates the space in Clowder and returns its ID
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            space_name(string): the name of the space to create
        Return:
            Returns the ID if the space was created. None is returned otherwise
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        """

        # Make the call to create the space
        url = "%s/spaces?key=%s" % (clowder_api_url, api_key)
        post_args = {"headers": {"Content-Type": "application/json"},
                     "data": json.dumps({"name": space_name})
                    }
        
        result_id = __local__.post(url, post_args, result_key='id', result_index=0)
        if result_id is None:
            logging.warning("Unable to determine if space \"%s\" was created", space_name)

        return result_id

    @staticmethod
    def prepare_space(clowder_api_url: str, api_key: str, space_name: str, space_must_exist: bool) -> str:
        """Prepares the Clowder space for the extractor according to the user's wishes
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            space_name(string): the name of the space to create
            space_must_exist(boolean): set to None to create the space name if it doesn't exist,
                                       False if the name must not already exist, and True if the
                                       space name must already exist
        Return:
            Returns the space ID associated with the name or None if the conditions aren't as the
            user requested, or a problem ocurred
        """

        # First check if the space exists
        try:
            space_id = __local__.get_space_id(clowder_api_url, api_key, space_name)
        except requests.HTTPError as ex:
            logging.error("Exception caught while trying to get the ID for space \"%s\"",
                          space_name)
            logging.error("Exception information follows")
            logging.error(str(ex))
            return None
        except Exception as ex:
            logging.warning("An exception was caught while retrieving the ID for space \"%s\" and is being ignored",
                            space_name)
            logging.warning("Exception information follows")
            logging.warning(str(ex))

        # Here we check if the caller cares about the space name existing in Clowder
        if not space_must_exist is None:
            if space_must_exist == (space_id is None):
                if space_must_exist:
                    logging.warning("The space \"%s\" doesn't exist and it should", space_name)
                else:
                    logging.warning("The space \"%s\" exists when it should not", space_name)
                return None

        # We create the space if it doesn't exist already
        if space_id is None:
            try:
                space_id = __local__.create_space(clowder_api_url, api_key, space_name)
            except requests.HTTPError as ex:
                logging.error("Exception caught while trying to create space \"%s\"", space_name)
                logging.error("Exception information follows")
                logging.error(str(ex))
                return None
            except Exception as ex:
                logging.warning("An exception was caught while creating the space \"%s\" and is being ignored",
                                space_name)
                logging.warning("Exception information follows")
                logging.warning(str(ex))
            finally:
                if space_id is None:
                    logging.error("Unable to determine if space \"%s\" creation was a success or not", space_name)
                    return None  # pylint: disable=lost-exception

        return space_id

    @staticmethod
    def checked_remove_file(clowder_api_url: str, api_key: str, dataset_id: str, filename: str) -> bool:
        """Checks for a file in a dataset and deletes it if found
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_id(string): the ID of the dataset to look in for the file
            filename(string): the name of the file to find and remove
        Return:
            Returns True if the file was found and removed. False is returned
            if the file wasn't found
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        """

        # Try to find the file
        url = "%s/api/datasets/%s/files?key=%s" % (clowder_api_url, dataset_id, api_key)

        result_json = __local__.get(url)
        # Try to find the ID
        if not result_json is None:
            for one_file in result_json:
                if 'filename' in one_file and one_file['filename'] == filename:
                    return __local__.remove_file_by_id(clowder_api_url, api_key, one_file['id'])

        logging.warning("Unable to determine if file \"%s\" was removed from dataset %s",
                        filename, dataset_id)
        return False

    @staticmethod
    def remove_file_by_id(clowder_api_url: str, api_key: str, file_id: str) -> bool:
        """Deletes the file identified by its ID
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_id(string): the ID of the dataset to remove the file from
            file_id(string): the ID of the file to remove
        Return:
            Returns True if the file was reported as removed. False is returned otherwise
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        """
        url = "%s/files/%s?key=%s" % (clowder_api_url, file_id, api_key)

        result_status = __local__.delete(url, result_key='status')
        if result_status is None:
            logging.warning("Unable to determine if file %s was deleted", file_id)

        return not result_status is None

    @staticmethod
    def upload_as_file(clowder_api_url: str, api_key: str, dataset_id: str, filename: str, configuration: str) -> str:
        """Uploads a string as a file
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_id(string): the ID of the dataset to create the file in
            filename(string): the name of the file to create
            configuration(string): the formatted configuration string for the file contents
        Return:
            The ID of the uploaded file or None if there was a problem
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            A check is not made for an existing file. This may result in files with the same name
            residing in the dataset
        """

        # Upload the temporary file to the dataset
        result_id = None
        url = "%sapi/uploadToDataset/%s?key=%s&extract=false" % (clowder_api_url, dataset_id, api_key)
        post_args = {"files": {"File": (filename, configuration)}
                    }

        result_id = __local__.post(url, post_args, result_key='id')

        if result_id is None:
            logging.warning("Unable to determine if upload of file \"%s\" with string configuration was successful",
                            filename)

        return result_id

    @staticmethod
    def upload_file(clowder_api_url: str, api_key: str, dataset_id: str, filename: str, config_file: str) -> str:
        """Uploads a string as a file
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_id(string): the ID of the dataset to create the file in
            filename(string): the name of the file to create
            config_file(string): the path to the configuration file to load
        Return:
            The ID of the uploaded file or None if there was a problem
        Exceptions:
            Throws HTTPError if the API request was not successful. A ValueError
            exception is raised if the returned JSON is invalid.
        Notes:
            A check is not made for an existing file. This may result in files with the same name
            residing in the dataset
        """
        tmp_folder = None
        our_filename = config_file
        do_cleanup = lambda folder: shutil.rmtree(folder) if not folder is None else None

        # Determine our file to upload by making sure it's named correctly
        base_filename = os.path.basename(our_filename)
        if base_filename != filename:
            tmp_folder = tempfile.mkdtemp()
            our_filename = os.path.join(tmp_folder, filename)
            shutil.copy(config_file, our_filename)

        # Upload the file to the dataset
        result_id = None
        url = "%sapi/uploadToDataset/%s?key=%s&extract=false" % (clowder_api_url, dataset_id, api_key)
        post_args = {"files": {"File": open(our_filename, 'rb')}}
        try:
            result_id = __local__.post(url, post_args, result_key='id')
        finally:
            # Clean up any temporary files and folders
            do_cleanup(tmp_folder)

        if result_id is None:
            logging.warning("Unable to determine if upload of file \"%s\" as configuration file \"%s\" was successful",
                            filename, config_file)

        return result_id

    @staticmethod
    def start_extractor(clowder_api_url: str, api_key: str, dataset_id: str, extractor_name: str) -> bool:
        """Starts the extractor for the indicated dataset
        Args:
            clowder_api_url(string): the URL to the Clowder instance's API to call
            api_key(string): the key to use when calling the API
            dataset_id(string): the ID of the dataset to create the file in
            extractor_name(string): the Clowder name of the extractor to run
        Return:
            Returns True if the request was successful and False if not
        Exceptions:
            Throws HTTPError if the API request was not successful.
        """
        url = "%s/datasets/%s/extractions?key=%s" % (clowder_api_url, dataset_id, api_key)
        body_params = {'extractor': extractor_name}
        request_headers = {'Content-Type': 'application/json'}
        result = requests.post(url,
                               headers=request_headers,
                               data=json.dumps(body_params))
        result.raise_for_status()

        return result.ok

def prepare_experiment(study_name: str, season: str, timestamp: str) -> dict:
    """Returns a dictionary with the correct experiment configuration
    Args:
        studyName(string): the name of the study
        season(string): the season of the study
        timestamp(string): ISO 8601 timestamp formatted as YYYY-MM-DDThh:mm:ssTZD
    Return:
        A dictionary containing the experiment values
    Notes:
        No checks are made on the values passed in to ensure they conform
    """
    return {
        "studyName": study_name,
        "season": season,
        "observationTimestamp": timestamp
    }

def start_extractor(clowder_url: str, experiment: dict, username: str, password: str, dataset: str,
                    extractor: str, space_name: str, api_key: str = None,
                    space_must_exist: bool = None, config_file: str = None) -> bool:
    """Makes a request to start an extraction job
    Args:
        clowder_url(string): URL to Clowder instance to access
        experiment(dict): dictionary of experiment definition values
        username(string): name of Clowder user
        password(string): password associated with Clowder user
        dataset(string): name of the dataset to associate with the extractor request
        extractor(string): string identifying extractor to run
        space_name(string): name of space to use with extractor
        api_key(string): API key to use when making Clowder API calls
        space_must_exist(boolean): set to None to create the space name if it doesn't exist,
                                   False if the name must not already exist, and True if the
                                   space name must already exist
        config_file(string): path to optional configuration file, or a string to use as
                             configuration, or None for no configuration
    Return:
        True is returned if the request was made and False if there was a problem
    Notes:
        Information is logged when a problem occurs
    """

    space_id = None
    clowder_api = clowder_url + "/api"
    our_api_key = api_key

    # We wrap everything in an try-except block
    try:
        # Get an API key if needed
        if our_api_key is None:
            our_api_key = __local__.get_api_key(clowder_url, username, password)

        # Make sure the dataset exists
        dataset_id = __local__.get_dataset_id(clowder_api, our_api_key, dataset)
        if dataset_id is None:
            return False

        # Make sure we can find the extractor requested
        extractor_name = __local__.find_extractor_name(clowder_api, our_api_key, extractor)
        if not extractor_name:
            return False

        # Get the ID of the space that is named, based upon the specified condition of
        # space_must_exist
        space_id = __local__.prepare_space(clowder_api, our_api_key, space_name,
                                           space_must_exist)
        if not space_id:
            return False

        # Create an in-memory experiment.yaml file: https://osf.io/xdkcy/wiki/Configuration%20YAML/
        experiment_file = io.StringIO()
        experiment_file.write("%YAML 1.1\n---\npipeline:\n")
        for key in experiment:
            experiment_file.write(YAML_INDENT + key + ": " + experiment[key] + "\n")
        experiment_file.write(YAML_INDENT + "clowder:" + "\n")
        experiment_file.write(YAML_INDENT2 + "username: " + username + "\n")
        experiment_file.write(YAML_INDENT2 + "password: " + password + "\n")
        experiment_file.write(YAML_INDENT2 + "space: " + space_id + "\n")

        # Replace/upload the experiment.yaml file
        __local__.checked_remove_file(clowder_api, our_api_key, dataset_id, "experiment.yaml")
        experiment_yaml = experiment_file.getvalue()
        experiment_file.close()
        experiment_file_id = __local__.upload_as_file(clowder_api, our_api_key, dataset_id,
                                                      "experiment.yaml", experiment_yaml)
        if not experiment_file_id:
            return False

        # Replace/upload the extractor-opendronemap.txt file
        extractor_config_file = "extractor-%s.txt" % (extractor)
        if config_file:
            config_file_id = __local__.upload_file(clowder_api, our_api_key, dataset_id,
                                                   extractor_config_file, config_file)
        else:
            config_file_id = __local__.upload_as_file(clowder_api, our_api_key, dataset_id,
                                                      extractor_config_file, "")
        if not config_file_id:
            return False

        # Make the call to start the extractor
        request_id = __local__.start_extractor(clowder_api, our_api_key, dataset_id, extractor_name)
        if not request_id:
            logging.warning("The extractor \"%d\" wasn't started", extractor_name)
            return False
    
    except Exception as ex:
        logging.error("An exception was caught while attempting to schedule extractor \"%s\"",
                      extractor_name)
        logging.error("Exception information follows")
        logging.error(str(ex))
        return False

    return True
