# Continuous Integration

We are using Continuous Integration (CI) methodologies coupled with a master/develop/branches GIT topology to manage basic acceptance criteria and respository deployment.

## Overview

The CI tool we are using is [TravisCI](https://travis-ci.com).
Aside from the `.travis.yml` file needed at the root of this resository, this folder contains all the supporting files needed.
This folder will not contain large data files used by the Travis CI builds/jobs or any other build-related files needed to build an extractor from the command line.

It's expected that extractors can be built and deployed without any of the files in this folder through command line and other non-CI tools.
The files in this folder are for supporting the CI environment.

## Approach

The drone-pipeline repository, as well as other TERRA REF repositories, follow a non-standard scheme.
The expected scheme is to have a repository build one system.
The drone-pipeline repository builds at least two extractors located in sub-folders off the top folder.
Each of the extractors is separate from each other and may be built separately as well.

To allow this repository organization to remain effective and to allow minimal CI processing, the following steps were taken:
 1. Require each extractor's branch to contain the name of that extractor as part of the branch name
 2. Require the folder containing the extractor contain the extractor's name
 3. Require each new extractor to be explicitly added to the `.travis.yml` file

Each extractor is expected to have both a source dataset, and a comparison dataset.
The former is used to populate the data needed by the extractor to produce a result.
The second contains the data that is used to confirm the results produced by the extractor from its CI run.

## Builds and Jobs

With TravisCI a build contains one or more jobs and a Job is a series of steps to execute.
There are several ways to split a build into more than one sequential and asynchronous jobs.
We are using the `matrix` approach to the Travis CI configuration which allows jobs to run concurrently.

### Build Matrix

Each extractor has its own named section in the matrix portion of the Travis CI YAML file.
It's expected that each of these sections contains all the extractor specific information needed by the job.
The matrix configuration is used because it allows multiple extractors to be built and testing concurrently, which is helpful for the develop and master branches of the tree.
Travis CI allows jobs to run concurrently and consecutively in different build stages.
Making use of these, and other, Travis CI features is encouraged.

Each extractor in the build matrix is given a meaningful and unique name; for example, "OpenDroneMap Extractor".
In addition to the name, there are environment variables that need to be set, as well as a test condifion for building the extractor.
The required environmental variables are as follows. Other extractor-specific environment variables can also be defined.
* EXTRACTOR_BRANCH - the key tag associated with the extractor. Used in branch and folder detection as described in the **Approach** section above
* TEST_SOURCE_ARCHIVE - the name of the .tar archive containing input files to the extractor test
* TEST_COMPARE_ARCHIVE - the name of the .tar archive contining comparison files used to test the extractor's results
* EXTRACTOR_MASTER_DOCKERHUB_NAME - the tag used when pushing a successfully built and tested extractor to DockerHub. Only used when referencing the *master* branch

The test condition is used to determine if an extractor job should be started.
This allows a more inclusive overall build environment to be specified while only running extractor jobs as needed.
For example, the build may exclude any branches that are for testing while the test conditions in the matrix only run an extractor's jobs when an appropriate branch is pushed.

The following condition will build the OpenDroneMap extractor when the *master* or *develop* branches are pushed, as well as any branches that have `opendronemap` or `odm` in their names, or a branch name includes the key `travis`.
```if: branch = master OR branch = develop OR branch =~ /.*opendronemap.*/ OR branch =~ /.*odm.*/ OR branch =~ /.*travis.*/```

As sample matrix inclusive entry is as follows:
```
    - name: "OpenDroneMap Extractor"
      env: EXTRACTOR_BRANCH=opendronemap
      env: TEST_SOURCE_ARCHIVE=odm_test_data.tar
      env: TEST_COMPARE_ARCHIVE=odm_results.tar
      env: EXTRACTOR_MASTER_DOCKERHUB_NAME=chrisatua/extractors:opendronemap
      if: branch = master OR branch = develop OR branch =~ /.*opendronemap.*/ OR branch =~ /.*odm.*/ OR branch =~ /.*travis.*/
```

### Job steps

Each of the non-configuration commands is intended to be run for each job.
Customization for any particular extractor is not considered desireable, but is allowed as described below.
The build name (GIT branch or tag name) is used to determine specfics for each step of a job.
Example of this are: determining the folder associated with an extractor, and other discovery actions based upon the build name and extractor.

### Extractor Specific Steps

Each job is run using a common environment configuration.
While the common environment may be sufficient for most jobs, sometimes additional work needs to be done that's relevant for only one extractor.

If an expectractor's build needs to run specific commands for only that extractor, it's expected that a script is used.
The script needs to first confirm that the job is specificly for the targetted extractor and no other; the script will be called multiple times (once per job for example) and should only do work for the correct extractor.
The script will immediately return successfully once it determines the current job is not for the expected extractor.
When a scribpt determines that the job is for the expected extractor, normal processing ocurrs along with normal success and failure conditions.

Extractor specific scripts can perform actions such as downloading and installing additional libraries and tools, and perform other unique tasks.

## Data Archive Files

As part of a build, extractors are built and run.
The extractors need data to process, and after running, their results need to be tested.
This data is provided to the build through [TAR](https://linux.die.net/man/1/tar) archive files.
Two environment variables (TEST_SOURCE_ARCHIVE and TEST_COMPARE_ARCHIVE), as described above, are used to identify these archives for each extractor.
The source archive expects a flat layout of the files to use as input to testing the extractor.
The compare archive can have a flat layout, or contain folders.
The layout of the compare archive is flat when the extractor's results are only in one dataset.
The compare archive contains folders when the extractor's results are contained in more than one dataset.
