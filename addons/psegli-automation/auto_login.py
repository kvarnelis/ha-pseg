#!/usr/bin/env python3
"""
PSEG NJ Auto Login Addon
Uses realistic browsing pattern to avoid detection and obtain authentication cookies.
"""
import asyncio
import logging
import random
import time
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


class PSEGAutoLogin:
    """PSEG NJ automated login using realistic browsing pattern."""
    
    def __init__(self, email: str, password: str):
        """Initialize PSEG auto login."""
        self.email = email
        self.password = password
        self.headless = True  # Must be headless in addon environment
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.login_cookies = {}
        self.exceptional_dashboard_data = None
        
        # URLs for the realistic browsing flow - FIXED FOR NJ
        self.brave_search_url = "https://search.brave.com/search?q=pseg+new+jersey&source=desktop"
        self.pseg_main_url = "https://nj.pseg.com/"
        self.login_page_url = "https://nj.myaccount.pseg.com/user/login"
        self.id_domain = "https://id.nj.myaccount.pseg.com/"
        self.dashboard_url = "https://nj.myaccount.pseg.com/dashboards"
        self.exceptional_dashboard = "https://nj.myaccount.pseg.com/dashboards/exceptionaldashboard"
        self.mysmartenergy_redirect = "https://nj.myaccount.pseg.com/LI/Header/RedirectMDMWidget"
        self.final_dashboard = "https://mysmartenergy.nj.pseg.com/Dashboard"
    
    async def setup_browser(self) -> bool:
        """Initialize Playwright browser with stealth options."""
        try:
            _LOGGER.info("🚀 Initializing Playwright browser...")
            self.playwright = await async_playwright().start()
            
            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # Create context with stealth options
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                extra_http_headers={
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"'
                },
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                screen={
                    'width': 1920,
                    'height': 1080
                }
            )
            
            # Create page and apply stealth
            self.page = await self.context.new_page()
            
            # Apply stealth techniques
            await self.page.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // Ensure window.chrome exists
                if (!window.chrome) {
                    Object.defineProperty(window, 'chrome', {
                        get: () => ({
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {}
                        }),
                        configurable: true
                    });
                }
                
                // Override navigator.permissions
                if (!navigator.permissions) {
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: function() { return Promise.resolve({ state: 'granted' }); }
                        }),
                        configurable: true
                    });
                }
                
                // Override navigator.plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const pluginArray = [];
                        const pluginNames = ['Chrome PDF Plugin', 'Chrome PDF Viewer', 'Native Client'];
                        const pluginDescriptions = ['Portable Document Format', 'Portable Document Format', 'Native Client Executable'];
                        const pluginFilenames = ['internal-pdf-viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', 'internal-nacl-plugin'];
                        
                        for (let i = 0; i < pluginNames.length; i++) {
                            const plugin = {
                                name: pluginNames[i],
                                description: pluginDescriptions[i],
                                filename: pluginFilenames[i]
                            };
                            pluginArray[i] = plugin;
                        }
                        
                        Object.defineProperty(pluginArray, 'length', { value: pluginNames.length });
                        return pluginArray;
                    },
                    configurable: true
                });
                
                // Override window dimensions
                Object.defineProperty(window, 'outerWidth', {
                    get: () => 1922,
                    configurable: true
                });
                Object.defineProperty(window, 'outerHeight', {
                    get: () => 1055,
                    configurable: true
                });
                
                // Override deviceMemory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                    configurable: true
                });
                
                console.log('🔍 Stealth techniques applied');
            """)
            
            # Set up request interception
            await self.setup_request_interception()
            
            _LOGGER.info("✅ Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to setup browser: {e}")
            return False
    
    async def setup_request_interception(self):
        """Set up request interception to capture cookies and exceptional dashboard data."""
        try:
            await self.page.route("**/*", self.handle_request)
            _LOGGER.info("✅ Request interception setup complete")
        except Exception as e:
            _LOGGER.warning(f"Could not setup request interception: {e}")
    
    async def handle_request(self, route):
        """Handle intercepted requests to capture cookies and exceptional dashboard data."""
        try:
            request = route.request
            if "mysmartenergy.nj.pseg.com" in request.url:
                # Capture cookies from MySmartEnergy requests
                if hasattr(request, 'headers') and 'cookie' in request.headers:
                    cookie_header = request.headers['cookie']
                    if cookie_header:
                        # Parse cookies and store them
                        self.parse_cookies(cookie_header)
            elif "exceptionaldashboard" in request.url and request.method == "POST":
                # Capture exceptional dashboard request data
                _LOGGER.info("🔍 Intercepted exceptional dashboard POST request")
                self.exceptional_dashboard_data = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data if hasattr(request, 'post_data') else None
                }
                _LOGGER.info(f"📋 Captured exceptional dashboard data")
        except Exception as e:
            _LOGGER.debug(f"Error handling request: {e}")
        
        # Continue with the request
        await route.continue_()
    
    def parse_cookies(self, cookie_header: str):
        """Parse cookie header and extract important cookies."""
        try:
            cookies = cookie_header.split(';')
            for cookie in cookies:
                cookie = cookie.strip()
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    
                    # Store important cookies
                    if name in ['MM_SID', '__RequestVerificationToken', 'ASP.NET_SessionId']:
                        self.login_cookies[name] = value
        except Exception as e:
            _LOGGER.warning(f"Error parsing cookies: {e}")
    
    async def simulate_realistic_browsing(self) -> bool:
        """Simulate realistic browsing pattern to avoid detection."""
        try:
            _LOGGER.info("🌐 Starting login flow...")
            
            # Set page timeout to be more generous for the entire process
            self.page.set_default_timeout(60000)  # 60 seconds
            
            # Skip straight to the login page - no need for nj.pseg.com
            _LOGGER.info("🔑 Step 1: Navigating directly to login page...")
            await self.page.goto(self.login_page_url, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            _LOGGER.info("✅ Login page loaded")
            
            # Check if we got redirected to the ID provider
            current_url = self.page.url
            _LOGGER.info(f"📍 Current URL: {current_url}")
            
            # Step 2: Fill login form
            _LOGGER.info("📝 Step 2: Filling login form...")
            
            # Wait for form fields
            await self.page.wait_for_selector('input[name="username"], input[type="email"], input[id="username"]', timeout=10000)
            await self.page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
            
            # Find username field
            username_field = await self.page.query_selector('input[name="username"], input[type="email"], input[id="username"]')
            if username_field:
                await username_field.click()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                await username_field.fill(self.email)
                _LOGGER.info("✅ Username entered")
            else:
                _LOGGER.error("❌ Username field not found")
                return False
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Find password field
            password_field = await self.page.query_selector('input[name="password"], input[type="password"]')
            if password_field:
                await password_field.click()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                await password_field.fill(self.password)
                _LOGGER.info("✅ Password entered")
            else:
                _LOGGER.error("❌ Password field not found")
                return False
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Find and click LOG IN button
            _LOGGER.info("🔘 Looking for LOG IN button...")
            login_submit_button = await self.page.wait_for_selector('button[type="submit"], input[type="submit"], button:has-text("LOG IN"), button:has-text("Sign In")', timeout=10000)
            
            if not login_submit_button:
                _LOGGER.error("❌ LOG IN button not found")
                return False
            
            _LOGGER.info("✅ LOG IN button found, clicking...")
            
            # Click the login button
            await login_submit_button.click()
            
            # Wait for dashboard to load
            _LOGGER.info("🔄 Waiting for dashboard to load...")
            
            try:
                # Wait for redirect to dashboard
                await self.page.wait_for_url(lambda url: "nj.myaccount.pseg.com/dashboards" in url or "myaccount.pseg.com" in url, timeout=30000)
                await asyncio.sleep(random.uniform(2.0, 3.0))
                _LOGGER.info("✅ Dashboard loaded")
            except Exception as e:
                # Check if we're still on the login page (login failed)
                current_url = self.page.url
                if "id.nj.myaccount.pseg.com" in current_url:
                    _LOGGER.error(f"❌ Login failed - still on login page: {current_url}")
                    return False
                elif "nj.myaccount.pseg.com" in current_url:
                    _LOGGER.info(f"✅ On myaccount page: {current_url}")
                else:
                    _LOGGER.error(f"❌ Failed to reach dashboard: {current_url}")
                    return False
            
            # Step 3: Navigate to MySmartEnergy
            _LOGGER.info("⚡ Step 3: Navigating to MySmartEnergy dashboard...")
            
            # Wait for the page to settle
            await asyncio.sleep(3.0)
            
            # Try to find and click the MySmartEnergy link, or navigate directly
            try:
                # First try to find a link to MySmartEnergy
                mysmartenergy_link = await self.page.query_selector('a[href*="mysmartenergy"], a:has-text("MySmartEnergy"), a:has-text("Smart Energy")')
                if mysmartenergy_link:
                    _LOGGER.info("✅ Found MySmartEnergy link, clicking...")
                    await mysmartenergy_link.click()
                    await asyncio.sleep(3.0)
                else:
                    # Try the redirect URL
                    _LOGGER.info("🔄 Trying redirect URL...")
                    await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
            except Exception as e:
                _LOGGER.warning(f"⚠️ MySmartEnergy link not found, trying direct navigation: {e}")
                await self.page.goto(self.final_dashboard, wait_until='domcontentloaded', timeout=20000)
            
            # Wait for MySmartEnergy dashboard
            try:
                await self.page.wait_for_url(lambda url: "mysmartenergy.nj.pseg.com" in url, timeout=20000)
            except Exception as e:
                _LOGGER.warning(f"⚠️ URL wait failed: {e}, trying direct navigation...")
                current_url = self.page.url
                if "mysmartenergy.nj.pseg.com" not in current_url:
                    await self.page.goto(self.final_dashboard, wait_until='domcontentloaded', timeout=20000)
            
            await asyncio.sleep(3.0)
            
            _LOGGER.info("✅ MySmartEnergy Dashboard loaded")
            
            # Step 4: Get cookies from the final dashboard
            _LOGGER.info("🍪 Step 4: Capturing cookies from final dashboard...")
            
            # Wait a moment for any additional requests to complete
            await asyncio.sleep(3.0)
            
            # Get cookies from browser context
            context_cookies = await self.context.cookies()
            for cookie in context_cookies:
                if cookie['domain'] in ['.pseg.com', '.nj.pseg.com', 'nj.pseg.com', '.myaccount.pseg.com', 'nj.myaccount.pseg.com', '.mysmartenergy.nj.pseg.com', 'mysmartenergy.nj.pseg.com']:
                    self.login_cookies[cookie['name']] = cookie['value']
                    _LOGGER.info(f"🍪 Context cookie: {cookie['name']} = {cookie['value'][:50]}...")
            
            _LOGGER.info("✅ Realistic browsing pattern completed successfully")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Error during realistic browsing: {e}")
            return False
    
    def format_cookies_for_api(self) -> str:
        """Format cookies in the format expected by the API."""
        try:
            cookie_strings = []
            if 'MM_SID' in self.login_cookies:
                cookie_strings.append(f"MM_SID={self.login_cookies['MM_SID']}")
            if '__RequestVerificationToken' in self.login_cookies:
                cookie_strings.append(f"__RequestVerificationToken={self.login_cookies['__RequestVerificationToken']}")
            
            if cookie_strings:
                result = "; ".join(cookie_strings)
                _LOGGER.info(f"🍪 Formatted cookies for API: {result[:100]}...")
                return result
            else:
                _LOGGER.warning("⚠️ No valid cookies to format for API")
                return ""
                
        except Exception as e:
            _LOGGER.warning(f"Error formatting cookies for API: {e}")
            return ""
    
    async def get_cookies(self) -> Optional[str]:
        """Get cookies by following the realistic browsing pattern."""
        try:
            if not await self.setup_browser():
                _LOGGER.error("❌ Failed to setup browser")
                return None
            
            # Follow the realistic browsing pattern
            if not await self.simulate_realistic_browsing():
                _LOGGER.error("❌ Realistic browsing pattern failed")
                return None
            
            # Check if we got the cookies we need
            if self.login_cookies:
                _LOGGER.info("✅ SUCCESS: Got cookies from realistic browsing pattern")
                for name, value in self.login_cookies.items():
                    _LOGGER.info(f"🍪 {name}: {value[:50]}...")
                
                # Format cookies for API use
                return self.format_cookies_for_api()
            else:
                _LOGGER.warning("⚠️ No cookies captured, but browsing completed")
                return ""
                
        except Exception as e:
            _LOGGER.error(f"Error getting cookies: {e}")
            return None
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            _LOGGER.warning(f"Error during cleanup: {e}")


# API Endpoints for Home Assistant integration
async def get_pseg_cookies(email: str, password: str) -> Optional[str]:
    """
    Get PSEG cookies for Home Assistant integration.
    
    Args:
        email: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        _LOGGER.info("🚀 Starting PSEG cookie acquisition for Home Assistant...")
        cookie_getter = PSEGAutoLogin(email=email, password=password)
        return await cookie_getter.get_cookies()
    except Exception as e:
        _LOGGER.error(f"Failed to get PSEG cookies: {e}")
        return None


def get_pseg_cookies_sync(email: str, password: str) -> Optional[str]:
    """
    Synchronous wrapper for get_pseg_cookies.
    
    Args:
        email: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        return asyncio.run(get_pseg_cookies(email, password))
    except Exception as e:
        _LOGGER.error(f"Failed to get PSEG cookies synchronously: {e}")
        return None


# Compatibility wrapper for existing integration
async def get_fresh_cookies(username: str, password: str) -> Optional[str]:
    """
    Compatibility wrapper for existing integration.
    This function maintains the same interface as the old implementation.
    
    Args:
        username: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        _LOGGER.info(f"Login attempt for user: {username}")
        return await get_pseg_cookies(username, password)
    except Exception as e:
        _LOGGER.error(f"Login error: {e}")
        return None


# Test function for standalone usage
async def main():
    """Test function for standalone usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='PSEG NJ Auto Login - Home Assistant Addon')
    parser.add_argument('--email', required=True, help='PSEG account email/username')
    parser.add_argument('--password', required=True, help='PSEG account password')
    
    args = parser.parse_args()
    
    _LOGGER.info("🚀 Starting PSEG NJ Auto Login - Home Assistant Addon")
    _LOGGER.info(f"📧 Email: {args.email}")
    _LOGGER.info("🔒 Headless mode: True (required for addon environment)")
    
    cookies = await get_pseg_cookies(args.email, args.password)
    
    if cookies:
        _LOGGER.info("🎉 SUCCESS: Cookies obtained successfully!")
        _LOGGER.info("=" * 80)
        _LOGGER.info("COOKIE STRING (for Home Assistant integration):")
        _LOGGER.info("=" * 80)
        _LOGGER.info(cookies)
        _LOGGER.info("=" * 80)
        _LOGGER.info(f"📋 Total length: {len(cookies)} characters")
        return 0
    else:
        _LOGGER.error("❌ FAILED: Could not obtain cookies")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
