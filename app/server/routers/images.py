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
import os
import tempfile
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from .auth import verify_api_key_or_cookie
from export_data import export_data
from import_data import import_data


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/export-images', dependencies=[Depends(verify_api_key_or_cookie)])
def export_images():
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        export_data(temp.name)
        return FileResponse(temp.name, media_type='application/json', background=BackgroundTask(os.remove, temp.name))


def import_task(file):
    with tempfile.NamedTemporaryFile(delete=True) as temp:
        temp.write(file.file.read())
        import_data(temp.name)


@router.post('/import-images', dependencies=[Depends(verify_api_key_or_cookie)])
async def import_images(request: Request, background_tasks: BackgroundTasks):
    data = await request.form()
    if 'file' not in data:
        raise HTTPException(status_code=400, detail='file form field required')
    file = data['file']
    if file.content_type != 'application/json':
        raise HTTPException(status_code=400, detail='file must be of type application/json')
    background_tasks.add_task(import_task, file)
    return JSONResponse(content={'message': 'success'}, status_code=201)
