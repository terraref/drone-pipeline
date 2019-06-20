#!/usr/bin/env python

"""Registers the extractor using the file passed in as a parameter
"""
import sys
import os
import json
import requests

# Load the extractor JSON
reg_data = None

num_args = len(sys.argv)
if num_args < 2:
    raise RuntimeError("Missing file name of extractor registration JSON")

if not os.path.isfile(sys.argv[1]):
    raise RuntimeError("Extractor registration JSON file was not found")

try:
    with open(sys.argv[1]) as in_file:
        reg_data = json.load(in_file)
except Exception:
    pass

if not reg_data:
    raise RuntimeError("Extractor registration JSON file is empty or invalid")

# Register the extractor
key = os.getenv("API_KEY")
clowder_uri = os.getenv("CLOWDER_HOST_URI", "http://localhost:9000")

url = "%s/api/extractors?key=%s" % (clowder_uri, key)
headers = {"accept": "application/json", "Content-Type": "application/json"}

res = requests.post(url, headers=headers, data=json.dumps(reg_data))
res.raise_for_status()

print("Extractor registration result: " + str(res.content))
