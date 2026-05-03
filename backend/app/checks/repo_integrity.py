"""Detect forks, boilerplate ratio, and hardcoded credentials in the repo."""

import re
import subprocess
from pathlib import Path

from app.checks.interface import CheckContext, CheckResult

# Patterns for hardcoded credentials
SECRET_PATTERNS = [
    (r'(?:API|SECRET)_?KEY\s*[=:]\s*["\'][^\s]{20,}["\']', "API key"),
    (r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^\s]{6,}["\']', "hardcoded password"),
    (r'(?:token|auth)\s*[=:]\s*["\'][^\s]{20,}["\']', "auth token"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "private key"),
    (r'(?:mongodb|postgres|mysql|redis)://[^\s\'"]+', "database URL with credentials"),
    (r"(?:sk-|pk-)[a-zA-Z0-9]{20,}", "Stripe/OpenAI key"),
    (r"(?:ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]{20,}", "GitHub token"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"amzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "AWS key"),
]

# Boilerplate fingerprints (unique file hashes or patterns)
BOILERPLATE_INDICATORS = {
    "create-react-app": ["src/App.test.tsx", "src/App.css", "src/logo.svg", "public/manifest.json"],
    "next.js": ["pages/_app.tsx", "pages/index.tsx", "styles/globals.css"],
    "vite": ["src/vite-env.d.ts", "public/vite.svg", "index.html"],
    "expo": ["app.json", "babel.config.js", "assets/icon.png", "assets/splash.png"],
    "django": ["manage.py", "project/wsgi.py", "project/asgi.py", "project/urls.py"],
    "flutter": ["pubspec.yaml", "lib/main.dart", "test/widget_test.dart"],
    "spring boot": ["src/main/resources/application.properties", "mvnw", "mvnw.cmd"],
    "rails": ["config/routes.rb", "app/controllers/application_controller.rb", "Gemfile"],
}


async def check_repo_integrity(context: CheckContext) -> CheckResult:
    """Check for forks, boilerplate ratio, and hardcoded credentials."""
    repos = context.repo_paths or ([context.repo_path] if context.repo_path else [])
    if not repos:
        return CheckResult(
            check_name="repo-integrity",
            check_category="devpost_alignment",
            score=20,
            status="pass",
            details={"reason": "No repo available"},
        )

    all_secrets = []
    total_files = 0
    boilerplate_hits: dict[str, list[str]] = {}
    all_forks = []

    for repo in repos:
        # 1. Fork detection
        fork_info = _check_fork(repo)
        if fork_info:
            all_forks.append(fork_info)

        # 2. Scan for secrets + count files
        secrets, file_count = _scan_files(repo)
        all_secrets.extend(secrets)
        total_files += file_count

        # 3. Boilerplate detection
        bp = _detect_boilerplate(repo)
        for template, files in bp.items():
            if template not in boilerplate_hits:
                boilerplate_hits[template] = []
            boilerplate_hits[template].extend(files)

    score = 0
    evidence = []

    # Fork scoring
    if all_forks:
        score += 60
        urls = [f.get("upstream_url", "unknown") for f in all_forks]
        evidence.append(f"Repo is a fork of: {', '.join(urls)}")

    # Secrets scoring
    unique_secrets = len(set(s[1] for s in all_secrets))
    if all_secrets:
        score += min(unique_secrets * 15, 40)
        evidence.append(
            f"Found {len(all_secrets)} potential hardcoded secret(s): {', '.join(set(s[1] for s in all_secrets))}"
        )

    # Boilerplate scoring
    if boilerplate_hits:
        best_match = max(boilerplate_hits.items(), key=lambda x: len(x[1]))
        bp_pct = round(len(best_match[1]) / max(total_files, 1) * 100)
        if len(best_match[1]) >= 3 and bp_pct > 30:
            score += 20
            evidence.append(f"Detected {best_match[0]} boilerplate — {bp_pct}% of files are template defaults")
        elif len(best_match[1]) >= 2:
            evidence.append(f"Possible {best_match[0]} template detected")

    # Empty repo detection
    if total_files < 5:
        score += 15
        evidence.append(f"Only {total_files} source files found — very minimal project")

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="repo-integrity",
        check_category="devpost_alignment",
        score=score,
        status=status,
        details={
            "forks": all_forks,
            "secrets_found": len(all_secrets),
            "secret_types": list(set(s[1] for s in all_secrets)),
            "boilerplate_detected": {k: len(v) for k, v in boilerplate_hits.items()} if boilerplate_hits else None,
            "total_files": total_files,
        },
        evidence=evidence,
    )


def _check_fork(repo: Path) -> dict | None:
    """Check if repo is a fork by examining git remote configuration."""
    try:
        # Method 1: check if upstream remote exists
        result = subprocess.run(
            ["git", "-C", str(repo), "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        remotes = result.stdout.strip()
        if "upstream" in remotes:
            for line in remotes.split("\n"):
                if "upstream" in line and "(fetch)" in line:
                    url = line.split()[1]
                    return {"upstream_url": url, "detection": "upstream remote found"}

        # Method 2: check git config for fork info
        result = subprocess.run(
            ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        origin_url = result.stdout.strip()

        # Method 3: check if there are merge commits from a different repo
        result = subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline", "--merges", "-5"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip() and "Merge pull request" in result.stdout:
            merge_lines = result.stdout.strip().split("\n")
            for line in merge_lines:
                if "from " in line.lower() and "/" in line:
                    return {
                        "upstream_url": origin_url,
                        "detection": "merge commits from external repos",
                        "merges": merge_lines[:3],
                    }
    except Exception:
        pass
    return None


def _scan_files(repo: Path) -> tuple[list[tuple[str, str]], int]:
    """Scan source files for hardcoded secrets and count them."""
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    skip_exts = {".jpg", ".png", ".gif", ".mp4", ".zip", ".tar", ".gz", ".pth", ".pt", ".bin", ".exe"}
    source_exts = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".rb",
        ".php",
        ".env",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".sh",
        ".bash",
        ".html",
        ".css",
        ".md",
        ".txt",
        ".xml",
    }

    compiled = [(re.compile(p, re.IGNORECASE), label) for p, label in SECRET_PATTERNS]
    secrets = []
    file_count = 0

    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(repo).parts
        if any(p in skip_dirs for p in parts):
            continue
        if path.suffix.lower() in skip_exts:
            continue
        if path.suffix.lower() not in source_exts:
            continue
        try:
            if path.stat().st_size > 500_000:  # skip large files
                continue
            content = path.read_text(errors="ignore")
            file_count += 1
            for pattern, label in compiled:
                for match in pattern.finditer(content):
                    rel = str(path.relative_to(repo))
                    secrets.append((f"{rel}:{match.group()[:60]}...", label))
        except Exception:
            continue

    return secrets[:20], file_count


def _detect_boilerplate(repo: Path) -> dict[str, list[str]]:
    """Detect boilerplate template files by fingerprinting."""
    hits: dict[str, list[str]] = {}
    for template, indicators in BOILERPLATE_INDICATORS.items():
        found = []
        for indicator in indicators:
            # Check if exact file exists
            path = repo / indicator
            if path.exists():
                found.append(indicator)
            # Check glob patterns
            for match in repo.glob(indicator):
                rel = str(match.relative_to(repo))
                if rel not in found:
                    found.append(rel)
        if found:
            hits[template] = found
    return hits
