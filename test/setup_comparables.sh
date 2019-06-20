#!/bin/bash

set -ev

# Make the folder for the data files
mkdir compare

# Copy and decompress the TAR file
cp $1 compare/
cd  compare

# Decompress the tar file
TAR_FILENAME="$1"
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
tar -xv -f "${TAR_FILENAME}"

# Remove the tar file copy
rm "${TAR_FILENAME}"

