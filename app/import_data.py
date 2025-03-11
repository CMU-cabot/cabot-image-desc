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

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python script.py <image_filepath>')
        sys.exit(1)

    filepath = sys.argv[1]

    with open(filepath) as input_stream:
        data = json.load(input_stream)

    for entry in data:
        id = entry["_id"]
        location = collection.find_one({"_id": ObjectId(id)})
        if location:
            update = {}
            for key in entry.keys():
                if key not in location or location[key] != entry[key]:
                    if key == "_id":
                        continue
                    update[key] = entry[key]
            collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": update}
            )
            print(f"{id} updated {update}")
        else:
            print(f"{id} inserted")
            entry["_id"] = ObjectId(id)
            collection.insert_one(entry)
