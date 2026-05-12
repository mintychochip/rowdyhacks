"""Stealth crawling utilities for WAF bypass and human-like behavior."""

import asyncio
import random

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


def get_stealth_headers(content_type: str = "text/html", referer: str | None = None) -> dict:
    """Generate randomized HTTP request headers that mimic a real browser.

    Rotates user agents, accept languages, cache directives, and viewport
    hints to reduce WAF fingerprinting.

    Behavior:
    1. Select a random user agent from the rotation list.
    2. Resolve the Accept header based on ``content_type``.
    3. Build a headers dict with randomized language, encoding, cache
       directives, and sec-fetch hints.
    4. Add a Referer (explicit or random).
    5. Optionally inject a random Viewport-Width header.
    6. Return the headers dict.

    Raises: None
    Side Effects: None (read-only, uses random module).
    Dependencies: random module.
    Consumers: StealthClient, direct crawling helpers.
    """
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
    """Async HTTP client with stealth features.

    Combines header rotation, randomized delays, exponential back-off,
    and special handling for WAF responses (403/429) and server errors.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0,
    ):
        """Initialize the stealth HTTP client.

        Behavior:
        1. Store retry, delay, and timeout parameters as instance attributes.
        2. Initialize the internal ``httpx.AsyncClient`` placeholder and request counter.

        Raises: None
        Side Effects: Mutates instance state.
        Dependencies: None
        Consumers: StealthClient instantiation.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0

    async def __aenter__(self):
        """Enter the async context and create the underlying ``httpx`` client.

        Behavior:
        1. Instantiate an ``httpx.AsyncClient`` with the configured timeout and redirects.
        2. Return the ``StealthClient`` instance.

        Raises: None
        Side Effects: Creates and stores an ``httpx.AsyncClient``.
        Dependencies: httpx.AsyncClient.
        Consumers: Async context manager entry for StealthClient.
        """
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context and close the underlying HTTP client.

        Behavior:
        1. If an ``httpx.AsyncClient`` is stored, close it.

        Raises: None
        Side Effects: Closes the internal ``httpx.AsyncClient``.
        Dependencies: httpx.AsyncClient.aclose.
        Consumers: Async context manager exit for StealthClient.
        """
        if self._client:
            await self._client.aclose()

    async def get(self, url: str, headers: dict | None = None) -> httpx.Response:
        """Make a stealth GET request with retry logic and WAF evasion.

        Retries on 403 (WAF block), 429 (rate limit), and 5xx server
        errors using randomized exponential back-off.

        Behavior:
        1. Loop up to ``max_retries`` attempts.
        2. On subsequent attempts, apply exponential back-off with jitter.
        3. Generate stealth headers if none are provided.
        4. Randomize the request timeout slightly.
        5. Execute the GET request via ``httpx``.
        6. Handle 403 (retry with different headers) and 429 (sleep then retry).
        7. Raise for non-retryable HTTP errors or return the response on success.

        Raises: httpx.HTTPStatusError for non-retryable HTTP errors.
        Raises: Exception if all retry attempts are exhausted.
        Side Effects: Creates network requests; mutates ``self._request_count``.
        Dependencies: httpx.AsyncClient, get_stealth_headers.
        Consumers: Crawler modules, Devpost scrapers.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Add jitter to delay (exponential backoff with randomization)
                if attempt > 0:
                    delay = min(self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1), self.max_delay)
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

    async def post(self, url: str, data: dict | None = None, headers: dict | None = None) -> httpx.Response:
        """Make a stealth POST request.

        Behavior:
        1. Generate JSON-oriented stealth headers if none are provided.
        2. POST the JSON payload to the target URL via ``httpx``.
        3. Return the response.

        Raises: None
        Side Effects: Creates a network request.
        Dependencies: httpx.AsyncClient, get_stealth_headers.
        Consumers: Crawler modules that need POST requests.
        """
        request_headers = headers or get_stealth_headers("json")

        return await self._client.post(
            url,
            json=data,
            headers=request_headers,
            timeout=self.timeout,
        )


class ProxyRotator:
    """Round-robin proxy selector for future proxy-provider integration."""

    def __init__(self, proxies: list[str] | None = None):
        """Initialize the proxy rotator.

        Behavior:
        1. Store the proxy list and reset the round-robin index to 0.

        Raises: None
        Side Effects: Mutates instance state.
        Dependencies: None
        Consumers: ProxyRotator instantiation.
        """
        self.proxies = proxies or []
        self._current_index = 0

    def get_next_proxy(self) -> str | None:
        """Return the next proxy in round-robin rotation.

        Behavior:
        1. If no proxies are configured, return ``None``.
        2. Select the current proxy by index.
        3. Advance the index modulo the proxy list length.
        4. Return the selected proxy URL.

        Raises: None
        Side Effects: Mutates ``self._current_index``.
        Dependencies: None
        Consumers: StealthClient, crawling dispatchers.
        """
        if not self.proxies:
            return None
        proxy = self.proxies[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.proxies)
        return proxy


# Human-like behavior delays
async def human_like_delay(min_seconds: float = 0.5, max_seconds: float = 3.0, action: str = "page_view"):
    """Pause execution to simulate human-like interaction delays.

    Behavior:
    1. Look up the default delay range for the given ``action``.
    2. Fall back to the provided ``min_seconds`` and ``max_seconds`` if the action is unknown.
    3. Generate a random delay within the resolved range.
    4. Await ``asyncio.sleep`` for that duration.

    Raises: None
    Side Effects: Blocks the async event loop for the delay duration.
    Dependencies: asyncio, random.
    Consumers: Crawlers, scrapers, stealth navigation.
    """
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
    """Generate randomized browser fingerprint components.

    Behavior:
    1. Randomly select viewport width and height from common presets.
    2. Randomly select color depth, pixel ratio, and timezone offset.
    3. Return a dict with ``viewport``, ``color_depth``, ``pixel_ratio``, and ``timezone_offset``.

    Raises: None
    Side Effects: None (read-only, uses random module).
    Dependencies: random module.
    Consumers: Playwright-based crawlers, stealth initialization.
    """
    return {
        "viewport": {
            "width": random.choice([1280, 1366, 1440, 1536, 1920]),
            "height": random.choice([720, 768, 900, 1080, 1200]),
        },
        "color_depth": random.choice([24, 32]),
        "pixel_ratio": random.choice([1.0, 1.25, 1.5, 2.0]),
        "timezone_offset": random.choice([-480, -420, -360, -300, -240, -180, -120, -60, 0, 60, 120]),
    }
