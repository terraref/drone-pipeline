# Open Drone Map Extractor

Open Drone Map Orthomosaic, LAZ, and boundary shape file extractor

## Authors:

* Christophe Schnaufer, University of Arizona, Tucson AZ

## Overview

This extractor uses Open Drone Maps to create a geo-referenced orthomosaic of the source images along with a LAZ point cloud file. 
A shapefile of the boundary of the data in the orthmosaic and point cloud data is also produced.
This extractor uses the Clowder OpenDroneMap extractor as its starting point.

_Input_

  - Evaluation is triggered when a file named 'extractors-opendronemap.txt' is placed into a dataset
  - All JPEG images in the dataset containing the 'extractors-opendronemap.txt' file are used

_Output_

  - A dataset each for the orthomosaic, pointcloud, and shapefile data

## Application

### Docker

The Dockerfile included in this directory can be used to build this extractor in a container.

_Building the Docker image_

```sh
docker build -f Dockerfile -t terra-odm.
```

_Running the image locally_
```sh
docker run \
  --add-host="localhost:{LOCAL_IP}" \
  -e 'RABBITMQ_URI=amqp://rabbitmq/%2F' \
  -e 'RABBITMQ_EXCHANGE=clowder' \
  -e 'REGISTRATION_ENDPOINTS=http://localhost:9000/clowder/api/extractors?key={SECRET_KEY}' \
  -e 'TZ=/user/share/zoneinfo/US/Central' \
  -e 'CLOWDER_USER={CLOWDER_USER_EMAIL}' \
  -e 'CLOWDER_PASS={CLOWDER_USER_PASSWORD}' \
  -e 'CLOWDER_SPACE={DESTINATION_SPACE}' \
  terra-odm
```
Note that by default RabbitMQ will not allow "guest:guest" access to non-local addresses, which includes Docker. You may need to create an additional local RabbitMQ user for testing.

_Running the image remotely_
```sh
docker run \
  -e 'RABBITMQ_URI=amqp://{RMQ_USER}:{RMQ_PASSWORD}@rabbitmq.ncsa.illinois.edu/clowder' \
  -e 'RABBITMQ_EXCHANGE=terra' \
  -e 'REGISTRATION_ENDPOINTS=http://terraref.ncsa.illinosi.edu/clowder//api/extractors?key={SECRET_KEY}' \
  -e 'TZ=/user/share/zoneinfo/US/Central' \
  -e 'CLOWDER_USER={CLOWDER_USER_EMAIL}' \
  -e 'CLOWDER_PASS={CLOWDER_USER_PASSWORD}' \
  -e 'CLOWDER_SPACE={DESTINATION_SPACE}' \
  terra-odm
```

### Dependencies

* All the Python scripts syntactically support Python 2.7 and above. Please make sure that the Python in the running environment is in appropriate version.

## Failure Conditions

### Image Stitching Artifacts

Refer to OpenDroneMap's web site for information on artifacts on image stitching 
