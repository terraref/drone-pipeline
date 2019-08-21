#!/bin/bash

set -ev

# Get the name of the clowder instance
CLOWDER_NAME=$1
if [[ -z "${CLOWDER_NAME}" ]]; then
    CLOWDER_NAME=`docker ps | grep "clowder_1" | sed -r 's/.*(\b.+_clowder_1).*/\1/'`
fi
SLEEP_SECONDS=10

if [[ -z "$CLOWDER_NAME" ]]; then
    echo "Unable to find clowder instance name!"
    exit 1
fi

echo "Clowder name: ${CLOWDER_NAME}"
echo "Sleep time in seconds: ${SLEEP_SECONDS}"

# Wait for clowder to get all started
COUNT=1
for (( ; ; ))
do
    echo "Sleep before checking container: ${COUNT}"
    ((COUNT=COUNT+1))
    sleep "${SLEEP_SECONDS}"
    echo 'docker logs "${CLOWDER_NAME}" 2>&1 | grep "Listening for HTTP on /0.0.0.0:9000"'
    docker logs "${CLOWDER_NAME}" 2>&1 > clog.txt
    RES=`grep "Listening for HTTP on /0.0.0.0:9000" clog.txt || echo ""`
    if [[ -n "${RES}" ]]; then break; fi
    echo "Clowder not ready yet"
    if [[ "${COUNT}" == "10000" ]]; then
        echo "Exceeding wait time limit. Assuming clowder won't ever be ready"
        exit 2
    fi
done

echo "Clowder appears to be up and ready"
