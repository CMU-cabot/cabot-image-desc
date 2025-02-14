#!/usr/bin/env python3

import sys
import json
from pymongo import MongoClient

mongo_client = MongoClient('mongodb://mongo:27017/')
db = mongo_client['geo_image_db']
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
        location = collection.find_one({"_id": id})
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
