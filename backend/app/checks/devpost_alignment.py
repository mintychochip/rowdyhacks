"""Check Devpost claims against actual repository code."""

from app.checks.interface import CheckContext, CheckResult

PACKAGE_FILES = [
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "composer.json",
    "build.gradle",
    "pom.xml",
]


async def check_alignment(context: CheckContext) -> CheckResult:
    """Verify claimed tech stack matches actual code."""
    if not context.repo_path:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=30,
            status="warn",
            details={"reason": "No repo available"},
        )

    if not context.scraped.claimed_tech:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=0,
            status="pass",
            details={"reason": "No claimed tech to verify"},
        )

    score = 0
    details = {"missing_tech": [], "found_tech": [], "dead_files_pct": 0}
    evidence = []
    repo = context.repo_path

    # Search package files for claimed tech
    package_content = ""
    for pf in PACKAGE_FILES:
        p = repo / pf
        if p.exists():
            package_content += p.read_text(errors="ignore") + "\n"

    for tech in context.scraped.claimed_tech:
        tech_lower = tech.lower()
        found = tech_lower in package_content.lower()
        if not found:
            # Also search imports in common source dirs
            for src_dir in [repo / "src", repo / "app", repo]:
                if not src_dir.exists():
                    continue
                for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"]:
                    matches = list(src_dir.rglob(f"*{ext}"))
                    for f in matches[:50]:  # limit search
                        content = f.read_text(errors="ignore").lower()
                        if tech_lower in content:
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        if found:
            details["found_tech"].append(tech)
        else:
            details["missing_tech"].append(tech)
            score += 15

    # Dead file detection (crude: files with no content or only comments)
    total_files = 0
    empty_files = 0
    for f in repo.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in [".git/", "node_modules/", "__pycache__/", ".venv/"]):
            total_files += 1
            content = f.read_text(errors="ignore").strip()
            if len(content) < 10:
                empty_files += 1
    if total_files > 0:
        details["dead_files_pct"] = round(empty_files / total_files * 100)

    if details["dead_files_pct"] > 30:
        score += 20

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="claimed-vs-actual-tech",
        check_category="devpost_alignment",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
