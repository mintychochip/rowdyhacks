"""Check if declared dependencies are actually imported in the codebase."""

import json
import re

from app.checks.interface import CheckContext, CheckResult


async def check_dead_deps(context: CheckContext) -> CheckResult:
    """Find dependencies listed in package files that are never imported."""
    if not context.repo_path:
        return CheckResult(
            check_name="dead-dependencies",
            check_category="devpost_alignment",
            score=20,
            status="pass",
            details={"reason": "No repo available"},
        )

    repo = context.repo_path
    declared: list[str] = []
    imports_found: set[str] = set()
    evidence: list[str] = []

    # 1. Extract declared dependencies from package files
    pkg_json = repo / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                for dep in data.get(key) or {}:
                    declared.append(dep.lower())
        except Exception:
            pass

    req_txt = repo / "requirements.txt"
    if req_txt.exists():
        for line in req_txt.read_text(errors="ignore").split("\n"):
            line = line.strip().lower()
            if line and not line.startswith("#") and not line.startswith("-"):
                pkg = re.split(r"[=<>~!\[]", line)[0].strip()
                if pkg:
                    declared.append(pkg)

    pipfile = repo / "Pipfile"
    if pipfile.exists():
        for line in pipfile.read_text(errors="ignore").split("\n"):
            m = re.match(r'^\s*["\']?([\w.-]+)["\']?\s*=', line.strip())
            if m:
                declared.append(m.group(1).lower())

    if not declared:
        return CheckResult(
            check_name="dead-dependencies",
            check_category="devpost_alignment",
            score=0,
            status="pass",
            details={"reason": "No package files found"},
        )
    declared = list(set(declared))  # dedup

    # 2. Scan source files for imports
    source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java"}
    skip_dirs = {"node_modules", "__pycache__", ".venv", "venv", ".git", "dist", "build"}

    all_code = ""
    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(repo).parts
        if any(p in skip_dirs for p in parts):
            continue
        if f.suffix.lower() not in source_exts:
            continue
        try:
            all_code += f.read_text(errors="ignore").lower() + "\n"
        except Exception:
            pass

    # 3. Check each declared dependency for usage
    missing = []
    for dep in sorted(declared):
        # Normalize: react-dom → react.dom, @scope/pkg → scope/pkg
        normalized = dep.replace("-", ".").replace("@/", "").split("/")[-1]
        # Check various import patterns
        patterns = [
            re.escape(dep),  # exact package name in import/require
            re.escape(normalized),  # normalized
            f"from [\"']{re.escape(dep)}",  # python import
            f"import {re.escape(dep)}",  # python import
            f"require\\([\"'].*{re.escape(dep)}",  # JS require
        ]
        found = False
        for pat in patterns:
            if re.search(pat, all_code):
                found = True
                imports_found.add(dep)
                break
        if not found:
            missing.append(dep)

    pct_dead = round(len(missing) / len(declared) * 100) if declared else 0

    score = 0
    if len(missing) > 0:
        if pct_dead > 50:
            score = 40
            evidence.append(
                f"{pct_dead}% of dependencies ({len(missing)}/{len(declared)}) never imported — likely inflated tech stack"
            )
        elif pct_dead > 25:
            score = 25
            evidence.append(f"{pct_dead}% of dependencies ({len(missing)}/{len(declared)}) never imported")
        else:
            score = 10
            evidence.append(f"{len(missing)} unused dependencies: {', '.join(missing[:5])}")

    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="dead-dependencies",
        check_category="devpost_alignment",
        score=score,
        status=status,
        details={
            "total_declared": len(declared),
            "imported": len(imports_found),
            "missing": missing,
            "pct_dead": pct_dead,
        },
        evidence=evidence,
    )
