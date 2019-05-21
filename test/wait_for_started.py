#!/usr/bin/env python

"""Waits for the container to get fully started
"""
import os
import re
import sys
import time
import datetime
import subprocess

SLEEP_SECONDS_ID = 5
SLEEP_SECONDS_STARTED = 10
CONTAINER_ID_LOOP_MAX = 10
CONTAINER_STARTED_LOOP_MAX = 10

CONTAINER_NAMED = os.getenv("DOCKER_NAMED_CONTAINER")

# Make sure we're configured correctly
num_args = len(sys.argv)
if num_args < 2:
    raise RuntimeError("Missing the extractor name or its clowder name")

dockerizedName = sys.argv[1].strip()

# Find the ID
dockerId = None
filter_param = ""
if not CONTAINER_NAMED is None:
    filter_param = '--filter "name=' + CONTAINER_NAMED + '"'
bash_cmd = "docker ps " + filter_param + " | grep '" + dockerizedName +"' || echo ' '"
print("Bash command: " + bash_cmd)
for i in range(0, CONTAINER_ID_LOOP_MAX):
    cmd_res = subprocess.check_output(["/bin/bash", "-c", bash_cmd])
    res = str(cmd_res)
    print("Res: "+res)
    if not dockerizedName in res:
        print("Sleeping while waiting for extractor...")
        time.sleep(SLEEP_SECONDS_ID)
    else:
        try:
            dockerId = re.search(r"^\S*", res).group(0).strip()
            if dockerId.startswith("b'"):
                dockerId = dockerId[2:]
        except Exception:
            pass

        if not dockerId is None:
            break

if dockerId is None:
    raise RuntimeError("Unable to find Docker ID of extractor: '" + dockerizedName + "'")

# Loop here until we detect the end of processing
print("Docker id: "+dockerId)
done = False
starttime = datetime.datetime.now()
print("Begining waiting for extractor: " + dockerizedName)
bash_cmd = "docker logs " + dockerId + " 2>&1 | tail -n 50 || echo ' '"
print("Bash command: " + bash_cmd)
for i in range(1, CONTAINER_STARTED_LOOP_MAX):
    cmd_res = subprocess.check_output(["/bin/bash", "-c", bash_cmd])
    res = str(cmd_res)
    print("Result: " + res)
    if "Waiting for messages." in res:
        print("Detected start of waiting for messages")
        sys.exit(0)
    if "exit status" in res:
        print("Extractor status command exited with an error.")
        print("Partial results follows.")
        print(res)
        raise RuntimeError("Early exit from checking docker container status: "  + dockerizedName)
    if "Traceback" in res:
        print("Docker container appears to have thrown an unhandled exception")
        print("Partial results follow.")
        print(res)
        raise RuntimeError("Container threw an exception: " + dockerizedName)
    curtime = datetime.datetime.now()
    timedelta = curtime - starttime
    print("Sleep while waiting on container: " + str(timedelta.total_seconds()) + " elapsed seconds")
    time.sleep(SLEEP_SECONDS_STARTED)
