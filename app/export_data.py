#!/usr/bin/env python3

import sys
import json
from pymongo import MongoClient

mongo_client = MongoClient('mongodb://mongo:27017/')
db = mongo_client['geo_image_db']
collection = db['images']

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python export_data.py <filepath>')
        sys.exit(1)
    filepath = sys.argv[1]

    entries = list(collection.find({}))
    with open(filepath, "w") as output_stream:
        output_stream.write(json.dumps(entries, default=str))
