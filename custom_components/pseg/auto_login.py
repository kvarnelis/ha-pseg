#!/usr/bin/env python3
"""Automated login for PSEG using the automation addon."""

import asyncio
import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

async def check_addon_health() -> bool:
    """Check if the addon is available and healthy."""
    try:
        logger.debug("Checking addon health...")
        
        async with aiohttp.ClientSession() as session:
            # Check if addon is available via direct port access
            try:
                async with session.get("http://localhost:8000/health", timeout=5) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("status") == "healthy":
                            logger.debug("Addon is healthy and available")
                            return True
                        else:
                            logger.debug("Addon responded but status is not healthy")
                            return False
                    else:
                        logger.debug(f"Addon health check failed with status {resp.status}")
                        return False
            except Exception as e:
                logger.debug(f"Addon health check failed: {e}")
                return False
                
    except Exception as e:
        logger.debug(f"Error checking addon health: {e}")
        return False

async def get_manual_cookies() -> Optional[str]:
    """Get manually saved cookies from the addon."""
    try:
        logger.info("Checking for manually saved cookies...")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/cookies/get",
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
        if not await check_addon_health():
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
                "http://localhost:8000/login",
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
