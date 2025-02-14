#!/usr/bin/env python3

import base64
import os
import sys
import argparse
import datetime
from io import BytesIO

from openai import OpenAI
from pymongo import MongoClient
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from PIL.TiffImagePlugin import IFDRational
import hashlib

IMAGE_DESCRIPTION_PROMPT = """
# 概要
- 画像に写っているものをリストで表示。リストのみ
- それぞれの写っているものについて視覚的な特徴を記述
- フォーマットは以下の通りで```は含まない
```
- ＜名称＞：＜詳細＞
```

# リストに含めないもの
- 画像に写っているものなどの説明
- 天気に関するもの、表現
- 人
- 乗り物
"""
if os.getenv('OPENAI_API_KEY'):
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def transcribe_image_query(filepath):
    def resize_with_aspect_ratio(image, target_size):
        original_width, original_height = image.size
        if original_width > original_height:
            new_width = target_size
            new_height = int((target_size / original_width) * original_height)
        else:
            new_height = target_size
            new_width = int((target_size / original_height) * original_width)
        return image.resize((new_width, new_height))

    def parse_exif(exif_data):
        def convert_to_degrees(value):
            """Helper function to convert GPS coordinates to degrees."""
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        gps_info = {}
        exif = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == 'GPSInfo':
                gps_latitude = None
                gps_longitude = None
                gps_direction = None
                for gps_tag in value:
                    sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                    if sub_tag_name == 'GPSLatitude':
                        gps_latitude = convert_to_degrees(value[gps_tag])
                    elif sub_tag_name == 'GPSLatitudeRef':
                        if value[gps_tag] != 'N' and gps_latitude is not None:
                            gps_latitude = -gps_latitude
                    elif sub_tag_name == 'GPSLongitude':
                        gps_longitude = convert_to_degrees(value[gps_tag])
                    elif sub_tag_name == 'GPSLongitudeRef':
                        if value[gps_tag] != 'E' and gps_longitude is not None:
                            gps_longitude = -gps_longitude
                    elif sub_tag_name == 'GPSImgDirection':
                        gps_direction = value[gps_tag]
                if gps_latitude is not None and gps_longitude is not None:
                    gps_info['Latitude'] = gps_latitude
                    gps_info['Longitude'] = gps_longitude
                if gps_direction is not None:
                    gps_info['Direction'] = gps_direction
            else:
                if isinstance(value, IFDRational):
                    exif[tag_name] = float(value)
                elif isinstance(value, (int, str)):
                    exif[tag_name] = value
                elif isinstance(value, tuple):
                    exif[tag_name] = [float(e) for e in value]
                else:
                    print([tag_name, type(value), value])
        return gps_info, exif

    def get_md5_hash(filepath):
        # Create an MD5 hash object
        md5_hash = hashlib.md5()

        # Open the file in binary mode
        with open(filepath, 'rb') as file:
            # Read the file in chunks to avoid memory issues with large files
            for chunk in iter(lambda: file.read(4096), b''):
                md5_hash.update(chunk)

        # Return the hexadecimal digest of the MD5 hash
        return md5_hash.hexdigest()

    def linux_time_from_exif(exif):
        # TODO (consider time zone)
        datestr, timestr = str(exif['DateTime']).split(" ")
        items = datestr.split(":")
        items.extend(timestr.split(":"))
        items = [int(v) for v in items]
        return datetime.datetime(*items).timestamp()

    image = Image.open(filepath)
    image_hash = get_md5_hash(filepath)
    # Extract EXIF data
    gps_info, exif = parse_exif(image._getexif())
    image = resize_with_aspect_ratio(image, 512)
    with BytesIO() as buffer:
        image.convert('RGB').save(buffer, format='JPEG')
        jpeg_image_bytes = buffer.getvalue()
    jpeg_filepath = f'{os.path.splitext(filepath)[0]}_shrunk.jpeg'
    with open(jpeg_filepath, 'wb') as f:
        f.write(jpeg_image_bytes)
    base64_image = base64.b64encode(jpeg_image_bytes).decode('utf-8')
    image_uri = f'data:image/jpeg;base64,{base64_image}'
    filename = os.path.basename(filepath)

    return ({
        'model': 'gpt-4o-2024-08-06',
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': IMAGE_DESCRIPTION_PROMPT.format(longitude=gps_info['Longitude'], latitude=gps_info['Latitude'], direction=gps_info['Direction'])
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_uri
                        },
                    },
                ],
            }
        ]}, {
            'filename': filename,
            'image_hash': image_hash,
            'location': {
                'type': 'Point',
                'coordinates': [gps_info['Longitude'], gps_info['Latitude']]
            },
            'direction': float(gps_info['Direction']),
            'image': image_uri,
            'linuxtime': linux_time_from_exif(exif),
            'exif': exif
    })


def post_query(query):
    return openai_client.chat.completions.create(**query)


def get_result(response, metadata):
    description = response.choices[0].message.content

    metadata.update({
        'description': description
    })
    return metadata


mongo_client = MongoClient('mongodb://mongo:27017/')
db = mongo_client['geo_image_db']
collection = db['images']

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process an image file to transcribe its content.')
    parser.add_argument('-f', '--file', required=True, help='Path to the image file')
    parser.add_argument('-t', '--tags', nargs='*', help='Tags to associate with the image')
    parser.add_argument('-c', '--clear-tags', action='store_true', help='Clear all tags from the image')
    parser.add_argument('-d', '--dryrun', action='store_true', help='Perform a dry run without modifying the database')
    parser.add_argument('-r', '--retry', action='store_true', help='Descrtibe image even if the entry has already description')
    args = parser.parse_args()

    filepath = args.file
    query, metadata = transcribe_image_query(filepath)

    existing_entry = collection.find_one({
        'filename': metadata['filename'],
        'image_hash': metadata['image_hash']
    })

    if existing_entry:
        if args.clear_tags:
            existing_entry['tags'] = []
        elif args.tags:
            existing_entry['tags'] = args.tags
        update = {}
        for key in metadata:
            if key not in existing_entry or existing_entry[key] != metadata[key]:
                update[key] = metadata[key]
        if args.dryrun:
            print(F"Dry run: The image is already transcribed ({existing_entry['_id']}): {existing_entry['description']}, with updated: {update=}")
            if args.retry:
                print(F"Will retry description {query}")
        else:
            if args.retry:
                response = post_query(query)
                print(F"Received data: {response}")
                data = get_result(response, metadata)
                for key in data:
                    if key not in existing_entry or existing_entry[key] != data[key]:
                        update[key] = data[key]

            collection.update_one(
                {'_id': existing_entry['_id']},
                {'$set': update}
            )
            print(F"The image is already transcribed ({existing_entry['_id']}): {existing_entry['description']}, with updated: {update=}")
    else:
        if args.dryrun:
            print(f"Dry run: Would post query and insert data for image: {filepath}\n{query}")
        else:
            print(F"Posting query")
            response = post_query(query)
            print(F"Received data: {response}")
            data = get_result(response, metadata)
            if args.tags:
                data['tags'] = args.tags
            print(F"Insert data into the DB")

            collection.insert_one(data)
