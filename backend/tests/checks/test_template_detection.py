"""Tests for template detection check."""

import json
from uuid import uuid4

import pytest
from app.checks.interface import CheckContext, ScrapedData
from app.checks.template_detection import check_template


@pytest.mark.asyncio
async def test_template_no_repo(tmp_path):
    context = CheckContext(repo_path=None, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_template(context)
    assert result.status == "pass"
    assert result.score == 0


@pytest.mark.asyncio
async def test_template_react_app_detected(tmp_path):
    # Simulate Create React App structure
    package = {"name": "my-app", "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0", "react-scripts": "5.0.1"}}
    (tmp_path / "package.json").write_text(json.dumps(package))

    # Create src/App.js with CRA marker
    (tmp_path / "src").mkdir()
    (tmp_path / "src/App.js").write_text("""
function App() {
  return (
    <div className="App">
      <header className="App-header">
        <p>Edit src/App.js and save to reload.</p>
        <a href="https://reactjs.org">Learn React</a>
      </header>
    </div>
  );
}
export default App;
""")

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_template(context)

    # Should detect CRA template
    assert result.details.get("best_template_match") == "create-react-app"
    assert result.details.get("template_confidence", 0) > 0.4


@pytest.mark.asyncio
async def test_template_custom_code_passes(tmp_path):
    # Create substantial custom code
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("""
def calculate_matrix(data):
    \"\"\"Custom algorithm implementation.\"\"\"
    result = []
    for i, row in enumerate(data):
        processed = [x * 2 + i for x in row if x > 0]
        result.append(processed)
    return result

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.cache = {}

    def process(self, item):
        if item.id in self.cache:
            return self.cache[item.id]
        result = self._transform(item)
        self.cache[item.id] = result
        return result

    def _transform(self, item):
        return {
            "id": item.id,
            "value": item.value * 1.5,
            "metadata": item.get_metadata()
        }

if __name__ == "__main__":
    processor = DataProcessor({"batch_size": 100})
    print("Initialized")
""")

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_template(context)

    # Should pass with low confidence for templates
    assert result.status in ["pass", "warn"]
    assert result.details.get("template_confidence", 1.0) < 0.7


@pytest.mark.asyncio
async def test_template_no_code_files(tmp_path):
    # Empty repo
    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_template(context)

    assert result.status == "warn"
    assert result.details.get("reason") == "No code files found"
