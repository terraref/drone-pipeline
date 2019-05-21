#!/usr/bin/env python

"""Extracts the results from Clowder
"""

import os
import sys
import json
import requests

clowder_uri = os.getenv("CLOWDER_HOST_URI", "http://localhost:9000")

API_BASE = "%s/api" % (clowder_uri)

# Get the name of the test dataset
fetch_ds_name = None
argc = len(sys.argv)
if argc > 1:
    fetch_ds_name = sys.argv[1]

# Get all the dataset names
key = os.getenv("API_KEY")
KEY_PARAM = "key=%s" % (key)
headers = {"accept": "application/json"}

url = "%s/datasets?%s" % (API_BASE, KEY_PARAM)
res = requests.get(url, headers=headers)
res.raise_for_status()

# Create a storage locations for datasets
destdir = "./datasets"
if not os.path.isdir(destdir):
    os.makedirs(destdir)

# Get all the datasets
return_ds = {}
datasets = res.json()
for ds in datasets:
    if 'name' in ds and 'id' in ds and (fetch_ds_name is None or ds['name'] == fetch_ds_name):
        print("Fetching files for dataset '" + ds['name'])
        url = "%s/datasets/%s/files?%s" % (API_BASE, ds['id'], KEY_PARAM)
        res = requests.get(url, headers=headers)
        res.raise_for_status()

        # Download and store each file in the dataset under the dataset name
        files = res.json()
        print("Dataset files: " + str(files))
        ds_files = []
        for fn in files:
            print("Fetching file: " + fn['filename'])
            url = "%s/files/%s?%s" % (API_BASE, fn['id'], KEY_PARAM)
            res = requests.get(url, stream=True)
            res.raise_for_status()

            filepath = os.path.join(destdir, ds['name'])
            if not os.path.isdir(filepath):
                os.makedirs(filepath)
            dest = os.path.join(filepath, fn['filename'])
            try:
                with open(dest, "wb") as out_file:
                    for chunk in res.iter_content(chunk_size=10*1024):
                        out_file.write(chunk)
            except:
                os.remove(dest)
                raise
            ds_files.append(dest)
        return_ds[ds['name']] = ds_files

print(json.dumps(return_ds))
