# Copyright (c) 2024  Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
from pymongo import MongoClient

# Configure MongoDB connection
mongodb_host = os.getenv('MONGODB_HOST', 'mongodb://mongo:27017/')
mongodb_name = os.getenv('MONGODB_NAME', 'geo_image_db')
client = MongoClient(mongodb_host)
db = client[mongodb_name]
image_collection = db['images']

# Ensure the collection is indexed for geospatial queries
image_collection.create_index([("location", "2dsphere")])


def get_description_by_lat_lng(lat, lng, floor, max_distance, max_count=0):
    # ...existing code...
    query = {
        'location': {
            '$near': {
                '$geometry': {
                    'type': 'Point',
                    'coordinates': [lng, lat]
                },
                '$maxDistance': max_distance
            }
        }
    }
    if floor:
        query['floor'] = floor
    if max_count:
        locations = list(image_collection.find(query).limit(max_count))
    else:
        locations = list(image_collection.find(query))
    for location in locations:
        location['_id'] = str(location['_id'])
    return locations
