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

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from bson import ObjectId
from ..auth import verify_api_key_or_cookie
from ..db import get_description_by_lat_lng, image_collection


router = APIRouter()


@router.get('/locations/{location_id}', dependencies=[Depends(verify_api_key_or_cookie)])
def read_location(location_id: str, request: Request):
    location = image_collection.find_one({"_id": ObjectId(location_id)})
    if not location:
        raise HTTPException(status_code=404, detail='Location not found')
    location['_id'] = str(location['_id'])
    return JSONResponse(content=location)


@router.get('/locations', dependencies=[Depends(verify_api_key_or_cookie)])
def read_locations_by_lat_lng(lat: float = Query(...), lng: float = Query(...), distance: float = Query(1000)):
    locations = get_description_by_lat_lng(lat, lng, 0, distance)
    if not locations:
        raise HTTPException(status_code=404, detail='No locations found within the given distance')
    return JSONResponse(content=locations)
