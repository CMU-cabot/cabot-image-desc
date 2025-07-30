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
import sys
from pathlib import Path
from fastapi import Depends
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .routers import auth
from .routers.auth import verify_api_key_or_cookie
from .routers import locations
from .routers import description
from .routers import images
from .routers import logs

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


# Serve index.html on accessing root path
@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_root():
    logger.info("root get")
    return await read_index()


@app.get("/index.html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_index():
    return HTMLResponse(content=read_file("index.html"))


@app.get("/list.html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_list():
    return HTMLResponse(content=read_file("list.html"))


@app.get("/test.html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key_or_cookie)])
async def read_test():
    return HTMLResponse(content=read_file("test.html"))


def read_file(filename):
    """Read a file from the static directory."""
    logger.info(f"read_file {filename}")
    file_path = Path("/static") / filename
    if not file_path.exists():
        logger.error(f"File {filename} not found.")
        return None
    initial_location = os.getenv("INITIAL_LOCATION", '{"lat": 35.62414166666667, "lng": 139.77542222222223, "floor": 1}')
    html_content = file_path.read_text().replace("INITIAL_LOCATION_PLACEHOLDER", initial_location).replace("VERSION_PLACEHOLDER", version)
    return html_content


# Register the locations router
app.include_router(auth.router)
app.include_router(locations.router)
app.include_router(description.router)
app.include_router(images.router)
app.include_router(logs.router)

# Mount static files for serving HTML, JS, and CSS
app.mount("/js/lib", StaticFiles(directory="/static_js_lib"), name="static/js/lib")
# This should be last to avoid conflicts with other routes
app.mount("/", StaticFiles(directory="/static"), name="static")

# Read version information from version.txt
version_file_path = Path("/app/version.txt")
version = "unknown"
if version_file_path.exists():
    try:
        with version_file_path.open("r") as version_file:
            version = version_file.read().strip()
            logger.info(f"Application version: {version}")
    except Exception as e:
        logger.error(f"Failed to read version file: {e}")
else:
    logger.warning("Version file not found.")
