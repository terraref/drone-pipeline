# Drone Pipeline

Generalizing the TERRA REF pipelines for processing data from UAV's

## Overview

This project is leveraging the work done in the TERRA REF project to create a drone-specfic processing pipeline for plant based analysis.
It assumes you are familiar with [Clowder's][https://opensource.ncsa.illinois.edu/bitbucket/projects/CATS] concepts of extractors.

### Challenges

There are several challenges to adapting the pipeline to work with drone data.
Among these challenges are:
* unique workflows
* emerging standards
* leveraging third party softwere
* different data storage layouts and access mechanisms
* widely differing processing environments (single laptops to HPCs)
* changing technologial landscape (new programming languages, new algorithms, and machine learning to name some)

### Goals

By setting the appropriate development goals it's believed the above challenges can be addressed in a way that provides relevance into the future.
These goals are:
* commonality - use, and allow the use of, standards wherever possible
* customization - ability to conform the drone pipelines to an individual's or group's needs
* simplicity - make it as simple as possible to use and customize the pipeline
* flexibility - provide common pipeline elements while allowing situational uniqueness; not everyones needs are the same

### Approach

To provide a meaningful pipeline as quickly as possible, an iterative approach is being taken.
This approach will restrict the achievement of the goals in the short term, but will not prevent their completion in the future.
For example, a custom pipeline job submission API may not be available immediately, but hand-driven custom pipeline processing could be.

## User Stories

[User stories][https://github.com/terraref/drone-pipeline/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+label%3A%22user+story%22] are used to define the goals and needs of drone pipeline users.

## Contributing

Please read [CONTRIBUTING.md][https://github.com/terraref/drone-pipeline/blob/opendronemap/CONTRIBUTING.md] for details on our Code Of Conduct, the process of submitting pull requests, and other details.

## Versioning 

We are following [Semantic Versioning][https://semver.org/] for version numbers. 
Note that a tag may contain older code for what you are interested in since only changed extractors/sub-projects are built for any tag.

## Authors

* Dr. David Shaner LeBauer - Principal Architect and visionary - University of Arizona
* Christophe Schnaufer - Initial contributor - University of Arizona

## Acknowledgments

The [CONTRIBUTORS.md][https://github.com/terraref/drone-pipeline/blob/opendronemap/CONTRIBUTORS.md] file contains the list of contributors that wish to be acknowledged.
