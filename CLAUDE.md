# CLAUDE.md - PSE&G NJ Home Assistant Integration

## Project Overview

This is a Home Assistant integration for PSE&G New Jersey energy usage data. It consists of two components:

1. **Addon** (`addons/psegli-automation/`) - Playwright-based browser automation to obtain authentication cookies
2. **Integration** (`custom_components/pseg/`) - HA integration that fetches energy data using those cookies

## Key Files

- `addons/psegli-automation/auto_login.py` - Main login automation script
- `addons/psegli-automation/main.py` - FastAPI server exposing `/login` endpoint
- `addons/psegli-automation/Dockerfile` - Container build with Playwright/Chromium
- `custom_components/pseg/pseg.py` - API client for fetching energy data
- `custom_components/pseg/__init__.py` - HA integration setup

## PSE&G NJ URLs (NOT Long Island!)

This is forked from a PSEG Long Island integration. The NJ URLs are different:

- Main site: `https://nj.pseg.com/` (heavy, avoid if possible)
- Login: `https://nj.myaccount.pseg.com/user/login`
- ID provider: `https://id.nj.myaccount.pseg.com/`
- Dashboard: `https://nj.myaccount.pseg.com/dashboards`
- MySmartEnergy: `https://mysmartenergy.nj.pseg.com/Dashboard`

The login button on nj.pseg.com is `#btnLogin` (not `#login`).

## MySmartEnergy Direct Login

MySmartEnergy has its own login form at `https://mysmartenergy.nj.pseg.com/`:
- Email field: `#LoginEmail`
- Password field: `#LoginPassword`
- Login button: `.loginBtn` (has reCAPTCHA)
- SSO link: `a[href="/Saml/okta-prod/SignIn"]` ("Sign in Via My Account")

The SSO route avoids reCAPTCHA but requires navigating through myaccount.pseg.com.

## Testing Locally

Run Playwright with visible browser to debug:

```bash
cd addons/psegli-automation
pip install playwright
playwright install chromium

# Edit auto_login.py, set self.headless = False
python auto_login.py --email your@email.com --password yourpass
```

## Common Issues

1. **Timeout on nj.pseg.com** - The main site is very heavy. Skip it and go directly to login page.
2. **Wrong URL patterns** - Original code used Long Island URLs (`www.psegliny.com`). Make sure all URLs use NJ patterns.
3. **networkidle hangs** - Don't use `wait_for_load_state('networkidle')` on PSEG pages. Use `domcontentloaded` instead.
4. **Cookie domains** - Cookies come from multiple domains: `.pseg.com`, `nj.myaccount.pseg.com`, `mysmartenergy.nj.pseg.com`

## Deployment

After editing files:

1. Commit and push to GitHub fork
2. In Home Assistant: Settings → Add-ons → PSEG Automation → Rebuild
3. Check logs at Settings → Add-ons → PSEG Automation → Log tab
4. Test via `http://homeassistant.local:8000/docs`

## API Endpoints

The addon exposes:
- `GET /health` - Health check
- `POST /login` - JSON body: `{"username": "...", "password": "..."}`
- `POST /login-form` - Form data: `username=...&password=...`
- `GET /docs` - Swagger UI

## Cookies Needed

The integration needs these cookies from `mysmartenergy.nj.pseg.com`:
- `MM_SID` - MyMeter session ID (primary)
- `__RequestVerificationToken` - CSRF token

## Energy Data API

Once authenticated, data is fetched from:
- `POST /Dashboard/Chart` - Set date range and granularity
- `GET /Dashboard/ChartData` - Returns hourly usage JSON

## Repository Structure

```
ha-pseg/
├── addons/
│   └── psegli-automation/
│       ├── auto_login.py      # Browser automation
│       ├── main.py            # FastAPI server
│       ├── Dockerfile
│       ├── config.yaml        # HA addon config
│       └── requirements.txt
├── custom_components/
│   └── pseg/
│       ├── __init__.py        # Integration setup
│       ├── pseg.py            # API client
│       ├── config_flow.py     # Setup UI
│       ├── const.py           # Constants
│       └── manifest.json
├── repository.yaml            # HA addon repo config
└── hacs.json                  # HACS config
```

## Development Log

Maintain a detailed log of all attempted approaches and their results in `revisions.md`. This file should track:

- What was tried
- Why it was tried
- The exact results (success/failure)
- Error messages if applicable
- Next steps or conclusions

This helps avoid repeating failed approaches and documents the journey to a working solution.
