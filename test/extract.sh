#!/bin/bash

set -ev

TAR_FILENAME="$1"
FOLDER_NAME="$2"

# Check parameters
if [[ -z "${TAR_FILENAME}" ]]; then
    echo "Missing first parameter of tar filename"
    exit 1
fi
if [[ -z "${FOLDER_NAME}" ]]; then
    echo "Missing second parameter of destination folder"
    exit 1
fi

# Make the folder for the files
mkdir "${FOLDER_NAME}"

# Check if we are pulling the file from somewhere
if [[ "${TAR_FILENAME}" =~ ^gdrive:* ]]; then
    # We expect the format to be "gdrive:<## file id ##>/<## file name ##>"
    FILEID=`[[ "${TAR_FILENAME}" =~ :(.*)\/ ]] && echo "${BASH_REMATCH[1]}"`
    TAR_FILENAME=`[[ "${TAR_FILENAME}" =~ \/(.*)$ ]] && echo "${BASH_REMATCH[1]}"`
    if [[ -z "${FILEID}" ]]; then
        echo "Missing a file identifier"
        exit 1
    fi
    if [[ -z "${TAR_FILENAME}" ]]; then
        echo "Missing a file name"
        exit 1
    fi
    curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${FILEID}" > /dev/null
    curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${FILEID}" -o "${TAR_FILENAME}"
    rm ./cookie
fi

# Copy the TAR file
cp "${TAR_FILENAME}" "${FOLDER_NAME}/"
cd  "${FOLDER_NAME}"

# Decompress the tar file
if [[ ! -f "./${TAR_FILENAME}" ]]; then
    # The copied file doesn't exist - possibly due to folder structure - so we try to find it
    for fn in *.tar; do
        [[ -f "${fn}" ]] || break
        echo "Checking if file ${fn} matches ${TAR_FILENAME}"
        if [[ "${TAR_FILENAME}" == *"${fn}" ]]; then
            TAR_FILENAME="${fn}"
            break
        fi
    done
fi
tar -x -f "${TAR_FILENAME}"

# Remove the tar file copy
rm "${TAR_FILENAME}"
