#!/usr/bin/env python

"""Simple python file to upload files to a dataset
"""
import sys
import os
import requests

# pylint: disable=invalid-name

# Get the list of files to upload
data_path = "./data"
files = [os.path.join(data_path, f) for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f))]
num_files = len(files)
if num_files <= 0:
    sys.exit(0)

# Prepare to upload the files
key = os.getenv("API_KEY")
dataset = os.getenv("DATASET_ID")
clowder_uri = os.getenv("CLOWDER_HOST_URI", "http://localhost:9000")

print("API KEY: "+key)
print("DATASET ID: "+dataset)
print("CLOWDER URI: "+clowder_uri)

url = "%s/api/datasets" % (clowder_uri)
headers = {"accept": "application/json"}
res = requests.get(url, headers=headers, auth=("test@example.com", "testPassword"))
res.raise_for_status()
print("Current datasets: "+str(res.content))

url = "%s/api/uploadToDataset/%s?extract=false&key=%s" % (clowder_uri, dataset, key)
headers = {"accept": "application/json"}

print ("URL: "+url)
print("Headers: "+str(headers))
for one_file in files:
    base_name = os.path.basename(one_file)
    if base_name[0] == '.':
        print("Skipping hidden file '" + one_file + "'")
        continue

    print("Attempting upload of file '" + one_file + "'")
    with open(one_file, 'rb') as fh:
        res = requests.post(url, headers=headers, files={"File": (os.path.basename(one_file), fh)})
        res.raise_for_status()
