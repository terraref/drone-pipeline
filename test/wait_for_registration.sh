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

# Wait for the registration
COUNT=1
for (( ; ; ))
do
    echo "Sleep before checking container: ${COUNT}"
    ((COUNT=COUNT+1))
    sleep "${SLEEP_SECONDS}"

    docker logs "${CLOWDER_NAME}" 2>&1 > rlog.txt
    EADDR=`grep --text -A 10 "test@example\.com" rlog.txt || echo ""`
    if [[ -n "${EADDR}" ]]; then
        REG=`(echo "${EADDR}" | grep "to complete your registration") || echo ""`
        if [[ -n "${REG}" ]]; then
            echo "${REG}" > reg.txt
            break
        fi
    fi
    if [[ "${COUNT}" == "10000" ]]; then
        echo "Exceeding wait time limit. Assuming clowder never got the request"
        exit 2
    fi
done

echo "Found registration line and saved to file 'reg.txt'"
ls -l
