# ElevationServiceTester

Test for bad results and missing data from a GeoJSON elevation lookup service. 

Test works by dividing the planet into 1 degree cells, picking 9 points from each cell, and looking up their elevation.
If no points in a cell are over land the cell will not be looked up.
Whether or not a cell is on land is determined looking up the point in the [Natural Earth 1:10M land dataset](http://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/)

# Usage

`./test.py http://example.com/geojson/`

Results will be saved in a file named status.geojson, and are in the format of a GeoJSON feature collection of polygons, 1 for each cell over land, color coded for status of each cell.
* Cells that returned a server error are colored red.
* Cells that returned an elevation of 0 for all points are colored orange. If all results are 0 it is most likely bad or missing data.
* Cells that returned an elevation other than 0 for at least 1 point are colored green.

 # Acknowledgments
 This was built for testing an elevation service running on [https://github.com/perliedman/elevation-service](https://github.com/perliedman/elevation-service).