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
from collections import Counter, defaultdict, deque
from datetime import datetime
import multiprocessing
import time
from io import BytesIO
import logging
from logging.handlers import RotatingFileHandler
from enum import Enum
import heapq

# Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# --- CONFIGURATION ---
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
    
    def __init__(self, log_dir="crawl_logs", log_images=True, log_scripts=True, log_cookies=True):
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
            "cookies": [],
            "errors": [],
            "performance": [],
            "pages": []
        }
        
        self.log_images_enabled = log_images
        self.log_scripts_enabled = log_scripts
        self.log_cookies_enabled = log_cookies
        
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
    
    def _write_log(self, log_type, message, level=logging.INFO):
        """Write a log message to both the in-memory log and the file handler"""
        if log_type in self.handlers:
            logger = logging.getLogger(f"CrawlLogger.{log_type}")
            logger.setLevel(logging.DEBUG)
            if not logger.handlers:
                logger.addHandler(self.handlers[log_type])
            logger.log(level, message)
    
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
        message = f"{method} {endpoint} - Status: {status_code} ({response_time:.2f}ms)"
        self._write_log("api", message, LogLevel.API.value)
        print(f"[API] {message}")
    
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
        message = f"{method} {url} - Status: {status} ({size} bytes, {duration:.2f}ms)"
        self._write_log("network", message, LogLevel.NETWORK.value)
        print(f"[NETWORK] {message}")
    
    def log_image(self, url, source_page, dimensions=None, format_type=None, file_size=None, alt_text=None):
        if not self.log_images_enabled:
            return
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
        message = f"{url}{dim_str} from {source_page}"
        self._write_log("images", message)
        print(f"[IMAGE] {url}{dim_str}")
    
    def log_javascript(self, script_url, script_type, page_url, async_load=False, defer_load=False, content_size=None):
        if not self.log_scripts_enabled:
            return
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
            async_str = " [async]" if async_load else ""
            defer_str = " [defer]" if defer_load else ""
            message = f"External: {script_url}{async_str}{defer_str} from {page_url}"
            self._write_log("javascript", message)
            print(f"[SCRIPT] {script_url}{async_str}{defer_str}")
        else:
            size_str = f" ({content_size} bytes)" if content_size else ""
            message = f"Inline: {page_url}{size_str}"
            self._write_log("javascript", message)
            print(f"[INLINE-SCRIPT] {page_url}{size_str}")
    
    def log_error(self, error_type, url, message, traceback_info=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "url": url,
            "message": message,
            "traceback": traceback_info
        }
        self.logs["errors"].append(entry)
        log_message = f"{error_type} on {url}: {message}"
        self._write_log("errors", log_message, logging.ERROR)
        print(f"[ERROR] {log_message}")
    
    def log_performance(self, metric_name, value, unit="ms"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "metric": metric_name,
            "value": value,
            "unit": unit
        }
        self.logs["performance"].append(entry)
        message = f"{metric_name}: {value} {unit}"
        self._write_log("performance", message)
        print(f"[PERF] {message}")

    def log_cookies(self, url, cookies):
        if not self.log_cookies_enabled:
            return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "page_url": url,
            "cookies": cookies
        }
        self.logs["cookies"].append(entry)
        message = f"Found {len(cookies)} cookies on {url}: {[c.get('name', 'unknown') for c in cookies]}"
        self._write_log("cookies", message)
        print(f"[COOKIES] Found {len(cookies)} cookies on {url}")

    def log_page_visit(self, url, title=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "title": title
        }
        self.logs["pages"].append(entry)
        message = f"Visited: {url} - Title: {title or 'No title'}"
        self._write_log("pages", message)
    
    def export_logs(self, filename="crawler_logs.json"):
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "logs": self.logs,
            "summary": {
                "total_api_calls": len(self.logs["api"]),
                "total_network_events": len(self.logs["network"]),
                "total_images": len(self.logs["images"]),
                "total_js_logs": len(self.logs["javascript"]),
                "total_cookie_logs": len(self.logs["cookies"]),
                "total_errors": len(self.logs["errors"]),
                "performance_metrics": len(self.logs["performance"]),
                "total_webpages_visited": len(self.logs["pages"])
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"Logs exported to {filename}")
            
            self.close_handlers()
            
            return filename
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return None
    
    def close_handlers(self):
        """Close all file handlers to ensure logs are flushed to disk"""
        for log_type, handler in self.handlers.items():
            handler.flush()
            handler.close()
    
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
    "image_only": False,
    "proxy": None
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
    "images_found": 0,
    "path_map": defaultdict(list)
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


class JSRunner:
    """
    Framework for running custom JavaScript on every crawled page.
    Provides access to Silky's logger, stats, and crawler state.
    """
    
    def __init__(self, script=None, script_file=None, on_page_load=None, on_data_found=None):
        """
        Initialize JS Runner with script or callback functions.
        
        Args:
            script: JavaScript code as string
            script_file: Path to .js file to load
            on_page_load: Python callback function(url, page, context) -> None
            on_data_found: Python callback function(url, data, context) -> None
        """
        self.script = script
        self.script_file = script_file
        self.on_page_load = on_page_load
        self.on_data_found = on_data_found
        self.results = []
        
        if script_file and not script:
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    self.script = f.read()
            except Exception as e:
                print(f"[JS RUNNER] Failed to load script file: {e}")
    
    def build_context(self, crawler, url, page):
        """
        Build the context object that JS can interact with.
        Provides access to Silky's internals.
        """
        return {
            'url': url,
            'title': page.title() if page else '',
            
            'pages_crawled': crawler.stats.get('pages_crawled', 0),
            'errors': crawler.stats.get('errors', 0),
            'images_found': crawler.stats.get('images_found', 0),
            
            'visited': list(crawler.visited),
            'visited_count': len(crawler.visited),
            
            'collected_count': len(crawler.collected_data),
            
            'can_log': True,
        }
    
    def inject_silky_api(self, page, context):
        """
        Inject Silky API into page's window object so JS can interact with crawler.
        """
        api_script = f"""
        window.Silky = {{
            context: {json.dumps(context)},
            
            results: [],
            
            log: function(message) {{
                console.log('[SILKY]', message);
                this.results.push({{
                    type: 'log',
                    message: message,
                    timestamp: new Date().toISOString()
                }});
            }},
            
            warn: function(message) {{
                console.warn('[SILKY]', message);
                this.results.push({{
                    type: 'warn',
                    message: message,
                    timestamp: new Date().toISOString()
                }});
            }},
            
            error: function(message) {{
                console.error('[SILKY]', message);
                this.results.push({{
                    type: 'error',
                    message: message,
                    timestamp: new Date().toISOString()
                }});
            }},
            
            collect: function(data) {{
                this.results.push({{
                    type: 'data',
                    data: data,
                    timestamp: new Date().toISOString()
                }});
            }},
            
            countElements: function(selector) {{
                return document.querySelectorAll(selector).length;
            }},
            
            extractText: function(selector) {{
                const elements = document.querySelectorAll(selector);
                return Array.from(elements).map(el => el.textContent.trim());
            }},
            
            extractAttributes: function(selector, attribute) {{
                const elements = document.querySelectorAll(selector);
                return Array.from(elements).map(el => el.getAttribute(attribute));
            }},
            
            extractLinks: function(selector = 'a[href]') {{
                const links = document.querySelectorAll(selector);
                return Array.from(links).map(a => a.href);
            }},
            
            waitForElement: function(selector, timeout = 5000) {{
                return new Promise((resolve, reject) => {{
                    const element = document.querySelector(selector);
                    if (element) {{
                        resolve(element);
                        return;
                    }}
                    
                    const observer = new MutationObserver(() => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            observer.disconnect();
                            resolve(element);
                        }}
                    }});
                    
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true
                    }});
                    
                    setTimeout(() => {{
                        observer.disconnect();
                        reject(new Error('Element not found: ' + selector));
                    }}, timeout);
                }});
            }},
            
            exists: function(selector) {{
                return document.querySelector(selector) !== null;
            }},
            
            getMeta: function() {{
                const meta = {{}};
                document.querySelectorAll('meta').forEach(m => {{
                    const name = m.getAttribute('name') || m.getAttribute('property');
                    const content = m.getAttribute('content');
                    if (name && content) meta[name] = content;
                }});
                return meta;
            }},
            
            stopCrawl: function(reason) {{
                this.results.push({{
                    type: 'stop',
                    reason: reason,
                    timestamp: new Date().toISOString()
                }});
            }},
            
            skipUrl: function(url, reason) {{
                this.results.push({{
                    type: 'skip',
                    url: url,
                    reason: reason,
                    timestamp: new Date().toISOString()
                }});
            }}
        }};
        """
        
        try:
            page.evaluate(api_script)
            return True
        except Exception as e:
            print(f"[JS RUNNER] Failed to inject Silky API: {e}")
            return False
    
    def execute(self, page, crawler, url):
        """
        Execute the JS Runner script on the current page.
        """
        if not self.script and not self.on_page_load:
            return None
        
        try:
            context = self.build_context(crawler, url, page)
            
            if not self.inject_silky_api(page, context):
                return None
            
            if self.script:
                result = page.evaluate(self.script)
            else:
                result = None
            
            if self.on_page_load:
                try:
                    self.on_page_load(url, page, context)
                except Exception as e:
                    print(f"[JS RUNNER] on_page_load callback error: {e}")
            
            silky_results = page.evaluate("window.Silky.results")
            
            for item in silky_results:
                item['url'] = url
                self.results.append(item)
                
                if item['type'] == 'log':
                    print(f"[JS→SILKY] {item['message']}")
                elif item['type'] == 'error':
                    print(f"[JS→ERROR] {item['message']}")
                    crawler.logger.log_error("JSRunner", url, item['message'])
                elif item['type'] == 'data':
                    if self.on_data_found:
                        try:
                            self.on_data_found(url, item['data'], context)
                        except Exception as e:
                            print(f"[JS RUNNER] on_data_found callback error: {e}")
                elif item['type'] == 'stop':
                    print(f"[JS→STOP] {item['reason']}")
                    crawler.stop_on_reached = True
            
            return {
                'script_result': result,
                'silky_results': silky_results,
                'url': url
            }
            
        except Exception as e:
            print(f"[JS RUNNER] Execution error on {url}: {e}")
            crawler.logger.log_error("JSRunner", url, str(e))
            return None


class PlaywrightCrawler:
    def __init__(self, logger=None, max_depth=0, max_pages=0, on_site_only=False,
                 content_filter=None, url_include=None, url_exclude=None, image_only=False,
                 network_logging_config=None, page_timeout=15000, proxy=None, cookies=None,
                 log_images=True, log_scripts=True, log_cookies=True, global_crawl_stats=None,
                 force_domain=None, stop_on_url=None, js_runner=None):
        self.logger = logger or CrawlLogger(log_images=log_images, log_scripts=log_scripts, log_cookies=log_cookies)
        self.logger.log_images_enabled = log_images
        self.logger.log_scripts_enabled = log_scripts
        self.logger.log_cookies_enabled = log_cookies
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.on_site_only = on_site_only
        self.content_filter = content_filter
        self.url_include = re.compile(url_include) if url_include and url_include.upper() != 'N/A' else None
        self.url_exclude = re.compile(url_exclude) if url_exclude and url_exclude.upper() != 'N/A' else None
        self.image_only = image_only
        self.network_logging_config = network_logging_config or NetworkLoggingConfig(enabled=False)
        self.page_timeout = page_timeout  # in milliseconds!!!!
        self.proxy = proxy
        self.initial_cookies = cookies or {}
        
        self.force_domain = force_domain 
        self.force_domain_parsed = None
        if self.force_domain:
            self.force_domain_parsed = self._parse_force_domain(force_domain)
        
        self.stop_on_url = stop_on_url
        self.stop_on_reached = False
        self.stop_on_smart = stop_on_url is not None 
        
        self.link_queue = []
        
        self.js_runner = js_runner  
        self.js_runner_enabled = js_runner is not None
        self.js_runner_results = []  
        
        self.visited = set()
        self.collected_data = []
        self.start_url = None
        self.allowed_domains = []
        
        if global_crawl_stats:
            self.stats = global_crawl_stats
            if "start_time" not in self.stats or self.stats["start_time"] is None:
                self.stats["start_time"] = datetime.now()
            if "images" not in self.stats:
                self.stats["images"] = []
            if "javascript" not in self.stats:
                self.stats["javascript"] = {
                    "external_scripts": [],
                    "inline_scripts": [],
                    "total_external": 0,
                    "total_inline": 0
                }
            if "network_requests" not in self.stats:
                self.stats["network_requests"] = []
            if "api_calls" not in self.stats:
                self.stats["api_calls"] = []
            if "content_types" not in self.stats:
                self.stats["content_types"] = Counter()
            if "link_map" not in self.stats:
                self.stats["link_map"] = defaultdict(list)
            if "inbound_links" not in self.stats:
                self.stats["inbound_links"] = Counter()
            if "broken_links" not in self.stats:
                self.stats["broken_links"] = []
            if "path_map" not in self.stats:
                self.stats["path_map"] = defaultdict(list)
        else:
            self.stats = {
                "pages_crawled": 0,
                "images_found": 0,
                "errors": 0,
                "skipped": 0,
                "start_time": datetime.now(),
                "network_requests": [],
                "api_calls": [],
                "images": [],
                "content_types": Counter(),
                "link_map": defaultdict(list),
                "inbound_links": Counter(),
                "broken_links": [],
                "path_map": defaultdict(list),
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
        
        if self.force_domain_parsed and not self._matches_force_domain(url):
            self.stats["skipped"] += 1
            return False
        
        return True
    
    def _parse_force_domain(self, pattern):
        """
        Parse force_domain pattern to extract constraints.
        Examples:
          - "https://test.example.com/guide/*" -> stay on test.example.com under /guide/
          - "https://example.com/*" -> stay on example.com
          - "https://*.example.com/*" -> stay on any subdomain of example.com
        """
        parsed = urlparse(pattern)
        
        scheme = parsed.scheme if parsed.scheme else 'https'
        netloc = parsed.netloc
        path_pattern = parsed.path
        
        if '*' in netloc:
            netloc_regex = netloc.replace('.', r'\.').replace('*', r'[^.]+')
            netloc_regex = f'^{netloc_regex}$'
        else:
            netloc_regex = None
        
        if '*' in path_pattern:
            path_regex = path_pattern.replace('*', '.*')
            path_regex = f'^{path_regex}$'
        else:
            path_regex = None
        
        return {
            'scheme': scheme,
            'netloc': netloc,
            'netloc_regex': netloc_regex,
            'path_pattern': path_pattern,
            'path_regex': path_regex
        }
    
    def _matches_force_domain(self, url):
        """Check if URL matches the force_domain pattern."""
        if not self.force_domain_parsed:
            return True
        
        parsed_url = urlparse(url)
        config = self.force_domain_parsed
        
        if config['scheme'] and parsed_url.scheme != config['scheme']:
            return False
        
        if config['netloc_regex']:
            if not re.match(config['netloc_regex'], parsed_url.netloc):
                return False
        else:
            if parsed_url.netloc != config['netloc']:
                return False
        
        if config['path_regex']:
            if not re.match(config['path_regex'], parsed_url.path):
                return False
        elif config['path_pattern'] and config['path_pattern'] != '/' and config['path_pattern'] != '/*':
            if not parsed_url.path.startswith(config['path_pattern'].rstrip('*')):
                return False
        
        return True
    
    def _calculate_link_score(self, link_url, current_url):
        """
        Calculate priority score for a link when stop_on_url is set.
        Higher scores = higher priority = crawled first.
        
        Scoring rules (ported from scraper.py smart scoring):
        +100: Link URL contains stop_on_url text
        +50:  Link is on same domain as stop_on_url
        +5:   Link stays on current domain
        -10:  Link is to irrelevant pages (about, terms, privacy, etc.)
        """
        if not self.stop_on_url:
            return 0
        
        score = 0
        link_url_lower = link_url.lower()
        stop_on_url_lower = self.stop_on_url.lower()
        
        if link_url == self.stop_on_url:
            return 1000
        
        if stop_on_url_lower in link_url_lower:
            score += 100
        
        try:
            stop_on_domain = urlparse(self.stop_on_url).netloc
            link_domain = urlparse(link_url).netloc
            
            if stop_on_domain and link_domain == stop_on_domain:
                score += 50
        except:
            pass
        
        try:
            current_domain = urlparse(current_url).netloc
            link_domain = urlparse(link_url).netloc
            
            if current_domain and link_domain == current_domain:
                score += 5
        except:
            pass
        
        irrelevant_keywords = [
            "about", "terms", "privacy", "policy", "cookie", 
            "legal", "disclaimer", "contact", "sitemap", "help"
        ]
        
        if any(keyword in link_url_lower for keyword in irrelevant_keywords):
            score -= 10
        
        return score
    
    def extract_images_from_page(self, page: Page, url: str):
        img_list = []

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

                img_list.append({
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
                const bgImages = [];
                try {
                    document.querySelectorAll('*').forEach(el => {
                        try {
                            const style = window.getComputedStyle(el);
                            const bgImage = style.backgroundImage;
                            if (bgImage && bgImage !== 'none') {
                                const match = bgImage.match(/url\(["\']?([^"\')]+)["\']?\)/);
                                if (match && match[1]) {
                                    bgImages.push(match[1]);
                                }
                            }
                        } catch (e) {
                            // Skip elements that fail
                        }
                    });
                } catch (e) {
                    // Return whatever we found so far
                }
                return bgImages;
            }""")

            for img_url in css_images:
                img_url = urljoin(url, img_url)
                img_list.append({
                    "url": img_url,
                    "type": "css_background",
                    "alt": None,
                    "dimensions": None
                })
                self.logger.log_image(img_url, url, format_type="css_background")

        except Exception as e:
            self.logger.log_error("CSSImageExtraction", url, str(e))

        self.stats["images_found"] += len(img_list)
        
        if "images" not in self.stats:
            self.stats["images"] = []
        self.stats["images"].extend(img_list)
        
        return img_list
    
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

            if not isinstance(script_data, list):
                script_data = []

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
            
            if "javascript" not in self.stats:
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
    
    def crawl_page(self, page: Page, url: str, depth: int = 0, path: list = None):
        if self.stop_on_url and url == self.stop_on_url:
            self.stop_on_reached = True
            print(f"[STOP-ON] Reached target URL: {url}")
            self.logger.log_performance(f"Reached stop-on URL: {url}", 0, "event")
        
        if self.stop_on_reached and url != self.stop_on_url:
            print(f"[STOP-ON] Skipping {url} - stop URL already reached")
            return
        
        if url in self.visited or (self.max_pages > 0 and self.stats["pages_crawled"] >= self.max_pages):
            return

        if self.max_depth > 0 and depth >= self.max_depth:
            self.stats["skipped"] += 1
            return

        if not self.should_crawl_url(url):
            return
        
        if path is None:
            path = [url]
        
        self.stats["path_map"][url] = path

        try:
            if self.initial_cookies:
                for name, value in self.initial_cookies.items():
                    try:
                        page.context.add_cookies([{
                            "name": name,
                            "value": value,
                            "url": url
                        }])
                    except Exception as e:
                        self.logger.log_error("CookieSetting", url, f"Failed to set cookie {name}: {str(e)}")

            initial_cookies = {}
            try:
                initial_cookies_list = page.context.cookies()
                initial_cookies = {cookie['name']: cookie for cookie in initial_cookies_list}
            except Exception as e:
                self.logger.log_error("InitialCookieExtraction", url, str(e))

            start_time = time.time()
            response = page.goto(url, wait_until='load', timeout=self.page_timeout)
            load_time = (time.time() - start_time) * 1000

            self.visited.add(url)
            self.stats["pages_crawled"] += 1
            
            if response:
                try:
                    content_type = response.headers.get('content-type', 'unknown')
                    content_type = content_type.split(';')[0].strip()
                    self.stats["content_types"][content_type] += 1
                except Exception as e:
                    self.stats["content_types"]["unknown"] += 1
            else:
                self.stats["content_types"]["unknown"] += 1

            try:
                final_cookies_list = page.context.cookies()
                final_cookies = {cookie['name']: cookie for cookie in final_cookies_list}

                new_cookies = []
                for name, cookie in final_cookies.items():
                    if name not in initial_cookies:
                        new_cookies.append(cookie)
                    elif initial_cookies[name]['value'] != cookie['value']:
                        new_cookies.append(cookie)

                if new_cookies and self.logger.log_cookies_enabled:
                    self.logger.log_cookies(url, new_cookies)
            except Exception as e:
                self.logger.log_error("CookieExtraction", url, str(e))

            title = page.title() or ""
            self.logger.log_page_visit(url, title=title)

            self.logger.log_performance(f"Page Load - {url}", load_time, "ms")
            
            js_runner_result = None
            if self.js_runner_enabled and self.js_runner:
                try:
                    if isinstance(self.js_runner, JSRunner):
                        js_runner_result = self.js_runner.execute(page, self, url)
                    elif isinstance(self.js_runner, str):
                        temp_runner = JSRunner(script=self.js_runner)
                        js_runner_result = temp_runner.execute(page, self, url)
                        self.js_runner_results.extend(temp_runner.results)
                    
                    if js_runner_result:
                        self.js_runner_results.append(js_runner_result)
                        print(f"[JS RUNNER] Executed on {url} - {len(js_runner_result.get('silky_results', []))} results")
                        
                except Exception as e:
                    self.logger.log_error("JSRunnerExecution", url, str(e))
                    print(f"[JS RUNNER ERROR] {url}: {e}")
            
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

                if self.logger.log_images_enabled:
                    print(f"[IMAGES] {len(images)} images | Depth: {depth} | {url}")

            else:
                try:
                    text_content = page.evaluate("() => document.body.innerText") or ""
                except Exception as e:
                    self.logger.log_error("TextContentExtraction", url, str(e))
                    text_content = ""

                if self.content_filter and self.content_filter.upper() != 'N/A':
                    if self.content_filter.lower() not in text_content.lower():
                        self.stats["skipped"] += 1
                        return

                try:
                    h1_tags = page.evaluate("() => Array.from(document.querySelectorAll('h1')).map(el => el.textContent)")
                except Exception as e:
                    self.logger.log_error("H1TagsExtraction", url, str(e))
                    h1_tags = []

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

                if self.logger.log_images_enabled:
                    self.extract_images_from_page(page, url)

                if self.logger.log_scripts_enabled:
                    self.extract_javascript_from_page(page, url)

            try:
                links = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter((href, index, self) => self.indexOf(href) === index);
                }""")
            except Exception as e:
                self.logger.log_error("LinksExtraction", url, str(e))
                links = []

            outgoing_links = []
            
            if self.stop_on_smart and not self.stop_on_reached:
                scored_links = []
                
                for link_url in links or []:
                    link_url = urljoin(url, link_url)
                    outgoing_links.append(link_url)
                    self.stats["inbound_links"][link_url] += 1
                    
                    if link_url not in self.visited and self.should_crawl_url(link_url):
                        if self.max_depth == 0 or depth + 1 < self.max_depth:
                            score = self._calculate_link_score(link_url, url)
                            new_path = path + [link_url]
                            scored_links.append((score, link_url, depth + 1, new_path))
                
                scored_links.sort(key=lambda x: x[0], reverse=True)
                
                if scored_links and self.stop_on_url:
                    print(f"[SMART] Top 3 scored links from {url}:")
                    for i, (score, link, _, _) in enumerate(scored_links[:3]):
                        print(f"  {i+1}. Score: {score:4d} | {link}")
                
                for score, link_url, link_depth, link_path in scored_links:
                    heapq.heappush(self.link_queue, (-score, link_url, link_depth, link_path))
            
            else:
                for link_url in links or []:
                    link_url = urljoin(url, link_url)
                    outgoing_links.append(link_url)
                    self.stats["inbound_links"][link_url] += 1
                    
                    if self.stop_on_reached:
                        continue
                    
                    if link_url not in self.visited and self.should_crawl_url(link_url):
                        if self.max_depth == 0 or depth + 1 < self.max_depth:
                            new_path = path + [link_url]
                            self.crawl_page(page, link_url, depth + 1, new_path)
            
            self.stats["link_map"][url] = outgoing_links
        
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
                proxy_settings = {"server": self.proxy} if self.proxy else None
                browser = p.chromium.launch(headless=True, proxy=proxy_settings)
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
                    self.crawl_page(page, url, 0, path=None)
                
                if self.stop_on_smart and not self.stop_on_reached:
                    print(f"\n[SMART] Processing {len(self.link_queue)} queued links by priority...")
                    
                    while self.link_queue and not self.stop_on_reached:
                        neg_score, link_url, link_depth, link_path = heapq.heappop(self.link_queue)
                        
                        if link_url in self.visited:
                            continue
                        if self.max_pages > 0 and self.stats["pages_crawled"] >= self.max_pages:
                            break
                        
                        self.crawl_page(page, link_url, link_depth, link_path)
                    
                    if self.stop_on_reached:
                        print(f"[SMART] ✓ Target found! Stopped smart crawling.")
                    else:
                        print(f"[SMART] Queue exhausted without finding target.")
                
                browser.close()
        
        except Exception as e:
            self.logger.log_error("BrowserCrawl", "N/A", str(e))
            self.stats["errors"] += 1
        
        self.logger.close_handlers()
        
        return {
            "data": self.collected_data,
            "stats": self.stats,
            "logs": self.logger.get_summary(),
            "js_runner_results": self.js_runner_results if self.js_runner_enabled else []
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
                 image_only=False, cookies=None, manager_dict=None, parent_pid=None, logger=None, proxy=None, *args, **kwargs):
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
        self.crawl_logger = logger or CrawlLogger()
        self.path_map = {}
        self.proxy = proxy

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
            meta = {'proxy': self.proxy} if self.proxy else {}
            yield scrapy.Request(url, callback=self.parse, cookies=self.cookies,
                               cb_kwargs={'depth': 0, 'path': [url]}, errback=self.handle_error, meta=meta)

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

    def parse(self, response, depth=0, path=None):
        url = response.url
        if url in self.visited:
            return
        self.visited.add(url)
        self.pages_count += 1
        crawl_stats["pages_crawled"] += 1
        
        title = response.css('title::text').get() or ""
        self.crawl_logger.log_page_visit(url, title=title.strip())

        if path is None:
            path = [url]
        self.path_map[url] = path

        if self.max_depth > 0 and depth >= self.max_depth:
            crawl_stats["skipped"] += 1
            return

        content_type = response.headers.get('Content-Type', b'').decode('utf-8').split(';')[0]
        crawl_stats["content_types"][content_type] += 1
        
        if self.image_only:
            images = self.extract_and_log_images(response)
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
                
            meta_desc = response.css('meta[name="description"]::attr(content)').get() or ""
            h1_tags = response.css('h1::text').getall()

            images = self.extract_and_log_images(response)
            crawl_stats["images_found"] += len(images)

            page_data = {
                "url": url,
                "content": text,
                "title": title.strip(),
                "meta_description": meta_desc.strip(),
                "h1_tags": h1_tags,
                "depth": depth,
                "content_type": content_type,
                "images": [img['url'] for img in images]
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
                meta = {'proxy': self.proxy} if self.proxy else {}
                yield scrapy.Request(link_url, callback=self.parse, cookies=self.cookies,
                                   cb_kwargs={'depth': depth+1, 'path': path + [link_url]}, errback=self.handle_error, dont_filter=False, meta=meta)
            
            elif max_depth_check:
                crawl_stats["skipped"] += 1

        crawl_stats["link_map"][url] = outgoing_links

    def extract_and_log_images(self, response):
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
            
            self.crawl_logger.log_image(full_url, response.url, dimensions=dimensions, alt_text=alt_text)
            images.append({
                "url": full_url,
                "type": "img_tag",
                "alt_text": alt_text,
                "dimensions": dimensions
            })

        style_images = response.css('*::attr(style)').re(r'url\(["\']?([^"\')]+)["\']?\)')
        for src in style_images:
            full_url = urljoin(response.url, src)
            self.crawl_logger.log_image(full_url, response.url, format_type="css_background")
            images.append({
                "url": full_url,
                "type": "css_background",
                "alt_text": None,
                "dimensions": None
            })
        
        return images

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
                "images_found": crawl_stats["images_found"],
                "path_map": dict(self.path_map)
            }
        }

        if not self.manager_dict:
            crawl_stats["path_map"] = dict(self.path_map)
        
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


def run_crawler_process(start_urls, on_site_only, max_depth, max_pages, content_filter, url_include, url_exclude, file_types, image_only, cookies, manager_dict, parent_pid, proxy=None):
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
                  parent_pid=parent_pid,
                  proxy=proxy)
    
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


def run_local_crawler(start_urls, on_site_only=False, max_depth=0, max_pages=0, content_filter=None, url_include=None, url_exclude=None, file_types=None, image_only=False, cookies=None, threads=6, proxy=None):
    
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
    
    process.crawl(SearchSpider, start_urls=start_urls, on_site_only=on_site_only, max_depth=max_depth_setting, max_pages=max_pages_setting, content_filter=content_filter, url_include=url_include, url_exclude=url_exclude, file_types=file_types, image_only=image_only, cookies=cookies, manager_dict=None, parent_pid=None, proxy=proxy)
    
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
            elif key == "proxy":
                params['proxy'] = value if value.upper() != 'N/A' else None
                
    return url, params
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
                        params['file_type'], params['image_only'], None, manager_dict, parent_pid, params.get('proxy')
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
    global collected_data, crawl_stats
    print(f"[DEBUG] show_statistics - collected_data length: {len(collected_data)}")
    print(f"[DEBUG] crawl_stats pages_crawled: {crawl_stats.get('pages_crawled', 'N/A')}")
    print(_get_stats_text(crawl_stats))

def show_link_analysis():
    print(_get_link_analysis_text(crawl_stats))

def generate_sitemap():
    global collected_data
    print(f"[DEBUG] collected_data length: {len(collected_data)}")
    if collected_data:
        print(f"[DEBUG] First item keys: {list(collected_data[0].keys())}")
    print(_generate_sitemap_text(collected_data))


def export_data(to_file=False, filename="exported_data.dat"):
    global collected_data
    print(f"[DEBUG] export_data - collected_data length: {len(collected_data)}")
    if not collected_data:
        print("No data to export. Please run a crawl first.")
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

def show_js_results(js_results):
    """Display JS Runner results in a formatted way."""
    if not js_results:
        print("No JS Runner results available.")
        return
    
    print("\n=== JS RUNNER RESULTS ===\n")
    
    logs = []
    errors = []
    warnings = []
    data_items = []
    other = []
    
    for item in js_results:
        if isinstance(item, dict):
            if 'silky_results' in item:
                print(f"\n--- URL: {item.get('url', 'Unknown')} ---")
                for subitem in item.get('silky_results', []):
                    result_type = subitem.get('type', 'unknown')
                    if result_type == 'log':
                        logs.append(subitem)
                    elif result_type == 'error':
                        errors.append(subitem)
                    elif result_type == 'warn':
                        warnings.append(subitem)
                    elif result_type == 'data':
                        data_items.append(subitem)
                    else:
                        other.append(subitem)
    
    print(f"\nTotal Results: {len(js_results)}")
    print(f"  Logs: {len(logs)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Data Items: {len(data_items)}")
    print(f"  Other: {len(other)}")
    
    if errors:
        print("\n--- ERRORS ---")
        for err in errors[:10]:  # Limit to first 10
            print(f"  [{err.get('timestamp', 'N/A')}] {err.get('message', 'No message')}")
            if err.get('url'):
                print(f"    URL: {err['url']}")
    
    if warnings:
        print("\n--- WARNINGS ---")
        for warn in warnings[:10]:
            print(f"  [{warn.get('timestamp', 'N/A')}] {warn.get('message', 'No message')}")
    
    if data_items:
        print("\n--- DATA COLLECTED ---")
        for item in data_items[:10]:
            print(f"  [{item.get('timestamp', 'N/A')}]")
            data = item.get('data', {})
            if isinstance(data, dict):
                for key, value in list(data.items())[:5]:  
                    print(f"    {key}: {value}")
            else:
                print(f"    {data}")
    
    if logs:
        print("\n--- LOGS (first 10) ---")
        for log in logs[:10]:
            print(f"  [{log.get('timestamp', 'N/A')}] {log.get('message', 'No message')}")
    
    print("\n")

def export_js_results(js_results, filename=None):
    """Export JS Runner results to JSON file."""
    if not js_results:
        print("No JS Runner results to export.")
        return
    
    if not filename:
        filename = input("Export filename [js_runner_results.json]: ").strip() or "js_runner_results.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(js_results, f, indent=2, ensure_ascii=False)
        print(f"Successfully exported {len(js_results)} JS Runner results to '{filename}'")
    except Exception as e:
        print(f"Error exporting JS results: {e}")

def build_tree(path_map):
    root = None
    for url, path in path_map.items():
        if len(path) == 1:
            root = url
            break
    if not root:
        return None
    tree = {root: {}}
    for url, path in path_map.items():
        if url == root:
            continue
        current = tree[root]
        for p in path[1:]:
            if p not in current:
                current[p] = {}
            current = current[p]
    return tree

def print_tree(tree, prefix=""):
    if not tree:
        return
    items = list(tree.items())
    for i, (url, children) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{url}")
        extension = "    " if is_last else "│   "
        print_tree(children, prefix + extension)

def generate_tree():
    global crawl_stats
    path_map = crawl_stats.get("path_map", {})
    if not path_map:
        print("No path map available. Tree requires crawl data with path tracking.")
        return
    tree = build_tree(path_map)
    if tree:
        print("Crawl Tree:")
        print_tree(tree)
    else:
        print("Could not build tree.")

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
            crawl_stats["link_map"] = defaultdict(list, imported_stats.get("link_map", {}))
            crawl_stats["path_map"] = defaultdict(list, imported_stats.get("path_map", {}))
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
            content_lower = d.get("content", "").lower()
            title_lower = d.get("title", "").lower()
            if query_lower in title_lower:
                score += 10
            score += content_lower.count(query_lower)
            for h1 in d.get("h1_tags", []):
                if h1 and isinstance(h1, str) and query_lower in h1.lower():
                    score += 5
        elif d.get('type') == 'image':
            if query_lower in d.get('url', '').lower():
                score += 1
        if score > 0:
            scored_results.append((score, d))
    scored_results.sort(reverse=True, key=lambda x: x[0])
    if not scored_results:
        urls = [d["url"] for d in collected_data if "url" in d]
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
                print(f" {r['url']}\n")
            elif r.get('type') == 'image':
                print(f"{i}. [{score} pts] [IMAGE] {r['url']}")
                print(f" Source: {r.get('source_page', 'Unknown')}\n")
            else:
                print(f"{i}. [{score} pts] {r['url']}\n")


def show_info_for_url(url, logs_data):
    print(f"\n--- Log Info for {url} ---")
    
    page_entries = [p for p in logs_data.get("pages", []) if p["url"] == url]
    
    if not page_entries:
        print("No crawl data found for this exact URL.")
        all_urls = [p["url"] for p in logs_data.get("pages", [])]
        close_matches = get_close_matches(url, all_urls, n=3)
        if close_matches:
            print("Did you mean one of these?")
            for match in close_matches:
                print(f" - {match}")
        return

    for entry in page_entries:
        print(f"\n- Page Visit at {entry['timestamp']}")
        print(f"  - Title: {entry.get('title', 'N/A')}")
        
        
        # Images
        images = [i for i in logs_data.get("images", []) if i["source_page"] == url]
        if images:
            print(f"  - Images Found ({len(images)}):")
            for img in images:
                print(f"    - {img['url']}")
        
        # JS
        scripts = [s for s in logs_data.get("javascript", []) if s["page_url"] == url]
        if scripts:
            print(f"  - Scripts Found ({len(scripts)}):")
            for script in scripts:
                if script['script_type'] == 'external':
                    print(f"    - {script['script_url']}")
                else:
                    print(f"    - Inline script ({script.get('content_size_bytes', 'N/A')} bytes)")

        # Network Requests
        network_reqs = [r for r in logs_data.get("network", []) if url in r.get("url", "")]
        if network_reqs:
            print(f"  - Network Requests ({len(network_reqs)}):")
            for req in network_reqs:
                print(f"    - {req['method']} {req['url']} - Status: {req['status']}")
                
        # API Calls
        api_calls = [a for a in logs_data.get("api", []) if url in a.get("endpoint", "")]
        if api_calls:
            print(f"  - API Calls ({len(api_calls)}):")
            for call in api_calls:
                print(f"    - {call['method']} {call['endpoint']} - Status: {call['status_code']}")

    print("\n--- End of Info ---")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    print("="*60)
    print("SILKY     By Lil Skittle")
    print("  / _ \\")
    print("\\_\\(_)/_/")
    print(" _//o\\\\_ ")
    print("  /   \\")
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
            query = input("\nCommands: stats, links, tree, sitemap, search, export, exportfile, exportlinks, exportimages, exportimagedata, exit\nEnter command: ").strip()
            if query.lower() == "exit": sys.exit(0)
            elif query.lower() == "stats": show_statistics()
            elif query.lower() == "links": show_link_analysis()
            elif query.lower() == "tree": generate_tree()
            elif query.lower() == "sitemap": generate_sitemap()
            elif query.lower().startswith("search "):
                search_term = query[len("search "):].strip()
                if search_term:
                    search_data(search_term)
                else:
                    print("Please provide a search term after 'search'.")
            elif query.lower() == "search":
                print("Please provide a search term after 'search'.")
            elif query.lower() == "export": export_data()
            elif query.lower() == "exportlinks": export_urls_to_file()
            elif query.lower() == "exportimages": export_images_to_file()
            elif query.lower() == "exportimagedata": export_images_with_metadata()
            elif query.lower() == "exportfile":
                fn = input("Enter filename: ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=fn)
            else:
                print(f"Unknown command: '{query}'")

    elif mode == "importfile":
        filename = input("Enter filename to import (e.g. exported_data.dat): ").strip()
        import_file(filename)
        while True:
            query = input("\nCommands: stats, links, sitemap, search, export, exportfile, exportlinks, exportimages, exportimagedata, exit\nEnter command: ").strip()
            if query.lower() == "exit": sys.exit(0)
            elif query.lower() == "stats": show_statistics()
            elif query.lower() == "links": show_link_analysis()
            elif query.lower() == "sitemap": generate_sitemap()
            elif query.lower().startswith("search "):
                search_term = query[len("search "):].strip()
                if search_term:
                    search_data(search_term)
                else:
                    print("Please provide a search term after 'search'.")
            elif query.lower() == "search":
                print("Please provide a search term after 'search'.")
            elif query.lower() == "export": export_data()
            elif query.lower() == "exportlinks": export_urls_to_file()
            elif query.lower() == "exportimages": export_images_to_file()
            elif query.lower() == "exportimagedata": export_images_with_metadata()
            elif query.lower() == "exportfile":
                fn = input("Enter filename: ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=fn)
            else:
                print(f"Unknown command: '{query}'")

    else:
        print("\n--- CRAWL MODE ---")
        urls_input = input("Enter starting URL(s) (comma-separated for multiple): ").strip()
        start_urls = [url.strip() for url in urls_input.split(',')]
        if not start_urls or not any(start_urls):
            print("No valid starting URLs provided. Exiting.")
            sys.exit(1)
        
        print("\n--- CRAWLER ENGINE SELECTION ---")
        if PLAYWRIGHT_AVAILABLE:
            engine_choice = input("Choose engine (playwright / scrapy) [playwright]: ").strip().lower()
            engine = 'playwright' if engine_choice != 'scrapy' else 'scrapy'
        else:
            engine = 'scrapy'
            print("Playwright not installed. Using Scrapy (install with: pip install playwright)")
        
        network_logging_config = None
        page_timeout = 15000
        log_images = True
        log_scripts = True
        log_cookies = True
        if engine == 'playwright':
            network_logging_config = NetworkLoggingConfig.from_user_input()

            print("\n--- PAGE TIMEOUT CONFIGURATION ---")
            print("Timeout for page load (in seconds). Lower = faster but may miss slow sites.")
            print("Recommended: 10-30 seconds. Fast sites: 5-10s, Slow sites: 20-30s")
            timeout_input = input("Page timeout in seconds [15]: ").strip()
            if timeout_input.isdigit():
                page_timeout = int(timeout_input) * 1000  # miliseconds!!!!!!!!!!
            else:
                page_timeout = 15000

            print("\n--- LOGGING TOGGLES ---")
            log_images_input = input("Log images? (yes/no) [yes]: ").strip().lower()
            log_images = log_images_input not in ['no', 'n', 'false', '0']

            log_scripts_input = input("Log scripts? (yes/no) [yes]: ").strip().lower()
            log_scripts = log_scripts_input not in ['no', 'n', 'false', '0']

            log_cookies_input = input("Log automatically generated cookies? (yes/no) [yes]: ").strip().lower()
            log_cookies = log_cookies_input not in ['no', 'n', 'false', '0']
        
        on_site = input(f"On Site Crawl only? (yes/no) [yes]: ").strip().lower()
        on_site_only = on_site in ['yes','y','true','1'] or not on_site
        
        print("\n--- FORCE DOMAIN (OPTIONAL) ---")
        print("Force crawler to stay within a specific domain/subdomain/path pattern.")
        print("Examples:")
        print("  - https://test.example.com/guide/* (stay on test.example.com under /guide/)")
        print("  - https://example.com/* (stay on example.com)")
        print("  - https://*.example.com/* (stay on any subdomain of example.com)")
        force_domain_input = input("Force domain pattern (or leave blank): ").strip()
        force_domain = force_domain_input if force_domain_input else None
        
        print("\n--- STOP-ON URL (OPTIONAL) ---")
        print("Crawler will stop when it reaches this specific URL.")
        print("Example: Start at https://example.com and stop at https://test.com")
        stop_on_url_input = input("Stop-on URL (or leave blank): ").strip()
        stop_on_url = stop_on_url_input if stop_on_url_input else None
        
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

        print("\n--- PROXY CONFIGURATION ---")
        print("Enter proxy address if needed (e.g., http://user:pass@host:port or socks5://host:port).")
        proxy_input = input("Proxy (or leave blank): ").strip() or None
        
        js_runner = None
        if engine == 'playwright':
            print("\n--- JS RUNNER (OPTIONAL) ---")
            print("Run custom JavaScript on every page. JS can interact with Silky via window.Silky API.")
            print("Options:")
            print("  1. Inline script (type JavaScript directly)")
            print("  2. Script file (path to .js file)")
            print("  3. Skip (no JS Runner)")
            js_choice = input("Choose option (1/2/3) [3]: ").strip()
            
            if js_choice == '1':
                print("\nEnter JavaScript (end with empty line):")
                script_lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    script_lines.append(line)
                if script_lines:
                    js_runner = JSRunner(script='\n'.join(script_lines))
                    print(f"[JS RUNNER] Loaded {len(script_lines)} lines of JavaScript")
            
            elif js_choice == '2':
                js_file = input("Enter path to .js file: ").strip()
                if js_file:
                    js_runner = JSRunner(script_file=js_file)
                    if js_runner.script:
                        print(f"[JS RUNNER] Loaded script from {js_file}")
                    else:
                        print(f"[JS RUNNER] Failed to load {js_file}")
                        js_runner = None
        
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
                    page_timeout=page_timeout,
                    proxy=proxy_input,
                    cookies=cookies,
                    log_images=log_images,
                    log_scripts=log_scripts,
                    log_cookies=log_cookies,
                    global_crawl_stats=crawl_stats,
                    force_domain=force_domain,
                    stop_on_url=stop_on_url,
                    js_runner=js_runner
                )
                result = crawler.run(start_urls)
            
            else:
                result = None
                run_local_crawler(start_urls, on_site_only, max_depth, max_pages, content_filter, 
                                url_include, url_exclude, file_types, image_only, cookies, threads, proxy=proxy_input)
        
        except KeyboardInterrupt:
            print("\n\n[STOP] Crawl interrupted by user (Ctrl+C). Showing partial results.")
            if engine == 'playwright' and 'crawler' in locals():
                result = {
                    "data": crawler.collected_data,
                    "stats": crawler.stats,
                    "logs": crawler.logger.get_summary()
                }
            else:
                result = None
        
        if engine == 'playwright' and result is not None:
            print(f"\n[DEBUG] result type: {type(result)}")
            print(f"[DEBUG] result is None: {result is None}")
            print(f"[DEBUG] result keys: {result.keys()}")
            print(f"[DEBUG] result['data'] length: {len(result['data'])}")
            print(f"[DEBUG] collected_data BEFORE extend: {len(collected_data)}")
            collected_data.extend(result["data"])
            print(f"[DEBUG] collected_data AFTER extend: {len(collected_data)}")
            crawl_stats.update(result["stats"])
            print(f"\n[INFO] Collected {len(collected_data)} pages of data")

        show_statistics()
        
        log_export_prompt = input("\nExport crawl logs? (yes/no) [yes]: ").strip().lower()
        if log_export_prompt in ['yes','y','true','1'] or not log_export_prompt:
            log_filename = input("Log filename [crawler_logs.json]: ").strip() or "crawler_logs.json"
            logger.export_logs(log_filename)
        
        while True:
            query = input("\nCommands: stats, links, tree, sitemap, info, search, export, exportfile, exportlinks, exportimages, exportimagedata, exportlogs, jsresults, exportjs, exit\nEnter command: ").strip()
            if query.lower() == "exit":
                sys.exit(0)
            elif query.lower() == "stats":
                show_statistics()
            elif query.lower() == "links":
                show_link_analysis()
            elif query.lower() == "tree":
                generate_tree()
            elif query.lower() == "sitemap":
                generate_sitemap()
            elif query.lower() == "info":
                url_to_find = input("Enter the URL to get info for: ").strip()
                show_info_for_url(url_to_find, logger.logs)
            elif query.lower().startswith("search"):
                if engine != 'scrapy':
                    print("Search command is only available for the Scrapy engine.")
                else:
                    search_term = query[len("search "):].strip()
                    if search_term:
                        search_data(search_term)
                    else:
                        print("Please provide a search term after 'search'.")
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
            elif query.lower() == "jsresults":
                if engine == 'playwright' and result and 'js_runner_results' in result:
                    show_js_results(result['js_runner_results'])
                else:
                    print("No JS Runner results available.")
            elif query.lower() == "exportjs":
                if engine == 'playwright' and result and 'js_runner_results' in result:
                    export_js_results(result['js_runner_results'])
                else:
                    print("No JS Runner results to export.")
            elif query.lower() == "exportfile":
                filename = input("Enter filename to save (default: exported_data.dat): ").strip() or "exported_data.dat"
                export_data(to_file=True, filename=filename)
            else:
                print(f"Unknown command: '{query}'")
                # Made by Lil Skittle, i am not responsible for any damage caused with this (:
                # Long Live Silky
