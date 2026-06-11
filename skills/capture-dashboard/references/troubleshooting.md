# Troubleshooting Guide: Dashboard Capture

This guide provides detailed solutions for common issues when capturing authenticated dashboards.

## Authentication Issues

### Cookie Format Problems

**Symptom**: Script fails with "Invalid cookie JSON format" error

**Causes**:
- Malformed JSON syntax
- Wrong export format from browser extension
- Encoding issues

**Solutions**:

1. **Validate JSON format**: Use a JSON validator (jsonlint.com) to check syntax
2. **Re-export cookies**: Use the cookie-editor extension and select "JSON" format explicitly
3. **Check for special characters**: Ensure there are no unescaped quotes or control characters

**Expected cookie format** (array of cookie objects):
```json
[
  {
    "name": "session_id",
    "value": "abc123...",
    "domain": ".example.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]
```

### Expired Cookies

**Symptom**: Authentication works initially but fails later

**Causes**:
- Session timeout
- Cookie expiration reached
- Server-side session invalidation

**Solutions**:

1. **Re-export fresh cookies**: Sign in again and export new cookies
2. **Check expiration**: Look at the `expires` field in cookies (Unix timestamp)
3. **Keep session active**: Re-export cookies if you haven't used them in a while

**Tip**: Some applications have very short session timeouts (15-30 minutes). Consider capturing immediately after exporting cookies.

### Domain/Subdomain Cookie Scoping

**Symptom**: Cookies work in browser but not in capture script

**Causes**:
- Cookie domain doesn't match target URL
- Subdomain mismatch
- Missing domain attribute

**Solutions**:

1. **Match domains exactly**: If your dashboard is at `app.example.com`, export cookies from that exact subdomain
2. **Check domain attribute**: Cookies with `domain: .example.com` (note the leading dot) work across subdomains
3. **Export from the right page**: Navigate to the exact dashboard page before exporting cookies

**Example**:
```
Dashboard URL: https://app.example.com/dashboard
Cookie domain: .example.com  ✓ (works)
Cookie domain: example.com   ✓ (works)
Cookie domain: www.example.com  ✗ (doesn't work for app.example.com)
```

### httpOnly and Secure Flags

**Symptom**: Some cookies missing or not working

**Causes**:
- httpOnly cookies not exported by extension
- Secure cookies require HTTPS
- SameSite restrictions

**Solutions**:

1. **Use a better extension**: Try "EditThisCookie" or "Cookie-Editor" which export httpOnly cookies
2. **Check HTTPS**: Cookies with `secure: true` only work over HTTPS
3. **SameSite attribute**: Cookies with `sameSite: Strict` may not work in automated contexts

**Manual cookie extraction** (if extension doesn't work):

Open browser DevTools (F12), go to Application/Storage > Cookies, and manually copy each cookie:

```javascript
// Run in browser console (on the authenticated page)
copy(JSON.stringify(document.cookie.split('; ').map(pair => {
  const [name, value] = pair.split('=');
  return {
    name,
    value,
    domain: window.location.hostname,
    path: '/',
    secure: window.location.protocol === 'https:',
    httpOnly: false  // JS can't access httpOnly cookies
  };
}), null, 2))
```

**Note**: This method doesn't capture httpOnly cookies. For those, use a browser extension.

## Cookie Export Issues

### Chrome Cookie-Editor

**Detailed steps**:

1. Install extension from Chrome Web Store: https://chrome.google.com/webstore/search/cookie-editor
2. Navigate to your authenticated dashboard page
3. Click the cookie-editor extension icon (usually in the toolbar)
4. Click "Export" button
5. Select "JSON" format (not "Netscape" or "Header String")
6. Copy the JSON output
7. Paste into a text editor and save as `cookies.json`

**Important**: Export cookies while you're on the actual dashboard page, not the login page.

### Firefox Cookie-Editor

Similar to Chrome:

1. Install Cookie-Editor from Firefox Add-ons
2. Navigate to authenticated dashboard
3. Click extension icon
4. Export as JSON
5. Save to file

### Microsoft Edge

Edge uses Chrome extensions:

1. Enable Chrome extensions in Edge
2. Install cookie-editor from Chrome Web Store
3. Follow Chrome instructions above

### Manual Cookie Extraction (All Browsers)

If extensions don't work, use DevTools:

1. Open DevTools (F12)
2. Go to "Application" tab (Chrome/Edge) or "Storage" tab (Firefox)
3. Click "Cookies" in the left sidebar
4. Select your domain
5. Copy each cookie manually

**Manual JSON construction**:
```json
[
  {
    "name": "COPY_FROM_DEVTOOLS",
    "value": "COPY_FROM_DEVTOOLS",
    "domain": ".example.com",
    "path": "/",
    "secure": true,
    "httpOnly": true
  }
]
```

### Cookie Validation

To verify your cookies are valid before using them:

```bash
# Quick validation (check if file exists and is valid JSON)
cat cookies.json | jq '.'

# If jq is not installed
node -e "console.log(JSON.stringify(JSON.parse(require('fs').readFileSync('cookies.json', 'utf8')), null, 2))"
```

## Capture Failures

### Network Timeouts

**Symptom**: "Navigation timeout of 30000 ms exceeded"

**Causes**:
- Slow network connection
- Heavy JavaScript execution on page
- Large resources loading
- Server response delays

**Solutions**:

1. **Increase timeout**: Modify config:
   ```json
   {
     "timeout": 60000
   }
   ```

2. **Check network**: Verify you can access the URL in browser
3. **Test with curl**: `curl -I https://dashboard.example.com`
4. **Try different waitUntil strategy**: Modify capture.js to use 'domcontentloaded' instead of 'networkidle0'

### CORS Issues

**Symptom**: Resources not loading, console errors about CORS

**Causes**:
- Cross-origin resources blocked
- Missing CORS headers
- Browser security restrictions

**Solutions**:

1. **CORS doesn't affect screenshots**: HTML capture may have missing resources, but screenshots will still work
2. **Use screenshot mode**: If HTML is broken due to CORS, use `--mode screenshots`
3. **Resources are captured as-is**: The HTML capture saves the page structure but linked resources may not load when viewing the HTML file

**Note**: This is a browser security feature and cannot be bypassed. Screenshots are not affected.

### JavaScript Errors on Page

**Symptom**: Page loads but looks broken or incomplete

**Causes**:
- JavaScript errors during page load
- Missing dependencies
- Race conditions in page initialization

**Solutions**:

1. **Wait longer**: Increase timeout to give JavaScript more time to execute
2. **Check browser console**: Run in non-headless mode to see errors:
   ```javascript
   // In capture.js, change:
   headless: false  // instead of headless: true
   ```

3. **Add custom wait**: For specific elements that load slowly, modify capture.js to wait for them:
   ```javascript
   await this.page.waitForSelector('.dashboard-loaded');
   ```

### Dynamic Content Loading

**Symptom**: Screenshots show loading spinners or incomplete content

**Causes**:
- Lazy-loaded content
- Infinite scroll
- Content loaded after user interaction

**Solutions**:

1. **Wait for networkidle0**: The script already does this, but some pages may need longer
2. **Add delay**: Insert a delay before capture:
   ```javascript
   await this.page.waitForTimeout(5000);  // Wait 5 seconds
   ```

3. **Scroll to load**: For infinite scroll, modify capture.js to scroll before capturing:
   ```javascript
   await this.page.evaluate(() => {
     window.scrollTo(0, document.body.scrollHeight);
   });
   await this.page.waitForTimeout(2000);
   ```

4. **Trigger interactions**: Click buttons or tabs to load content before capturing

## Output Issues

### File Permission Errors

**Symptom**: "EACCES: permission denied"

**Causes**:
- No write permission to output directory
- Directory owned by different user
- Read-only filesystem

**Solutions**:

1. **Check permissions**: `ls -la output/`
2. **Change ownership**: `sudo chown -R $USER output/`
3. **Use different directory**: Specify a directory you have permission to write to:
   ```bash
   --output ~/dashboard-captures
   ```

### Disk Space Problems

**Symptom**: "ENOSPC: no space left on device"

**Causes**:
- Full disk
- Large number of captures
- Full-page screenshots are large

**Solutions**:

1. **Check disk space**: `df -h`
2. **Clean up old captures**: Delete previous output directories
3. **Use HTML mode only**: HTML files are much smaller than screenshots:
   ```bash
   --mode html
   ```
4. **Reduce quality**: Modify capture.js to use lower quality screenshots

**Size estimates**:
- Full-page PNG screenshot: 500KB - 5MB per page
- HTML file: 50KB - 500KB per page
- 100 pages in "both" mode: ~250MB - 500MB

### Invalid Output Paths

**Symptom**: "ENOENT: no such file or directory"

**Causes**:
- Parent directory doesn't exist
- Invalid path characters
- Relative vs absolute path confusion

**Solutions**:

1. **Use absolute paths**: Specify full path:
   ```bash
   --output /home/user/captures
   ```

2. **Create parent directories**: The script creates output directories, but parent must exist:
   ```bash
   mkdir -p ~/captures
   node scripts/capture.js --output ~/captures/dashboard
   ```

3. **Check path**: Verify the directory exists: `ls -la /path/to/parent`

## Browser Issues

### Chromium Download Failures

**Symptom**: "Failed to launch the browser process" or "Chromium revision is not downloaded"

**Causes**:
- puppeteer installation incomplete
- Network issues during install
- Proxy/firewall blocking downloads

**Solutions**:

1. **Reinstall puppeteer**:
   ```bash
   npm uninstall -g puppeteer
   npm install -g puppeteer
   ```

2. **Manual Chromium download**: Set environment variable before installing:
   ```bash
   PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=false npm install -g puppeteer
   ```

3. **Check Chromium path**: Find where puppeteer stores Chromium:
   ```bash
   node -e "console.log(require('puppeteer').executablePath())"
   ```

4. **Use system Chrome**: Modify capture.js to use your system Chrome:
   ```javascript
   const browser = await puppeteer.launch({
     executablePath: '/usr/bin/google-chrome',  // or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
     headless: true
   });
   ```

### Headless Mode Problems

**Symptom**: Works in browser but not in script

**Causes**:
- Headless mode differences
- User agent detection
- Canvas/WebGL features missing in headless

**Solutions**:

1. **Run in non-headless mode** (for debugging):
   ```javascript
   // In capture.js, change:
   headless: false
   ```

2. **Set user agent**: Make the script appear as a real browser:
   ```javascript
   await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
   ```

3. **Enable additional features**:
   ```javascript
   args: [
     '--no-sandbox',
     '--disable-setuid-sandbox',
     '--disable-dev-shm-usage',
     '--disable-web-security'  // Only for testing
   ]
   ```

### Memory Issues with Large Captures

**Symptom**: "Out of memory" or process crashes

**Causes**:
- Too many pages being captured
- Large images on pages
- Memory leak in long-running captures

**Solutions**:

1. **Reduce crawl depth**: Limit to depth 1:
   ```json
   {"crawl": {"max_depth": 1}}
   ```

2. **Capture in batches**: Split into multiple runs
3. **Increase Node.js memory**: Run with more memory:
   ```bash
   NODE_OPTIONS="--max-old-space-size=4096" node scripts/capture.js --config config.json
   ```

4. **Close browser between pages**: Modify capture.js to restart browser periodically

## Crawling Issues

### Links Not Being Followed

**Symptom**: Only landing page captured

**Debug steps**:

1. **Check crawl.enabled**: Ensure it's `true` in config
2. **Verify max_depth**: Must be > 0 (default is 2)
3. **Check links on page**: Use browser DevTools to verify links exist:
   ```javascript
   Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
   ```

4. **Review exclude patterns**: Ensure patterns aren't too broad
5. **Check same-origin**: Verify links are same-origin if `same_origin_only: true`

**Test**: Run with verbose logging by adding console.log statements in the `extractLinks` method

### Same-Origin Restrictions

**Symptom**: External links not followed

**This is expected behavior**. By default, `same_origin_only: true` prevents crawling external sites.

**To allow external links** (use carefully):
```json
{
  "crawl": {
    "same_origin_only": false,
    "max_depth": 1  // Keep depth low to avoid crawling the entire internet
  }
}
```

**Warning**: Disabling same-origin restriction can result in capturing many unrelated pages.

### Depth Limit Not Working

**Symptom**: More pages captured than expected

**Causes**:
- Depth counting off by one
- Duplicate links at different depths
- Links on multiple pages

**Check metadata.json** to see the depth of each captured page:
```bash
cat output/metadata.json | jq '.pages[] | {url, depth}'
```

**Expected behavior**:
- Depth 0: Landing page (1 page)
- Depth 1: All links from landing page (N pages)
- Depth 2: All links from depth 1 pages (M pages)

With `max_depth: 2`, you'll get 1 + N + M pages total.

### Exclude Patterns Not Matching

**Symptom**: Pages with "logout" in URL still being captured

**Debug**:

1. **Check pattern syntax**: Patterns use wildcards (`*`), not regex
2. **Case sensitivity**: Matching is case-insensitive
3. **Test patterns**:
   ```javascript
   const pattern = "*logout*";
   const regex = new RegExp(pattern.replace(/\*/g, '.*'), 'i');
   console.log(regex.test("https://example.com/logout"));  // should be true
   ```

**Common patterns**:
```json
{
  "exclude_patterns": [
    "*logout*",           // Matches: /logout, /user/logout, /logout.php
    "*admin*",            // Matches: /admin, /admin/dashboard
    "*/delete/*",         // Matches: /user/delete/123
    "*?action=delete*"    // Matches: /page?action=delete&id=5
  ]
}
```

## Advanced Configuration

### Custom User Agents

To appear as a specific browser:

```json
{
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
```

**Note**: Requires modifying capture.js to read this config option.

### Viewport Sizing

The script uses 1920x1080 by default. To change:

Modify capture.js:
```javascript
await this.page.setViewport({ width: 1366, height: 768 });
```

### Custom Wait Strategies

For pages that load content dynamically:

```javascript
// Wait for specific element
await this.page.waitForSelector('.dashboard-content');

// Wait for specific time
await this.page.waitForTimeout(5000);

// Wait for network activity to stop
await this.page.waitForLoadState('networkidle0');

// Wait for DOM to be ready (faster but may miss content)
await this.page.waitForLoadState('domcontentloaded');
```

### Handling Pop-ups and Modals

If pages show modal dialogs:

```javascript
// Auto-dismiss dialogs
this.page.on('dialog', async dialog => {
  await dialog.dismiss();
});
```

## Debugging Tips

### Enable Verbose Logging

Add console.error statements in capture.js:

```javascript
console.error(`[DEBUG] Current URL: ${this.page.url()}`);
console.error(`[DEBUG] Cookies loaded: ${cookies.length}`);
console.error(`[DEBUG] Links found: ${links.length}`);
```

### Run in Non-Headless Mode

See the browser in action:

```javascript
// In capture.js, change:
headless: false
```

### Check Browser Console Logs

Capture console output from the page:

```javascript
this.page.on('console', msg => {
  console.error(`[PAGE LOG] ${msg.type()}: ${msg.text()}`);
});
```

### Validate Cookie JSON Format

```bash
# Check if file is valid JSON
cat cookies.json | jq '.'

# Pretty-print
cat cookies.json | jq '.' > cookies-formatted.json

# Check cookie count
cat cookies.json | jq 'length'

# Check cookie names
cat cookies.json | jq '.[].name'
```

### Test Single Page First

Before crawling, test with a single page:

```bash
node scripts/capture.js \
  --cookies cookies.json \
  --url https://dashboard.example.com \
  --no-crawl \
  --output ./test-output
```

### Review metadata.json

After capture, check for errors:

```bash
# Check status
cat output/metadata.json | jq '.status'

# List all errors
cat output/metadata.json | jq '.errors'

# Pages captured successfully
cat output/metadata.json | jq '.pages_captured'

# List URLs that failed
cat output/metadata.json | jq '.pages[] | select(.error) | .url'
```

## Common Error Messages

### "puppeteer not found"

**Solution**: Install puppeteer:
```bash
npm install -g puppeteer
```

### "Cookie file not found"

**Solution**: Provide absolute path or verify file exists:
```bash
ls -la cookies.json
node scripts/capture.js --cookies "$(pwd)/cookies.json" --url https://example.com
```

### "Authentication failed - redirected to login page"

**Solution**: Re-export fresh cookies. Current cookies are expired or invalid.

### "Invalid cookie JSON format"

**Solution**: Validate JSON syntax:
```bash
cat cookies.json | jq '.'
```

### "Navigation timeout of 30000 ms exceeded"

**Solution**: Increase timeout:
```json
{"timeout": 60000}
```

### "Missing required parameter: --cookies"

**Solution**: Provide cookies file:
```bash
node scripts/capture.js --cookies cookies.json --url https://example.com
```

## Getting Additional Help

If you're still experiencing issues:

1. **Check the script's JSON output**: Contains detailed error information
2. **Run with --help**: See all available options
3. **Test in non-headless mode**: Visual debugging helps identify issues
4. **Check metadata.json**: Contains details about what succeeded/failed
5. **Verify cookies are fresh**: Re-export and try again
6. **Test the URL in browser**: Ensure the page loads normally

**Common root causes**:
- 80% of issues: Expired or invalid cookies
- 15% of issues: Network/timeout problems
- 5% of issues: Configuration errors or missing dependencies
