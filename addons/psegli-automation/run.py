#!/usr/bin/env python3
"""PSEG Automation Addon - FastAPI Server"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

from auto_login import get_fresh_cookies

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERSION = "2.3a6"
app = FastAPI(title="PSEG Automation", version=VERSION)

# File to store manual cookies
COOKIE_FILE = "/data/manual_cookies.json"

@app.get("/")
async def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs")

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    cookies: Optional[str] = None
    error: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "psegli-automation"}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login to PSEG and return cookies."""
    try:
        logger.info(f"Login attempt for user: {request.username}")
        
        # Get fresh cookies using the compatibility function
        cookies = await get_fresh_cookies(request.username, request.password)
        
        if cookies:
            logger.info("Login successful, cookies obtained")
            return LoginResponse(success=True, cookies=cookies)
        else:
            logger.warning("Login failed, no cookies returned")
            return LoginResponse(success=False, error="Login failed")
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return LoginResponse(success=False, error=str(e))

@app.post("/login-form", response_model=LoginResponse)
async def login_form(username: str = Form(...), password: str = Form(...)):
    """Login endpoint that accepts form data."""
    return await login(LoginRequest(username=username, password=password))


# === Manual Cookie Management ===

def load_manual_cookies() -> Optional[dict]:
    """Load manually saved cookies from file."""
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
    return None


def save_manual_cookies(cookies: str) -> bool:
    """Save manually provided cookies to file."""
    try:
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        data = {
            "cookies": cookies,
            "saved_at": datetime.now().isoformat(),
        }
        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Cookies saved at {data['saved_at']}")
        return True
    except Exception as e:
        logger.error(f"Error saving cookies: {e}")
        return False


@app.get("/cookies", response_class=HTMLResponse)
async def cookies_page():
    """Page to view and set manual cookies."""
    saved = load_manual_cookies()
    saved_info = ""
    if saved:
        saved_info = f"""
        <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <strong>Current saved cookies:</strong><br>
            <code style="word-break: break-all;">{saved.get('cookies', '')[:100]}...</code><br>
            <small>Saved at: {saved.get('saved_at', 'unknown')}</small>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PSEG Manual Cookie Setup</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .instructions {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .instructions ol {{ margin: 0; padding-left: 20px; }}
            textarea {{ width: 100%; height: 150px; margin: 10px 0; font-family: monospace; }}
            button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            .version {{ color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h1>PSEG Manual Cookie Setup</h1>
        <p class="version">Version {VERSION}</p>

        {saved_info}

        <div class="instructions">
            <strong>How to get cookies:</strong>
            <ol>
                <li>Open Chrome/Firefox and go to <a href="https://mysmartenergy.nj.pseg.com" target="_blank">mysmartenergy.nj.pseg.com</a></li>
                <li>Log in manually (complete reCAPTCHA)</li>
                <li>Once logged in, open Developer Tools (F12)</li>
                <li>Go to Application tab → Cookies → mysmartenergy.nj.pseg.com</li>
                <li>Find <strong>MM_SID</strong> and <strong>__RequestVerificationToken</strong></li>
                <li>Copy their values and paste below in format:<br>
                    <code>MM_SID=value; __RequestVerificationToken=value</code></li>
            </ol>
        </div>

        <form action="/cookies" method="post">
            <label for="cookies"><strong>Paste cookies here:</strong></label>
            <textarea name="cookies" id="cookies" placeholder="MM_SID=abc123; __RequestVerificationToken=xyz789"></textarea>
            <button type="submit">Save Cookies</button>
        </form>

        <p><a href="/docs">← Back to API Docs</a></p>
    </body>
    </html>
    """


@app.post("/cookies", response_class=HTMLResponse)
async def save_cookies_form(cookies: str = Form(...)):
    """Save manually provided cookies."""
    if save_manual_cookies(cookies.strip()):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cookies Saved</title>
            <meta http-equiv="refresh" content="2;url=/cookies">
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }
                .success { background: #d4edda; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Cookies saved successfully!</h2>
                <p>Redirecting...</p>
            </div>
        </body>
        </html>
        """
    else:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }
                .error { background: #f8d7da; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Failed to save cookies</h2>
                <p><a href="/cookies">Try again</a></p>
            </div>
        </body>
        </html>
        """


@app.get("/cookies/get", response_model=LoginResponse)
async def get_saved_cookies():
    """Get the currently saved manual cookies."""
    saved = load_manual_cookies()
    if saved and saved.get('cookies'):
        return LoginResponse(success=True, cookies=saved['cookies'])
    return LoginResponse(success=False, error="No cookies saved. Visit /cookies to add them.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
