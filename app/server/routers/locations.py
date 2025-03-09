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

import logging
from bson import ObjectId
from fastapi import APIRouter, Form, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from .auth import verify_api_key_or_cookie
from ..db import get_description_by_lat_lng, image_collection


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/locations', dependencies=[Depends(verify_api_key_or_cookie)])
def read_locations_by_lat_lng(lat: float = Query(...), lng: float = Query(...), distance: float = Query(1000)):
    locations = get_description_by_lat_lng(lat, lng, 0, distance)
    if not locations:
        raise HTTPException(status_code=404, detail='No locations found within the given distance')
    return JSONResponse(content=locations)


@router.get('/locations/{location_id}', dependencies=[Depends(verify_api_key_or_cookie)])
def read_location(location_id: str, request: Request):
    location = image_collection.find_one({"_id": ObjectId(location_id)})
    if not location:
        raise HTTPException(status_code=404, detail='Location not found')
    location['_id'] = str(location['_id'])
    return JSONResponse(content=location)


@router.post("/update_description", dependencies=[Depends(verify_api_key_or_cookie)])
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


@router.post("/update_floor", dependencies=[Depends(verify_api_key_or_cookie)])
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


@router.post("/add_tag", dependencies=[Depends(verify_api_key_or_cookie)])
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


@router.post("/clear_tag", dependencies=[Depends(verify_api_key_or_cookie)])
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
