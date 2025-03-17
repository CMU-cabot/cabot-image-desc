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

import json
import logging
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .auth import verify_api_key_or_cookie

logger = logging.getLogger(__name__)
router = APIRouter()
print(Path(__file__))
print(Path(__file__).parent.parent.parent / "templates")
templates = Jinja2Templates(directory="/templates")
logs_dir = "/logs"


@router.get('/logs', dependencies=[Depends(verify_api_key_or_cookie)], response_class=HTMLResponse)
def logs(request: Request):
    try:
        directories = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
    except Exception as e:
        logger.error(f"Error accessing logs directory: {e}")
        raise HTTPException(status_code=500, detail="Could not access logs directory")

    return templates.TemplateResponse("logs.html", {"request": request, "directories": sorted(directories, reverse=True)})


@router.get('/logs/{directory}', dependencies=[Depends(verify_api_key_or_cookie)], response_class=HTMLResponse)
def logs_list_files(directory: str, request: Request):
    dir = os.path.join(logs_dir, directory)
    try:
        files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
    except Exception as e:
        logger.error(f"Error accessing logs file: {e}")
        raise HTTPException(status_code=500, detail="Could not access logs file")

    return templates.TemplateResponse("logs.html", {"request": request, "directory": directory, "files": sorted(files)})


@router.get('/logs/{directory}/{file}', dependencies=[Depends(verify_api_key_or_cookie)], response_class=HTMLResponse)
def logs_show_file(directory: str, file: str, request: Request):
    file_path = os.path.join(logs_dir, directory, file)
    images = []

    def extract_images(content):
        for key, value in enumerate(content) if type(content) == list else content.items() if type(content) == dict else []:
            if type(value) == str and value.startswith("data:image"):
                images.append(value)
                content[key] = f"{value[:50]}..."
            else:
                extract_images(value)

    with open(file_path, "r") as f:
        content = f.read()
        try:
            content = json.loads(content)
            extract_images(content)
            content = json.dumps(content, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
    return templates.TemplateResponse("logs.html", {"request": request, "directory": directory, "content": content, "images": images})
