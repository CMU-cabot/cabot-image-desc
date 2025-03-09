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
import secrets
from fastapi import APIRouter, Form, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory token storage for simplicity
tokens = set()


def generate_token():
    return secrets.token_hex(128)


def verify_api_key_or_cookie(request: Request, x_api_key: Optional[str] = Header(None)):
    logger.info(f"verify_api_key_or_cookie {x_api_key=}")
    API_KEY = os.getenv("API_KEY")
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
    raise ValueError("USERNAMES and PASSWORDS must have the same number of entries")
for username, password in zip(usernames, passwords):
    users[username] = password


# POST login endpoint
@router.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), next: str = None):
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


# GET logout endpoint
@router.get("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("token")
    if token in tokens:
        tokens.remove(token)
    response.delete_cookie("token", path="/")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# GET login page endpoint
@router.get("/login")
async def login_page(next: str = None):
    logger.info("login get")
    login_path = Path("/static/login.html")
    html_content = login_path.read_text()
    if next:
        html_content = html_content.replace('action="/login"', f'action="/login?next={next}"')
    return HTMLResponse(content=html_content)
