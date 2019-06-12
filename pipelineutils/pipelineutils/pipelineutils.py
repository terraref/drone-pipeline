"""Utility functions and classes for accessing the drone pipeline
"""

import requests
import io
import logging

import pyclowder
import terrautils

# Definitions
YAML_INDENT="    "
YAML_INDENT2=YAML_INDENT + YAML_INDENT

"""Class instance wrapping local functions
"""
class __local__(object):
    """Initialize class instance.
    """
    def __init__(self):
        pass
    
    """Returns an API key for the specified user
    Args:
        clowder_url(string): the Clowder URL (make sure it's not the API url)
        username(string): name of Clowder user
        password(string): password associated with Clowder user
    Return:
        A found API key or None if one isn't found
    """
    @staticmethod
    def getApiKey(clowder_url, username, password):
        # Get a key
        url = "%s/api/users/keys" % (clowder_url)
        result = requests.get(url, headers={"Accept": "application/json"}, auth=(username, password))
        result.raise_for_status()

        json_len = len(result.json())
        if json_len > 0:
            return result.json()[0]['key']
        
        return None
    
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
    @staticmethod
    def getDatasetID(clowder_api_url, api_key, dataset_name):
        # Look up the dataset
        url = "%s/api/datasets?key=%s&title=%s&exact=true" % (clowder_api_url, api_key, str(dataset_name))
        result = requests.get(url)
        result.raise_for_status()
        
        # Try to find the ID
        json_len = len(result.json())
        if json_len > 0:
            return result.json()[0]['id']
        
        return None
    
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
    @staticmethod
    def getSpaceID(clowder_api_url, api_key, space_name):
        # Make the call to get the ID
        url = "%s/spaces?key=%s&title=%s&exact=true" % (clowder_api_url, api_key, str(space_name))
        result = requests.get(url)
        result.raise_for_status()

        # Find the ID from a successful call and return it, or return not found value
        json_len = len(result.json())
        if json_len > 0:
            return result.json()[0]['id']
        return None
    
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
    @staticmethod
    def createSpace(clowder_api_url, api_key, space_name):
        # Make the call to create the space
        url = "%s/spaces?key=%s" % (clowder_api_url, api_key)
        result = requests.post(url, headers={"Content-Type": "application/json"},
                               data=json.dumps({"name": space_name}))
        result.raise_for_status()

        # Find the ID from a successful call and return it, or return not found value
        json_len = len(result.json())
        if json_len > 0:
            return result.json()[0]['id']
        return None
    
    """Prepares the Clowder space for the extractor according to the user's wishes
    Args:
        clowder_api_url(string): the URL to the Clowder instance's API to call
        api_key(string): the key to use when calling the API
        space_name(string): the name of the space to create
        space_must_exist(boolean): set to None to create the space name if it doesn't exist,
                                   False if the name must not already exist, and True if the
                                   space name must already exist
    Return:
        Returns the space ID associated with the name or False if the conditions aren't as the user
        requested, or a problem ocurred
    """
    @staticmethod
    def prepareSpace(clowder_api_url, api_key, space_name, space_must_exist):
        # First check if the space exists
        try:
            space_id = __local__.getSpaceID(clowder_api, api_key, space_name)
        except HTTPError as ex:
            # TODO: add logging
            return False
        except Exception as ex:
            # TODO: Replace 'pass' with logging
            pass

        # Here we check if the caller cares about the space name existing in Clowder
        if not space_must_exist is None:
            if space_must_exist == (space_id is None):
                # TODO: add logging
                return False

        # We create the space if it doesn't exist already
        if space_id is None:
            try:
                space_id = __local__.createSpace(clowder_api, api_key, space_name)
            except HTTPError as ex:
                # TODO: add logging
                return False
            except Exception as ex:
                # TODO: Replace 'pass' with logging
                pass
            finally:
                if space_id is None:
                    # TODO: logging
                    return False

        return space_id

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
    @staticmethod
    def checkedRemoveFile(clowder_api_url, api_key, dataset_id, filename):
        # Try to find the file
        url = "%s/api/datasets/%s/files?key=%s" % (clowder_api_url, dataset_id, api_key)
        result = requests.get(url)
        result.raise_for_status()
        
        # Try to find the ID
        json_len = len(result.json())
        if json_len > 0:
            for one_file in result.json():
                if 'filename' in one_file and one_file['filename'] == filename:
                    return __self__.removeFileByID(clowder_api_url, api_key, one_file['id'])

        return False
    
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
    @staticmethod
    def removeFileByID(clowder_api_url, api_key, file_id):
        url = "%s/files/%s?key=%s" % (clowder_api_url, file_id, api_key)
        result = requests.delete(url)
        result.raise_for_status()
        
        # Try to determine success
        json_len = len(result.json())
        if json_len > 0:
            if 'status' in result.json():
                if result.json()['status'] == "success":
                    return True
                
        return False
    
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
def start_extractor(clowder_url, experiment, username, password, dataset, extractor,
                    space_name, api_key=None, space_must_exist=None, config_file=None):
    
    space_id = None
    clowder_api = clowder_url + "/api"
    our_api_key = api_key
    
    # Get an API key if needed
    if our_api_key is None:
        our_api_key = __local__.getApiKey(clowder_url, username, password)
        
    # Make sure the dataset exists
    dataset_id = __local__.getDatasetID(clowder_api, our_api_key, dataset)
    if dataset_id is None:
        return False
    
    # Make sure we can find the extractor requested
    extractor_name = __local__.findExtractor(clowder_api, our_api_key, extractor)
    if not extractor_name:
        return False
    
    # Get the ID of the space that is named, based upon the specified condition of space_must_exist
    space_id = __local__.prepareSpace(clowder_api, our_api_key, space_name, space_must_exist)
    if not space_id:
        return False

    # Create an in-memory experiment.yaml file: https://osf.io/xdkcy/wiki/Configuration%20YAML/
    experiment_file = io.StringIO.StringIO()
    experiment_file.write("%YAML 1.1\n---\npipeline:\n")
    for key in experiment:
        experiment_file.write(YAML_INDENT + key + ": " + experiment[key] + "\n")
    experiment_file.write(YAML_INDENT + "clowder:" + "\n")
    experiment_file.write(YAML_INDENT2 + "username: " + username + "\n")
    experiment_file.write(YAML_INDENT2 + "password: " + password + "\n")
    experiment_file.write(YAML_INDENT2 + "space: " + space_id + "\n")
    
    # Replace/upload the experiment.yaml file
    __local__.checkedRemoveFile(clowder_api, our_api_key, dataset_id, "experiment.yaml")
    experiment_yaml = experiment_file.getvalue()
    experiment_file.close()
    experiment_file_id = __local__.uploadAsFile(clowder_api, our_api_key, dataset_id,
                                                  "experiment.yaml", experiment_yaml)
    if not experiment_file_id:
        return False
    
    # Replace/upload the extractor-opendronemap.txt file
    extractor_config_file = "extractor-%s.txt" % (extractor)
    if config_file:
        config_file_id = __local__.uploadFile(clowder_api, our_api_key, dataset_id,
                                              extractor_config_file, config_file)
    else:
        config_file_id = __local__.uploadAsFile(clowder_api, our_api_key, dataset_id,
                                              extractor_config_file, "")
    if not config_file_id:
        return False
    
    # Make the call to start the extractor
    request_id = __local__.startExtractor(clowder_api, our_api_key, dataset_id, extractor_name)
    if not request_id:
        return False