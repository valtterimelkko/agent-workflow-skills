# Browserless.io Reference

Browserless.io provides cloud-based browser automation that can bypass many bot detection systems.

## Authentication

API key should be available in environment:
```bash
export BROWSERLESSIO_API_KEY="your-api-key"
```

## Endpoints

### Function API (Recommended for simple cases)

Execute custom Puppeteer code in the cloud.

**URL:** `https://production-sfo.browserless.io/function?token=YOUR_API_TOKEN`

**Method:** POST

**Content-Type:** `application/javascript` or `application/json`

### BrowserQL API (Recommended for protected sites)

GraphQL-based stealth-first automation API with human-like behavior and advanced bot detection bypass.

**URL:** `https://production-sfo.browserless.io/browserql?token=YOUR_API_TOKEN`

**Key Features:**
- Built-in stealth mode (no extra configuration needed)
- Automatic human-like behavior (mouse movements, typing delays)
- CAPTCHA/Turnstile solving support
- Session persistence
- Proxy rotation

## Technique 1: Function API (Basic)

For sites with light protection:

```javascript
export default async function ({ page }) {
  await page.goto("https://example.com", { 
    waitUntil: "networkidle2", 
    timeout: 30000 
  });
  
  const text = await page.evaluate(() => document.body.innerText);
  const links = await page.evaluate(() => 
    Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
  );
  
  return { 
    data: { text, links }, 
    type: "application/json" 
  };
}
```

## Technique 2: BrowserQL for Protected Sites

For sites with Cloudflare, advanced bot detection, or persistent protection.

### Basic BrowserQL Query

```graphql
query {
  goto(url: "https://example.com") {
    waitForSelector(selector: "body") {
      text
      links
    }
  }
}
```

### With Stealth and Human-Like Behavior

```graphql
query {
  goto(url: "https://example.com", options: { 
    stealth: true,
    humanlike: true 
  }) {
    waitForTimeout(duration: 3000) {
      text
      links
      title
    }
  }
}
```

### Python Integration for BrowserQL

```python
import requests
import os

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
BROWSERLESS_URL = f"https://production-sfo.browserless.io/browserql?token={API_KEY}"

query = """
query Crawl($url: String!) {
  goto(url: $url, options: { stealth: true, humanlike: true }) {
    waitForTimeout(duration: 5000) {
      title
      text
      links
    }
  }
}
"""

response = requests.post(
    BROWSERLESS_URL,
    json={
        "query": query,
        "variables": {"url": "https://example.com"}
    },
    timeout=60
)

result = response.json()
```

## Technique 3: Handling CAPTCHA/Turnstile

BrowserQL can automatically solve CAPTCHAs when detected:

```graphql
query {
  goto(url: "https://protected-site.com", options: { 
    stealth: true,
    humanlike: true,
    solveCaptcha: true
  }) {
    waitForTimeout(duration: 10000) {
      text
      title
      captchaSolved
    }
  }
}
```

Or detect manually:

```python
puppeteer_code = '''
export default async function ({ page }) {
  await page.goto("https://example.com", { waitUntil: "networkidle2" });
  
  // Check for CAPTCHA/Turnstile
  const isCaptcha = await page.$('iframe[src*="captcha"], iframe[src*="turnstile"], .cf-turnstile');
  
  if (isCaptcha) {
    // Wait for manual solve or use solving service
    await page.waitForTimeout(15000);
  }
  
  const text = await page.evaluate(() => document.body.innerText);
  return { data: { text, hasCaptcha: !!isCaptcha }, type: "application/json" };
}
'''
```

## Technique 4: Session Persistence

For sites that require maintaining state across requests:

### Save Session

```javascript
export default async function ({ page, browser }) {
  await page.goto("https://example.com/login");
  
  // Perform login...
  await page.type('#username', 'user');
  await page.type('#password', 'pass');
  await page.click('#submit');
  await page.waitForNavigation();
  
  // Save cookies and localStorage
  const cookies = await page.cookies();
  const localStorage = await page.evaluate(() => {
    const data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      data[key] = localStorage.getItem(key);
    }
    return data;
  });
  
  return { 
    data: { cookies, localStorage }, 
    type: "application/json" 
  };
}
```

### Restore Session

```javascript
export default async function ({ page, browser, context }) {
  // Restore cookies
  if (context.cookies) {
    await page.setCookie(...context.cookies);
  }
  
  await page.goto("https://example.com/protected-page");
  
  // Restore localStorage
  if (context.localStorage) {
    await page.evaluate((data) => {
      for (const [key, value] of Object.entries(data)) {
        localStorage.setItem(key, value);
      }
    }, context.localStorage);
  }
  
  const text = await page.evaluate(() => document.body.innerText);
  return { data: { text }, type: "application/json" };
}
```

Pass context via JSON API:

```bash
curl -X POST "https://production-sfo.browserless.io/function?token=API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "export default async function ({ page, context }) { ... }",
    "context": {
      "cookies": [...],
      "localStorage": {...}
    }
  }'
```

## Technique 5: Proxy Rotation

For sites with IP-based rate limiting:

```javascript
export default async function ({ page, browser }) {
  // Use proxy via launch options (requires dedicated proxy plan)
  // Or rotate at account level in browserless dashboard
  
  await page.goto("https://example.com");
  const text = await page.evaluate(() => document.body.innerText);
  
  return { data: { text }, type: "application/json" };
}
```

With BrowserQL proxy option:

```graphql
query {
  goto(
    url: "https://example.com",
    options: { 
      stealth: true,
      proxy: { 
        host: "proxy.example.com",
        port: 8080,
        username: "user",
        password: "pass"
      }
    }
  ) {
    text
  }
}
```

## Technique 6: Advanced Stealth Configuration

When default stealth isn't enough:

```javascript
export default async function ({ page }) {
  // Set realistic viewport
  await page.setViewport({ 
    width: 1920, 
    height: 1080,
    deviceScaleFactor: 1
  });
  
  // Override user agent
  await page.setUserAgent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  );
  
  // Inject stealth scripts
  await page.evaluateOnNewDocument(() => {
    // Hide webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    
    // Fake plugins
    Object.defineProperty(navigator, 'plugins', { 
      get: () => [
        { name: 'Chrome PDF Plugin' },
        { name: 'Native Client' }
      ] 
    });
    
    // Fake languages
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  });
  
  await page.goto("https://example.com", { waitUntil: "networkidle2" });
  
  // Add human-like delays
  await new Promise(r => setTimeout(r, 3000 + Math.random() * 2000));
  
  const text = await page.evaluate(() => document.body.innerText);
  return { data: { text }, type: "application/json" };
}
```

## Handling Common Protection Mechanisms

### Cloudflare Challenges

Use BrowserQL with stealth mode:

```python
import requests
import os

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
url = f"https://production-sfo.browserless.io/browserql?token={API_KEY}"

query = """
query {
  goto(
    url: "https://cloudflare-protected-site.com",
    options: { 
      stealth: true,
      humanlike: true,
      timeout: 60000
    }
  ) {
    waitForTimeout(duration: 10000) {
      title
      text
      url  # Final URL after any redirects/challenges
    }
  }
}
"""

response = requests.post(url, json={"query": query}, timeout=70)
result = response.json()
```

### TLS Fingerprinting (JA3/JA4)

Browserless handles this automatically in stealth mode. No additional configuration needed.

### Rate Limiting

1. Add delays between requests:
```python
import time
time.sleep(2 + random.random() * 3)  # 2-5 second delay
```

2. Use session persistence to avoid re-challenging

3. Enable proxy rotation in browserless dashboard

## Python Integration Examples

### Basic Function API

```python
import requests
import os

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
BROWSERLESS_URL = f"https://production-sfo.browserless.io/function?token={API_KEY}"

def crawl_with_browserless(url):
    puppeteer_code = f'''
export default async function ({{ page }}) {{
  await page.goto("{url}", {{ 
    waitUntil: "networkidle2", 
    timeout: 30000 
  }});
  
  await new Promise(r => setTimeout(r, 3000));
  
  const text = await page.evaluate(() => document.body.innerText);
  const links = await page.evaluate(() => 
    Array.from(document.querySelectorAll('a[href]'))
      .map(a => a.getAttribute('href'))
      .filter(h => h && !h.startsWith('#'))
  );
  
  return {{ 
    data: {{ text, links }}, 
    type: "application/json" 
  }};
}}
'''
    
    response = requests.post(
        BROWSERLESS_URL,
        headers={'Content-Type': 'application/javascript'},
        data=puppeteer_code,
        timeout=55
    )
    
    return response.json()['data']
```

### Protected Site with BrowserQL

```python
import requests
import os

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
BROWSERLESS_URL = f"https://production-sfo.browserless.io/browserql?token={API_KEY}"

def crawl_protected_site(url):
    """Crawl sites with Cloudflare or advanced protection."""
    query = """
    query CrawlProtected($url: String!) {
      goto(url: $url, options: { 
        stealth: true, 
        humanlike: true,
        timeout: 60000 
      }) {
        waitForTimeout(duration: 8000) {
          title
          text
          links
          url
        }
      }
    }
    """
    
    response = requests.post(
        BROWSERLESS_URL,
        json={
            "query": query,
            "variables": {"url": url}
        },
        timeout=70
    )
    
    result = response.json()
    if result.get('data', {}).get('goto', {}).get('waitForTimeout'):
        return result['data']['goto']['waitForTimeout']
    return None
```

### With Session Persistence

```python
import json
import os

SESSION_FILE = "browserless_session.json"

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            return json.load(f)
    return {}

def save_session(session):
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f)

def crawl_with_session(url):
    session = load_session()
    
    puppeteer_code = f'''
export default async function ({{ page, context }}) {{
  // Restore session
  if (context.cookies) {{
    await page.setCookie(...context.cookies);
  }}
  
  await page.goto("{url}", {{ waitUntil: "networkidle2" }});
  
  // Extract content
  const data = await page.evaluate(() => ({{
    text: document.body.innerText,
    title: document.title
  }}));
  
  // Save updated session
  const cookies = await page.cookies();
  
  return {{
    data: {{ ...data, cookies }},
    type: "application/json"
  }};
}}
'''
    
    response = requests.post(
        BROWSERLESS_URL,
        headers={'Content-Type': 'application/json'},
        json={
            "code": puppeteer_code,
            "context": session
        },
        timeout=55
    )
    
    result = response.json()
    if result.get('data', {}).get('cookies'):
        save_session({"cookies": result['data']['cookies']})
    
    return result['data']
```

## Scrape API (Alternative)

For simpler extraction without custom code:

```bash
curl -X POST "https://production-sfo.browserless.io/scrape?token=YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "elements": [
      { "selector": "h1" },
      { "selector": "a" },
      { "selector": "p" }
    ],
    "gotoOptions": {
      "waitUntil": "networkidle2",
      "timeout": 30000
    }
  }'
```

## Limitations & Notes

### Free Tier Limits
- 60 second session timeout per request
- Limited concurrent sessions
- Rate limiting applies
- No dedicated stealth endpoints (use BrowserQL instead)

### Common Errors

**ERR_CERT_COMMON_NAME_INVALID**
- Site has SSL certificate issues
- Try `acceptInsecureCerts: true` (may not work on all plans)
- Try HTTP instead of HTTPS

**Navigation timeout**
- Page took too long to load
- Increase timeout in `gotoOptions`
- Check if site blocks automation

**Execution context destroyed**
- Page navigated during execution
- Add waits after goto before extracting content

**CAPTCHA loop**
- Site detected automation despite stealth
- Try BrowserQL with `humanlike: true`
- Add longer delays between actions
- Use session persistence after first solve

### When Browserless Fails

Some sites have extremely sophisticated protection:
- Advanced reCAPTCHA v3 with bot scoring
- Behavioral biometrics
- IP reputation checks with residential proxy requirements

In these cases:
1. Use BrowserQL with both `stealth: true` and `humanlike: true`
2. Enable proxy rotation
3. Implement session persistence
4. Add randomized delays between actions
5. Consider manual intervention for initial challenge

## Resources

- Official docs: https://docs.browserless.io/
- API reference: https://docs.browserless.io/rest-apis/intro
- Function API: https://docs.browserless.io/rest-apis/function
- BrowserQL docs: https://docs.browserless.io/browserql/intro
