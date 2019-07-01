#!/usr/bin/env python

"""Waits for the extract to finish
"""
import os
import re
import sys
import time
import datetime
import subprocess

SLEEP_SECONDS_ID = 5            # Number of seconds to wait between attempts to get extractor's ID
SLEEP_SECONDS_FINISH = 60       # Number of seconds to wait before chekcing if extractor is complete
CONTAINER_ID_LOOP_MAX = 10      # How many times to loop while attempting to get the container's ID
CONTAINER_FINISH_LOOP_MAX = 5000 # How many times to loop waiting for extractor to complete it's job

CONTAINER_NAMED = os.getenv("DOCKER_NAMED_CONTAINER")

# Make sure we're configured correctly
num_args = len(sys.argv)
if num_args < 2:
    raise RuntimeError("Missing the extractor name")

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
print("Docker id: " + dockerId)
done = False
starttime = datetime.datetime.now()
print("Begining monitoring of extractor: " + dockerizedName)
bash_cmd = "docker logs " + dockerId + " 2>&1 | tail -n 50 || echo ' '"
print("Bash command: " + bash_cmd)
for i in range(1, CONTAINER_FINISH_LOOP_MAX):
    print("Check container...")
    cmd_res = subprocess.check_output(["/bin/bash", "-c", bash_cmd])
    res = str(cmd_res)
    if "StatusMessage.done: Done processing" in res:
        print("Detected end of processing")
        print(res)
        new_bash_cmd = "docker logs " + dockerId + " 2>&1 | grep Traceback || echo ' '"
        cmd_res = subprocess.check_output(["/bin/bash", "-c", new_bash_cmd])
        res = cmd_res.decode("utf-8").strip()
        if res:
            raise RuntimeError("Post-process check: container threw an exception: " + dockerizedName)
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
    time.sleep(SLEEP_SECONDS_FINISH)

curtime = datetime.datetime.now()
timedelta = curtime - starttime
print(res)
raise RuntimeError("Timed out waiting on container: '" + dockerizedName + "' to finish: " + str(timedelta.total_seconds()) + " elapsed seconds")
