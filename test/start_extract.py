#!/usr/bin/env python

"""Starts the extract process
"""

import sys
import json
import requests

# Parameter check
argc = len(sys.argv)
if argc < 3:
     raise RuntimeError("Missing one or more parameters of extractor name, or URI for starting" \
                        " an extractor")

# Clarity of parameters byu mapping to names
extractor_name = sys.argv[1]
uri = sys.argv[2]

# Setup and print data
data_load = '{"extractor": "' + extractor_name + '"}'
print("Extractor: '" + extractor_name + "'")
print("URL: " + uri)

# Getting the data to send
json_data = json.loads(str(data_load))
headers = {"accept": "application/json", "Content-Type":"application/json"}

# We try a few times and stuff the queue
for i in range(1, 2):
    print("Sending extract message mumber " + str(i))
    res = requests.post(uri, headers=headers, data=json.dumps(json_data))
    res.raise_for_status()
