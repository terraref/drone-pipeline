import os
from osgeo import gdal, ogr
from dbfread import DBF

dbffile = "Season5_wheat_1row_Subplots - Copy.dbf"

print "File: "+dbffile
shape_table = DBF(dbffile, lowernames=True, ignore_missing_memofile=True)
shape_rows = iter(list(shape_table))
column_names = shape_table.field_names
for one_name in column_names:
    print " " + one_name

plot_name_idx = "id"

dbf_rows = 0
while shape_rows:
    try:
        row = next(shape_rows)
        dbf_rows += 1
#        print row[plot_name_idx]
    except StopIteration:
        print "End of loop"
        break

shapefile = "Season5_wheat_1row_Subplots - Copy.shp"
shape_in = ogr.Open(shapefile)
layer = shape_in.GetLayer(os.path.split(os.path.splitext(shapefile)[0])[1])
poly = layer.GetNextFeature()
shp_rows = 0
while poly:
    shp_rows += 1
    poly = layer.GetNextFeature()

print "Rows: " + str(dbf_rows) + " vs " + str(shp_rows)

print "Done"
