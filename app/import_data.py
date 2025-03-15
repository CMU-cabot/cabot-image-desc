#!/usr/bin/env python3

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
import sys
import json
from pymongo import MongoClient
from bson import ObjectId


# Configure MongoDB connection
mongodb_host = os.getenv('MONGODB_HOST', 'mongodb://mongo:27017/')
mongodb_name = os.getenv('MONGODB_NAME', 'geo_image_db')
client = MongoClient(mongodb_host)
db = client[mongodb_name]
collection = db['images']


def import_data(filepath):
    with open(filepath) as input_stream:
        for entry in json.load(input_stream):
            id = entry["_id"]
            entry["_id"] = ObjectId(id)
            collection.replace_one({"_id": entry["_id"]}, entry, upsert=True)
            print(f"{id} upserted")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python script.py <image_filepath>')
        sys.exit(1)

    import_data(sys.argv[1])
