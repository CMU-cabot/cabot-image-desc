#!/usr/bin/env python3

import os
import sys
import json
from pymongo import MongoClient

mongodb_host = os.getenv('MONGODB_HOST', 'mongodb://mongo:27017/')
mongodb_name = os.getenv('MONGODB_NAME', 'geo_image_db')
client = MongoClient(mongodb_host)
db = client[mongodb_name]
collection = db['images']

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python export_data.py <filepath>')
        sys.exit(1)
    filepath = sys.argv[1]

    entries = list(collection.find({}))
    with open(filepath, "w") as output_stream:
        output_stream.write(json.dumps(entries, default=str))
