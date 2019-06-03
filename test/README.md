# Continuous Integration

We are using Continuous Integration (CI) methodologies coupled with a master/develop/branches GIT topology to manage basic acceptance criteria and respository deployment.

## Overview

The CI tool we are using is (TravisCI)[https://travis-ci.com].
Aside from the `.travis.yml` file needed at the root of this respoitory, this folder contains all the supporting files needed.
This folder will not contain large data files used by the Travis CI builds/jobs or any build related files needed to build an extractor from the command line.

It's expected that extractors can be built and deployed without any of the files in this folder using command line tools.
The files in this folder are for supporting the CI system used.

## Approach

The drone-pipeline repository, as well as other TERRA REF repositories, follow a non-standard scheme.
The expected method is to have a repository build one system.
The drone-pipeline repository builds at least two extractors located in sub-folders off the top folder.
Each of these extractors is separate from each other and may be built separately as well.

To allow this repository organization to remain effective and to allow minimal CI processing, the following steps were taken:
- 1) Require each extractor's branch to contain the name of that extractor as part of the branch name
- 2) Require the folder containing the extractor contain the extractor's name
- 3) Require each new extractor to be explicitly added to the `.travis.yml` file

