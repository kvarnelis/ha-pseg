# Revisions Log

## 2026-01-07: Okta Login Form Field Selectors

### Problem
Login failing with timeout waiting for username field:
```
Error during realistic browsing: Page.wait_for_selector: Timeout 10000ms exceeded.
waiting for locator("input[name=\"username\"], input[type=\"email\"], input[id=\"username\"]") to be visible
```

### Analysis
The login page redirects to Okta identity provider at `id.myaccount.pseg.com/oauth2/...`. Okta uses different field names than standard forms:
- Username: `identifier` or `idp-discovery-username` (not `username`)
- Password: `credentials.passcode` (not just `password`)

### Changes Made
Updated `auto_login.py` selectors:

**Username field (line ~249):**
```python
# Old:
'input[name="username"], input[type="email"], input[id="username"]'

# New:
'input[name="identifier"], input[name="username"], input[id="idp-discovery-username"], input[id="okta-signin-username"]'
```

**Password field (line ~265):**
```python
# Old:
'input[name="password"], input[type="password"]'

# New:
'input[name="credentials.passcode"], input[name="password"], input[type="password"]'
```

Also increased timeout from 10000ms to 15000ms.

### Result
Pending - needs rebuild and test.

### Next Steps
1. Commit and push changes
2. Rebuild addon in Home Assistant
3. Test login again

---

## 2026-01-07: Skip nj.pseg.com (Previous Fix)

### Problem
Timeout on Step 2 navigating to PSEG main site:
```
Error during realistic browsing: Timeout 30000ms exceeded.
🏠 Step 2: Navigating to PSEG main site...
```

### Analysis
The `nj.pseg.com` main site is extremely heavy and times out. As noted in `claude.md`: "The main site is very heavy. Skip it and go directly to login page."

### Changes Made
Removed the "realistic browsing pattern" that:
1. Went to Brave search
2. Navigated to nj.pseg.com
3. Clicked login button

Instead, now navigates directly to `https://nj.myaccount.pseg.com/user/login`.

### Result
SUCCESS - Addon now gets to login page. But then fails on finding form fields (see above).
