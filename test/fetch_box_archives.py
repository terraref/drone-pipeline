#!/usr/bin/env python

"""Pulls files from Box
"""
import sys
import os

from boxsdk import JWTAuth
from boxsdk import Client

BOX_CONFIG = os.getenv("BOX_CONFIG_FILE", "box.json")

# Make sure we have files to download
argc = len(sys.argv)
if argc < 2:
    print("No filenames specified on the command line to download")
    sys.exit(0)

def get_id_from_folder(boxclient, parent_id, item_name, item_type='folder'):
    """Retrieves the contents of a parent folder looking for a sub folder
    Args:
        boxclient(obj): the Box client instance
        parent_id(str): the ID of the parent folder
        item_name(str): the name of the item we're trying to find
        item_type(str): one of 'file' or 'folder'. Defaults to 'folder'
    Return:
        The ID of the found item. None is returned if there's a problem or the item
        name wasn't found in the parent folder
    """
    folder_list = boxclient.folder(folder_id=str(parent_id)).get()
    if not folder_list:
        return None
    if not 'item_collection' in folder_list:
        return None
    if not 'entries' in folder_list['item_collection']:
        return None

    for entry in folder_list['item_collection']['entries']:
        if 'name' in entry and 'type' in entry:
            if entry['name'] == item_name and entry['type'] == item_type:
                return entry['id']

    return None

# Authentication from settings file
box_auth = JWTAuth.from_settings_file(BOX_CONFIG)

# Get auth client
box_client = Client(box_auth)

# Loop through the arguments downloading the files
for idx in range(1, argc):
    # Get the filename to download and the path
    file_path = sys.argv[idx]
    filefolder, filename = os.path.split(file_path)
    if not filename:
        print("An invalid file download was requested: '" + file_path + "'")
        continue

    # Find the ID of the folder the file is to be in
    folder_id = "0"
    if filefolder:
        parts = filefolder.split('/')
        for one_folder in parts:
            folder_id = get_id_from_folder(box_client, folder_id, one_folder, item_type='folder')
            if not folder_id:
                break

    if not folder_id:
        print("Folder not found in Box: '" + file_path + "'")
        continue

    # Get the ID of the file
    file_id = get_id_from_folder(box_client, folder_id, filename, item_type='file')
    if not file_id:
        print("File name not found in folder: '" + file_path + "'")

    # Download the file
    # We use the box file name instead of our name so that the search for the correct
    # file can be changed if needed (to include regular expressions, for example)
    box_file = box_client.file(file_id=file_id).get()
    with open(box_file.name, 'wb') as output_file:
        box_file.download_to(output_file)
