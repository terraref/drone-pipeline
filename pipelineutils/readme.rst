pipelineutils
=============

Python library for interfacing with the drone pipeline.

This package provides standard functions for interacting with drone pipeline 
services and data.

Primary use case: development of the drone pipeline.

Installation
------------

The easiest way install pipelineutils is using pip and pulling from PyPI.::


    pip install pipelineutils

Because this system is still under rapid development, you may need a
specific branch from the pipelineutils repository. You can either clone the
repository from GitHub and install locally with following commands::

    git clone https://github.com/terraref/drone-pipeline
    git checkout <branch>
    cd drone-pipeline/pipelineutils
    pip install .

Functions and Classes
---------------------

**dronepipeline.py** utilities for interacting with the drone pipeline
