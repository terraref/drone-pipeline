#!/bin/bash

set -ev

# Make the folder for the data files
mkdir compare

# Copy and decompress the TAR file
cp $1 compare/
cd  compare
tar -xv -f $1

# Remove the tar file copy
rm $1

