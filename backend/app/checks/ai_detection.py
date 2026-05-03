"""Detect AI-generated code patterns."""

from app.checks.interface import CheckContext, CheckResult

AI_PHRASES = [
    "i hope this helps",
    "certainly!",
    "here's the implementation",
    "let me know if you have any questions",
    "this function takes",
    "first, we need to",
    "as you can see",
]


async def check_ai(context: CheckContext) -> CheckResult:
    """Heuristic check for AI-generated code patterns."""
    if not context.repo_path:
        return CheckResult(
            check_name="ai-detection",
            check_category="ai_detection",
            score=20,
            status="pass",
            details={"reason": "No repo to analyze"},
        )

    score = 0
    details = {"ai_phrases_found": 0, "high_comment_ratio": False, "style_shifts": 0}
    evidence = []
    repo = context.repo_path

    total_lines = 0
    comment_lines = 0
    prev_style = None

    _SKIP_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "target",
        "vendor",
        "models",
        "weights",
        "checkpoints",
        "data",
        "datasets",
    }
    _SKIP_EXTS = {
        ".jpg",
        ".png",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".mp4",
        ".mp3",
        ".zip",
        ".tar",
        ".gz",
        ".pth",
        ".pt",
        ".h5",
        ".pb",
        ".bin",
        ".exe",
        ".dll",
        ".so",
        ".pyc",
        ".class",
        ".o",
    }
    _SOURCE_EXTS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".html",
        ".css",
        ".md",
        ".yml",
        ".yaml",
        ".json",
        ".sh",
        ".r",
        ".ipynb",
    }
    max_bytes = 500_000
    bytes_read = 0

    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(repo).parts
        if any(p in _SKIP_DIRS for p in parts):
            continue
        if f.suffix.lower() in _SKIP_EXTS:
            continue
        if f.suffix.lower() not in _SOURCE_EXTS:
            continue
        if bytes_read > max_bytes:
            break
        try:
            content = f.read_text(errors="ignore")
            bytes_read += len(content)
            lines = content.split("\n")
            total_lines += len(lines)

            # Count comment lines
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(("#", "//", "/*", "*", "<!--")) or stripped == "":
                    comment_lines += 1

            # AI phrases
            lower = content.lower()
            for phrase in AI_PHRASES:
                if phrase in lower:
                    details["ai_phrases_found"] += 1
                    evidence.append(f"{f.name}: '{phrase}'")

            # Style shift detection (tab vs space mix in same file)
            tab_lines = sum(1 for l in lines if l.startswith("\t"))
            space_lines = sum(1 for l in lines if l.startswith("  ") or l.startswith("    "))
            if tab_lines > 3 and space_lines > 3:
                details["style_shifts"] += 1
        except Exception:
            continue

    if total_lines > 0:
        ratio = comment_lines / total_lines
        if ratio > 0.3:
            details["high_comment_ratio"] = True
            score += 15

    if details["ai_phrases_found"] > 3:
        score += 20

    if details["style_shifts"] > 2:
        score += 10

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="ai-detection",
        check_category="ai_detection",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
