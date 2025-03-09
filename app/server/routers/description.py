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

import base64
import datetime
import json
import logging
import math
import os
import time
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

# Import required functions/classes from openai_agent and auth
from ..openai.openai_agent import GPTAgent
from ..openai.openai_agent import TranslatedDescription, construct_prompt_for_image_description
from ..openai.openai_agent import StopReason, construct_prompt_for_stop_reason
from .auth import verify_api_key_or_cookie
from ..db import get_description_by_lat_lng

router = APIRouter()
gpt_agent = GPTAgent()

logger = logging.getLogger(__name__)


def getOrientation(rotation, direction):
    direction = -direction * math.pi / 180
    diff = direction - rotation
    while diff < -math.pi:
        diff += math.pi * 2
    while diff > math.pi:
        diff -= math.pi * 2
    return diff


def get_relative_coordinates(lat1, lng1, lat2, lng2, rotation):
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    R = 6371000
    d_lat = lat2_rad - lat1_rad
    d_lng = lng2_rad - lng1_rad
    x = R * d_lng * math.cos((lat1_rad + lat2_rad) / 2)
    y = R * d_lat
    relative_x = x * math.cos(rotation) + y * math.sin(rotation)
    relative_y = -x * math.sin(rotation) + y * math.cos(rotation)
    return relative_x, relative_y


def classify_direction(radian):
    front_threshold = 30
    degree = radian * 180 / math.pi
    if abs(degree) < front_threshold:
        return "front"
    elif abs(degree) > (180 - front_threshold):
        return "back"
    elif degree > 0:
        return "left"
    else:
        return "right"


def preprocess_descriptions(locations, rotation, lat, lng, max_distance):
    dummy_object = {"distance": 9999, "description": ""}
    tags_to_use = {"sign", "poi", "highpriority"}
    location_per_directions = {"front": dummy_object.copy(), "left": dummy_object.copy(), "right": dummy_object.copy()}
    for location in locations:
        tag = location.get("tags", [])
        if len(set(tag).intersection(tags_to_use)) == 0:
            continue
        if "sign" in tag:
            location["description"] = "これはこの方向にある看板に関する追加の説明文章です。" + location["description"]
        elif "highpriority" in tag:
            location["description"] = "【重要！】" + location["description"]
        elif "poi" in tag:
            location["description"] = "これはこの方向にある施設・設備に関する追加の説明文章です。" + location["description"]
        direction = location['direction']
        location['relative_direction'] = getOrientation(rotation, direction)
        loc_lat = location['location']['coordinates'][1]
        loc_lng = location['location']['coordinates'][0]
        relative_x, relative_y = get_relative_coordinates(lat, lng, loc_lat, loc_lng, rotation)
        location['relative_coordinates'] = {'x': relative_x, 'y': relative_y}
        location['distance'] = math.sqrt(relative_x ** 2 + relative_y ** 2)
        direction = classify_direction(location["relative_direction"])
        distance = math.sqrt(relative_x ** 2 + relative_y ** 2)
        if direction == "back":
            continue
        if direction == "front":
            location["description"] = "前：" + location["description"]
        elif direction == "left":
            location["description"] = "左：" + location["description"]
        elif direction == "right":
            location["description"] = "右：" + location["description"]
        if distance < location_per_directions[direction]["distance"]:
            location_per_directions[direction] = location
    past_explanations = ""
    for past_description in gpt_agent.past_descriptions.copy():
        rel_x, rel_y = get_relative_coordinates(lat, lng, past_description["location"]["lat"], past_description["location"]["lng"], rotation)
        if math.sqrt(rel_x ** 2 + rel_y ** 2) < max_distance:
            past_explanations += past_description["description"] + "\n"
        else:
            gpt_agent.past_descriptions.remove(past_description)
    return location_per_directions, past_explanations


@router.get('/description', dependencies=[Depends(verify_api_key_or_cookie)])
async def read_description_by_lat_lng(lat: float = Query(...),
                                      lng: float = Query(...),
                                      floor: int = Query(0),
                                      rotation: float = Query(...),
                                      max_count: Optional[int] = Query(10),
                                      max_distance: Optional[float] = Query(100),
                                      lang: Optional[str] = Query("ja"),
                                      ):
    logger.info("description get")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)

    location_per_directions, past_explanations = preprocess_descriptions(locations, rotation, lat, lng, max_distance)

    request_length_index = 3  # which is the shortest press to the button UI
    distance_to_travel = 51  # meter

    prompt = construct_prompt_for_image_description(request_length_index=request_length_index,
                                                    distance_to_travel=distance_to_travel,
                                                    front=location_per_directions["front"]["description"],
                                                    right=location_per_directions["right"]["description"],
                                                    left=location_per_directions["left"]["description"],
                                                    past_explanations=past_explanations,
                                                    lang=lang,
                                                    )

    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(prompt=prompt, response_format=TranslatedDescription)
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.parsed.description
    translated = original_result.choices[0].message.parsed.translated
    lang = original_result.choices[0].message.parsed.lang
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", description)
    logger.info("Translated description: %s", translated)
    logger.info("Language: %s", lang)

    # log
    date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_json(directory=date, name="params", data={
        "lat": lat,
        "lng": lng,
        "rotation": rotation,
        "max_count": max_count,
        "max_distance": max_distance,
        "distance_to_travel": distance_to_travel,
        "prompt": prompt,
        "lang": lang,
    })
    log_json(directory=date, name="openai-query", data=query)
    log_json(directory=date, name="openai-prompt", data=prompt)
    log_json(directory=date, name="locations", data=locations)
    log_json(directory=date, name="openai-response", data=json.loads(original_result.model_dump_json()))

    return {
        'locations': locations,
        'elapsed_time': elapsed_time,
        'description': description,
        'translated': translated,
        'lang': lang,
    }


# TODO: upload a live image and describe the image, using nearby data
@router.post('/description_with_live_image', dependencies=[Depends(verify_api_key_or_cookie)])
async def read_description_by_lat_lng_with_image(request: Request,
                                                 lat: float = Query(...),
                                                 lng: float = Query(...),
                                                 floor: int = Query(0),
                                                 rotation: float = Query(...),
                                                 max_count: Optional[int] = Query(10),
                                                 max_distance: Optional[float] = Query(15),
                                                 length_index: Optional[int] = Query(0),  # which is the shortest press to the button UI
                                                 distance_to_travel: Optional[float] = Query(100),  # meter
                                                 lang: Optional[str] = Query("ja"),
                                                 ):
    logger.info("description_with_live_image post")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)

    images = await request.json()

    location_per_directions, past_explanations = preprocess_descriptions(locations, rotation, lat, lng, max_distance)

    count = 1
    tags = ""
    for image in images:
        position = image['position']
        tags += f"{count}枚目: {position}\n"
        count += 1

    prompt = construct_prompt_for_image_description(request_length_index=length_index,
                                                    distance_to_travel=distance_to_travel,
                                                    front=location_per_directions["front"]["description"],
                                                    right=location_per_directions["right"]["description"],
                                                    left=location_per_directions["left"]["description"],
                                                    past_explanations=past_explanations,
                                                    image_tags=tags,
                                                    lang=lang,
                                                    )

    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(prompt=prompt, images=images, response_format=TranslatedDescription)
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.parsed.description
    translated = original_result.choices[0].message.parsed.translated
    lang = original_result.choices[0].message.parsed.lang
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", description)
    logger.info("Translated description: %s", translated)
    logger.info("Language: %s", lang)

    # log
    date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_json(directory=date, name="images", data=images)
    log_json(directory=date, name="params", data={
        "lat": lat,
        "lng": lng,
        "rotation": rotation,
        "max_count": max_count,
        "max_distance": max_distance,
        "length_index": length_index,
        "distance_to_travel": distance_to_travel,
        "prompt": prompt,
        "lang": lang,
    })
    log_json(directory=date, name="openai-query", data=query)
    log_json(directory=date, name="openai-prompt", data=prompt)
    log_json(directory=date, name="locations", data=locations)
    log_json(directory=date, name="openai-response", data=json.loads(original_result.model_dump_json()))

    return {
        'locations': locations,
        'elapsed_time': elapsed_time,
        'description': description,
        'lang': lang,
        'translated': translated,
    }


@router.post("/stop_reason", dependencies=[Depends(verify_api_key_or_cookie)])
async def stop_reason(request: Request,
                      lat: float = Query(...),
                      lng: float = Query(...),
                      floor: int = Query(0),
                      rotation: float = Query(...),
                      max_count: Optional[int] = Query(10),
                      max_distance: Optional[float] = Query(100),
                      length_index: Optional[int] = Query(0),
                      distance_to_travel: Optional[float] = Query(100),  # meter
                      lang: Optional[str] = Query("ja"),
                      ):
    logger.info("stop_reason post")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)

    images = await request.json()

    _, past_explanations = preprocess_descriptions(locations, rotation, lat, lng, max_distance)

    count = 1
    tags = ""
    temp = []
    for image in images:
        position = image["position"]
        if "front" != position:
            continue
        tags += f"{count}枚目: {position}\n"
        count += 1
        temp.append(image)

    prompt = construct_prompt_for_stop_reason(request_length_index=length_index,
                                              distance_to_travel=distance_to_travel,
                                              past_explanations=past_explanations,
                                              image_tags=tags,
                                              lang=lang,
                                              )

    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(prompt=prompt, images=temp, response_format=StopReason)
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.parsed.message
    translated = original_result.choices[0].message.parsed.translated
    lang = original_result.choices[0].message.parsed.lang
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", description)
    logger.info("Translated description: %s", translated)
    logger.info("Language: %s", lang)

    # log
    date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_json(directory=date, name="images", data=temp)
    log_json(
        directory=date,
        name="params",
        data={
            "mode": "stop-reason",
            "lat": lat,
            "lng": lng,
            "rotation": rotation,
            "max_count": max_count,
            "max_distance": max_distance,
            "length_index": length_index,
            "distance_to_travel": distance_to_travel,
            "prompt": prompt,
            "lang": lang,
        },
    )
    log_json(directory=date, name="openai-query", data=query)
    log_text(directory=date, name="openai-prompt", data=prompt)
    log_json(
        directory=date, name="openai-response", data=json.loads(original_result.model_dump_json())
    )
    log_image(directory=date, position="front", images=temp)

    return {
        "locations": locations,
        "elapsed_time": elapsed_time,
        "description": description,
        "translated": translated,
        "lang": lang,
    }


def log_json(directory, name, data):
    basepath = f"/logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{name}.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log_text(directory, name, data):
    basepath = f"/logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{name}.txt", "w") as f:
        print(data, file=f)


def log_image(directory, position, images):
    image = list(filter(lambda x: x["position"] == position, images))
    if image:
        image_uri = image[0]["image_uri"]

    basepath = f"/logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{position}.jpg", "wb") as f:
        f.write(base64.b64decode(image_uri.split(",")[1]))
