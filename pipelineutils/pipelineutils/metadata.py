#!/usr/bin/env python

'''Metadata utilities for the drone pipeline
'''

from terrautils.extractors import load_json_file
from terrautils.metadata import get_terraref_metadata, get_season_and_experiment

# pylint: disable=invalid-name

# Returns any found season, experiment, and timestamp
def season_experiment_timestamp_from_metadata(json_file, default_season_name,
                                              default_experiment_name, default_timestamp,
                                              dataset_name=None):
    """Looks through the JSON file for dataset information and pipeline information

    Args:
        json_file(str): path to the JSON file to load
        default_season_name(str): default season value if not found in JSON
        default_season_name(str): default season value if not found in JSON
        default_experiment_name(str): default experiment value if not found in JSON
        default_timestamp(str): default timestamp value if not found in JSON
        dataset_name(str): Optional name of a dataset to use to perform a lookup
                           (used for Terra Ref compatibility)

    Return:
        A list of the season name, experiment name, timestamp, and pipeline JSON are
        returned.

    Note:
        If both Terra Ref and pipeline data are available in the JSON (and the dataset_name is
        specified), the Terra Ref data is searched first, followed by the pipeline data. The
        pipeline data fields will override any Terra Ref fields. If only Terra Ref or only
        pipeline metadata is found, then those fields will be returned. If nothing is found,
        the default values are returned.

        Pipeline JSON is only returned if it's found in the JSON file. Dataset JSON will not
        be returned
    """

    # Default our return variables
    # pylint: disable=line-too-long
    (ret_season, ret_experiment, ret_timestamp) = (default_season_name, default_experiment_name, default_timestamp)
    # pylint: enable=line-too-long
    ret_json = None

    # Load the file as JSON and extract information from it
    try:
        dataset_json = load_json_file(json_file)
        if not dataset_json is None:
            # If we have a dataset name then we can look for, and use, Terra Ref data
            if not dataset_name is None:
                terra_md_full = get_terraref_metadata(dataset_json)
                if terra_md_full:
                    timestamp = dataset_name.split(" - ")[1]
                    # pylint: disable=line-too-long
                    (season_name, experiment_name, _) = get_season_and_experiment(timestamp, 'plotclipper', terra_md_full)
                    # pylint: enable=line-too-long
                    # Only set the timestamp if we have found meaningful data
                    if season_name != 'Unknown Season':
                        ret_season = season_name
                        ret_timestamp = timestamp
                    if experiment_name != 'Unknown Experiment':
                        ret_experiment = experiment_name
                        ret_timestamp = timestamp
    # pylint: disable=broad-except
    except Exception:
        pass

    # Stored pipeline data overrides Terra Ref data
    try:
        if not dataset_json is None:
            ret_json = pipeline_get_dataset_metadata(dataset_json)
            if ret_json:
                # pylint: disable=line-too-long
                (season_name, experiment_name, timestamp) = pipeline_get_season_experiment_timestamp(ret_json)
                # pylint: enable=line-too-long
                if not season_name is None:
                    ret_season = season_name
                if not experiment_name is None:
                    ret_experiment = experiment_name
                if not timestamp is None:
                    ret_timestamp = timestamp
    # pylint: disable=broad-except
    except Exception:
        pass

    return (ret_season, ret_experiment, ret_timestamp, ret_json)

def pipeline_get_dataset_metadata(check_json):
    """Searches the JSON for pipeline data

    Args:
        check_json(JSON): the JSON, or list of JSON, to search

    Return:
        The found JSON is returned, otherwise None is returned.

    Note:
        The JSON passed in is assumed to be iterable (as in an array).

        There are two keys looked for off the JSON passed in, as follows, in order:
            1) "content" -> "pipeline"
            2) "pipeline"
    """
    found_metadata = None

    # Look for a list of JSON
    if isinstance(check_json, list):
        for one_metadata in check_json:
            if 'content' in one_metadata:
                if 'pipeline' in one_metadata['content']:
                    found_metadata = one_metadata['content']['pipeline']
                    break

        if found_metadata is None:
            for one_metadata in check_json:
                if 'pipeline' in one_metadata:
                    found_metadata = one_metadata['pipeline']
                    break

    elif 'pipeline' in check_json:
        found_metadata = check_json['pipeline']

    return found_metadata

# Returns season, experiement, and timestamp from json
def pipeline_get_season_experiment_timestamp(pipeline_json):
    """Returns the found season, experiment, and timestamp

    Args:
        pipeline_json(JSON): the JSON to search

    Return:
        Returns the found season, experiment, and timestamp.

    Note:
        None is returned for any fields that are not found
    """
    (ret_season, ret_experiment, ret_timestamp) = (None, None, None)

    if 'season' in pipeline_json:
        ret_season = pipeline_json['season']
    if 'studyName' in pipeline_json:
        ret_experiment = pipeline_json['studyName']
    if 'observationTimeStamp' in pipeline_json:
        ret_timestamp = pipeline_json['observationTimeStamp']

    return (ret_season, ret_experiment, ret_timestamp)
