# Plot clipping by shapefile extractor

Clip GeoTIFF files according to shapefile geometry

## Overview

Clipping is triggered by a shapefile being added to a dataset.
The clipped files are placed into a new dataset and organized by plot.
Image pixel size is consistency maintained for all clipped images on a per-plot basis.

A date value is used to organize the clipped files.
By default the local machine date for when the clipping was started is used.
To force the date to a certain value, include it in the shapefile name with a leading ' - ' separator.
A trailing ' - ' separator is needed if the date is not the last part of the filename before the file extension.
The date must use a four digit year format and must come first.
The day and month need to be two digits each.
The ISO-8601 standard is used for the format of the short date as follows; YYYY-MM-DD.
For example, "My Shapefile.shp" would become "My Shapefile - 2020-05-10.shp".

By default the plot images are organized by the plot sequence number that is actively clipping images.
The naming of plots can be changed by specifying an associated .dbf file.

If an associated .dbf file is available, the following fields can be used to further refine the clipped file organization:
1. season_name
2. experiment_name
3. plot_name
If any of these fields are missing, it's ignored.
A path for the clipped images is determined based upon these fields, with each field value the name of a folder, followed by the date (as determined above).
For example, `<season name>/<experiment name>/<date>/<plot name>`
Making an associated .dbf file available missing any of these field names causes the default behavior for that field in path naming.

TBD: A mask for each image is generated as well.

TBD: What coordinate systems are supported?
