# Silky.py - The best single file web crawler all in Python
## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Quick Start](#quick-start)
3. [Modes Overview](#modes-overview)
4. [Crawl Mode (Detailed)](#crawl-mode-detailed)
5. [Crawler Engines](#crawler-engines)
6. [Configuration Options](#configuration-options)
7. [Network & API Logging](#network--api-logging)
8. [JavaScript Logging](#javascript-logging)
9. [Image Logging](#image-logging)
10. [Export & Analysis](#export--analysis)
11. [Discord Bot Mode](#discord-bot-mode)
12. [Import & Data Analysis](#import--data-analysis)
13. [Troubleshooting](#troubleshooting)
14. [Examples](#examples)

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
=====================================
WEB CRAWLER
=====================================

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
- ✓ Lightweight and fast
- ✓ Good for basic HTML parsing
- ✓ Lower memory usage
- ✗ No JavaScript rendering
- ✗ Cannot see dynamic content

**Playwright** (modern):
- ✓ Renders JavaScript
- ✓ Handles dynamic content
- ✓ Better for SPAs (React, Vue, etc.)
- ✓ Network event logging
- ✗ Slower than Scrapy
- ✗ Requires browser installation

**Choose Playwright if:**
- Site uses JavaScript frameworks (React, Vue, Angular)
- Content loads dynamically
- You need to monitor network requests
- You want to track JavaScript files

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

### On-Site Crawling

```
On Site Crawl only? (yes/no) [yes]: yes
```

- **yes**: Only follow links within the same domain
- **no**: Follow links to external sites

### Crawl Depth & Pages

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

### File Types

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

#### Limitations:
- Slower than Scrapy
- Higher memory usage
- Requires browser

---

## Configuration Options

### Available Commands During Crawl

After crawl completes, use these commands:

```
Commands: search, stats, links, sitemap, export, exportfile, exportlinks, 
          exportimages, exportimagedata, exportlogs, exit
```

| Command | Output |
|---------|--------|
| `search <query>` | Find pages/images containing text |
| `stats` | Crawl statistics (pages, errors, types) |
| `links` | Link analysis (most linked pages) |
| `sitemap` | Site structure by depth |
| `export` | Compress and copy data to clipboard |
| `exportfile` | Save compressed data to file |
| `exportlinks` | Save all URLs to text file |
| `exportimages` | Save all image URLs to text file |
| `exportimagedata` | Save images with metadata (JSON) |
| `exportlogs` | Save all logs (JSON) |
| `exit` | Quit program |

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

#### Monitor Third-party APIs
```
URL patterns: api.github.com/*,api.twitter.com/*
Methods: (all)
Status codes: (all)
```

---

## JavaScript Logging

### Overview

JavaScript logging tracks all scripts loaded on pages, including external files and inline code.

### What Gets Logged

**External Scripts:**
- Full URL
- Type (javascript, module, etc.)
- Async/defer attributes
- Integrity hash
- Source page

**Inline Scripts (>1KB):**
- Inline identifier
- Size in bytes
- First 100 characters
- Source page

### Console Output

```
[SCRIPTS] 15 external, 4 inline | https://example.com
[SCRIPT] https://cdn.example.com/jquery.min.js
[SCRIPT] https://google-analytics.com/ga.js [async]
[SCRIPT] https://example.com/app.js [defer]
[INLINE-SCRIPT] https://example.com/page... (3456 bytes)
```

### Log Files

- **File**: `crawl_logs/javascript_[timestamp].log`
- **JSON**: Included in `crawler_logs.json`

### Example Use Cases

#### Find All Analytics Scripts
```bash
grep -i "analytics\|tracking" crawler_logs.json
```

#### Count External Scripts by Domain
```bash
jq '.logs.javascript[] | select(.script_type == "external") | .script_url' \
  crawler_logs.json | cut -d'/' -f3 | sort | uniq -c
```

#### Find Non-optimized Scripts (Not Async/Defer)
```bash
jq '.logs.javascript[] | select(.async == false and .defer == false)' \
  crawler_logs.json
```

---

## Image Logging

### Overview

Image logging captures all images on pages with metadata.

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

### Log Files Directory

```
crawl_logs/
├── general_[timestamp].log
├── api_[timestamp].log
├── network_[timestamp].log
├── images_[timestamp].log
├── javascript_[timestamp].log
├── errors_[timestamp].log
└── performance_[timestamp].log
```

### Analysis Commands

#### View Statistics
```
Command: stats
Shows: Pages crawled, errors, skipped, content types
```

#### Analyze Links
```
Command: links
Shows: Most linked pages, pages with most outgoing links
```

#### View Site Map
```
Command: sitemap
Shows: Site structure organized by depth
```

#### Search Content
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
Commands: search, stats, links, sitemap, export, exportfile, 
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
3. Disable SSL verification (for testing): May need proxy
4. Check content filter is not too restrictive
5. Verify URL patterns match actual pages

### Timeout Errors

**Problem:** `Timeout 30000ms exceeded` or similar
**Solutions:**
1. Increase page timeout: Set to 20-30 seconds
2. Change wait condition: Use `load` instead of `networkidle`
3. Reduce depth/pages to crawl fewer pages
4. Check internet connection speed

### JavaScript Not Rendering

**Problem:** Dynamic content missing
**Solutions:**
1. Switch to Playwright engine
2. Increase page timeout (Playwright needs time)
3. Check if site requires login

### Memory Issues

**Problem:** Out of memory during crawl
**Solutions:**
1. Reduce max pages
2. Use Scrapy instead of Playwright
3. Close other applications
4. Reduce thread count

### Network Logging Not Appearing

**Problem:** No network events logged
**Solutions:**
1. Check network logging is enabled
2. Verify URL patterns match actual requests
3. Check method/status code filters
4. Use `*` as URL pattern to test

### Script Extraction Fails

**Problem:** JavaScript extraction errors
**Solutions:**
1. These are usually safe to ignore
2. Check error logs for details
3. Try reducing page timeout
4. Use Scrapy crawler instead

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

### Example 3: JavaScript Site

```
Starting URL: https://app.example.com
Crawler: Playwright
Timeout: 20s
Image Mode: Yes

Result:
- Dynamic images loaded
- JavaScript execution tracked
- 78 images found
- 12 external scripts
- 4 inline scripts
```

### Example 4: Data Analysis

```
Previous crawl data loaded
Search: "tutorial"
Results: 12 pages matching

Export options:
- Save all URLs to file
- Send to Discord
- Generate report
```

### Example 5: Scheduled Crawling

```
# Run basic crawl
python Silky.py

# After crawl completes
Command: exportlogs
Output: crawler_logs.json

# Load later for analysis
python Silky.py
Mode: import
File: exported_data.dat
```

---

## Tips & Best Practices

### Performance

1. **Use Scrapy for static sites** - Much faster
2. **Limit depth/pages** - Faster crawls, less memory
3. **Reduce threads** - Slower but more stable
4. **Enable caching** - Keep previously crawled pages

### Network Logging

1. **Be specific with patterns** - Reduces log size
2. **Exclude static assets** - Cleaner logs
3. **Set minimum size** - Focus on data
4. **Use status code filters** - Find errors

### JavaScript Logging

1. **Monitor third-party scripts** - Security concern
2. **Check async/defer attributes** - Performance
3. **Track large inline scripts** - Move to external files

### Image Logging

1. **Export metadata** - Get full details
2. **Check alt text** - SEO and accessibility
3. **Monitor dimensions** - Responsive design

### Data Export

1. **Regular exports** - Backup crawl data
2. **Use version control** - Track changes
3. **Document findings** - Add notes to exports

---

## Keyboard Shortcuts

During menu input:
- `Ctrl+C` - Interrupt crawl
- `Ctrl+D` - EOF (exit input)

---

## File Locations

- **Logs**: `crawl_logs/` directory
- **Exports**: Current directory
- **Configuration**: None (command-line only)

---

## Command Line Quick Reference

```bash
# Run crawler
python Silky.py

# Run in background (Linux/Mac)
python Silky.py &

# Run with timeout (Linux/Mac)
timeout 3600 python Silky.py
```

---

## Getting Help

### Within Program

```
Command: help
Command: /crawl help (Discord bot)
```

### Common Issues

1. **Import errors**: Install missing dependencies
2. **Permission denied**: Run with correct permissions
3. **Connection errors**: Check internet connectivity

---

## Version Information

- **Python**: 3.8+
- **Scrapy**: Latest
- **Playwright**: Latest

---

Stay Silky.

