#!/usr/bin/env python3
"""Automated login for PSEG using the automation addon."""

import asyncio
import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Try multiple URLs for addon - HAOS uses different networking
ADDON_URLS = [
    "http://172.30.32.1:8000",           # HAOS default gateway (most reliable)
    "http://homeassistant.local:8000",   # HAOS host network
    "http://localhost:8000",             # Direct (if same container)
    "http://host.docker.internal:8000",  # Docker for Mac/Windows
]

# Cache the working URL to avoid repeated probing
_working_url = None

async def _find_working_url() -> Optional[str]:
    """Find a working URL for the addon."""
    global _working_url

    if _working_url:
        return _working_url

    async with aiohttp.ClientSession() as session:
        for base_url in ADDON_URLS:
            try:
                logger.debug(f"Trying addon URL: {base_url}")
                async with session.get(f"{base_url}/health", timeout=3) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("status") == "healthy":
                            logger.info(f"Found working addon URL: {base_url}")
                            _working_url = base_url
                            return base_url
            except Exception as e:
                logger.debug(f"URL {base_url} failed: {e}")
                continue

    logger.warning("No working addon URL found")
    return None

async def check_addon_health() -> bool:
    """Check if the addon is available and healthy."""
    try:
        logger.debug("Checking addon health...")
        url = await _find_working_url()
        return url is not None
    except Exception as e:
        logger.debug(f"Error checking addon health: {e}")
        return False

async def get_manual_cookies() -> Optional[str]:
    """Get manually saved cookies from the addon."""
    try:
        logger.info("Checking for manually saved cookies...")

        base_url = await _find_working_url()
        if not base_url:
            logger.warning("Addon not available")
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/cookies/get",
                timeout=10
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success") and result.get("cookies"):
                        logger.info("Found manually saved cookies")
                        return result["cookies"]
                    else:
                        logger.debug("No manual cookies saved")
                        return None
                else:
                    logger.debug(f"Manual cookies request failed with status {resp.status}")
                    return None

    except Exception as e:
        logger.debug(f"Failed to get manual cookies: {e}")
        return None


async def get_fresh_cookies(username: str, password: str) -> Optional[str]:
    """Get fresh cookies using the automation addon."""
    try:
        logger.info("Requesting fresh cookies from PSEG automation addon...")

        # First check if addon is healthy
        base_url = await _find_working_url()
        if not base_url:
            logger.warning("Addon not available or unhealthy, cannot get fresh cookies")
            return None

        # First, try to get manually saved cookies (reCAPTCHA bypass)
        manual_cookies = await get_manual_cookies()
        if manual_cookies:
            logger.info("Using manually saved cookies (reCAPTCHA bypass)")
            return manual_cookies

        # If no manual cookies, try automated login (may fail due to reCAPTCHA)
        logger.info("No manual cookies found, attempting automated login...")

        # Try to connect to the addon
        async with aiohttp.ClientSession() as session:
            # Request login via addon
            login_data = {
                "username": username,
                "password": password
            }

            logger.info("Sending login request to addon with timeout=120s...")

            async with session.post(
                f"{base_url}/login",
                json=login_data,
                timeout=120  # Extended timeout to match addon processing time
            ) as resp:
                logger.info(f"Addon response received: status={resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"Addon response: {result}")
                    if result.get("success") and result.get("cookies"):
                        logger.info("Successfully obtained cookies from addon")
                        return result["cookies"]
                    else:
                        logger.error(f"Addon login failed: {result.get('error', 'Unknown error')}")
                        logger.info("TIP: Save cookies manually at http://homeassistant.local:8000/cookies")
                        return None
                else:
                    logger.error(f"Addon request failed with status {resp.status}")
                    return None

    except Exception as e:
        logger.error(f"Failed to get cookies from addon: {e}")
        return None
