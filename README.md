# Drone Pipeline

Generalizing the TERRA REF pipelines for processing data from UAV's

## Overview

This project is leveraging the work done in the TERRA REF project to create a drone-specific processing pipeline for plant based analysis.
It assumes you are familiar with [Clowder's](https://opensource.ncsa.illinois.edu/bitbucket/projects/CATS) concepts of extractors.

### Challenges

There are several challenges to adapting the pipeline to work with drone data.
Among these challenges are:
* unique workflows
* emerging standards
* leveraging third party software
* different data storage layouts and access mechanisms
* widely differing processing environments (single laptops to HPCs)
* changing technological landscape (new programming languages, new algorithms, and machine learning to name some)

### Goals

By setting the appropriate development goals, it's believed the above challenges can be addressed in a way that provides relevance into the future.
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

[User stories](https://github.com/terraref/drone-pipeline/issues/new/choose) are used to define the goals and needs of drone pipeline users.

## Code Of Conduct
Follow the link to read our [Code of Conduct](https://github.com/terraref/drone-pipeline/CODEOFCONDUCT.md) stored on our GitHub repository.

## Contributing

Please read [CONTRIBUTING.md](https://github.com/terraref/drone-pipeline/CONTRIBUTING.md) for details on how anyone can contribute to this project.

## Versioning 

We are following [Semantic Versioning](https://semver.org/) for version numbers. 
Note that a tag may contain older code for what you are interested in since only changed extractors/sub-projects are built for any tag.

## Authors

* Dr. David Shaner LeBauer - Principal Architect and visionary - University of Arizona
* Christophe Schnaufer - Lead Developer - University of Arizona

We are building off the efforts of the [TERRA REF](https://github.com/terraref) folks.
Here are some of the contributors to that effort in first name order:
* [Charlie Zender](https://github.com/czender)
* [Craig Willis](https://github.com/craig-willis)
* [Max Burnette](https://github.com/max-zilla)
* [Nick Heyek](https://github.com/nheyek)
* [Rob Kooper](https://github.com/robkooper)
* [ZongyangLi](https://github.com/ZongyangLi)

There are many others that have contributed, so head over to the project and check them out.

## Acknowledgments

The [CONTRIBUTORS.md](https://github.com/terraref/drone-pipeline/CONTRIBUTORS.md) file contains the list of contributors that wish to be acknowledged.
