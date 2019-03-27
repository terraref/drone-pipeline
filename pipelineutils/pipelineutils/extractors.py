"""Extractor base for drone-pipeline extractors
"""

import os
import re
import requests

from terrautils.extractors import TerrarefExtractor

# Adds additional command line arguments
# pylint: disable=unused-argument
def add_arguments(parser):
    """Adds common arguments to the pipeline extractor
    """
    pass

# Class for drone pipeline extractors
class PipelineExtractor(TerrarefExtractor):
    """Provide common methods for drone pipeline extractors
    """
    def __init__(self):
        """Initialization of class instance
        """
        super(PipelineExtractor, self).__init__()

        add_arguments(self.parser)

    # Performs any additional setup needed
    def setup(self, base='', site='', sensor=''):
        """Performs post-initialization setup of class instance

        Args:
            base(str): optional base path for storing files on disk; starts from the root folder
            site(str): optional location name used to lookup folder and file name formatting
            sensor(str): optional name of primary sensor this extractor represents; used to lookup
                         folder and file name formatting
        """
        super(PipelineExtractor, self).setup(base=base, site=site, sensor=sensor)

    # Date lookup formats property definition
    @property
    def date_format_regex(self):
        """Returns array of regex expressions for different date formats
        """
        # We lead with the best formatting to use, add on the rest
        return [r'(\d{4}(/|-){1}\d{1,2}(/|-){1}\d{1,2})',
                r'(\d{1,2}(/|-){1}\d{1,2}(/|-){1}\d{4})'
               ]

    # Extract the date from a timestamp
    # pylint: disable=too-many-nested-blocks
    def get_datestamp(self, name):
        """Extracts the timestamp from the name. The parts of a date can be separated by
           single hyphens or slashes ('-' or '/') and no white space.

        Args:
            name(str): string to lookup a timestamp in. The first found datestamp is returned.

        Returns:
            The extracted timestamp as YYYY-MM-DD. Throws an exception if the timestamp isn't found

        Exceptions:
            RuntimeError is thrown if a timestamp isn't found

        Notes:
            This function only cares about if the timestamp looks correct. It doesn't
            figure out if month and date are correct. The return string is reformatted if
            the year is in the wrong spot
        """

        formats = self.date_format_regex

        # If there's a date in the dataset name it will be what we use
        dataset_len = len(name)
        if name and isinstance(name, basestring) and dataset_len > 0:
            for part in name.split(" - "):
                for form in formats:
                    res = re.search(form, part)
                    if res:
                        date = res.group(0)
                        if not '-' in date[:4]:
                            return date
                        else:
                            split_date = date.split("-")
                            if len(split_date) == 3:
                                return date[2] + "-" + date[1] + "-" + date[0]

        raise RuntimeError("Invalid name. Needs to include a date such as " +
                           "'My data - YYYY-MM-DD - more text'")

    # Find the user associated with the dataset
    # pylint: disable=no-self-use
    def get_dataset_username(self, host, secret_key, dataset_name):
        """Looks up the name of the user associated with the dataset

        Args:
            host(str): the partial URI of the API path including protocol ('/api' portion and
                       after is not needed); assumes a terminating '/'
            secret_key(str): access key for API use
            dataset_name(str): the name of the dataset belonging to the user to lookup

        Return:
            Returns the registered name of the found user. If the user is not found, None is
            returned. If a full name is available, that's returned. Otherwise the last name
            is returned and/or the first name (either both in that order, or one); a space
            separates the two names if both are concatenated and returned.

        Note:
            Any existing white space is kept intact for the name returned.

        Exceptions:
            HTTPError is thrown if a request fails
            ValueError ia thrown if the server returned data that is not JSON
        """
        # Initialize some variables
        user_id = None
        user_name = None

        # Get all available datasets and try to find a matching name
        url = "%sapi/datasets?key=%s" % (host, secret_key)
        result = requests.get(url)
        result.raise_for_status()

        ret = result.json()
        for one_set in ret:
            if ('name' in one_set) and ('authorId' in one_set):
                if one_set['name'] == dataset_name:
                    user_id = one_set['authorId']
                    break

        if not user_id is None:
            url = "%sapi/users/%s?key=%s" % (host, user_id, secret_key)
            result = requests.get(url)
            result.raise_for_status()

            ret = result.json()
            if 'fullName' in ret:
                user_name = ret['fullName']
            else:
                if 'lastName' in ret:
                    user_name = ret['lastName']
                if 'firstName' in ret:
                    # pylint: disable=line-too-long
                    user_name = ((user_name + ' ') if not user_name is None else '') + ret['firstName']

        return user_name

    # Returns a string that can be used as part of the base path for storing files
    def get_username_with_base_path(self, host, secret_key, dataset_name, base_path=None):
        """Looks up the name of the user associated with the dataset and returns 'unknown'
           if not found

        Args:
            host(str): the partial URI of the API path including protocol ('/api' portion and
                       after is not needed); assumes a terminating '/'
            secret_key(str): access key for API use
            dataset_name(str): the name of the dataset belonging to the user to lookup
            base_path(str): Optional starting path which will have the user name appended

        Return:
            As set of user name and modified base_path.
            The user name as defined in get_dataset_username() with underscores replacing
            whitespace and invalid characters changed to periods ('.'). If a username wasn't
            found by calling get_dataset_username(), the string 'unknown' is returned
            The base_path with the user name appended to it, or None if base_path is None
        """
        try:
            username = self.get_dataset_username(host, secret_key, dataset_name)
        # pylint: disable=broad-except
        except Exception:
            username = None

        # If we don't have a name, see if a username was specified on the command line
        if (username is None) and (not self.clowder_user is None):
            username = self.clowder_user.strip()
            un_len = len(username)
            if un_len <= 0:
                username = None

        # Clean up the string
        if not username is None:
            # pylint: disable=line-too-long
            username = username.replace('/', '.').replace('\\', '.').replace('&', '.').replace('*', '.').replace("'", '.').replace('"', '.').replace('`', '.')
            username = username.replace(' ', '_').replace('\t', '_').replace('\r', '_')
        else:
            username = 'unknown'

        # Build up the path if the caller desired that
        new_base_path = None
        if not base_path is None:
            new_base_path = os.path.join(base_path, username)
            new_base_path = new_base_path.rstrip('/')

        return (username, new_base_path)
