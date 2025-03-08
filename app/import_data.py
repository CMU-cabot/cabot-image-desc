#!/usr/bin/env python3

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
                    update[key] = entry[key]
            collection.update_one(
                {"_id": id},
                {"$set": update}
            )
            print(f"{id} updated {update}")
        else:
            print(f"{id} inserted")
            collection.insert_one(entry)
