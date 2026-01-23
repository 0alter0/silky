import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse, urljoin
from difflib import get_close_matches
import sys
import json
import zlib
import base64
import os
import re
import requests
from collections import Counter, defaultdict
from datetime import datetime
import multiprocessing
import time
from io import BytesIO
import logging
from logging.handlers import RotatingFileHandler
from enum import Enum

# Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# --- CONFIGURATION ---
# Ts not needed anymore lol
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzzLoNPs7JtcXgeBjLv3VslIyRP7SE7I3SKL6hfGKdxbp58tROetamXW6R5DPK_ttcA/exec" 
# ---------------------

try:
    import discord
    DISCORD_LIB_AVAILABLE = True
except ImportError:
    DISCORD_LIB_AVAILABLE = False

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    API = 25
    NETWORK = 26
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


logging.addLevelName(LogLevel.API.value, "API")
logging.addLevelName(LogLevel.NETWORK.value, "NETWORK")


class CrawlLogger:
    
    def __init__(self, log_dir="crawl_logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs = {
            "general": [],
            "api": [],
            "network": [],
            "images": [],
            "javascript": [],
            "errors": [],
            "performance": []
        }
        
        self.handlers = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        for log_type in self.logs.keys():
            filename = os.path.join(self.log_dir, f"{log_type}_{self.timestamp}.log")
            handler = RotatingFileHandler(filename, maxBytes=10*1024*1024, backupCount=5)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.handlers[log_type] = handler
    
    def log_api_call(self, endpoint, method, status_code, response_time, data=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time,
            "data_size": len(json.dumps(data)) if data else 0
        }
        self.logs["api"].append(entry)
        print(f"[API] {method} {endpoint} - Status: {status_code} ({response_time:.2f}ms)")
    
    def log_network_event(self, url, method, status, content_type, size, duration):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "method": method,
            "status": status,
            "content_type": content_type,
            "size_bytes": size,
            "duration_ms": duration
        }
        self.logs["network"].append(entry)
        print(f"[NETWORK] {method} {url} - Status: {status} ({size} bytes, {duration:.2f}ms)")
    
    def log_image(self, url, source_page, dimensions=None, format_type=None, file_size=None, alt_text=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "source_page": source_page,
            "dimensions": dimensions,
            "format": format_type,
            "file_size_bytes": file_size,
            "alt_text": alt_text
        }
        self.logs["images"].append(entry)
        dim_str = f" ({dimensions[0]}x{dimensions[1]})" if dimensions else ""
        print(f"[IMAGE] {url[:80]}{dim_str}")
    
    def log_javascript(self, script_url, script_type, page_url, async_load=False, defer_load=False, content_size=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "script_url": script_url,
            "script_type": script_type,
            "page_url": page_url,
            "async": async_load,
            "defer": defer_load,
            "content_size_bytes": content_size
        }
        self.logs["javascript"].append(entry)
        
        if script_type == "external":
            script_display = script_url[:80]
            async_str = " [async]" if async_load else ""
            defer_str = " [defer]" if defer_load else ""
            print(f"[SCRIPT] {script_display}{async_str}{defer_str}")
        else:
            size_str = f" ({content_size} bytes)" if content_size else ""
            print(f"[INLINE-SCRIPT] {page_url[:60]}...{size_str}")
    
    def log_error(self, error_type, url, message, traceback_info=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "url": url,
            "message": message,
            "traceback": traceback_info
        }
        self.logs["errors"].append(entry)
        print(f"[ERROR] {error_type} on {url}: {message}")
    
    def log_performance(self, metric_name, value, unit="ms"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "metric": metric_name,
            "value": value,
            "unit": unit
        }
        self.logs["performance"].append(entry)
        print(f"[PERF] {metric_name}: {value} {unit}")
    
    def export_logs(self, filename="crawler_logs.json"):
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "logs": self.logs,
            "summary": {
                "total_api_calls": len(self.logs["api"]),
                "total_network_events": len(self.logs["network"]),
                "total_images": len(self.logs["images"]),
                "total_errors": len(self.logs["errors"]),
                "performance_metrics": len(self.logs["performance"])
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"Logs exported to {filename}")
            return filename
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return None
    
    def get_summary(self):
        summary = {
            "api_calls": len(self.logs["api"]),
            "network_events": len(self.logs["network"]),
            "images": len(self.logs["images"]),
            "errors": len(self.logs["errors"]),
            "performance_points": len(self.logs["performance"])
        }
        return summary

# Only for discord bot hosting
HOST_LIMITS = {
    "max_depth": 100, 
    "max_pages": 5000,
    "timeout_seconds": 300 
}

DEFAULT_PARAMS = {
    "site_only": True,
    "pages": HOST_LIMITS["max_pages"],
    "depth": HOST_LIMITS["max_depth"],  
    "filter": None,
    "include_pattern": None,
    "exclude_pattern": None,
    "file_type": None,
    "image_only": False
}


collected_data = []

crawl_stats = {
    "pages_crawled": 0,
    "start_time": None,
    "errors": 0,
    "skipped": 0,
    "link_map": defaultdict(list),
    "inbound_links": Counter(),
    "content_types": Counter(),
    "broken_links": [],
    "images_found": 0
}

discord_config = {
    "enabled": False,
    "webhook_url": None,
    "mode": None
}

def get_main_domain(url):
    netloc = urlparse(url).netloc
    parts = netloc.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return netloc


class NetworkLoggingConfig:
    def __init__(self, enabled=False, log_all=False, url_patterns=None, methods=None, 
                 min_size=0, status_codes=None, exclude_patterns=None):
        self.enabled = enabled
        self.log_all = log_all
        self.url_patterns = url_patterns or []
        self.methods = [m.upper() for m in (methods or [])]
        self.min_size = min_size
        self.status_codes = status_codes
        self.exclude_patterns = exclude_patterns or []
        
        self.compiled_patterns = []
        for pattern in self.url_patterns:
            try:
                regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
                self.compiled_patterns.append(re.compile(regex_pattern))
            except Exception as e:
                print(f"Warning: Invalid URL pattern '{pattern}': {e}")
        
        self.compiled_exclude = []
        for pattern in self.exclude_patterns:
            try:
                regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
                self.compiled_exclude.append(re.compile(regex_pattern))
            except Exception as e:
                print(f"Warning: Invalid exclude pattern '{pattern}': {e}")
    
    def should_log(self, url, method, status_code=None, size=0):
        if not self.enabled:
            return False
        
        if self.log_all:
            return True
        
        for pattern in self.compiled_exclude:
            if pattern.search(url):
                return False
        
        if self.methods and method.upper() not in self.methods:
            return False
        
        if self.status_codes and status_code not in self.status_codes:
            return False
        
        if size < self.min_size:
            return False
        
        if not self.url_patterns:
            return False
        
        for pattern in self.compiled_patterns:
            if pattern.search(url):
                return True
        
        return False
    
    @staticmethod
    def from_user_input():
        print("\n--- NETWORK LOGGING CONFIGURATION ---")
        enable_logging = input("Enable network/API logging? (yes/no) [no]: ").strip().lower()
        
        if enable_logging not in ['yes', 'y', 'true', '1']:
            return NetworkLoggingConfig(enabled=False)
        
        log_all = input("Log ALL network requests? (yes/no) [no]: ").strip().lower()
        if log_all in ['yes', 'y', 'true', '1']:
            return NetworkLoggingConfig(enabled=True, log_all=True)
        
        print("\nURL Patterns (supports wildcards like 'example.com/api/*'):")
        print("Examples: 'example.com/api/user', 'example.com/api/*', '*.api.example.com', 'api/*'")
        url_input = input("Enter URL patterns (comma-separated) [none]: ").strip()
        url_patterns = [p.strip() for p in url_input.split(',')] if url_input else []
        
        print("\nHTTP Methods (GET, POST, PUT, DELETE, PATCH, etc.):")
        methods_input = input("Enter HTTP methods (comma-separated) [all]: ").strip()
        methods = [m.strip().upper() for m in methods_input.split(',')] if methods_input else []
        
        print("\nStatus Codes to log (e.g., 200,404,500 or leave blank for all):")
        status_input = input("Enter status codes (comma-separated) [all]: ").strip()
        status_codes = None
        if status_input:
            try:
                status_codes = [int(s.strip()) for s in status_input.split(',')]
            except ValueError:
                print("Invalid status codes, logging all.")
                status_codes = None
        
        min_size = 0
        size_input = input("Minimum response size to log in bytes [0]: ").strip()
        if size_input.isdigit():
            min_size = int(size_input)
        
        print("\nExclude patterns (URLs matching these will NOT be logged):")
        exclude_input = input("Enter exclude patterns (comma-separated) [none]: ").strip()
        exclude_patterns = [p.strip() for p in exclude_input.split(',')] if exclude_input else []
        
        config = NetworkLoggingConfig(
            enabled=True,
            log_all=False,
            url_patterns=url_patterns,
            methods=methods,
            min_size=min_size,
            status_codes=status_codes,
            exclude_patterns=exclude_patterns
        )
        
        print("\n--- Network Logging Config Summary ---")
        print(f"Enabled: Yes")
        print(f"URL Patterns: {url_patterns or 'None'}")
        print(f"Methods: {methods or 'All'}")
        print(f"Status Codes: {status_codes or 'All'}")
        print(f"Min Size: {min_size} bytes")
        print(f"Exclude Patterns: {exclude_patterns or 'None'}")
        
        return config


class PlaywrightCrawler:
    def __init__(self, logger=None, max_depth=0, max_pages=0, on_site_only=False,
                 content_filter=None, url_include=None, url_exclude=None, image_only=False,
                 network_logging_config=None, page_timeout=15000):
        self.logger = logger or CrawlLogger()
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.on_site_only = on_site_only
        self.content_filter = content_filter
        self.url_include = re.compile(url_include) if url_include and url_include.upper() != 'N/A' else None
        self.url_exclude = re.compile(url_exclude) if url_exclude and url_exclude.upper() != 'N/A' else None
        self.image_only = image_only
        self.network_logging_config = network_logging_config or NetworkLoggingConfig(enabled=False)
        self.page_timeout = page_timeout  # in milliseconds!!!!
        
        self.visited = set()
        self.collected_data = []
        self.start_url = None
        self.allowed_domains = []
        
        self.stats = {
            "pages_crawled": 0,
            "images_found": 0,
            "errors": 0,
            "skipped": 0,
            "start_time": datetime.now(),
            "network_requests": [],
            "api_calls": [],
            "images": [],
            "javascript": {
                "external_scripts": [],
                "inline_scripts": [],
                "total_external": 0,
                "total_inline": 0
            }
        }
    
    def should_crawl_url(self, url):
        if self.on_site_only and get_main_domain(url) not in self.allowed_domains:
            self.stats["skipped"] += 1
            return False
        if self.url_include and not self.url_include.search(url):
            self.stats["skipped"] += 1
            return False
        if self.url_exclude and self.url_exclude.search(url):
            self.stats["skipped"] += 1
            return False
        return True
    
    def extract_images_from_page(self, page: Page, url: str):
        images = []
        
        try:
            img_elements = page.query_selector_all('img')
            for img in img_elements:
                img_url = img.get_attribute('src') or img.get_attribute('data-src')
                if not img_url:
                    continue
                
                img_url = urljoin(url, img_url)
                alt_text = img.get_attribute('alt')
                
                width = img.get_attribute('width')
                height = img.get_attribute('height')
                dimensions = None
                if width and height:
                    try:
                        dimensions = (int(width), int(height))
                    except ValueError:
                        pass
                
                images.append({
                    "url": img_url,
                    "type": "img_tag",
                    "alt": alt_text,
                    "dimensions": dimensions
                })
                
                self.logger.log_image(img_url, url, dimensions=dimensions, alt_text=alt_text)
        
        except Exception as e:
            self.logger.log_error("ImageExtraction", url, str(e))
        
        try:
            css_images = page.evaluate(r"""() => {
                const images = [];
                try {
                    document.querySelectorAll('*').forEach(el => {
                        try {
                            const style = window.getComputedStyle(el);
                            const bgImage = style.backgroundImage;
                            if (bgImage && bgImage !== 'none') {
                                const match = bgImage.match(/url\(["\']?([^"\')]+)["\']?\)/);
                                if (match && match[1]) {
                                    images.push(match[1]);
                                }
                            }
                        } catch (e) {
                            // Skip elements that fail
                        }
                    });
                } catch (e) {
                    // Return whatever we found so far
                }
                return images;
            }""")
            
            for img_url in css_images:
                img_url = urljoin(url, img_url)
                images.append({
                    "url": img_url,
                    "type": "css_background",
                    "alt": None,
                    "dimensions": None
                })
                self.logger.log_image(img_url, url, format_type="css_background")
        
        except Exception as e:
            self.logger.log_error("CSSImageExtraction", url, str(e))
        
        self.stats["images_found"] += len(images)
        self.stats["images"].extend(images)
        return images
    
    def extract_javascript_from_page(self, page: Page, url: str):
        scripts = []
        
        try:
            script_data = page.evaluate(r"""() => {
                const scripts = [];
                try {
                    document.querySelectorAll('script').forEach((script, index) => {
                        try {
                            const scriptInfo = {
                                index: index,
                                type: script.type || 'text/javascript',
                                src: script.src || null,
                                inline: !script.src,
                                async: script.async,
                                defer: script.defer,
                                content_length: script.textContent ? script.textContent.length : 0,
                                first_100_chars: script.textContent ? script.textContent.substring(0, 100) : null,
                                nonce: script.nonce || null,
                                integrity: script.integrity || null
                            };
                            scripts.push(scriptInfo);
                        } catch (e) {
                            // Skip problematic scripts
                        }
                    });
                } catch (e) {
                    // Return whatever we found
                }
                return scripts;
            }""")
            
            external_scripts = []
            inline_scripts = []
            
            for script_info in script_data or []:
                if script_info['src']:
                    script_url = urljoin(url, script_info['src'])
                    script_entry = {
                        "url": script_url,
                        "type": "external",
                        "script_type": script_info['type'],
                        "async": script_info['async'],
                        "defer": script_info['defer'],
                        "integrity": script_info['integrity'],
                        "source_page": url
                    }
                    scripts.append(script_entry)
                    external_scripts.append(script_url)
                    
                    self.logger.log_javascript(
                        script_url,
                        "external",
                        url,
                        async_load=script_info['async'],
                        defer_load=script_info['defer']
                    )
                else:
                    script_entry = {
                        "url": f"{url}#inline-{script_info['index']}",
                        "type": "inline",
                        "script_type": script_info['type'],
                        "content_size": script_info['content_length'],
                        "first_100_chars": script_info['first_100_chars'],
                        "source_page": url
                    }
                    scripts.append(script_entry)
                    inline_scripts.append(script_entry)
                    
                    if script_info['content_length'] > 1024:
                        self.logger.log_javascript(
                            f"{url}#inline-{script_info['index']}",
                            "inline",
                            url,
                            content_size=script_info['content_length']
                        )
            
            if not hasattr(self.stats, 'javascript'):
                self.stats["javascript"] = {
                    "external_scripts": [],
                    "inline_scripts": [],
                    "total_external": 0,
                    "total_inline": 0,
                    "total_external_size": 0
                }
            
            self.stats["javascript"]["external_scripts"].extend(external_scripts)
            self.stats["javascript"]["inline_scripts"].extend(inline_scripts)
            self.stats["javascript"]["total_external"] += len(external_scripts)
            self.stats["javascript"]["total_inline"] += len(inline_scripts)
            
            print(f"[SCRIPTS] {len(external_scripts)} external, {len(inline_scripts)} inline | {url}")
        
        except Exception as e:
            self.logger.log_error("JavaScriptExtraction", url, str(e))
        
        return scripts
    
    def crawl_page(self, page: Page, url: str, depth: int = 0):
        if url in self.visited or (self.max_pages > 0 and self.stats["pages_crawled"] >= self.max_pages):
            return
        
        if self.max_depth > 0 and depth >= self.max_depth:
            self.stats["skipped"] += 1
            return
        
        if not self.should_crawl_url(url):
            return
        
        try:
            start_time = time.time()
            page.goto(url, wait_until='load', timeout=self.page_timeout)
            load_time = (time.time() - start_time) * 1000
            
            self.visited.add(url)
            self.stats["pages_crawled"] += 1
            
            self.logger.log_performance(f"Page Load - {url[:40]}...", load_time, "ms")
            
            title = page.title() or ""
            meta_desc = ""
            try:
                meta_elem = page.query_selector('meta[name="description"]')
                if meta_elem:
                    meta_desc = meta_elem.get_attribute('content') or ""
            except:
                pass
            
            if self.image_only:
                images = self.extract_images_from_page(page, url)
                for img in images:
                    page_data = {
                        "url": img["url"],
                        "source_page": url,
                        "depth": depth,
                        "type": "image",
                        "alt_text": img["alt"],
                        "dimensions": img["dimensions"]
                    }
                    self.collected_data.append(page_data)
                
                print(f"[IMAGES] {len(images)} images | Depth: {depth} | {url}")
            
            else:
                text_content = page.evaluate("() => document.body.innerText") or ""
                
                if self.content_filter and self.content_filter.upper() != 'N/A':
                    if self.content_filter.lower() not in text_content.lower():
                        self.stats["skipped"] += 1
                        return
                
                h1_tags = page.evaluate("() => Array.from(document.querySelectorAll('h1')).map(el => el.textContent)")
                
                page_data = {
                    "url": url,
                    "content": text_content[:50000], 
                    "title": title,
                    "meta_description": meta_desc,
                    "h1_tags": h1_tags or [],
                    "depth": depth,
                    "load_time_ms": load_time
                }
                
                self.collected_data.append(page_data)
                print(f"[SCRAPED] {len(self.collected_data)} | Depth: {depth} | {url}")
                
                if not self.image_only:
                    self.extract_images_from_page(page, url)
                    
                    self.extract_javascript_from_page(page, url)
            
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter((href, index, self) => self.indexOf(href) === index);
            }""")
            
            for link_url in links or []:
                if link_url not in self.visited and self.should_crawl_url(link_url):
                    if self.max_depth == 0 or depth + 1 < self.max_depth:
                        self.crawl_page(page, link_url, depth + 1)
        
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.log_error("PageCrawl", url, str(e))
    
    def run(self, start_urls):
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright is not installed. Run: pip install playwright")
            return None
        
        self.start_url = start_urls[0] if isinstance(start_urls, list) else start_urls
        self.allowed_domains = [get_main_domain(self.start_url)] if self.on_site_only else []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (compatible; PlaywrightCrawler/1.0)"
                )
                
                def log_request(request):
                    try:
                        response = request.response()
                        if response:
                            status = response.status
                            content_type = response.headers.get('content-type', 'unknown')
                            size = len(response.body()) if hasattr(response, 'body') else 0
                            method = request.method
                            
                            if self.network_logging_config.should_log(request.url, method, status, size):
                                self.logger.log_network_event(
                                    request.url,
                                    method,
                                    status,
                                    content_type,
                                    size,
                                    0
                                )
                    except Exception as e:
                        pass
                
                def log_response(response):
                    try:
                        method = response.request.method
                        url = response.url
                        content_type = response.headers.get('content-type', 'unknown')
                        status = response.status
                        
                        size = 0
                        try:
                            size = len(response.body())
                        except:
                            pass
                        
                        if self.network_logging_config.should_log(url, method, status, size):
                            self.logger.log_network_event(
                                url,
                                method,
                                status,
                                content_type,
                                size,
                                0
                            )
                    except Exception as e:
                        pass
                
                page.on("response", log_response)
                
                urls = start_urls if isinstance(start_urls, list) else [start_urls]
                for url in urls:
                    self.crawl_page(page, url, 0)
                
                browser.close()
        
        except Exception as e:
            self.logger.log_error("BrowserCrawl", "N/A", str(e))
            self.stats["errors"] += 1
        
        return {
            "data": self.collected_data,
            "stats": self.stats,
            "logs": self.logger.get_summary()
        }


def send_discord_message(content=None, embed=None, file_content=None, filename=None):
    if not discord_config["enabled"]:
        return
    try:
        data = {}
        files = None
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed]
            
        if file_content and filename:
            files = {'file': (filename, file_content, 'text/plain')}
            requests.post(discord_config["webhook_url"], data={'payload_json': json.dumps(data)}, files=files)
        else:
            requests.post(discord_config["webhook_url"], json=data)
    except Exception as e:
        print(f"Discord webhook failed: {e}")

# Gotta make a seperate script to quickly copy all cookies from the site (JS)
def parse_cookies(cookie_string):
    if not cookie_string or cookie_string.strip() == "":
        return {}
    
    cookie_string = cookie_string.strip()
    
    if cookie_string.startswith('{'):
        try:
            return json.loads(cookie_string)
        except json.JSONDecodeError:
            pass
    
    cookies = {}
    pairs = re.split(r'[;,]', cookie_string)
    for pair in pairs:
        pair = pair.strip()
        if '=' in pair:
            name, value = pair.split('=', 1)
            cookies[name.strip()] = value.strip()
    
    return cookies

class SearchSpider(scrapy.Spider):
    name = "search_spider"

    def __init__(self, start_urls=None, on_site_only=False, max_depth=0, max_pages=0, 
                 content_filter=None, url_include=None, url_exclude=None, file_types=None, 
                 image_only=False, cookies=None, manager_dict=None, parent_pid=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls if isinstance(start_urls, list) else [start_urls]
        self.visited = set()
        self.on_site_only = on_site_only
        self.allowed_domains = [get_main_domain(url) for url in self.start_urls] if on_site_only else []
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.content_filter = content_filter
        self.url_include = re.compile(url_include) if url_include and url_include.upper() != 'N/A' else None
        self.url_exclude = re.compile(url_exclude) if url_exclude and url_exclude.upper() != 'N/A' else None
        self.file_types = file_types.split(',') if file_types and file_types.upper() != 'N/A' else None
        self.image_only = image_only
        self.cookies = cookies or {}
        self.link_extractor = LinkExtractor()
        self.pages_count = 0
        self.manager_dict = manager_dict 
        self.parent_pid = parent_pid 
        self.local_data = [] 
        
        if not self.manager_dict:
            global crawl_stats
            crawl_stats["start_time"] = datetime.now()
            crawl_stats["pages_crawled"] = 0
            crawl_stats["errors"] = 0
            crawl_stats["skipped"] = 0
            crawl_stats["link_map"] = defaultdict(list)
            crawl_stats["inbound_links"] = Counter()
            crawl_stats["content_types"] = Counter()
            crawl_stats["broken_links"] = []
            crawl_stats["images_found"] = 0

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, cookies=self.cookies, 
                               cb_kwargs={'depth': 0}, errback=self.handle_error)

    def should_crawl_url(self, url):
        if self.on_site_only and get_main_domain(url) not in self.allowed_domains:
            crawl_stats["skipped"] += 1
            return False
        if self.url_include and not self.url_include.search(url):
            crawl_stats["skipped"] += 1
            return False
        if self.url_exclude and self.url_exclude.search(url):
            crawl_stats["skipped"] += 1
            return False
        if self.file_types:
            url_lower = url.lower()
            if not any(url_lower.endswith(f'.{ft.strip()}') for ft in self.file_types):
                if any(url_lower.endswith(f'.{ext}') for ext in ['pdf','doc','docx','zip','exe','jpg','png','gif','mp4','mp3']):
                    crawl_stats["skipped"] += 1
                    return False
        return True

    def parse(self, response, depth=0):
        url = response.url
        if url in self.visited:
            return
        self.visited.add(url)
        self.pages_count += 1
        crawl_stats["pages_crawled"] += 1
        
        if self.max_depth > 0 and depth >= self.max_depth:
            crawl_stats["skipped"] += 1
            return
        
        content_type = response.headers.get('Content-Type', b'').decode('utf-8').split(';')[0]
        crawl_stats["content_types"][content_type] += 1
        
        if self.image_only:
            images = []
            
            img_elements = response.css('img')
            for img_elem in img_elements:
                img_url = img_elem.css('::attr(src)').get() or img_elem.css('::attr(data-src)').get()
                if not img_url:
                    continue
                
                full_url = urljoin(response.url, img_url)
                alt_text = img_elem.css('::attr(alt)').get()
                width = img_elem.css('::attr(width)').get()
                height = img_elem.css('::attr(height)').get()
                
                dimensions = None
                if width and height:
                    try:
                        dimensions = (int(width), int(height))
                    except (ValueError, TypeError):
                        pass
                
                images.append({
                    "url": full_url,
                    "type": "img_tag",
                    "alt_text": alt_text,
                    "dimensions": dimensions
                })
            
            style_images = response.css('*::attr(style)').re(r'url\(["\']?([^"\')]+)["\']?\)')
            for src in style_images:
                full_url = urljoin(response.url, src)
                images.append({
                    "url": full_url,
                    "type": "css_background",
                    "alt_text": None,
                    "dimensions": None
                })
            
            crawl_stats["images_found"] += len(images)
            
            for img_data in images:
                page_data = {
                    "url": img_data["url"],
                    "source_page": url,
                    "depth": depth,
                    "type": "image",
                    "image_type": img_data["type"],
                    "alt_text": img_data["alt_text"],
                    "dimensions": img_data["dimensions"]
                }
                
                if not self.manager_dict:
                    collected_data.append(page_data)
                self.local_data.append(page_data)
            
            if not self.manager_dict:
                print(f"[IMAGES] {len(images)} images | Depth: {depth} | {url}")
            else:
                print(f"[IMAGES-MP/{self.parent_pid}] {len(images)} images | Depth: {depth} | {url}")
        else:
            text = " ".join(response.css("body *::text").getall()).strip()
            
            if self.content_filter and self.content_filter.upper() != 'N/A' and self.content_filter.lower() not in text.lower():
                crawl_stats["skipped"] += 1
                return
                
            title = response.css('title::text').get() or ""
            meta_desc = response.css('meta[name="description"]::attr(content)').get() or ""
            h1_tags = response.css('h1::text').getall()

            page_data = {
                "url": url,
                "content": text,
                "title": title.strip(),
                "meta_description": meta_desc.strip(),
                "h1_tags": h1_tags,
                "depth": depth,
                "content_type": content_type
            }

            if not self.manager_dict:
                collected_data.append(page_data)
            self.local_data.append(page_data)

            if not self.manager_dict:
                elapsed = (datetime.now() - crawl_stats["start_time"]).total_seconds()
                rate = crawl_stats["pages_crawled"] / elapsed if elapsed > 0 else 0
                print(f"[SCRAPED] {len(collected_data)} | Depth: {depth} | {url}")
            else:
                print(f"[SCRAPED-MP/{self.parent_pid}] {len(self.local_data)} | Depth: {depth} | {url}")

        links = self.link_extractor.extract_links(response)
        outgoing_links = []
        for link in links:
            link_url = link.url
            outgoing_links.append(link_url)
            crawl_stats["inbound_links"][link_url] += 1
            
            max_depth_check = self.max_depth > 0 and depth + 1 >= self.max_depth
            
            if link_url not in self.visited and self.should_crawl_url(link_url) and not max_depth_check:
                yield scrapy.Request(link_url, callback=self.parse, cookies=self.cookies,
                                   cb_kwargs={'depth': depth+1}, errback=self.handle_error, dont_filter=False)
            
            elif max_depth_check:
                crawl_stats["skipped"] += 1

        crawl_stats["link_map"][url] = outgoing_links

    def closed(self, reason):
        final_package = {
            "data": self.local_data,
            "stats": {
                "pages_crawled": crawl_stats["pages_crawled"],
                "start_time": crawl_stats["start_time"].isoformat() if isinstance(crawl_stats["start_time"], datetime) else str(crawl_stats["start_time"]),
                "errors": crawl_stats["errors"],
                "skipped": crawl_stats["skipped"],
                "link_map": dict(crawl_stats["link_map"]),
                "inbound_links": dict(crawl_stats["inbound_links"]),
                "content_types": dict(crawl_stats["content_types"]),
                "broken_links": crawl_stats["broken_links"],
                "images_found": crawl_stats["images_found"]
            }
        }
        
        if self.parent_pid:
            try:
                raw = json.dumps(final_package).encode("utf-8")
                compressed = zlib.compress(raw, level=9)
                
                temp_filename = f"results_{self.parent_pid}.dat"
                with open(temp_filename, "wb") as f:
                    f.write(compressed)
                
                if self.manager_dict:
                     self.manager_dict['temp_file'] = temp_filename
                
            except Exception as e:
                print(f"Error writing compressed data to file: {e}")
                if self.manager_dict:
                    self.manager_dict['error'] = f"File write error: {e}"


    def handle_error(self, failure):
        crawl_stats["errors"] += 1
        if failure.request and failure.request.url not in crawl_stats["broken_links"]:
            crawl_stats["broken_links"].append(failure.request.url)


def run_crawler_process(start_urls, on_site_only, max_depth, max_pages, content_filter, url_include, url_exclude, file_types, image_only, cookies, manager_dict, parent_pid):
    """
    Runs a single Scrapy crawler process. Used by run_discord_host.
    """
    settings = {
        "LOG_LEVEL": "ERROR",
        "USER_AGENT": "Mozilla/5.0 (compatible; SearchBuilder/1.0)",
        "CLOSESPIDER_PAGECOUNT": max_pages, 
        "CLOSESPIDER_TIMEOUT": HOST_LIMITS["timeout_seconds"], 
        "DEPTH_LIMIT": max_depth, 
        "DOWNLOAD_TIMEOUT": 15,
        "RETRY_TIMES": 2
    }
    
    global crawl_stats
    if manager_dict is not None:
        crawl_stats["start_time"] = datetime.now()
        crawl_stats["pages_crawled"] = 0
        crawl_stats["errors"] = 0
        crawl_stats["skipped"] = 0
        crawl_stats["link_map"] = defaultdict(list)
        crawl_stats["inbound_links"] = Counter()
        crawl_stats["content_types"] = Counter()
        crawl_stats["broken_links"] = []
        crawl_stats["images_found"] = 0
    
    process = CrawlerProcess(settings=settings)
    
    process.crawl(SearchSpider, 
                  start_urls=start_urls, 
                  on_site_only=on_site_only, 
                  max_depth=max_depth, 
                  max_pages=max_pages, 
                  content_filter=content_filter, 
                  url_include=url_include, 
                  url_exclude=url_exclude, 
                  file_types=file_types,
                  image_only=image_only,
                  cookies=cookies,
                  manager_dict=manager_dict,
                  parent_pid=parent_pid)
    
    try:
        process.start(stop_after_crawl=True) 
    except Exception as e:
        print(f"Scrapy process failed: {e}")
        if manager_dict:
            manager_dict['error'] = str(e)
        
    try:
        if process.running:
             process.stop()
    except Exception as e:
        pass


def run_local_crawler(start_urls, on_site_only=False, max_depth=0, max_pages=0, content_filter=None, url_include=None, url_exclude=None, file_types=None, image_only=False, cookies=None, threads=6):
    
    max_depth_setting = max_depth if max_depth > 0 else 0
    max_pages_setting = max_pages if max_pages > 0 else 0
    
    settings = {
        "LOG_LEVEL": "ERROR",
        "USER_AGENT": "Mozilla/5.0 (compatible; SearchBuilder/1.0)",
        "CLOSESPIDER_PAGECOUNT": max_pages_setting, 
        "CLOSESPIDER_TIMEOUT": HOST_LIMITS["timeout_seconds"] * 2,
        "DEPTH_LIMIT": max_depth_setting,
        "CONCURRENT_REQUESTS": threads,
        "DOWNLOAD_TIMEOUT": 15,
        "RETRY_TIMES": 2
    }
    
    global crawl_stats, collected_data
    collected_data.clear() 
    
    process = CrawlerProcess(settings=settings)
    
    process.crawl(SearchSpider, start_urls=start_urls, on_site_only=on_site_only, max_depth=max_depth_setting, max_pages=max_pages_setting, content_filter=content_filter, url_include=url_include, url_exclude=url_exclude, file_types=file_types, image_only=image_only, cookies=cookies, manager_dict=None, parent_pid=None)
    
    try:
        process.start()
    except Exception as e:
        print(f"Local crawl failed: {e}")


def _get_stats_text(stats):
    if not stats:
        return f"{'='*60}\nCRAWL STATISTICS\n{'='*60}\nNo crawl statistics found.\n{'='*60}\n"
    
    start_time_obj = stats.get("start_time")
    if isinstance(start_time_obj, str):
        try:
            start_time_obj = datetime.fromisoformat(start_time_obj)
        except ValueError:
            pass 

    elapsed = (datetime.now() - start_time_obj).total_seconds() if isinstance(start_time_obj, datetime) else 0
    pages_crawled = stats.get('pages_crawled', 0)
    rate = pages_crawled / elapsed if elapsed > 0 else 0
    
    stats_text = f"{'='*60}\nCRAWL STATISTICS\n{'='*60}\nPages Crawled: {pages_crawled}\nPages Skipped: {stats.get('skipped', 0)}\nErrors: {stats.get('errors', 0)}\nImages Found: {stats.get('images_found', 0)}\nCrawl Time: {elapsed:.1f}s\nCrawl Rate: {rate:.2f} pages/sec\nContent Types:"
    
    content_types = stats.get("content_types", {})
    if content_types:
        for ct, count in Counter(content_types).most_common():
            stats_text += f"\n {ct}: {count}"
            
    if stats.get("broken_links"):
        stats_text += f"\n\nBroken Links ({len(stats['broken_links'])}):"
        for link in stats["broken_links"]:
            stats_text += f"\n {link}"
    stats_text += f"\n{'='*60}\n"
    return stats_text

def _get_link_analysis_text(stats):
    inbound_links = stats.get("inbound_links", {})
    link_map = stats.get("link_map", {})
    
    if not inbound_links and not link_map:
        return "\n" + "="*60 + "\nLINK ANALYSIS\n" + "="*60 + "\nNo link data available.\n" + "="*60 + "\n"
    
    link_text = "\n" + "="*60 + "\nLINK ANALYSIS\n" + "="*60 + "\n\nMost Linked Pages (Top 10):"
    
    top_pages = Counter(inbound_links).most_common(10)
    for i, (url, count) in enumerate(top_pages, 1):
        link_text += f"\n{i}. [{count} links] {url}"
        
    link_text += "\n\nPages with Most Outgoing Links (Top 10):"
    outgoing = [(url, len(links)) for url, links in link_map.items()]
    outgoing.sort(key=lambda x: x[1], reverse=True)
    for i, (url, count) in enumerate(outgoing[:10], 1):
        link_text += f"\n{i}. [{count} outgoing] {url}"
        
    link_text += "\n" + "="*60 + "\n"
    return link_text

def _generate_sitemap_text(data):
    if not data:
        return "\n" + "="*60 + "\nSITE MAP (Title and URL by Depth)\n" + "="*60 + "\nNo collected page data found.\n" + "="*60 + "\n"
        
    sitemap_text = "\n" + "="*60 + "\nSITE MAP (Title and URL by Depth)\n" + "="*60 + "\n"
    by_depth = defaultdict(list)
    for page in data:
        depth = page.get('depth', 0)
        by_depth[depth].append(page)
    max_depth_found = max(by_depth.keys()) if by_depth else 0
    
    for depth in range(max_depth_found + 1):
        pages = by_depth[depth]
        if pages:
            indent = " " * (depth * 2)
            sitemap_text += f"\n{indent}Depth {depth} ({len(pages)} pages total):"
            
            for i, page in enumerate(pages): 
                title = page.get('title', 'No title')
                sitemap_text += f"\n{indent}├─ {title}"
                sitemap_text += f"\n{indent}   {page['url']}"
    sitemap_text += "\n" + "="*60 + "\n"
    return sitemap_text

def _generate_image_report_text(data):
    if not data:
        return "\n" + "="*60 + "\nIMAGE SCRAPING RESULTS\n" + "="*60 + "\nNo images found.\n" + "="*60 + "\n"
    
    image_text = "\n" + "="*60 + "\nIMAGE SCRAPING RESULTS\n" + "="*60 + "\n"
    image_text += f"Total Images Found: {len(data)}\n\n"
    
    by_source = defaultdict(list)
    for item in data:
        by_source[item.get('source_page', 'Unknown')].append(item['url'])
    
    for source_page, img_urls in by_source.items():
        image_text += f"\nSource Page: {source_page}\n"
        image_text += f"Images Found: {len(img_urls)}\n"
        image_text += "-"*30 + "\n"
        for img_url in img_urls:
            image_text += f"  {img_url}\n"
        image_text += "\n"
    
    image_text += "="*60 + "\n"
    return image_text
    
def generate_full_report_text(url, data, stats, image_only=False):
    """Generates the final human-readable report text with enhanced logging."""
    txt_output = f"CRAWL RESULTS FOR: {url}\n"
    txt_output += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    txt_output += _get_stats_text(stats)
    
    if image_only:
        txt_output += "\n" + "="*60 + "\nIMAGE URLs AND METADATA\n" + "="*60 + "\n"
        for item in data:
            if item.get('type') == 'image':
                img_info = f"URL: {item['url']}\n"
                if item.get('alt_text'):
                    img_info += f"Alt Text: {item['alt_text']}\n"
                if item.get('dimensions'):
                    img_info += f"Dimensions: {item['dimensions'][0]}x{item['dimensions'][1]}\n"
                if item.get('image_type'):
                    img_info += f"Type: {item['image_type']}\n"
                if item.get('source_page'):
                    img_info += f"Source Page: {item['source_page']}\n"
                txt_output += img_info + "-"*30 + "\n"
        txt_output += "="*60 + "\n"
    else:
        txt_output += _get_link_analysis_text(stats)
        txt_output += _generate_sitemap_text(data)
        
        image_data = [item for item in data if item.get('type') == 'image']
        if image_data:
            txt_output += _generate_image_report_text_enhanced(image_data)

        txt_output += "\n" + "="*60 + "\nRAW PAGE DATA (URLs and Titles)\n" + "="*60 + "\n"
        for page in data:
            if page.get('type') != 'image':
                txt_output += f"URL: {page['url']}\n"
                txt_output += f"Title: {page['title']}\n"
                if page.get('load_time_ms'):
                    txt_output += f"Load Time: {page['load_time_ms']:.2f}ms\n"
                txt_output += "-"*30 + "\n"
    return txt_output


def _generate_image_report_text_enhanced(image_data):
    """Enhanced image report with detailed metadata"""
    if not image_data:
        return "\n" + "="*60 + "\nIMAGE SCRAPING RESULTS\n" + "="*60 + "\nNo images found.\n" + "="*60 + "\n"
    
    image_text = "\n" + "="*60 + "\nIMAGE SCRAPING RESULTS\n" + "="*60 + "\n"
    image_text += f"Total Images Found: {len(image_data)}\n\n"
    
    by_source = defaultdict(list)
    by_type = defaultdict(int)
    by_dimensions = defaultdict(int)
    
    for item in image_data:
        by_source[item.get('source_page', 'Unknown')].append(item)
        img_type = item.get('image_type', 'unknown')
        by_type[img_type] += 1
        
        if item.get('dimensions'):
            dim_key = f"{item['dimensions'][0]}x{item['dimensions'][1]}"
            by_dimensions[dim_key] += 1
    
    image_text += "Images by Type:\n"
    for img_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        image_text += f"  • {img_type}: {count}\n"
    
    if by_dimensions:
        image_text += "\nImages by Dimensions:\n"
        for dims, count in sorted(by_dimensions.items(), key=lambda x: x[1], reverse=True):
            image_text += f"  • {dims}: {count}\n"
    
    image_text += "\nDetailed Image List by Source Page:\n"
    image_text += "-"*60 + "\n"
    for source_page, img_list in sorted(by_source.items()):
        image_text += f"\nSource Page: {source_page}\n"
        image_text += f"Images Found: {len(img_list)}\n"
        for i, img in enumerate(img_list, 1):
            image_text += f"\n  {i}. URL: {img['url']}\n"
            if img.get('alt_text'):
                image_text += f"     Alt: {img['alt_text']}\n"
            if img.get('dimensions'):
                image_text += f"     Size: {img['dimensions'][0]}x{img['dimensions'][1]}px\n"
            image_text += f"     Type: {img.get('image_type', 'unknown')}\n"
        image_text += "\n"
    
    image_text += "="*60 + "\n"
    return image_text


def parse_crawl_command(command_string, default_params):
    parts = command_string.split(' ')
    if len(parts) < 2 or not parts[1].startswith('http'):
        return None, "Usage: `/crawl <url> [options]`"

    url = parts[1]
    params = default_params.copy()
    
    for part in parts[2:]:
        if ':' in part:
            key, value = part.split(':', 1)
            key = key.lower()
            
            if key == "site_only":
                params['site_only'] = value.lower() in ['yes', 'true', '1']
            elif key == "pages":
                try: params['pages'] = min(int(value), HOST_LIMITS["max_pages"])
                except ValueError: return None, "Invalid page count."
            elif key == "depth":
                try: params['depth'] = min(int(value), HOST_LIMITS["max_depth"])
                except ValueError: return None, "Invalid depth."
            elif key == "filter":
                params['filter'] = value if value.upper() != 'N/A' else None
            elif key == "include_pattern":
                params['include_pattern'] = value if value.upper() != 'N/A' else None
            elif key == "exclude_pattern":
                params['exclude_pattern'] = value if value.upper() != 'N/A' else None
            elif key == "file_type":
                params['file_type'] = value if value.upper() != 'N/A' else None
            elif key == "image_only":
                params['image_only'] = value.lower() in ['yes', 'true', '1']
                
    return url, params
            # Simply the help message for the discord bot, no steal plz
async def discord_crawl_help(message, limits):
    help_message = (
        "**Web Crawler Command Help**\n"
        "---"
        "\n**1. Command Syntax:**\n"
        f"`/crawl <URL> [OPTIONS]`\n"
        "\n**2. Example Usages:**\n"
        "`/crawl https://amazon.com` (Uses all default limits)\n"
        "`/crawl https://blooket.com pages:100 depth:5 filter:test`\n"
        "`/crawl https://site.com site_only:no exclude_pattern:.*pdf$`\n"
        "`/crawl https://example.com image_only:yes` (Image scraping mode)"
        "\n**3. Current System Limits (for Discord Host):**\n"
        f" • Max Run Time: **{limits['timeout_seconds']} seconds**\n"
        f" • Max Pages: **{limits['max_pages']}**\n"
        f" • Max Depth: **{limits['max_depth']}**"
        "\n**4. Optional Parameters (Use `key:value`):**\n"
        f" • `site_only:yes/no` (Default: `yes`). If `no`, crawl outside the starting domain.\n"
        f" • `pages:<num>` (Max: {limits['max_pages']}). Sets the maximum number of pages to scrape.\n"
        f" • `depth:<num>` (Max: {limits['max_depth']}). Sets the maximum link depth to follow.\n"
        f" • `filter:<text>`: Only scrapes pages containing this text in the body content.\n"
        f" • `include_pattern:<regex>`: Only crawls URLs matching this Python regex pattern. Use `N/A` or skip for none.\n"
        f" • `exclude_pattern:<regex>`: Skips URLs matching this Python regex pattern. Use `N/A` or skip for none.\n"
        f" • `file_type:<ext,ext>`: Only crawls URLs ending with these file extensions (e.g., `html,php`). Use `N/A` or skip for none.\n"
        f" • `image_only:yes/no` (Default: `no`). If `yes`, only collect image URLs instead of page content."
    )
    
    embed = discord.Embed(
        title="Command Syntax and Limits",
        description=help_message,
        color=discord.Color.blue()
    )
    await message.channel.send(embed=embed)


def run_discord_host(token):
    if not DISCORD_LIB_AVAILABLE:
        print("Error: 'discord.py' is not installed. Run 'pip install discord.py'")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    crawling_state = {"active": False}

    @client.event
    async def on_ready():
        print(f'\n[HOST] Logged in as {client.user}')
        print(f'[HOST] Listening for commands. Send `/crawl <url> [options]` or `/crawl help` in Discord.')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith('/crawl'):
            
            if message.content.strip().lower() == '/crawl help':
                await discord_crawl_help(message, HOST_LIMITS)
                return
            
            if crawling_state["active"]:
                await message.channel.send("A crawl is already in progress. Please wait.")
                return

            url, params = parse_crawl_command(message.content, DEFAULT_PARAMS)
            
            if url is None:
                await message.channel.send(params)
                return

            crawling_state["active"] = True
            
            mode_text = "**Image Scraping Mode**" if params['image_only'] else "**Content Scraping Mode**"
            limits_text = (
                f"{mode_text}\n"
                f"**Target:** `{url}`\n"
                f"**Limits:** Max **{params['pages']} Pages** | Max **{params['depth']} Depth** | Max **{HOST_LIMITS['timeout_seconds']}s**\n"
                f"**On-Site Only:** `{params['site_only']}`\n"
                f"**Content Filter:** `{params['filter'] or 'None'}`"
            )
            await message.channel.send(f"**Starting Crawl**\n{limits_text}")
            
            parent_pid = os.getpid()
            temp_filename = f"results_{parent_pid}.dat"
            
            data = []
            stats = {}
            error = None
            
            try:
                with multiprocessing.Manager() as manager:
                    manager_dict = manager.dict()
                    
                    p = multiprocessing.Process(target=run_crawler_process, args=(
                        [url], params['site_only'], params['depth'], params['pages'], 
                        params['filter'], params['include_pattern'], params['exclude_pattern'], 
                        params['file_type'], params['image_only'], None, manager_dict, parent_pid
                    ))
                    p.start()
                    
                    p.join(timeout=HOST_LIMITS["timeout_seconds"] + 5) 

                    if p.is_alive():
                        p.terminate()
                        p.join()
                        await message.channel.send("**Crawl terminated!** The crawl hit the **time limit**.")
                    
                    error = manager_dict.get("error")
                    final_temp_file = manager_dict.get("temp_file")
                        
            except Exception as e:
                await message.channel.send(f"**Multiprocessing Error!** Failed during setup/teardown: `{e}`")
                error = f"Setup/Teardown failed: {e}"
            
            
            if error:
                await message.channel.send(f"Crawl process encountered a critical error: `{error}`")
                crawling_state["active"] = False
                return
            
            if os.path.exists(temp_filename):
                
                try:
                    with open(temp_filename, "rb") as f:
                        compressed = f.read()
                    
                    decompressed = zlib.decompress(compressed)
                    final_package = json.loads(decompressed.decode("utf-8"))
                    
                    data = final_package.get("data", [])
                    stats = final_package.get("stats", {})
                    
                except Exception as e:
                    await message.channel.send(f"**File Read Error!** Failed to read and parse the temporary data file: `{e}`")
                    crawling_state["active"] = False
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                    return
                
                crawled_count = stats.get('pages_crawled', 0)
                collected_count = len(data)

                if collected_count == 0 and crawled_count > 0:
                     await message.channel.send(f"Crawl finished. Pages Found: **{crawled_count}**, Pages Collected: **{collected_count}**. No pages matched filters/were collected.")
                elif collected_count == 0:
                     await message.channel.send("Crawl completed but returned no data. Check URL, filters, or access.")
                else:
                    try:
                        txt_output = generate_full_report_text(url, data, stats, params['image_only'])
                        
                        embed = discord.Embed(title="Crawl Finished", color=0x00ff00)
                        embed.add_field(name="Pages Scraped", value=str(crawled_count), inline=True)
                        embed.add_field(name="Errors/Broken Links", value=str(stats.get('errors', 0)), inline=True)
                        if params['image_only']:
                            embed.add_field(name="Images Found", value=str(stats.get('images_found', 0)), inline=True)
                        else:
                            embed.add_field(name="Total Pages Collected", value=f"{collected_count} items", inline=True)
                        
                        file_bin = BytesIO(txt_output.encode('utf-8'))
                        discord_file = discord.File(fp=file_bin, filename="results.txt")
                        
                        await message.channel.send(embed=embed, file=discord_file)
                        
                    except Exception as e:
                        await message.channel.send(f"Error processing final results: `{e}`")

                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            else:
                await message.channel.send("**File Missing!** Crawl finished, but the temporary data file was not created or found.")

            crawling_state["active"] = False

    try:
        client.run(token)
    except Exception as e:
        print(f"\n[ERROR] Bot failed to login: {e}")
        print("Ensure the Bot Token is correct and the Message Content Intent is enabled in the Developer Portal.")


def show_statistics():
    print(_get_stats_text(crawl_stats))

def show_link_analysis():
    print(_get_link_analysis_text(crawl_stats))

def generate_sitemap():
    global collected_data
    print(_generate_sitemap_text(collected_data))


def export_data(to_file=False, filename="exported_data.dat"):
    if not collected_data:
        print("No data to export.")
        return
    export_package = {
        "data": collected_data,
        "stats": {
            "pages_crawled": crawl_stats["pages_crawled"],
            "errors": crawl_stats["errors"],
            "content_types": dict(crawl_stats["content_types"]),
            "total_pages": len(collected_data),
            "images_found": crawl_stats["images_found"]
        }
    }
    raw = json.dumps(export_package).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    encoded = base64.b64encode(compressed).decode("utf-8")
    if to_file:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(encoded)
        print(f"\nExported {len(collected_data)} entries to '{filename}' ({len(encoded)} chars).")
    else:
        print("\nExported data string (also copied to clipboard):\n")
        print(encoded[:200] + "..." if len(encoded) > 200 else encoded)
        print(f"\nData size: {len(encoded)} chars for {len(collected_data)} links.")
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(encoded)
            except Exception as e:
                print(f"Couldn't copy to clipboard: {e}")
        else:
            print("Clipboard copy unavailable.")

def export_urls_to_file(filename="links.txt"):
    if not collected_data:
        print("No data collected to export.")
        return

    urls = [page.get("url", "") for page in collected_data if page.get("url")]
    url_list_text = "\n".join(urls)
    
    if not url_list_text:
        print("No URLs found in collected data.")
        return

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(url_list_text)
        print(f"Successfully wrote {len(urls)} URLs to '{filename}'.")
    except Exception as e:
        print(f"Error writing to file '{filename}': {e}")

def export_images_to_file(filename="images.txt"):
    if not collected_data:
        print("No data collected to export.")
        return

    images = []
    for item in collected_data:
        if item.get('type') == 'image':
            images.append(item.get('url', ''))
        elif 'images' in item:
            images.extend(item.get('images', []))
    
    if not images:
        print("No images found in collected data.")
        return

    image_list_text = "\n".join(images)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(image_list_text)
        print(f"Successfully wrote {len(images)} image URLs to '{filename}'.")
    except Exception as e:
        print(f"Error writing to file '{filename}': {e}")


def export_images_with_metadata(filename="images_metadata.json"):
    if not collected_data:
        print("No data collected to export.")
        return

    images_with_metadata = []
    for item in collected_data:
        if item.get('type') == 'image':
            img_entry = {
                "url": item.get('url', ''),
                "source_page": item.get('source_page', ''),
                "alt_text": item.get('alt_text'),
                "dimensions": item.get('dimensions'),
                "image_type": item.get('image_type', 'unknown'),
                "depth": item.get('depth', 0)
            }
            images_with_metadata.append(img_entry)
    
    if not images_with_metadata:
        print("No images found in collected data.")
        return

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(images_with_metadata, f, indent=2, ensure_ascii=False)
        print(f"Successfully wrote {len(images_with_metadata)} images with metadata to '{filename}'.")
    except Exception as e:
        print(f"Error writing to file '{filename}': {e}")

def import_data(data_string):
    try:
        decoded = base64.b64decode(data_string.encode("utf-8"))
        decompressed = zlib.decompress(decoded)
        imported = json.loads(decompressed.decode("utf-8"))
        if isinstance(imported, dict) and "data" in imported:
            collected_data.clear()
            collected_data.extend(imported["data"])
            
            global crawl_stats
            imported_stats = imported.get("stats", {})
            crawl_stats["pages_crawled"] = imported_stats.get("pages_crawled", len(collected_data))
            crawl_stats["errors"] = imported_stats.get("errors", 0)
            crawl_stats["content_types"] = Counter(imported_stats.get("content_types", {}))
            crawl_stats["images_found"] = imported_stats.get("images_found", 0)
            crawl_stats["start_time"] = datetime.now() 
            
            print(f"Imported {len(collected_data)} entries with metadata.")
        else:
            collected_data.clear()
            collected_data.extend(imported)
            print(f"Imported {len(collected_data)} entries (legacy format).")
    except Exception as e:
        print(f"Failed to import data: {e}")

def import_file(filename):
    if not os.path.exists(filename):
        print("File not found.")
        return
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data_str = f.read().strip()
        import_data(data_str)
    except Exception as e:
        print(f"Failed to import from file: {e}")

def search_data(query):
    query_lower = query.lower()
    scored_results = []
    for d in collected_data:
        score = 0
        if 'content' in d:
            content_lower = d["content"].lower()
            title_lower = d.get("title", "").lower()
            if query_lower in title_lower:
                score += 10
            score += content_lower.count(query_lower)
            for h1 in d.get("h1_tags", []):
                if query_lower in h1.lower():
                    score += 5
        elif d.get('type') == 'image':
            if query_lower in d.get('url', '').lower():
                score += 1
        if score > 0:
            scored_results.append((score, d))
    scored_results.sort(reverse=True, key=lambda x: x[0])
    if not scored_results:
        urls = [d["url"] for d in collected_data]
        close = get_close_matches(query, urls, n=5)
        if close:
            print("\nNo direct match, but maybe:")
            for c in close:
                print(f" → {c}")
        else:
            print("No matches found.")
    else:
        print(f"\nFound {len(scored_results)} results:\n")
        for i, (score, r) in enumerate(scored_results[:10], 1):
            if 'title' in r:
                title = r.get('title', 'No title')
                print(f"{i}. [{score} pts] {title}")
                print(f" {r['url']}\an")
            elif r.get('type') == 'image':
                print(f"{i}. [{score} pts] [IMAGE] {r['url']}")
                print(f" Source: {r.get('source_page', 'Unknown')}\n")
            else:
                print(f"{i}. [{score} pts] {r['url']}\n")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    print("="*60)
    print("SILKY     By Lil Skittle")
    print("""  / _ \\
\_\\(_)/_/
 _//o\\\\_ 
  /   \\""")
    print("="*60)
    
    mode = input("\nEnter mode (crawl / host / import / importfile): ").strip().lower()
    
    if mode == "host":
        print("\n--- HOST MODE (Discord Bot) ---")
        print("This requires a Discord Bot Token.")
        print(f"Limits: Max Pages={HOST_LIMITS['max_pages']}, Max Depth={HOST_LIMITS['max_depth']}, Timeout={HOST_LIMITS['timeout_seconds']}s")
        print("Command format: `/crawl <url> site_only:yes/no pages:500 depth:15 filter:text image_only:yes/no` (defaults apply if options are omitted). Use `/crawl help` for details.")
        token = input("Enter Discord Bot Token: ").strip()
        run_discord_host(token)
        
    elif mode == "import":
        data_str = input("\nPaste exported data string:\n").strip()
        import_data(data_str)
        while True:
            query = input("\nCommands: search, stats, links, sitemap, export, exportfile, exportlinks, exportimages, exportimagedata, exit\nEnter command or search query: ").strip()
            if query.lower() == "exit": sys.exit(0)
            elif query.lower() == "stats": show_statistics()
            elif query.lower() == "links": show_link_analysis()
            elif query.lower() == "sitemap": generate_sitemap()
            elif query.lower() == "export": export_data()
            elif query.lower() == "exportlinks": export_urls_to_file()
            elif query.lower() == "exportimages": export_images_to_file()
            elif query.lower() == "exportimagedata": export_images_with_metadata()
            elif query.lower() == "exportfile":
                fn = input("Enter filename: ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=fn)
            else: search_data(query)

    elif mode == "importfile":
        filename = input("Enter filename to import (e.g. exported_data.dat): ").strip()
        import_file(filename)
        while True:
            query = input("\nCommands: search, stats, links, sitemap, export, exportfile, exportlinks, exportimages, exportimagedata, exit\nEnter command or search query: ").strip()
            if query.lower() == "exit": sys.exit(0)
            elif query.lower() == "stats": show_statistics()
            elif query.lower() == "links": show_link_analysis()
            elif query.lower() == "sitemap": generate_sitemap()
            elif query.lower() == "export": export_data()
            elif query.lower() == "exportlinks": export_urls_to_file()
            elif query.lower() == "exportimages": export_images_to_file()
            elif query.lower() == "exportimagedata": export_images_with_metadata()
            elif query.lower() == "exportfile":
                fn = input("Enter filename: ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=fn)
            else: search_data(query)

    else:
        print("\n--- CRAWL MODE ---")
        urls_input = input("Enter starting URL(s) (comma-separated for multiple): ").strip()
        start_urls = [url.strip() for url in urls_input.split(',')]
        if not start_urls or not any(start_urls):
            print("No valid starting URLs provided. Exiting.")
            sys.exit(1)
        
        print("\n--- CRAWLER ENGINE SELECTION ---")
        if PLAYWRIGHT_AVAILABLE:
            engine = input("Choose crawler engine (scrapy/playwright) [scrapy]: ").strip().lower()
            if engine not in ['scrapy', 'playwright']:
                engine = 'scrapy'
        else:
            engine = 'scrapy'
            print("Playwright not installed. Using Scrapy (install with: pip install playwright)")
        
        network_logging_config = None
        page_timeout = 15000
        if engine == 'playwright':
            network_logging_config = NetworkLoggingConfig.from_user_input()
            
            print("\n--- PAGE TIMEOUT CONFIGURATION ---")
            print("Timeout for page load (in seconds). Lower = faster but may miss slow sites.")
            print("Recommended: 10-30 seconds. Fast sites: 5-10s, Slow sites: 20-30s")
            timeout_input = input("Page timeout in seconds [15]: ").strip()
            if timeout_input.isdigit():
                page_timeout = int(timeout_input) * 1000  # Convert to milliseconds
            else:
                page_timeout = 15000
        
        on_site = input(f"On Site Crawl only? (yes/no) [yes]: ").strip().lower()
        on_site_only = on_site in ['yes','y','true','1'] or not on_site
        
        max_depth_input = input("Max depth (0 for no limit) [0]: ").strip()
        max_depth = int(max_depth_input) if max_depth_input else 0
        max_pages_input = input("Max pages (0 for no limit) [0]: ").strip()
        max_pages = int(max_pages_input) if max_pages_input else 0
        
        threads_input = input("Number of threads [6]: ").strip()
        threads = int(threads_input) if threads_input.isdigit() else 6
        
        image_mode = input("Image scraping only? (yes/no) [no]: ").strip().lower()
        image_only = image_mode in ['yes','y','true','1']
        
        content_filter = input("Content filter (or leave blank): ").strip() or None
        url_include = input("URL include pattern (regex, or leave blank/N/A): ").strip() or None
        url_exclude = input("URL exclude pattern (regex, or leave blank/N/A): ").strip() or None
        file_types = input("File types to crawl (e.g., 'html,php,asp' or leave blank/N/A): ").strip() or None
        
        # As said, gotta make a new script for this
        print("\n--- COOKIE CONFIGURATION ---")
        print("Enter cookies to authenticate with the website (useful for sites requiring login).")
        print("Supported formats:")
        print("  1. name1=value1; name2=value2")
        print("  2. {\"name1\": \"value1\", \"name2\": \"value2\"}")
        print("  3. Leave blank to skip")
        cookie_input = input("Cookies (or leave blank): ").strip()
        cookies = parse_cookies(cookie_input) if cookie_input else None
        
        if cookies:
            print(f"Parsed {len(cookies)} cookie(s): {list(cookies.keys())}")
        
        use_discord = input("\nSend updates to Discord Webhook? (yes/no) [no]: ").strip().lower()
        if use_discord in ['yes','y','true','1']:
            discord_config["enabled"] = True
            discord_config["webhook_url"] = input("Enter Discord Webhook URL: ").strip()
            discord_config["mode"] = input("Choose mode (each/final/both) [final]: ").strip().lower() or "final"
            if discord_config["mode"] not in ["each","final","both"]:
                discord_config["mode"] = "final"
        
        logger = CrawlLogger()
        print(f"\n[LOGGING] Logs will be saved to: crawl_logs/")
        
        try:
            if engine == 'playwright':
                print("\n[BROWSER] Starting Playwright crawler (this may take a moment to initialize)...")
                crawler = PlaywrightCrawler(
                    logger=logger,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    on_site_only=on_site_only,
                    content_filter=content_filter,
                    url_include=url_include,
                    url_exclude=url_exclude,
                    image_only=image_only,
                    network_logging_config=network_logging_config,
                    page_timeout=page_timeout
                )
                result = crawler.run(start_urls)
                
                if result:
                    collected_data.extend(result["data"])
                    crawl_stats.update(result["stats"])
            
            else:
                run_local_crawler(start_urls, on_site_only, max_depth, max_pages, content_filter, 
                                url_include, url_exclude, file_types, image_only, cookies, threads)
        
        except KeyboardInterrupt:
            print("\n\n[STOP] Crawl interrupted by user (Ctrl+C). Showing partial results.")

        show_statistics()
        
        log_export_prompt = input("\nExport crawl logs? (yes/no) [yes]: ").strip().lower()
        if log_export_prompt in ['yes','y','true','1'] or not log_export_prompt:
            log_filename = input("Log filename [crawler_logs.json]: ").strip() or "crawler_logs.json"
            logger.export_logs(log_filename)
        
        while True:
            query = input("\nCommands: search, stats, links, sitemap, export, exportfile, exportlinks, exportimages, exportimagedata, exportlogs, exit\nEnter command or search query: ").strip()
            if query.lower() == "exit":
                sys.exit(0)
            elif query.lower() == "stats":
                show_statistics()
            elif query.lower() == "links":
                show_link_analysis()
            elif query.lower() == "sitemap":
                generate_sitemap()
            elif query.lower() == "export":
                export_data()
            elif query.lower() == "exportlinks":
                export_urls_to_file()
            elif query.lower() == "exportimages":
                export_images_to_file()
            elif query.lower() == "exportimagedata":
                export_images_with_metadata()
            elif query.lower() == "exportlogs":
                log_filename = input("Log filename [crawler_logs.json]: ").strip() or "crawler_logs.json"
                logger.export_logs(log_filename)
            elif query.lower() == "exportfile":
                filename = input("Enter filename to save (default: exported_data.dat): ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=filename)
            else:
                search_data(query)
                # Made by Lil Skittle, i am not responsible for any damage caused with this (:
                # Long Live Silky
