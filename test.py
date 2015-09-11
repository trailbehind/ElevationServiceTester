#!/usr/bin/env python

import logging
from optparse import OptionParser
import os
import requests
import json
import fiona
from shapely.geometry import Point, shape
from shapely.prepared import prep
import sys

SUCCESS_COLOR = '#8FD933'
POSSIBLE_ERROR_COLOR = '#FF9300'
ERROR_COLOR = '#FF0000'

def run_tests(bbox, service_url, status_path=None):    
    with fiona.open('ne_10m_land.geojson', 'r') as source:
        n = source.next()
        land_polygon = prep(shape(n['geometry']))

    features = []
    session = requests.Session()

    for lon in range(bbox[0], bbox[2]):
        for lat in range(bbox[1], bbox[3]):

            test_coords = []
            for x_offset in range(1,4):
                for y_offset in range(1,4):
                    test_coords.append((lon + x_offset/4.0, lat + y_offset/4.0))

            point_on_land = False
            for coord in test_coords:
                point = Point(coord[0], coord[1])
                if land_polygon.contains(point):
                    point_on_land = True
                    break

            if not point_on_land:    
                logging.debug("No points on land, %f,%f" % (lon, lat))
                continue

            hgt_filename = '%s%02i%s%03i.hgt' % ( 'N' if lat > 0 else 'S', abs(lat), \
                'W' if lon < 0 else 'E', abs(lon))
            
            elevation = test(test_coords, service_url, session=session)
            logging.debug("%i, %i response:%i" % (lon, lat, elevation))
            color = SUCCESS_COLOR
            if elevation == -9999:
                logging.info("fail %i,%i" % (lon, lat))
                color = ERROR_COLOR
            elif elevation == 0:
                logging.info("maybe fail %i,%i" % (lon, lat))
                color = POSSIBLE_ERROR_COLOR
            status_feature = {
                'type': 'Feature',
                'properties' : {
                    'result': elevation,
                    'hgt': hgt_filename,
                    'points': ";".join([",".join([str(f) for f in c]) for c in test_coords]),
                    'fill-opacity': 0.5,
                    'fill': color,
                    'stroke': '#000000',
                    'stroke-width': 1
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates' : [[
                        [lon, lat], 
                        [lon, lat + 1], 
                        [lon + 1, lat + 1],
                        [lon + 1, lat],
                        [lon, lat]
                    ]]
                }
            }
            features.append(status_feature)
            if status_path is not None and len(features) % 100 == 0:
                write_feature_collection(features, path=status_path)

    if status_path is not None:
        write_feature_collection(features, path=status_path)


def write_feature_collection(features, path):
    feature_collection = {
        'type': 'FeatureCollection',
        'features' : features
    }
    with open(path, 'wb') as f:
        json.dump(feature_collection, f, separators=(',', ': '), indent=4)


def test(coordinates, service_url, session=None):
    feature = {
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates' : coordinates
        }
    }
    json_feature = json.dumps(feature)
    logging.debug("requesting " + json_feature)
    if session:
        r = session.post(service_url,
            data=json_feature, 
            headers={
                'content-type': 'application/json'
            })
    else:
        r = requests.post(ELEVATION_SERVICE_URL,
            data=json_feature, 
            headers={
                'content-type': 'application/json'
            })

    logging.debug("response " + r.text)
    if r.status_code != 200:
        logging.error("%i,%i status code:%i" % \
            (coordinates[0][0], coordinates[0][1], r.status_code))
        return -9999

    response_data = r.json()
    if not response_data['geometry'] or \
        not response_data['geometry']['coordinates'] or \
        len(response_data['geometry']['coordinates']) != len(coordinates) or \
        len(response_data['geometry']['coordinates'][0]) != 3:
        logging.error("Unexpected response format %s" % (r.text))
        return -9999

    elevations = [x[2] for x in response_data['geometry']['coordinates']] 
    return max(elevations)


def _main():
    usage = "usage: %prog http://example.com/geojson/"
    parser = OptionParser(usage=usage,
                          description="")
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="Turn on debug logging")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                      help="turn off all logging")
    parser.add_option("-b", "--bounds", action="store", dest="bounds",
                      help="BBOX to test, in W,S,E,N format",
                      default="-180,-80,180,80")
    parser.add_option("-o", "--output", action="store", dest="output",
                      help="output file", default="status.geojson")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        logging.error("Server url missing")
        sys.exit(-1)

    logging.basicConfig(level=logging.DEBUG if options.debug else
    (logging.ERROR if options.quiet else logging.INFO))

    bounds_components = options.bounds.split(",")
    if len(bounds_components) != 4:
        logging.error("Bounds must have 4 components")
        sys.exit(-1)

    bounds = [int(f) for f in bounds_components]
    for i in [0, 2]:
        if bounds[i] < -180 or bounds[i] > 180:
            logging.error("bounds component %i out of range -180 to 180" % (i + 1))
            sys.exit(-1)

    for i in [1, 3]:
        if bounds[i] < -90 or bounds[i] > 90:
            logging.error("bounds component %i out of range -90 to 90" % (i + 1))
            sys.exit(-1)

    run_tests(bounds, args[0], status_path=options.output)

if __name__ == "__main__":
    _main()
