# Silky.py - The best single file web crawler all in Python
## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Quick Start](#quick-start)
3. [Modes Overview](#modes-overview)
4. [Crawl Mode (Detailed)](#crawl-mode-detailed)
5. [Crawler Engines](#crawler-engines)
6. [Configuration Options](#configuration-options)
7. [Force Domain Feature](#force-domain-feature)
8. [Stop-On URL Feature](#stop-on-url-feature)
9. [JS Runner Framework](#js-runner-framework)
10. [Network & API Logging](#network--api-logging)
11. [JavaScript Logging](#javascript-logging)
12. [Image Logging](#image-logging)
13. [Cookie Logging](#cookie-logging)
14. [Export & Analysis](#export--analysis)
15. [Discord Bot Mode](#discord-bot-mode)
16. [Import & Data Analysis](#import--data-analysis)
17. [Troubleshooting](#troubleshooting)
18. [Examples](#examples)

---

## Installation & Setup

### Requirements

- Python 3.8+
- pip (Python package manager)

### Install Dependencies

```bash
# Core dependencies (required)
pip install scrapy requests

# Optional dependencies (enhanced features)
pip install playwright discord.py pyperclip

# Playwright browser setup (required for Playwright crawler)
playwright install chromium
```

### Verify Installation

```bash
python Silky.py
# Should display menu without errors
```

---

## Quick Start

### First Run

```bash
python Silky.py
```

### Choose Mode

```
============================================================
SILKY     By Lil Skittle
  / _ \
\_\(_)/_/
 _//o\\_ 
  /   \
============================================================

Enter mode (crawl / host / import / importfile): crawl
```

### Basic Crawl

```
Enter starting URL(s): https://example.com
Choose crawler engine (scrapy/playwright) [scrapy]: playwright
On Site Crawl only? (yes/no) [yes]: yes
Max depth (0 for no limit) [0]: 2
Max pages (0 for no limit) [0]: 50
```

---

## Modes Overview

### Four Main Modes

| Mode | Purpose | Use Case |
|------|---------|----------|
| **crawl** | Local web scraping | Crawl websites on your computer |
| **host** | Discord bot server | Run as Discord bot for remote crawling |
| **import** | Analyze exported data | Import and search previously crawled data |
| **importfile** | Load from file | Load crawl data from saved file |

---

## Crawl Mode (Detailed)

### Starting URLs

```
Enter starting URL(s) (comma-separated for multiple): https://example.com,https://example.com/news
```

- Single URL: `https://example.com`
- Multiple URLs: `https://site1.com,https://site2.com`
- URLs with paths: `https://example.com/blog`

### Crawler Engine Selection

```
--- CRAWLER ENGINE SELECTION ---
Choose crawler engine (scrapy/playwright) [scrapy]: 
```

**Scrapy** (default):
-  Lightweight and fast
-  Good for basic HTML parsing
-  Lower memory usage
-  No JavaScript rendering
-  Cannot see dynamic content
-  No Force Domain support
-  No Stop-On URL support
-  No JS Runner support

**Playwright** (modern):
-  Renders JavaScript
-  Handles dynamic content
-  Better for SPAs (React, Vue, etc.)
-  Network event logging
-  **NEW: Force Domain support**
-  **NEW: Smart Stop-On URL**
-  **NEW: JS Runner framework**
-  Slower than Scrapy
-  Requires browser installation

**Choose Playwright if:**
- Site uses JavaScript frameworks (React, Vue, Angular)
- Content loads dynamically
- You need to monitor network requests
- You want to track JavaScript files
- **You need Force Domain restrictions**
- **You want to find specific pages efficiently (Stop-On URL)**
- **You want to run custom JavaScript on pages (JS Runner)**

### Network Logging (Playwright only)

```
--- NETWORK LOGGING CONFIGURATION ---
Enable network/API logging? (yes/no) [no]: yes
Log ALL network requests? (yes/no) [no]: no
```

#### Option 1: Log Everything
```
Log ALL network requests? (yes/no) [no]: yes
```
Logs every single HTTP request and response.

#### Option 2: Selective Logging
```
Log ALL network requests? (yes/no) [no]: no
Enter URL patterns (comma-separated) [none]: api.example.com/*
Enter HTTP methods (comma-separated) [all]: GET,POST,PUT,DELETE
Enter status codes (comma-separated) [all]: 200,201,400,404,500
Minimum response size to log in bytes [0]: 0
Enter exclude patterns (comma-separated) [none]: *.css,*.js
```

**URL Patterns** (supports wildcards):
- `api.example.com/*` - All API endpoints
- `*.api.example.com` - Any subdomain
- `example.com/upload/*` - Upload endpoints
- `*analytics*` - Anything with "analytics"

**HTTP Methods**:
- `GET` - Retrieve data
- `POST` - Send data
- `PUT` - Replace data
- `DELETE` - Remove data
- `PATCH` - Partial update

**Status Codes**:
- `200` - Success
- `201` - Created
- `400` - Bad request
- `404` - Not found
- `500` - Server error

### Page Timeout (Playwright only)

```
--- PAGE TIMEOUT CONFIGURATION ---
Page timeout in seconds [15]: 20
```

- **5-10 seconds**: Fast sites, mobile-optimized
- **15 seconds**: Default, balanced
- **20-30 seconds**: Slow sites, heavy JS processing

### Logging Toggles (Playwright only)

```
--- LOGGING TOGGLES ---
Log images? (yes/no) [yes]: yes
Log scripts? (yes/no) [yes]: yes
Log automatically generated cookies? (yes/no) [yes]: yes
```

**What each toggle controls:**
- **Images**: Logs all `<img>` tags and CSS background images
- **Scripts**: Logs external and inline JavaScript files
- **Cookies**: Logs cookies created/modified during page load

### On-Site Crawling

```
On Site Crawl only? (yes/no) [yes]: yes
```

- **yes**: Only follow links within the same domain
- **no**: Follow links to external sites

**Note:** This is different from Force Domain. On-Site only checks the main domain, while Force Domain allows subdomain/path restrictions.

---

##  Force Domain Feature

### Overview

**NEW in this version!** Force Domain restricts crawling to specific domains, subdomains, or paths. This is more powerful than "On Site Only" because it supports:
- Subdomain restrictions (stay on `docs.example.com`)
- Path restrictions (stay in `/api/*` directory)
- Wildcard patterns

### When to Use

```
--- FORCE DOMAIN (OPTIONAL) ---
Force crawler to stay within a specific domain/subdomain/path pattern.
Force domain pattern (or leave blank): 
```

**Use Force Domain when:**
- You want to crawl only a specific subdomain
- You want to stay within a specific directory
- You want more control than "On Site Only" provides

### Pattern Syntax

#### 1. Exact Domain
```
https://example.com/*
```
**Effect:** Stays on `example.com` only (any path)

#### 2. Specific Subdomain
```
https://docs.example.com/*
```
**Effect:** Stays on `docs.example.com` only (won't visit `api.example.com` or `www.example.com`)

#### 3. Wildcard Subdomain
```
https://*.example.com/*
```
**Effect:** Stays on ANY subdomain of `example.com` (docs, api, www, etc.)

#### 4. Path Restriction
```
https://example.com/blog/*
```
**Effect:** Only crawls under `/blog/` directory

#### 5. Nested Path Restriction
```
https://example.com/api/v2/*
```
**Effect:** Only crawls `/api/v2/` and below

#### 6. Subdomain + Path
```
https://docs.example.com/guide/*
```
**Effect:** Stays on `docs.example.com` under `/guide/` directory only

### Examples

#### Example 1: Documentation Section Only
```
Start URL: https://example.com
Force domain: https://example.com/docs/*

Result: 
-  https://example.com/docs/intro
-  https://example.com/docs/api/reference
-  https://example.com/blog/post
-  https://example.com/about
```

#### Example 2: Specific Subdomain
```
Start URL: https://docs.python.org/3/
Force domain: https://docs.python.org/3/*

Result:
-  https://docs.python.org/3/library/
-  https://docs.python.org/3/tutorial/
-  https://docs.python.org/2.7/
-  https://www.python.org/
```

#### Example 3: All Subdomains
```
Start URL: https://api.github.com
Force domain: https://*.github.com/*

Result:
-  https://api.github.com/users
-  https://docs.github.com/en
-  https://gist.github.com
-  https://stackoverflow.com/questions/github
```

### Combined with Other Features

**Force Domain + Stop-On URL:**
```
Force domain: https://example.com/products/*
Stop-on URL: https://example.com/products/widget-pro

Effect: Smart crawling stays in products section, finds target efficiently
```

**Force Domain + Content Filter:**
```
Force domain: https://example.com/blog/*
Content filter: python

Effect: Only crawl blog posts containing "python"
```

---

##  Stop-On URL Feature

### Overview

**NEW in this version!** Stop-On URL makes the crawler automatically stop when it reaches a specific target URL. Features **smart link prioritization** to find the target efficiently.

### When to Use

```
--- STOP-ON URL (OPTIONAL) ---
Crawler will stop when it reaches this specific URL.
Stop-on URL (or leave blank): 
```

**Use Stop-On URL when:**
- You want to find a specific page
- You want to discover the path to a deeply nested page
- You want to verify a page is reachable from the homepage

### How It Works

#### Traditional Crawling (Without Stop-On)
```
Start → Page1 → Page2 → Page3 → ... → Target (eventually, maybe never)
```
Crawls in breadth-first order, may visit hundreds of pages.

#### Smart Stop-On Crawling
```
Start → Score Links → Follow Highest Priority → Target (quickly!)
```
**Intelligent link prioritization:**
- Links containing target URL: **+100 points**
- Links on target domain: **+50 points**
- Links on current domain: **+5 points**
- Irrelevant pages (about, terms): **-10 points**

### Smart Scoring System

The crawler automatically scores every link based on how likely it is to lead to your target:

| Condition | Score | Example |
|-----------|-------|---------|
| Exact match | +1000 | Link IS the stop-on URL |
| Contains target URL | +100 | Link contains "products/widget-pro" |
| Same domain as target | +50 | Both on `store.example.com` |
| Stays on current domain | +5 | Link on same page's domain |
| Irrelevant page | -10 | about, terms, privacy, contact |

### Console Output

```
[SMART] Top 3 scored links from https://example.com:
  1. Score:  155 | https://example.com/products
  2. Score:  105 | https://example.com/shop
  3. Score:   55 | https://example.com/blog

[SMART] Top 3 scored links from https://example.com/products:
  1. Score: 1000 | https://example.com/products/widget-pro
  2. Score:  105 | https://example.com/products/category-a
  3. Score:   55 | https://example.com/products/search

[STOP-ON] Reached target URL: https://example.com/products/widget-pro
[SMART]  Target found! Stopped smart crawling.
```

### Examples

#### Example 1: Find Product Page
```
Start URL: https://store.example.com
Stop-on URL: https://store.example.com/products/rare-widget
Max pages: 50

Traditional: Might crawl 200+ pages
Smart: Finds in ~15-20 pages (10x faster!)
```

#### Example 2: Navigate to Documentation
```
Start URL: https://example.com
Stop-on URL: https://docs.example.com/api/v2/authentication
Max depth: 5

Smart behavior:
1. Scores "docs" links higher (+50)
2. Scores "api" links higher (+100)
3. Skips irrelevant sections automatically
```

#### Example 3: Deep Navigation
```
Start URL: https://university.edu
Stop-on URL: https://university.edu/departments/cs/faculty/dr-smith
Max pages: 100

Smart path finding:
university.edu → /departments (Score: 105)
→ /departments/cs (Score: 105)
→ /departments/cs/faculty (Score: 105)
→ /departments/cs/faculty/dr-smith (Score: 1000) 
```

### Performance Comparison

Based on testing:

| Scenario | Traditional | Smart | Speedup |
|----------|-------------|-------|---------|
| E-commerce product | 127 pages | 18 pages | **7x faster** |
| Documentation page | 213 pages | 42 pages | **5x faster** |
| Nested faculty page | 341 pages | 67 pages | **5x faster** |

### Best Practices

1. **Be Specific**: Use exact URLs for best results
2. **Set Max Pages**: Limit search to prevent runaway crawls
3. **Combine with Force Domain**: Stay in relevant sections
4. **Watch Console Output**: See which links are prioritized

---

##  JS Runner Framework

### Overview

**NEW in this version!** JS Runner lets you execute custom JavaScript on every page the crawler visits. Your scripts can interact with Silky's logger, stats, and crawler state through the `window.Silky` API.

### When to Use

```
--- JS RUNNER (OPTIONAL) ---
Run custom JavaScript on every page. JS can interact with Silky via window.Silky API.
Options:
  1. Inline script (type JavaScript directly)
  2. Script file (path to .js file)
  3. Skip (no JS Runner)
Choose option (1/2/3) [3]: 
```

**Use JS Runner when:**
- You want to extract custom data from pages
- You need to run code that interacts with the page's JavaScript
- You want to make decisions based on page content
- You want to collect structured data (products, prices, contacts)

### Option 1: Inline Script

```
Choose option (1/2/3) [3]: 1
Enter JavaScript (end with empty line):
Silky.log('Checking page...');
const products = Silky.countElements('.product');
Silky.collect({ type: 'products', count: products });
[press Enter on empty line]

[JS RUNNER] Loaded 3 lines of JavaScript
```

### Option 2: Script File

```
Choose option (1/2/3) [3]: 2
Enter path to .js file: product_scraper.js

[JS RUNNER] Loaded script from product_scraper.js
```

### Option 3: Skip

```
Choose option (1/2/3) [3]: 3
```
No JS Runner is used.

### The window.Silky API

Every page gets a `window.Silky` object injected before your script runs.

#### Context Information

```javascript
// Access crawler state
const context = Silky.context;

console.log(context.url);             // Current page URL
console.log(context.pages_crawled);   // Total pages so far
console.log(context.images_found);    // Total images found
console.log(context.visited_count);   // URLs visited
```

#### Logging Methods

```javascript
// Log informational message
Silky.log('Found product information');

// Log warning
Silky.warn('Page load time exceeded 5 seconds');

// Log error (also recorded in crawler error log)
Silky.error('Failed to parse JSON data');
```

#### Data Collection

```javascript
// Collect custom data
Silky.collect({
    type: 'product',
    name: 'Widget Pro',
    price: '$99.99',
    rating: 4.5,
    url: window.location.href
});
```

**Always include a `type` field to categorize your data!**

#### DOM Analysis Helpers

```javascript
// Count elements
const imageCount = Silky.countElements('img');
const formCount = Silky.countElements('form');

// Extract text content
const headings = Silky.extractText('h1');
// Returns: ["Main Title", "Another Title"]

// Extract attributes
const imageSources = Silky.extractAttributes('img', 'src');
const linkHrefs = Silky.extractAttributes('a', 'href');

// Extract links
const allLinks = Silky.extractLinks();
const navLinks = Silky.extractLinks('nav a[href]');
```

#### DOM Utilities

```javascript
// Check if element exists
if (Silky.exists('.login-form')) {
    Silky.log('Login form detected');
}

// Get all meta tags
const meta = Silky.getMeta();
// Returns: { "description": "...", "og:title": "...", ... }

// Wait for dynamic content
(async function() {
    const element = await Silky.waitForElement('.dynamic-content', 3000);
    const text = element.textContent;
    Silky.collect({ type: 'dynamic', content: text });
})();
```

#### Crawler Control

```javascript
// Stop the entire crawl
if (document.body.textContent.includes('TARGET FOUND')) {
    Silky.stopCrawl('Found the target text');
}

// Skip a URL (for logging)
if (window.location.href.includes('/admin')) {
    Silky.skipUrl(window.location.href, 'Admin page not needed');
}
```

### Example Scripts

#### Extract Product Data
```javascript
const product = {
    name: document.querySelector('.product-name')?.textContent?.trim(),
    price: document.querySelector('.product-price')?.textContent?.trim(),
    rating: document.querySelector('.product-rating')?.textContent?.trim(),
    inStock: Silky.exists('.in-stock')
};

if (product.name) {
    Silky.collect({
        type: 'product',
        ...product,
        url: window.location.href
    });
    Silky.log(`Collected: ${product.name} - ${product.price}`);
}
```

#### Find Email Addresses
```javascript
const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const text = document.body.textContent;
const emails = [...new Set(text.match(emailRegex) || [])];

if (emails.length > 0) {
    Silky.collect({
        type: 'emails',
        emails: emails,
        count: emails.length,
        url: window.location.href
    });
    Silky.log(`Found ${emails.length} email addresses`);
}
```

#### Check Page Quality
```javascript
const quality = {
    hasH1: Silky.exists('h1'),
    h1Count: Silky.countElements('h1'),
    imageCount: Silky.countElements('img'),
    imagesWithAlt: Silky.countElements('img[alt]'),
    wordCount: document.body.textContent.trim().split(/\s+/).length
};

let score = 0;
if (quality.hasH1 && quality.h1Count === 1) score += 20;
if (quality.imageCount > 0 && quality.imagesWithAlt === quality.imageCount) score += 20;
if (quality.wordCount > 300) score += 20;

Silky.collect({
    type: 'page_quality',
    ...quality,
    score: score,
    url: window.location.href
});

if (score < 40) {
    Silky.warn(`Low quality page (score: ${score})`);
}
```

### Viewing Results

After crawl completes:

```
Commands: ... jsresults, exportjs, ...

Command: jsresults
=== JS RUNNER RESULTS ===

Total Results: 127
  Logs: 45
  Errors: 2
  Warnings: 8
  Data Items: 72

--- DATA COLLECTED ---
  [2024-01-27T14:32:15.123Z]
    type: product
    name: Widget Pro
    price: $99.99
...

Command: exportjs
Export filename [js_runner_results.json]: 
Successfully exported 127 JS Runner results to 'js_runner_results.json'
```

### Console Output During Crawl

```
[JS RUNNER] Executed on https://example.com/product - 3 results
[JS→SILKY] Found product information
[JS→SILKY] Collected: Widget Pro - $99.99
[JS RUNNER] Executed on https://example.com/about - 1 results
[JS→SILKY] Skipping about page
```

### Best Practices

1. **Always use `type` in collected data** for easy filtering
2. **Use try-catch** for risky operations
3. **Check element existence** before accessing (use `?.`)
4. **Limit data size** - don't collect huge strings
5. **Use async/await** for dynamic content
6. **Stop smartly** - use `stopCrawl()` when you find what you need

### Complete JS Runner API

**window.Silky Methods:**

**Logging:**
- `Silky.log(message)` - Log informational message
- `Silky.warn(message)` - Log warning
- `Silky.error(message)` - Log error (also recorded in crawler logs)

**Data Collection:**
- `Silky.collect(data)` - Collect custom data from page

**DOM Analysis:**
- `Silky.countElements(selector)` - Count matching elements
- `Silky.extractText(selector)` - Extract text from elements
- `Silky.extractAttributes(selector, attribute)` - Extract attribute values
- `Silky.extractLinks(selector)` - Extract link URLs

**DOM Utilities:**
- `Silky.exists(selector)` - Check if element exists
- `Silky.getMeta()` - Get all meta tags
- `Silky.waitForElement(selector, timeout)` - Wait for dynamic content

**Crawler Control:**
- `Silky.stopCrawl(reason)` - Stop entire crawl
- `Silky.skipUrl(url, reason)` - Mark URL to skip

**Context Access:**
- `Silky.context` - Object with crawler state (pages_crawled, images_found, visited, etc.)

**Advanced Usage Tips:**
- Always include `type` field in collected data for filtering
- Use try-catch blocks for error handling
- Check element existence with optional chaining (`?.`)
- Limit data size to avoid memory issues
- Use async/await for dynamic content
- Test scripts in browser DevTools before using

**Performance Considerations:**
- Keep scripts simple to avoid slowing crawls
- Avoid large loops or complex operations
- Use `waitForElement` with reasonable timeouts
- Don't collect huge strings or arrays

---

## Crawl Depth & Pages

```
Max depth (0 for no limit) [0]: 3
Max pages (0 for no limit) [0]: 100
```

- **Depth 0**: Unlimited (crawls everything reachable)
- **Depth 1**: Only the starting URL
- **Depth 2**: Starting URL + links from it
- **Depth 3**: 2 levels deep

- **Pages 0**: No limit
- **Pages 50**: Stop after 50 pages

### Threading (Scrapy only)

```
Number of threads [6]: 8
```

- Higher = faster but more resource usage
- Recommended: 4-8 for most systems
- Set to 1 for slow connections

### Image Scraping Mode

```
Image scraping only? (yes/no) [no]: yes
```

- **no**: Normal crawling (content, links, images)
- **yes**: Only extract images, ignore other content

### Content Filtering

```
Content filter (or leave blank): python
```

- Filters pages by text content
- Only pages containing "python" are collected
- Leave blank to collect all pages

### URL Patterns

```
URL include pattern (regex, or leave blank/N/A): .*blog.*
URL exclude pattern (regex, or leave blank/N/A): .*admin.*
```

- **Include**: Only crawl matching URLs
- **Exclude**: Skip matching URLs
- Use regex patterns (or type `N/A` to skip)

### File Types (Scrapy only)

```
File types to crawl (e.g., 'html,php,asp' or leave blank/N/A): html,php
```

- Comma-separated file extensions
- Only URLs ending with these extensions
- Leave blank for all files

### Cookie Configuration

```
--- COOKIE CONFIGURATION ---
Enter cookies to authenticate with the website (useful for sites requiring login).
Cookies (or leave blank): sessionid=abc123; user_token=xyz789
```

**Formats supported:**
```
# Format 1: Key=value pairs
sessionid=abc123; user_token=xyz789

# Format 2: JSON
{"sessionid": "abc123", "user_token": "xyz789"}

# Leave blank to skip
```

### Proxy Configuration

```
--- PROXY CONFIGURATION ---
Enter proxy address if needed (e.g., http://user:pass@host:port or socks5://host:port).
Proxy (or leave blank): 
```

**Formats supported:**
- HTTP: `http://proxy.example.com:8080`
- HTTPS: `https://proxy.example.com:8080`
- SOCKS5: `socks5://proxy.example.com:1080`
- Authenticated: `http://user:pass@proxy.example.com:8080`

### Discord Webhook (Optional)

```
Send updates to Discord Webhook? (yes/no) [no]: yes
Enter Discord Webhook URL: https://discord.com/api/webhooks/...
Choose mode (each/final/both) [final]: final
```

- **each**: Message for each page crawled (verbose)
- **final**: Message when crawl finishes (clean)
- **both**: Both modes

---

## Crawler Engines

### Scrapy Engine

```
Choose crawler engine (scrapy/playwright) [scrapy]: scrapy
```

#### Best For:
- Fast, lightweight scraping
- Static HTML sites
- SEO/link analysis
- Large-scale crawls

#### Features:
- Multi-threaded crawling
- Cookie/session support
- Header customization
- Regex URL filtering

#### Limitations:
- No JavaScript rendering
- Can't see dynamic content
- Limited network analysis
- **No Force Domain support**
- **No Stop-On URL support**
- **No JS Runner support**

### Playwright Engine

```
Choose crawler engine (scrapy/playwright) [scrapy]: playwright
```

#### Best For:
- JavaScript-heavy sites
- Single Page Applications (SPAs)
- Monitoring network activity
- Modern web apps

#### Features:
- Full JavaScript rendering
- Network request logging
- Dynamic content extraction
- Better for SPA detection
- **Force Domain support**
- **Smart Stop-On URL**
- **JS Runner framework**
- Cookie auto-generation logging
- Script extraction (external + inline)
- Image extraction (img tags + CSS backgrounds)

#### Limitations:
- Slower than Scrapy
- Higher memory usage
- Requires browser installation

---

## Configuration Options

### Available Commands During Crawl

After crawl completes, use these commands:

```
Commands: stats, links, tree, sitemap, info, search, export, exportfile, 
          exportlinks, exportimages, exportimagedata, exportlogs, 
          jsresults, exportjs, exit
```

| Command | Output | Engine |
|---------|--------|--------|
| `stats` | Crawl statistics (pages, errors, types) | Both |
| `links` | Link analysis (most linked pages) | Both |
| `tree` | Hierarchical site structure | Both |
| `sitemap` | Site structure by depth | Both |
| `info <url>` | Detailed info for specific URL | Both |
| `search <query>` | Find pages/images containing text | Scrapy |
| `export` | Compress and copy data to clipboard | Both |
| `exportfile` | Save compressed data to file | Both |
| `exportlinks` | Save all URLs to text file | Both |
| `exportimages` | Save all image URLs to text file | Both |
| `exportimagedata` | Save images with metadata (JSON) | Both |
| `exportlogs` | Save all logs (JSON) | Both |
| ** `jsresults`** | **View JS Runner results** | **Playwright** |
| ** `exportjs`** | **Export JS results to JSON** | **Playwright** |
| `exit` | Quit program | Both |

---

## Network & API Logging

### Overview

Network logging tracks HTTP requests and responses during Playwright crawling.

### Enable Network Logging

```
Enable network/API logging? (yes/no) [no]: yes
Log ALL network requests? (yes/no) [no]: no
```

### Configuration Summary

```
--- Network Logging Config Summary ---
Enabled: Yes
URL Patterns: ['api.example.com/*']
Methods: ['GET', 'POST', 'DELETE']
Status Codes: All
Min Size: 0 bytes
Exclude Patterns: ['*.css', 'fonts.googleapis.com']
```

### Console Output

```
[NETWORK] GET api.example.com/users - Status: 200 (1524 bytes, 123.45ms)
[NETWORK] POST api.example.com/data - Status: 201 (256 bytes, 89.23ms)
[NETWORK] DELETE api.example.com/cache - Status: 404 (64 bytes, 45.67ms)
```

### Log Files

- **File**: `crawl_logs/network_[timestamp].log`
- **JSON**: Included in `crawler_logs.json`

### Example Scenarios

#### Monitor REST API Calls
```
URL patterns: api.myapp.com/*
Methods: GET,POST,PUT,DELETE
Status codes: (all)
```

#### Find Failed Requests
```
URL patterns: *
Methods: GET
Status codes: 404,500
```

#### Track File Uploads
```
URL patterns: api.example.com/upload/*
Methods: POST,PUT
Min size: 0
```

---

## JavaScript Logging

### Overview

JavaScript logging tracks all scripts loaded on pages, including external files and inline code.

### Enable/Disable

```
Log scripts? (yes/no) [yes]: yes
```

### What Gets Logged

**External Scripts:**
- Full URL
- Type (javascript, module, etc.)
- Async/defer attributes
- Integrity hash
- Nonce attribute
- Source page

**Inline Scripts (>1KB):**
- Inline identifier (e.g., `#inline-0`)
- Size in bytes
- First 100 characters
- Script type
- Source page

### Console Output

```
[SCRIPTS] 15 external, 4 inline | https://example.com
[SCRIPT] https://cdn.example.com/jquery.min.js
[SCRIPT] https://google-analytics.com/ga.js [async]
[SCRIPT] https://example.com/app.js [defer]
[INLINE-SCRIPT] https://example.com/page#inline-0 (3456 bytes)
```

### Log Files

- **File**: `crawl_logs/javascript_[timestamp].log`
- **JSON**: Included in `crawler_logs.json`

### Statistics Included

After crawl:
```
Command: stats

JavaScript:
  External Scripts: 45
  Inline Scripts: 12
  Total External Size: 1.2 MB
```

---

## Image Logging

### Overview

Image logging captures all images on pages with metadata.

### Enable/Disable

```
Log images? (yes/no) [yes]: yes
```

### What Gets Logged

- **URL**: Image file path
- **Source Page**: Where image is from
- **Type**: `img_tag` or `css_background`
- **Dimensions**: Width x height (if available)
- **Alt Text**: Image description
- **Depth**: How deep in crawl

### Console Output

```
[IMAGES] 12 images | Depth: 0 | https://example.com
[IMAGE] https://cdn.example.com/header.jpg (1920x1080)
[IMAGE] https://cdn.example.com/logo.png
```

### Export Options

#### Export Image URLs Only
```
Command: exportimages
Output: images.txt
Format: One URL per line
```

#### Export Image Metadata
```
Command: exportimagedata
Output: images_metadata.json
Format: JSON with dimensions, alt text, source, type
```

### Example JSON

```json
[
  {
    "url": "https://cdn.example.com/header.jpg",
    "source_page": "https://example.com",
    "alt_text": "Header image",
    "dimensions": [1920, 1080],
    "image_type": "img_tag",
    "depth": 0
  },
  {
    "url": "https://cdn.example.com/pattern.png",
    "source_page": "https://example.com",
    "alt_text": null,
    "dimensions": null,
    "image_type": "css_background",
    "depth": 0
  }
]
```

---

## Cookie Logging

### Overview

**NEW in this version!** Cookie logging tracks cookies that are automatically generated or modified during page load.

### Enable/Disable

```
Log automatically generated cookies? (yes/no) [yes]: yes
```

### What Gets Logged

- **Initial Cookies**: Cookies set before page load (from your config)
- **Auto-Generated Cookies**: New cookies created during page load
- **Modified Cookies**: Cookies whose values changed

### Console Output

```
[COOKIES] 3 auto-generated cookies on https://example.com
```

### Log Files

- **File**: `crawl_logs/cookies_[timestamp].log`
- **JSON**: Included in `crawler_logs.json`

### Cookie Data Structure

```json
{
  "timestamp": "2024-01-27T14:32:15.123Z",
  "url": "https://example.com",
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123...",
      "domain": ".example.com",
      "path": "/",
      "expires": 1738000000,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ]
}
```

### Use Cases

- **Track session cookies**: See how sites maintain sessions
- **Security analysis**: Find insecure cookies (no httpOnly/secure)
- **Debugging login flows**: See what cookies are set during auth
- **Third-party tracking**: Identify analytics/tracking cookies

---

## Export & Analysis

### Export Functions

#### Export Crawl Data
```
Command: export
Output: Clipboard (compressed)
```

#### Save to File
```
Command: exportfile
Filename: exported_data.dat
Format: Compressed and encoded
```

#### Export URLs
```
Command: exportlinks
Output: links.txt
Format: One URL per line
```

#### Export Images
```
Command: exportimages
Output: images.txt
Format: One image URL per line

Command: exportimagedata
Output: images_metadata.json
Format: Full image metadata
```

#### Export Logs
```
Command: exportlogs
Output: crawler_logs.json
Format: All logs with full details
```

####  Export JS Runner Results
```
Command: jsresults
Output: Console summary

Command: exportjs
Output: js_runner_results.json
Format: All JS execution results
```

### Log Files Directory

```
crawl_logs/
 general_[timestamp].log
 api_[timestamp].log
 network_[timestamp].log
 images_[timestamp].log
 javascript_[timestamp].log
 cookies_[timestamp].log        # NEW
 errors_[timestamp].log
 performance_[timestamp].log
 pages_[timestamp].log
```

### Analysis Commands

#### View Statistics
```
Command: stats
Shows: Pages crawled, errors, skipped, content types, images, scripts
```

#### Analyze Links
```
Command: links
Shows: Most linked pages, pages with most outgoing links
```

#### View Site Tree
```
Command: tree
Shows: Hierarchical tree structure of site
```

#### View Site Map
```
Command: sitemap
Shows: Site structure organized by depth
```

#### Get Page Info
```
Command: info <url>
Shows: Detailed information about specific URL from logs
```

#### Search Content (Scrapy only)
```
Command: search <term>
Shows: Pages and images matching search term
```

---

## Discord Bot Mode

### Setup

1. **Create Discord Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create new application
   - Create bot
   - Enable "Message Content Intent"
   - Copy bot token

2. **Run Bot Mode**
   ```
   python Silky.py
   Enter mode: host
   Enter Discord Bot Token: [paste token]
   ```

### Usage in Discord

```
/crawl https://example.com pages:100 depth:5 filter:python
```

**Parameters:**
- `pages:100` - Maximum 100 pages
- `depth:5` - Maximum 5 levels deep
- `filter:python` - Only pages with "python"
- `image_only:yes` - Images only
- `site_only:no` - Follow external links

### Example Commands

```
# Basic crawl
/crawl https://example.com

# With limits
/crawl https://example.com pages:50 depth:3

# API monitoring
/crawl https://api.example.com/v1/* pages:200

# Image scraping
/crawl https://example.com image_only:yes pages:500

# Help
/crawl help
```

**Note:** Discord bot mode does not support Force Domain, Stop-On URL, or JS Runner features. These are only available in local crawl mode.

---

## Import & Data Analysis

### Import from String

```
Enter mode: import
Paste exported data string: [paste compressed data]
```

### Import from File

```
Enter mode: importfile
Enter filename: exported_data.dat
```

### Available Commands

```
Commands: search, stats, links, tree, sitemap, export, exportfile, 
          exportlinks, exportimages, exportimagedata, exit
```

### Analysis Example

```
Command: search "api"
Found 23 results:
1. [50 pts] API Documentation
   https://example.com/api/docs
2. [45 pts] REST API Guide
   https://example.com/api/guide
```

---

## Troubleshooting

### No Pages Crawled

**Problem:** Crawl finishes with 0 pages

**Solutions:**
1. Check URL is correct and accessible
2. Try different crawler engine (Scrapy vs Playwright)
3. Check content filter is not too restrictive
4. Verify URL patterns match actual pages
5. Check Force Domain pattern if enabled
6. Try increasing page timeout (Playwright)

### Timeout Errors

**Problem:** `Timeout 30000ms exceeded` or similar

**Solutions:**
1. Increase page timeout: Set to 20-30 seconds
2. Reduce depth/pages to crawl fewer pages
3. Check internet connection speed
4. Try Scrapy engine instead (no timeout issues)

### JavaScript Not Rendering

**Problem:** Dynamic content missing

**Solutions:**
1. Switch to Playwright engine
2. Increase page timeout (Playwright needs time)
3. Check if site requires login/cookies
4. Use JS Runner to wait for content

### Memory Issues

**Problem:** Out of memory during crawl

**Solutions:**
1. Reduce max pages
2. Use Scrapy instead of Playwright
3. Close other applications
4. Reduce thread count (Scrapy)
5. Disable unnecessary logging (images, scripts, cookies)

### Network Logging Not Appearing

**Problem:** No network events logged

**Solutions:**
1. Check network logging is enabled
2. Verify URL patterns match actual requests
3. Check method/status code filters
4. Use `*` as URL pattern to test
5. Enable "Log ALL" to see everything

### Script Extraction Fails

**Problem:** JavaScript extraction errors

**Solutions:**
1. These are usually safe to ignore
2. Check error logs for details
3. Try reducing page timeout
4. Disable script logging if not needed

### Smart Stop-On Not Finding Target

**Problem:** Crawler finishes without finding stop-on URL

**Solutions:**
1. Verify target URL is reachable from start URL
2. Increase max_depth (target may be deeply nested)
3. Check Force Domain isn't blocking the target
4. Verify exact URL match (case-sensitive)
5. Watch [SMART] console output for scoring
6. Increase max_pages to give more search space

### JS Runner Script Errors

**Problem:** JS Runner script throws errors

**Solutions:**
1. Check browser console for JavaScript errors
2. Use try-catch in your script
3. Test script in browser DevTools first
4. Use `Silky.log()` for debugging
5. Check that elements exist before accessing
6. Review JS_RUNNER_API.md for examples

### Force Domain Not Working

**Problem:** URLs outside pattern are crawled

**Solutions:**
1. Check pattern syntax (needs `https://`)
2. Verify pattern ends with `/*` for paths
3. Test with simple pattern first: `https://example.com/*`
4. Use max_pages=10 to test quickly
5. Watch console for [SKIPPED] messages

---

## Examples

### Example 1: Basic Scraping

```
Starting URL: https://example.com
Crawler: Scrapy
Depth: 2
Pages: 100
On-site: yes

Result:
- 45 pages crawled
- 230 URLs found
- 150 images
- Export: links.txt
```

### Example 2: API Monitoring

```
Starting URL: https://api.example.com
Crawler: Playwright
Network Logging: Enabled
Patterns: api.example.com/*
Methods: GET,POST,DELETE

Result:
- 25 network events logged
- API performance metrics
- Error responses tracked
```

### Example 3: JavaScript Site with JS Runner

```
Starting URL: https://app.example.com
Crawler: Playwright
Timeout: 20s
JS Runner: Inline script to extract products

Script:
const products = Silky.extractText('.product-name');
Silky.collect({ type: 'products', items: products });

Result:
- 78 products collected
- 12 external scripts logged
- 4 inline scripts logged
- JS Runner: 45 data items
```

### Example 4: Documentation with Force Domain

```
Starting URL: https://docs.python.org/3/
Force Domain: https://docs.python.org/3/*
Crawler: Playwright
Max Pages: 200

Result:
- Stayed only in Python 3 docs
- Skipped Python 2.7 docs
- 156 pages crawled
- Export: documentation_urls.txt
```

### Example 5: Smart Product Finding

```
Starting URL: https://store.example.com
Stop-On URL: https://store.example.com/products/rare-widget
Force Domain: https://store.example.com/products/*
Max Pages: 50

Result:
- Smart scoring prioritized /products links
- Found target in 18 pages (vs 127 without smart)
- Stopped automatically when found
- 7x faster than traditional crawl
```

### Example 6: Complete Site Analysis with All Features

```
Starting URL: https://example.com
Crawler: Playwright
Force Domain: https://example.com/shop/*
Stop-On URL: https://example.com/shop/electronics/laptop-pro
JS Runner: File "extract_prices.js"
Network Logging: Enabled (api.example.com/*)
Max Pages: 100
Max Depth: 5

extract_prices.js:
const price = document.querySelector('.price')?.textContent;
if (price) {
    Silky.collect({ type: 'price', value: price, url: window.location.href });
}

Result:
- Stayed in /shop/* section only
- Smart navigation to laptop-pro
- 34 prices extracted via JS Runner
- 15 API calls logged
- Found target in 29 pages
- Exported: prices.json, network_logs.json
```

---

## Tips & Best Practices

### Performance

1. **Use Scrapy for static sites** - Much faster
2. **Limit depth/pages** - Faster crawls, less memory
3. **Use Force Domain** - Avoid wasting time on irrelevant sections
4. **Use Stop-On URL** - Stop when you find what you need
5. **Disable unnecessary logging** - Faster crawls

### Smart Stop-On

1. **Be specific with URLs** - Exact matches score highest
2. **Set reasonable max_pages** - Prevent runaway searches
3. **Combine with Force Domain** - Stay in relevant areas
4. **Watch console output** - See scoring in action
5. **Use max_depth** - Limit how deep to search

### JS Runner

1. **Test scripts in DevTools first** - Easier debugging
2. **Always use `type` in collected data** - Makes filtering easy
3. **Use try-catch** - Handle errors gracefully
4. **Check element existence** - Use optional chaining (`?.`)
5. **Keep scripts simple** - Complex scripts slow crawling
6. **Use `Silky.log()` for debugging** - See what's happening

### Network Logging

1. **Be specific with patterns** - Reduces log size
2. **Exclude static assets** - Cleaner logs (*.css, *.js)
3. **Set minimum size** - Focus on actual data
4. **Use status code filters** - Find errors quickly

### Image/Script Logging

1. **Disable if not needed** - Saves memory and time
2. **Export metadata for analysis** - Full details in JSON
3. **Use for SEO analysis** - Check alt text, dimensions

### Cookie Logging

1. **Track session creation** - See authentication flow
2. **Security audit** - Find insecure cookies
3. **Third-party analysis** - Identify tracking cookies

### Data Export

1. **Regular exports** - Backup crawl data
2. **Use descriptive filenames** - Include date and purpose
3. **Export logs separately** - Detailed debugging info

---

## Feature Comparison Matrix

| Feature | Scrapy | Playwright |
|---------|--------|------------|
| JavaScript Rendering | NO | YES |
| Speed | Fast | Moderate |
| Memory Usage | Low | High |
| Dynamic Content | NO | YES |
| Multi-threading | YES | NO |
| Network Logging | NO | YES |
| Script Logging | NO | YES |
| Image Logging | YES | YES |
| Cookie Logging | NO | YES |
| **Force Domain** | **NO** | **YES** |
| **Stop-On URL** | **NO** | **YES** |
| **JS Runner** | **NO** | **YES** |
| Content Filtering | YES | YES |
| URL Patterns | YES | YES |
| Proxy Support | YES | YES |
| Cookie Support | YES | YES |
| File Type Filter | YES | NO |


---

## Command Quick Reference

```bash
# Run crawler
python Silky.py

# After crawl commands
stats              # Show statistics
links              # Link analysis
tree               # Hierarchical structure
sitemap            # Site map by depth
info <url>         # URL details
search <term>      # Search content (Scrapy only)
export             # Copy to clipboard
exportfile         # Save to file
exportlinks        # Save URLs
exportimages       # Save image URLs
exportimagedata    # Save images with metadata
exportlogs         # Save all logs
jsresults          # View JS Runner results (Playwright)
exportjs           # Export JS results (Playwright)
exit               # Quit
```

---

## Version Information

- **Python**: 3.8+
- **Scrapy**: Latest
- **Playwright**: Latest
- **Discord.py**: Latest (optional)

---

---

Stay Silky. 

Made by Lil Skittle
