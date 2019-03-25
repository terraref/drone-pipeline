"""Extractor base for drone-pipeline extractors
"""

import re

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
