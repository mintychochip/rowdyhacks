"""Scrape Devpost submission pages for metadata."""
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.crawler.stealth import StealthClient, human_like_delay

DEVPOST_DOMAIN_RE = re.compile(r"^(.*\.)?devpost\.com$", re.IGNORECASE)
GITHUB_DOMAIN_RE = re.compile(r"^(www\.)?github\.com$", re.IGNORECASE)


def _fetch_page_sync(url: str) -> str:
    """Fetch a page synchronously and return its HTML text."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return response.text


class ScraperError(Exception):
    """Raised when scraping fails (HTTP error, parse failure, invalid URL)."""


def is_devpost_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(DEVPOST_DOMAIN_RE.match(parsed.netloc or ""))


def is_github_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(GITHUB_DOMAIN_RE.match(parsed.netloc or ""))


async def scrape_devpost(url: str) -> "ScrapedData":
    """Scrape a Devpost submission page with stealth features."""
    from app.checks.interface import ScrapedData

    if not is_devpost_url(url):
        raise ScraperError(f"Not a Devpost URL: {url}")

    async with StealthClient(max_retries=3, base_delay=2.0) as client:
        try:
            response = await client.get(url)
            # Add human-like delay after page load
            await human_like_delay(action="page_view")
        except httpx.HTTPError as e:
            raise ScraperError(f"HTTP error scraping Devpost: {e}") from e

    soup = BeautifulSoup(response.text, "lxml")

    data = ScrapedData()

    # Title from og:title or h1
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        data.title = og_title["content"].strip()
    else:
        h1 = soup.find("h1")
        if h1:
            data.title = h1.get_text(strip=True)

    # Description from og:description or first substantial p
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        data.description = og_desc["content"].strip()

    # Claimed tech ("Built With" section)
    tech_tags = soup.select("#built-with .cp-tag, [class*='built-with'] .cp-tag")
    for tag in tech_tags:
        text = tag.get_text(strip=True)
        if text:
            data.claimed_tech.append(text)

    # Team members
    for member_el in soup.select(".software-team-member, [class*='team-member']"):
        name_el = member_el.select_one("a, .name, [class*='name']")
        if name_el:
            name = name_el.get_text(strip=True)
            profile_url = name_el.get("href", "") if name_el.name == "a" else ""
            if name:
                data.team_members.append({"name": name, "devpost_profile": profile_url})

    # GitHub URL — look for links to github.com (multiple strategies)
    # Strategy 1: direct links with github.com in href
    for link in soup.select("a[href*='github.com']"):
        href = link.get("href", "")
        if is_github_url(href):
            data.github_url = href
            break

    # Strategy 2: links where the visible text or nearby text mentions "GitHub" or "Repo"
    if not data.github_url:
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text(strip=True).lower()
            if is_github_url(href):
                data.github_url = href
                break
            # If the link text says GitHub/Repo but href is a Devpost redirect,
            # try to extract the real URL from query params
            if ("github" in text or "repo" in text) and "devpost.com" not in href:
                if is_github_url(href):
                    data.github_url = href
                    break

    # Strategy 3: scan all text for github.com/owner/repo patterns
    if not data.github_url:
        body_text = soup.get_text()
        gh_match = re.search(r'github\.com/[\w.-]+/[\w.-]+', body_text)
        if gh_match:
            data.github_url = f"https://{gh_match.group(0)}"

    # Video URL
    for iframe in soup.select("iframe[src*='youtube.com'], iframe[src*='vimeo.com']"):
        data.video_url = iframe.get("src", "")
        break
    if not data.video_url:
        for link in soup.select("a[href*='youtube.com'], a[href*='vimeo.com']"):
            data.video_url = link.get("href", "")
            break

    # Slides URL
    for link in soup.select("a[href*='figma.com'], a[href*='docs.google.com/presentation'], a[href*='slides.com']"):
        data.slides_url = link.get("href", "")
        break

    # Hackathon name/URL from "Submitted to" section
    submissions_div = soup.find("div", id="submissions")
    if submissions_div:
        # Find the first link with actual text content (not just an image)
        for link in submissions_div.find_all("a", href=True):
            text = link.get_text(strip=True)
            if text:
                data.hackathon_name = text
                data.hackathon_url = link["href"]
                break

    return data
