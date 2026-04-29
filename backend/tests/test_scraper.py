import pytest
from app.scraper import is_devpost_url, is_github_url, scrape_devpost, ScraperError
from app.checks.interface import ScrapedData


class TestUrlDetection:
    def test_devpost_urls(self):
        assert is_devpost_url("https://devpost.com/software/my-project")
        assert is_devpost_url("https://myproject.devpost.com")
        assert is_devpost_url("https://www.devpost.com/software/x")

    def test_not_devpost_urls(self):
        assert not is_devpost_url("https://github.com/user/repo")
        assert not is_devpost_url("https://evil.devpost.com.malicious.site")
        assert not is_devpost_url("https://fakedevpost.com/software/x")

    def test_github_urls(self):
        assert is_github_url("https://github.com/user/repo")
        assert is_github_url("https://www.github.com/user/repo")

    def test_not_github_urls(self):
        assert not is_github_url("https://devpost.com/software/x")
        assert not is_github_url("https://evil.github.com.malicious.site")


SAMPLE_DEVPOST_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta property="og:title" content="AI Study Buddy" />
  <meta property="og:description" content="An AI-powered study assistant for students" />
</head>
<body>
  <h1>AI Study Buddy</h1>
  <section id="built-with">
    <span class="cp-tag">Python</span>
    <span class="cp-tag">FastAPI</span>
    <span class="cp-tag">React</span>
    <span class="cp-tag">OpenAI</span>
  </section>
  <div class="software-team-member">
    <a href="/alice">Alice Smith</a>
  </div>
  <div class="software-team-member">
    <a href="/bob">Bob Jones</a>
  </div>
  <a href="https://github.com/alice/study-buddy">View on GitHub</a>
  <a href="https://youtube.com/watch?v=abc123">Demo Video</a>
  <a href="https://figma.com/file/xyz">Design File</a>
</body>
</html>"""


@pytest.mark.asyncio
async def test_scrape_devpost_full_page(monkeypatch):
    """Scrape a sample Devpost page and verify all fields."""
    import httpx

    class MockResponse:
        text = SAMPLE_DEVPOST_HTML
        def raise_for_status(self):
            pass

    async def mock_get(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    data = await scrape_devpost("https://devpost.com/software/ai-study-buddy")
    assert data.title == "AI Study Buddy"
    assert data.description == "An AI-powered study assistant for students"
    assert "Python" in data.claimed_tech
    assert "FastAPI" in data.claimed_tech
    assert "OpenAI" in data.claimed_tech
    assert len(data.team_members) == 2
    assert data.team_members[0]["name"] == "Alice Smith"
    assert data.github_url == "https://github.com/alice/study-buddy"
    assert data.video_url == "https://youtube.com/watch?v=abc123"
    assert data.slides_url == "https://figma.com/file/xyz"


@pytest.mark.asyncio
async def test_scrape_non_devpost_url():
    with pytest.raises(ScraperError, match="Not a Devpost URL"):
        await scrape_devpost("https://github.com/user/repo")
