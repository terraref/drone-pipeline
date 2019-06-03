# pipelineutils
## Done Pipeline Utilities
Python library for drone-pipeline specific modules and methods that are shared by multiple extractors

### extractors.py
* PipelineExtractor - Common pipeline extractor classs other extractors can descend from

## Distributing Updates
As needs arise this library will change to address those needs.
This section lists the commands needed build and publish an updated library

The following steps need to be done:
1. Setup the build envorinment
2. Build the library
3. Optional, install locally
4. Push to PyPi

### Setup the build environment
There are two folders that are created with building a library that should be removed.
These are the 'dist' and 'build' folders.
Removing them ensures that only the current version of the library is referenced for uploading and installing.

Also be sure to update the version number in the `setup.py` file following the project numbering conventions.

### Build the library
To build the library the following command is used:
`python setup.py sdist bdist_wheel`

### Install locally
The following command installs the release locally (replace `<version>` with the actual version number): 
`sudo -H pip install -U pipelineutils==<version>`

### Push to PyPi
Run the following command to push the library to the PyPi repository:
`sudo -H python -m twine upload dist/*`

Refer to the PyPi [website](https://pypi.org) for the latest information
