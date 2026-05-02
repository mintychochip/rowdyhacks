"""Stealth crawling utilities for WAF bypass and human-like behavior."""
import asyncio
import random
from typing import Optional

import httpx


# Rotate through realistic browser user agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.65",
]

# Realistic accept headers
ACCEPT_HEADERS = {
    "text/html": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "json": "application/json, text/plain, */*",
}

# Common referrers to rotate
REFERRERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://devpost.com/hackathons",
    "https://github.com/",
]


def get_stealth_headers(content_type: str = "text/html", referer: Optional[str] = None) -> dict:
    """Generate stealth request headers that look like a real browser."""
    user_agent = random.choice(USER_AGENTS)
    accept = ACCEPT_HEADERS.get(content_type, ACCEPT_HEADERS["text/html"])
    
    headers = {
        "User-Agent": user_agent,
        "Accept": accept,
        "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.9", "en;q=0.8"]),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if not referer else "cross-site",
        "Cache-Control": random.choice(["max-age=0", "no-cache"]),
    }
    
    if referer:
        headers["Referer"] = referer
    else:
        headers["Referer"] = random.choice(REFERRERS)
    
    # Add random viewport hints (some browsers send this)
    if random.random() > 0.5:
        headers["Viewport-Width"] = str(random.choice([1280, 1366, 1440, 1920, 2560]))
    
    return headers


class StealthClient:
    """HTTP client with stealth features: rotation, delays, retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get(self, url: str, headers: Optional[dict] = None) -> httpx.Response:
        """Make a stealth GET request with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Add jitter to delay (exponential backoff with randomization)
                if attempt > 0:
                    delay = min(
                        self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        self.max_delay
                    )
                    await asyncio.sleep(delay)
                
                # Generate stealth headers
                request_headers = headers or get_stealth_headers()
                
                # Add slight randomization to timeout
                timeout = self.timeout + random.uniform(-2, 2)
                
                response = await self._client.get(
                    url,
                    headers=request_headers,
                    timeout=max(5, timeout),
                )
                
                self._request_count += 1
                
                # Handle common WAF responses
                if response.status_code == 403:
                    # Might be WAF block, retry with different headers
                    if attempt < self.max_retries - 1:
                        continue
                
                if response.status_code == 429:
                    # Rate limited, wait longer
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(retry_after + random.uniform(1, 5))
                        continue
                
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (500, 502, 503, 504):
                    # Server error, retry
                    continue
                raise
            except httpx.NetworkError as e:
                last_error = e
                continue
        
        raise last_error or Exception(f"Max retries exceeded for {url}")
    
    async def post(self, url: str, data: Optional[dict] = None, headers: Optional[dict] = None) -> httpx.Response:
        """Make a stealth POST request."""
        request_headers = headers or get_stealth_headers("json")
        
        return await self._client.post(
            url,
            json=data,
            headers=request_headers,
            timeout=self.timeout,
        )


class ProxyRotator:
    """Simple proxy rotation (for future use with proxy providers)."""
    
    def __init__(self, proxies: Optional[list[str]] = None):
        self.proxies = proxies or []
        self._current_index = 0
    
    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.proxies)
        return proxy


# Human-like behavior delays
async def human_like_delay(
    min_seconds: float = 0.5,
    max_seconds: float = 3.0,
    action: str = "page_view"
):
    """Simulate human-like delays between actions."""
    base_delays = {
        "page_view": (1.0, 4.0),
        "scroll": (0.3, 1.5),
        "click": (0.2, 0.8),
        "form_fill": (0.5, 2.0),
    }
    
    min_sec, max_sec = base_delays.get(action, (min_seconds, max_seconds))
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


# Fingerprint randomization
def randomize_fingerprint() -> dict:
    """Generate randomized browser fingerprint components."""
    return {
        "viewport": {
            "width": random.choice([1280, 1366, 1440, 1536, 1920]),
            "height": random.choice([720, 768, 900, 1080, 1200]),
        },
        "color_depth": random.choice([24, 32]),
        "pixel_ratio": random.choice([1.0, 1.25, 1.5, 2.0]),
        "timezone_offset": random.choice([-480, -420, -360, -300, -240, -180, -120, -60, 0, 60, 120]),
    }
