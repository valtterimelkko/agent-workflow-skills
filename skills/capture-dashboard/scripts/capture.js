#!/usr/bin/env node
/**
 * capture.js - Capture authenticated dashboards as screenshots and HTML
 *
 * USAGE:
 *   node capture.js --config config.json
 *   node capture.js --cookies cookies.json --url https://dashboard.example.com --mode both
 *
 * FEATURES:
 *   - Cookie-based authentication
 *   - Same-origin crawling (max 2 levels deep, BFS algorithm)
 *   - Full-page screenshots (PNG format)
 *   - HTML capture with inline resources
 *   - Safety filters (automatically excludes logout, delete, etc.)
 *   - Graceful error handling with partial results
 *
 * OUTPUT:
 *   JSON output with capture status and file paths:
 *   {
 *     "status": "success",
 *     "pages_captured": 5,
 *     "output_directory": "./output",
 *     "capture_time": "2026-02-05T12:34:56Z",
 *     "pages": [...]
 *   }
 *
 * CONFIGURATION:
 *   Required:
 *     - cookies: Path to cookie JSON file
 *     - landing_page: Starting URL for capture
 *
 *   Optional:
 *     - output_dir: Output directory (default: ./output)
 *     - mode: "screenshots" | "html" | "both" (default: both)
 *     - crawl.enabled: Enable crawling (default: true)
 *     - crawl.max_depth: Max depth (default: 2)
 *     - crawl.same_origin_only: Same-origin restriction (default: true)
 *     - crawl.exclude_patterns: URL patterns to skip (default: logout, delete, etc.)
 */

const fs = require('fs');
const path = require('path');
const { URL } = require('url');

// Check for puppeteer
let puppeteer;
try {
  puppeteer = require('puppeteer');
} catch (e) {
  console.error(JSON.stringify({
    status: 'error',
    error: 'puppeteer not found. Install with: npm install -g puppeteer',
    error_code: 'DEPENDENCY_MISSING'
  }));
  process.exit(1);
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG = {
  output_dir: './output',
  mode: 'both',
  crawl: {
    enabled: true,
    max_depth: 2,
    same_origin_only: true,
    exclude_patterns: [
      '*logout*',
      '*signout*',
      '*delete*',
      '*remove*',
      '*destroy*',
      '*sign-out*',
      '*log-out*'
    ]
  },
  screenshot: {
    full_page: true,
    format: 'png'
  },
  html: {
    inline_resources: true
  },
  timeout: 30000
};

/**
 * Main dashboard capture class
 */
class DashboardCapturer {
  constructor(config) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    // Merge nested objects
    if (config.crawl) {
      this.config.crawl = { ...DEFAULT_CONFIG.crawl, ...config.crawl };
    }
    if (config.screenshot) {
      this.config.screenshot = { ...DEFAULT_CONFIG.screenshot, ...config.screenshot };
    }
    if (config.html) {
      this.config.html = { ...DEFAULT_CONFIG.html, ...config.html };
    }

    this.visited = new Set();
    this.queue = [];
    this.results = [];
    this.browser = null;
    this.page = null;
    this.errors = [];
  }

  /**
   * Initialize browser and load cookies
   */
  async initialize() {
    try {
      // Launch browser
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage'
        ]
      });

      this.page = await this.browser.newPage();
      await this.page.setViewport({ width: 1920, height: 1080 });

      // Load cookies
      const cookiesPath = path.resolve(this.config.cookies);
      if (!fs.existsSync(cookiesPath)) {
        throw new Error(`Cookie file not found: ${cookiesPath}`);
      }

      const cookieData = fs.readFileSync(cookiesPath, 'utf8');
      let cookies;

      try {
        cookies = JSON.parse(cookieData);
      } catch (e) {
        throw new Error(`Invalid cookie JSON format: ${e.message}`);
      }

      // Handle different cookie export formats
      if (Array.isArray(cookies)) {
        await this.page.setCookie(...cookies);
      } else if (typeof cookies === 'object') {
        // Convert object format to array format if needed
        const cookieArray = Object.entries(cookies).map(([name, value]) => ({
          name,
          value: String(value),
          domain: new URL(this.config.landing_page).hostname
        }));
        await this.page.setCookie(...cookieArray);
      } else {
        throw new Error('Cookies must be an array or object');
      }

      // Create output directories
      this.ensureOutputDirectories();

      return true;
    } catch (error) {
      throw new Error(`Initialization failed: ${error.message}`);
    }
  }

  /**
   * Ensure output directories exist
   */
  ensureOutputDirectories() {
    const outputDir = path.resolve(this.config.output_dir);

    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    if (this.config.mode === 'screenshots' || this.config.mode === 'both') {
      const screenshotDir = path.join(outputDir, 'screenshots');
      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
      }
    }

    if (this.config.mode === 'html' || this.config.mode === 'both') {
      const htmlDir = path.join(outputDir, 'html');
      if (!fs.existsSync(htmlDir)) {
        fs.mkdirSync(htmlDir, { recursive: true });
      }
    }
  }

  /**
   * Main capture method - BFS crawling
   */
  async capture() {
    try {
      // Add landing page to queue
      this.queue.push({
        url: this.config.landing_page,
        depth: 0,
        parent: null
      });

      // BFS traversal
      while (this.queue.length > 0) {
        const current = this.queue.shift();

        // Skip if already visited or depth exceeded
        if (this.visited.has(current.url)) {
          continue;
        }

        if (current.depth > this.config.crawl.max_depth) {
          continue;
        }

        // Skip if URL matches exclude patterns
        if (this.shouldSkipUrl(current.url)) {
          continue;
        }

        this.visited.add(current.url);

        // Log progress
        console.error(`[${this.visited.size}/${this.visited.size + this.queue.length}] Capturing: ${current.url} (depth: ${current.depth})`);

        try {
          // Navigate to page
          await this.page.goto(current.url, {
            waitUntil: 'networkidle0',
            timeout: this.config.timeout
          });

          // Check for authentication failures (redirect to login)
          const currentUrl = this.page.url();
          if (this.isLoginPage(currentUrl) && currentUrl !== current.url) {
            throw new Error('Authentication failed - redirected to login page. Cookies may be expired.');
          }

          // Capture page data
          const pageData = {
            url: current.url,
            depth: current.depth,
            parent: current.parent,
            timestamp: new Date().toISOString()
          };

          // Capture screenshot
          if (this.config.mode === 'screenshots' || this.config.mode === 'both') {
            try {
              const screenshotInfo = await this.captureScreenshot(current.url);
              pageData.screenshot = screenshotInfo;
            } catch (error) {
              pageData.screenshot_error = error.message;
              this.errors.push({
                url: current.url,
                type: 'screenshot',
                error: error.message
              });
            }
          }

          // Capture HTML
          if (this.config.mode === 'html' || this.config.mode === 'both') {
            try {
              const htmlInfo = await this.captureHTML(current.url);
              pageData.html = htmlInfo;
            } catch (error) {
              pageData.html_error = error.message;
              this.errors.push({
                url: current.url,
                type: 'html',
                error: error.message
              });
            }
          }

          this.results.push(pageData);

          // Extract links for next level (if crawling enabled)
          if (this.config.crawl.enabled && current.depth < this.config.crawl.max_depth) {
            const links = await this.extractLinks(current.url);
            for (const link of links) {
              if (!this.visited.has(link)) {
                this.queue.push({
                  url: link,
                  depth: current.depth + 1,
                  parent: current.url
                });
              }
            }
          }
        } catch (error) {
          // Graceful degradation - log error but continue
          this.errors.push({
            url: current.url,
            type: 'navigation',
            error: error.message
          });

          this.results.push({
            url: current.url,
            depth: current.depth,
            parent: current.parent,
            timestamp: new Date().toISOString(),
            error: error.message
          });
        }
      }

      return this.results;
    } catch (error) {
      throw new Error(`Capture failed: ${error.message}`);
    }
  }

  /**
   * Check if URL should be skipped based on exclude patterns
   */
  shouldSkipUrl(url) {
    // Same-origin check
    if (this.config.crawl.same_origin_only) {
      try {
        const landingOrigin = new URL(this.config.landing_page).origin;
        const urlOrigin = new URL(url).origin;
        if (landingOrigin !== urlOrigin) {
          return true;
        }
      } catch (e) {
        return true; // Invalid URL, skip it
      }
    }

    // Exclude pattern check
    for (const pattern of this.config.crawl.exclude_patterns) {
      const regex = new RegExp(pattern.replace(/\*/g, '.*'), 'i');
      if (regex.test(url)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Check if URL is a login page
   */
  isLoginPage(url) {
    const loginPatterns = [
      /login/i,
      /signin/i,
      /sign-in/i,
      /auth/i,
      /authenticate/i
    ];

    return loginPatterns.some(pattern => pattern.test(url));
  }

  /**
   * Extract links from current page
   */
  async extractLinks(currentUrl) {
    try {
      const links = await this.page.evaluate(() => {
        return Array.from(document.querySelectorAll('a[href]'))
          .map(a => a.href)
          .filter(href => href && href.startsWith('http'));
      });

      // Deduplicate
      return [...new Set(links)];
    } catch (error) {
      console.error(`Failed to extract links from ${currentUrl}: ${error.message}`);
      return [];
    }
  }

  /**
   * Capture screenshot of current page
   */
  async captureScreenshot(url) {
    const filename = this.urlToFilename(url) + '.png';
    const filepath = path.join(
      path.resolve(this.config.output_dir),
      'screenshots',
      filename
    );

    await this.page.screenshot({
      path: filepath,
      fullPage: this.config.screenshot.full_page
    });

    return {
      filename,
      path: filepath,
      relative_path: path.relative(process.cwd(), filepath)
    };
  }

  /**
   * Capture HTML of current page
   */
  async captureHTML(url) {
    const filename = this.urlToFilename(url) + '.html';
    const filepath = path.join(
      path.resolve(this.config.output_dir),
      'html',
      filename
    );

    const content = await this.page.content();
    fs.writeFileSync(filepath, content, 'utf8');

    return {
      filename,
      path: filepath,
      relative_path: path.relative(process.cwd(), filepath)
    };
  }

  /**
   * Convert URL to safe filename
   */
  urlToFilename(url) {
    try {
      const urlObj = new URL(url);
      let filename = urlObj.hostname + urlObj.pathname;

      // Remove trailing slash
      if (filename.endsWith('/')) {
        filename = filename.slice(0, -1);
      }

      // Replace index.html, index.php, etc. with just the directory name
      filename = filename.replace(/\/index\.(html|php|htm|aspx?)$/i, '');

      // Replace non-alphanumeric characters with underscore
      filename = filename.replace(/[^a-zA-Z0-9]/g, '_');

      // Remove consecutive underscores
      filename = filename.replace(/_+/g, '_');

      // Remove leading/trailing underscores
      filename = filename.replace(/^_|_$/g, '');

      // Limit length
      if (filename.length > 200) {
        filename = filename.substring(0, 200);
      }

      // If filename is empty, use 'page'
      if (!filename) {
        filename = 'page';
      }

      return filename;
    } catch (e) {
      // Fallback for invalid URLs
      return 'page_' + Date.now();
    }
  }

  /**
   * Generate metadata output
   */
  async generateOutput() {
    const metadata = {
      status: this.errors.length === 0 ? 'success' : (this.results.length > 0 ? 'partial' : 'failed'),
      pages_captured: this.results.length,
      pages_failed: this.errors.length,
      output_directory: path.resolve(this.config.output_dir),
      capture_time: new Date().toISOString(),
      config: {
        landing_page: this.config.landing_page,
        mode: this.config.mode,
        max_depth: this.config.crawl.max_depth,
        same_origin_only: this.config.crawl.same_origin_only
      },
      pages: this.results,
      errors: this.errors.length > 0 ? this.errors : undefined
    };

    // Write metadata.json
    const metadataPath = path.join(
      path.resolve(this.config.output_dir),
      'metadata.json'
    );
    fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2), 'utf8');

    return metadata;
  }

  /**
   * Clean up browser
   */
  async close() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

/**
 * Parse command-line arguments
 */
function parseArgs(args) {
  const config = {};

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    switch (arg) {
      case '--config':
        config._configFile = args[++i];
        break;
      case '--cookies':
        config.cookies = args[++i];
        break;
      case '--url':
      case '--landing-page':
        config.landing_page = args[++i];
        break;
      case '--mode':
        config.mode = args[++i];
        break;
      case '--output':
      case '--output-dir':
        config.output_dir = args[++i];
        break;
      case '--max-depth':
        config.crawl = config.crawl || {};
        config.crawl.max_depth = parseInt(args[++i], 10);
        break;
      case '--no-crawl':
        config.crawl = config.crawl || {};
        config.crawl.enabled = false;
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
        break;
    }
  }

  return config;
}

/**
 * Print help message
 */
function printHelp() {
  console.log(`
capture.js - Capture authenticated dashboards as screenshots and HTML

USAGE:
  node capture.js --config config.json
  node capture.js --cookies cookies.json --url https://dashboard.example.com

OPTIONS:
  --config FILE         Load configuration from JSON file
  --cookies FILE        Path to cookie JSON file (required if no config)
  --url URL             Landing page URL (required if no config)
  --mode MODE           Capture mode: screenshots, html, or both (default: both)
  --output DIR          Output directory (default: ./output)
  --max-depth N         Maximum crawl depth (default: 2)
  --no-crawl            Disable crawling, only capture landing page
  --help, -h            Show this help message

CONFIGURATION FILE FORMAT:
  {
    "cookies": "./cookies.json",
    "landing_page": "https://dashboard.example.com",
    "output_dir": "./output",
    "mode": "both",
    "crawl": {
      "enabled": true,
      "max_depth": 2,
      "same_origin_only": true,
      "exclude_patterns": ["*logout*", "*delete*"]
    }
  }

OUTPUT:
  JSON output with capture results and file paths

EXAMPLES:
  # Capture with config file
  node capture.js --config config.json

  # Capture screenshots only
  node capture.js --cookies cookies.json --url https://example.com --mode screenshots

  # Single page capture (no crawling)
  node capture.js --cookies cookies.json --url https://example.com --no-crawl
`);
}

/**
 * Main execution
 */
async function main() {
  try {
    // Parse arguments
    const args = process.argv.slice(2);

    if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
      printHelp();
      process.exit(0);
    }

    let config = parseArgs(args);

    // Load config file if specified
    if (config._configFile) {
      const configPath = path.resolve(config._configFile);
      if (!fs.existsSync(configPath)) {
        throw new Error(`Config file not found: ${configPath}`);
      }

      const fileConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      config = { ...fileConfig, ...config };
      delete config._configFile;
    }

    // Validate required parameters
    if (!config.cookies) {
      throw new Error('Missing required parameter: --cookies or cookies in config file');
    }

    if (!config.landing_page) {
      throw new Error('Missing required parameter: --url or landing_page in config file');
    }

    // Validate mode
    if (config.mode && !['screenshots', 'html', 'both'].includes(config.mode)) {
      throw new Error('Invalid mode. Must be: screenshots, html, or both');
    }

    // Create capturer and run
    const capturer = new DashboardCapturer(config);

    await capturer.initialize();
    await capturer.capture();
    const output = await capturer.generateOutput();
    await capturer.close();

    // Print JSON output
    console.log(JSON.stringify(output, null, 2));

    process.exit(output.status === 'success' ? 0 : 1);
  } catch (error) {
    console.error(JSON.stringify({
      status: 'error',
      error: error.message,
      timestamp: new Date().toISOString()
    }, null, 2));

    process.exit(1);
  }
}

// Run main if executed directly
if (require.main === module) {
  main();
}

module.exports = { DashboardCapturer };
