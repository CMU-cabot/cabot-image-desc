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

from fastapi import HTTPException, status, Response
from fastapi import FastAPI, Form, Query, Request, Header, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pymongo import MongoClient
from typing import Optional
from pydantic import BaseModel
from .openai_agent import GPTAgent, construct_prompt_for_image_description
from .openai_agent import construct_prompt_for_stop_reason
from bson import ObjectId
import os
import math
import logging
import sys
import time
import base64
import datetime
import json
import secrets

# Set up logging configuration to output to stderr
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level to capture
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log messages to stderr
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()
gpt_agent = GPTAgent()

# Configure MongoDB connection
mongodb_host = os.getenv('MONGODB_HOST', 'mongodb://mongo:27017/')
mongodb_name = os.getenv('MONGODB_NAME', 'geo_image_db')
client = MongoClient(mongodb_host)
db = client[mongodb_name]
image_collection = db['images']

# Ensure the collection is indexed for geospatial queries
image_collection.create_index([("location", "2dsphere")])

API_KEY = os.getenv("API_KEY")

# Store tokens in memory for simplicity (consider using a database for production)
tokens = set()


def generate_token():
    return secrets.token_hex(16)


def verify_api_key_or_cookie(request: Request, x_api_key: Optional[str] = Header(None)):
    logger.info("verify_api_key_or_cookie")
    if x_api_key and x_api_key == API_KEY:
        return
    token = request.cookies.get("token")
    if not token or token not in tokens:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Redirecting to login",
            headers={"Location": f"/login?next={request.url.path}"}
        )


# Load users from environment variables
users = {}
usernames = os.getenv("USERNAMES", "").split(",")
passwords = os.getenv("PASSWORDS", "").split(",")
if len(usernames) != len(passwords):
    raise ValueError("USERNAMES and PASSWORDS environment variables must have the same number of entries")

for username, password in zip(usernames, passwords):
    users[username] = password


@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), next: Optional[str] = None):
    logger.info("login post")
    correct_password = users.get(username)
    if not correct_password or not secrets.compare_digest(correct_password, password):
        return HTMLResponse(content="Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)
    token = generate_token()
    tokens.add(token)
    redirect_url = next if next else "/"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="token", value=token, httponly=True, secure=True, path="/")
    return response


@app.get("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("token")
    if token in tokens:
        tokens.remove(token)
    response.delete_cookie("token", path="/")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def login_page(next: Optional[str] = None):
    logger.info("login get")
    login_path = Path("/static/login.html")
    html_content = login_path.read_text()
    if next:
        html_content = html_content.replace('action="/login"', f'action="/login?next={next}"')
    return HTMLResponse(content=html_content)


# API to get a location by its ID
@app.get('/locations/{location_id}', dependencies=[Depends(verify_api_key_or_cookie)])
def read_location(location_id: str):
    location = image_collection.find_one({"_id": ObjectId(location_id)})
    if not location:
        raise HTTPException(status_code=404, detail='Location not found')
    location['_id'] = str(location['_id'])
    return location


# API to get locations by latitude, longitude, and optional distance
@app.get('/locations', dependencies=[Depends(verify_api_key_or_cookie)])
def read_locations_by_lat_lng(lat: float = Query(...), lng: float = Query(...), distance: Optional[float] = Query(1000)):
    locations = get_description_by_lat_lng(lat, lng, 0, distance)
    if not locations:
        raise HTTPException(status_code=404, detail='No locations found within the given distance')
    return locations


# Existing function to get nearby locations
def get_description_by_lat_lng(lat, lng, floor, max_distance, max_count=0):
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


# Function to get the relative orientation
def getOrientation(rotation, direction):
    direction = -direction * math.pi / 180
    diff = direction - rotation
    # Normalize diff
    while diff < -math.pi:
        diff += math.pi * 2
    while math.pi < diff:
        diff -= math.pi * 2
    return diff

# New function to calculate relative coordinates


def get_relative_coordinates(lat1, lng1, lat2, lng2, rotation):
    # Convert latitude and longitude to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    # Approximate radius of Earth in meters
    R = 6371000

    # Calculate differences
    d_lat = lat2_rad - lat1_rad
    d_lng = lng2_rad - lng1_rad

    # Calculate distances in the local tangent plane
    x = R * d_lng * math.cos((lat1_rad + lat2_rad) / 2)
    y = R * d_lat

    # Apply rotation to get relative coordinates
    relative_x = x * math.cos(rotation) + y * math.sin(rotation)
    relative_y = -x * math.sin(rotation) + y * math.cos(rotation)

    return relative_x, relative_y


def classify_direction(radian):
    """take in degree and return the direction from back, left, front, right"""
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

    tags_to_use = ["sign", "poi", "highpriority"]
    tags_to_use = set(tags_to_use)

    location_per_directions = {"front": dummy_object, "left": dummy_object, "right": dummy_object}
    for location in locations:
        tag = location["tags"] if "tags" in location else []
        set_tag = set(tag)
        # if there is interection between the tags
        if len(set_tag.intersection(tags_to_use)) == 0:
            continue
        if "sign" in tag:
            location["description"] = "これはこの方向にある看板に関する追加の説明文章です。" + location["description"]
        elif "highpriority" in tag:
            location["description"] = "【重要！】" + location["description"]
        elif "poi" in tag:
            location["description"] = "これはこの方向にある施設・設備に関する追加の説明文章です。" + location["description"]

        direction = location['direction']
        location['relative_direction'] = getOrientation(rotation, direction)

        # Calculate relative coordinates
        loc_lat = location['location']['coordinates'][1]
        loc_lng = location['location']['coordinates'][0]
        relative_x, relative_y = get_relative_coordinates(lat, lng, loc_lat, loc_lng, rotation)
        location['relative_coordinates'] = {'x': relative_x, 'y': relative_y}
        location['distance'] = math.sqrt(relative_x ** 2 + relative_y ** 2)

        direction = classify_direction(location["relative_direction"])
        distance = math.sqrt(relative_x ** 2 + relative_y ** 2)  # assuming on the euclidean plane

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

    # if len(location_per_directions) == 0:
    #     result = "近くには説明できるものが何もありません"

    past_explanations = ""
    for past_description in gpt_agent.past_descriptions:
        relative_x, relative_y = get_relative_coordinates(lat, lng, past_description["location"]["lat"], past_description["location"]["lng"], rotation)
        distance = math.sqrt(relative_x ** 2 + relative_y ** 2)
        if distance < max_distance:
            past_explanations += past_description["description"] + "\n"
        else:
            gpt_agent.past_descriptions.remove(past_description)

    return location_per_directions, past_explanations

# Endpoint to read description by latitude and longitude


@app.get('/description', dependencies=[Depends(verify_api_key_or_cookie)])
async def read_description_by_lat_lng(
        lat: float = Query(...),
        lng: float = Query(...),
        floor: int = Query(0),
        rotation: float = Query(...),
        max_count: Optional[int] = Query(10),
        max_distance: Optional[float] = Query(100)):

    logger.info("description get")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)
    # if not locations:
    #     raise HTTPException(status_code=404, detail='No locations found within the given distance')

    location_per_directions, past_explanations = preprocess_descriptions(locations, rotation, lat, lng, max_distance)

    request_length_index = 3  # which is the shortest press to the button UI
    distance_to_travel = 51  # meter

    prompt = construct_prompt_for_image_description(request_length_index=request_length_index,
                                                    distance_to_travel=distance_to_travel,
                                                    front=location_per_directions["front"]["description"],
                                                    right=location_per_directions["right"]["description"],
                                                    left=location_per_directions["left"]["description"],
                                                    past_explanations=past_explanations,
                                                    )

    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(
        prompt=prompt
    )
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.content
    logger.info(f"prompt: {prompt}")
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", original_result)

    return {
        'locations': locations,
        'elapsed_time': elapsed_time,
        'description': description
    }

# TODO: upload a live image and describe the image, using nearby data


@app.post('/description_with_live_image', dependencies=[Depends(verify_api_key_or_cookie)])
async def read_description_by_lat_lng_with_image(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    floor: int = Query(0),
    rotation: float = Query(...),
    max_count: Optional[int] = Query(10),
    max_distance: Optional[float] = Query(15),
    length_index: Optional[int] = Query(0),  # which is the shortest press to the button UI
    distance_to_travel: Optional[float] = Query(100),  # meter
):
    logger.info("description_with_live_image post")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)
    # if not locations:
    #     raise HTTPException(status_code=404, detail='No locations found within the given distance')

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
                                                    image_tags=tags)

    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(
        prompt=prompt,
        images=images
    )
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.content
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", description)

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
        "prompt": prompt
    })
    log_json(directory=date, name="openai-query", data=query)
    log_json(directory=date, name="openai-prompt", data=prompt)
    log_json(directory=date, name="locations", data=locations)
    log_json(directory=date, name="openai-response", data=json.loads(original_result.json()))

    return {
        'locations': locations,
        'elapsed_time': elapsed_time,
        'description': description
    }


@app.post("/stop_reason", dependencies=[Depends(verify_api_key_or_cookie)])
async def stop_reason(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    floor: int = Query(0),
    rotation: float = Query(...),
    max_count: Optional[int] = Query(10),
    max_distance: Optional[float] = Query(100),
    length_index: Optional[int] = Query(
        0
    ),  # which is the shortest press to the button UI
    distance_to_travel: Optional[float] = Query(100),  # meter
):
    logger.info("stop_reason post")
    locations = get_description_by_lat_lng(lat, lng, floor, max_distance, max_count)
    # describe without existing image data
    # if not locations:
    #     raise HTTPException(status_code=404, detail='No locations found within the given distance')

    images = await request.json()

    _, past_explanations = preprocess_descriptions(
        locations, rotation, lat, lng, max_distance
    )

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

    prompt = construct_prompt_for_stop_reason(
        request_length_index=length_index,
        distance_to_travel=distance_to_travel,
        past_explanations=past_explanations,
        image_tags=tags,
    )

    class StopReason(BaseModel):
        pedestrian_info: str
        object_info: str
        thought: str
        message: str

        def to_dict(self):
            return self.dict()
    st = time.time()
    (original_result, query) = await gpt_agent.query_with_images(prompt=prompt, images=temp, response_format=StopReason)
    elapsed_time = time.time() - st
    description = original_result.choices[0].message.parsed.message
    logger.info("Time taken: %s", elapsed_time)
    logger.info("Generated description: %s", description)

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
        },
    )
    log_json(directory=date, name="openai-query", data=query)
    log_text(directory=date, name="openai-prompt", data=prompt)
    log_json(
        directory=date, name="openai-response", data=json.loads(original_result.json())
    )
    log_image(directory=date, position="front", images=temp)

    return {
        "locations": locations,
        "elapsed_time": elapsed_time,
        "description": description,
    }


def log_json(directory, name, data):
    basepath = f"logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{name}.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log_text(directory, name, data):
    basepath = f"logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{name}.txt", "w") as f:
        print(data, file=f)


def log_image(directory, position, images):
    image = list(filter(lambda x: x["position"] == position, images))
    if image:
        image_uri = image[0]["image_uri"]

    basepath = f"logs/{directory}"
    os.makedirs(basepath, exist_ok=True)
    with open(f"{basepath}/{position}.jpg", "wb") as f:
        f.write(base64.b64decode(image_uri.split(",")[1]))


@app.post("/update_description", dependencies=[Depends(verify_api_key_or_cookie)])
async def update(id: str = Query(...), description: str = Form(...)):
    logger.info(["updateDescription", id, description])
    # Find the document by ID
    location = image_collection.find_one({"_id": ObjectId(id)})
    if not location:
        raise HTTPException(status_code=404, detail="Document not found")
    image_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"description": description}}
    )
    logger.info(F"updated description {description}")
    return {"message": "Description updated successfully", "description": description}


@app.post("/update_floor", dependencies=[Depends(verify_api_key_or_cookie)])
async def update_floor(id: str = Query(...), floor: int = Form(...)):
    logger.info(["updateFloor", id, floor])
    # Find the document by ID
    location = image_collection.find_one({"_id": ObjectId(id)})
    if not location:
        raise HTTPException(status_code=404, detail="Document not found")
    image_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"floor": floor}}
    )
    logger.info(F"updated floor {floor}")
    return {"message": "Floor updated successfully", "floor": floor}


@app.post("/add_tag", dependencies=[Depends(verify_api_key_or_cookie)])
async def add_tag(id: str = Query(...), tag: str = Form(...)):
    logger.info(["addTag", id, tag])
    # Find the document by ID
    location = image_collection.find_one({"_id": ObjectId(id)})
    if not location:
        raise HTTPException(status_code=404, detail="Document not found")
    # Check if the tag already exists
    existing_tags = location.get("tags", [])
    logger.info(existing_tags)
    if tag in existing_tags:
        logger.info("tag in existing_tags")
        return {"message": "Tag already exists", "tag": tag, "all_tags": existing_tags}
    # Update the document with the new tag
    updated_tags = existing_tags + [tag]
    image_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"tags": updated_tags}}
    )
    logger.info(F"updated tags {updated_tags}")
    return {"message": "Tag added successfully", "tag": tag, "all_tags": updated_tags}


@app.post("/clear_tag", dependencies=[Depends(verify_api_key_or_cookie)])
async def clear_tag(id: str = Query(...)):
    logger.info(["clearTag", id])
    # Find the document by ID
    location = image_collection.find_one({"_id": ObjectId(id)})
    if not location:
        raise HTTPException(status_code=404, detail="Document not found")
    # Check if the tag already exists

    # Update the document with the new tag
    updated_tags = []
    image_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"tags": updated_tags}}
    )
    logger.info(F"updated tags {updated_tags}")
    return {"message": "Tag cleared successfully"}

# Serve index.html on accessing root path


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_root():
    logger.info("root get")
    return await read_index()


@app.get("/index.html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_index():
    logger.info("index get")
    index_path = Path("/static/index.html")
    initial_location = os.getenv("INITIAL_LOCATION", '{"lat": 35.62414166666667, "lng": 139.77542222222223, "floor": 1}')
    html_content = index_path.read_text().replace("INITIAL_LOCATION_PLACEHOLDER", initial_location)
    return HTMLResponse(content=html_content)


@app.get("/list.html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_list():
    logger.info("list get")
    index_path = Path("/static/list.html")
    initial_location = os.getenv("INITIAL_LOCATION", '{"lat": 35.62414166666667, "lng": 139.77542222222223, "floor": 1}')
    html_content = index_path.read_text().replace("INITIAL_LOCATION_PLACEHOLDER", initial_location)
    return HTMLResponse(content=html_content)


# Mount static files for serving HTML, JS, and CSS
app.mount("/js/lib", StaticFiles(directory="/static_js_lib"), name="static/js/lib")
app.mount("/", StaticFiles(directory="/static"), name="static")

# Main entry point
# Note: To run the FastAPI application, use the command: `uvicorn your_filename:app --reload`
