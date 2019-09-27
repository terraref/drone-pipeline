# Canopy Cover by shapefile extractor

Calculate canopy cover on a per-image basis

## Overview

The greenness value is calculated as follows for an entire image:

`sum(green pixels) / (sum(red pixels) + sum(green pixels) + sum(blue pixels))`

## Expected workflow

It is expected that this extractor is triggered when a plot-level image has been uploaded to Clowder.

## Output

Currently the greenness value is stored in two locations: the metadata associated with the dataset the image is in (TODO: and in BETYdb).
