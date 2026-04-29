"""Smart build verification — detect project type, try to build, report results."""
import subprocess
import time
from pathlib import Path
from app.checks.interface import CheckContext, CheckResult


BUILD_DETECTORS = [
    {
        "name": "npm",
        "files": ["package.json"],
        "install": ["npm", "install", "--legacy-peer-deps"],
        "build": ["npm", "run", "build"],
        "timeout": 300,
    },
    {
        "name": "yarn",
        "files": ["yarn.lock", "package.json"],
        "install": ["yarn", "install"],
        "build": ["yarn", "build"],
        "timeout": 300,
    },
    {
        "name": "pnpm",
        "files": ["pnpm-lock.yaml", "package.json"],
        "install": ["pnpm", "install"],
        "build": ["pnpm", "build"],
        "timeout": 300,
    },
    {
        "name": "pip",
        "files": ["requirements.txt"],
        "install": ["pip", "install", "-r", "requirements.txt"],
        "build": None,  # no build step, just install verification
        "timeout": 180,
    },
    {
        "name": "poetry",
        "files": ["pyproject.toml", "poetry.lock"],
        "install": ["poetry", "install"],
        "build": None,
        "timeout": 180,
    },
    {
        "name": "pipenv",
        "files": ["Pipfile", "Pipfile.lock"],
        "install": ["pipenv", "install"],
        "build": None,
        "timeout": 180,
    },
    {
        "name": "cargo",
        "files": ["Cargo.toml"],
        "install": ["cargo", "fetch"],
        "build": ["cargo", "build", "--release"],
        "timeout": 600,
    },
    {
        "name": "go",
        "files": ["go.mod"],
        "install": ["go", "mod", "download"],
        "build": ["go", "build", "./..."],
        "timeout": 300,
    },
    {
        "name": "make",
        "files": ["Makefile"],
        "install": None,
        "build": ["make"],
        "timeout": 300,
    },
    {
        "name": "gradle",
        "files": ["build.gradle", "build.gradle.kts"],
        "install": None,
        "build": ["./gradlew", "build", "-x", "test"],
        "timeout": 600,
    },
    {
        "name": "maven",
        "files": ["pom.xml"],
        "install": None,
        "build": ["mvn", "compile", "-q"],
        "timeout": 600,
    },
    {
        "name": "bun",
        "files": ["bun.lockb", "package.json"],
        "install": ["bun", "install"],
        "build": ["bun", "run", "build"],
        "timeout": 300,
    },
    {
        "name": "composer",
        "files": ["composer.json"],
        "install": ["composer", "install", "--no-interaction"],
        "build": None,
        "timeout": 180,
    },
]


async def check_build(context: CheckContext) -> CheckResult:
    """Detect project type and try to build it."""
    repos = context.repo_paths or ([context.repo_path] if context.repo_path else [])
    if not repos:
        return CheckResult(
            check_name="build-verify", check_category="asset_integrity",
            score=20, status="pass", details={"reason": "No repo available"},
        )

    all_results = []
    for repo in repos:
        result = _try_build(repo)
        all_results.append(result)

    # Aggregate across repos
    total_builds = sum(1 for r in all_results if r["detected"])
    total_success = sum(1 for r in all_results if r.get("build_success"))
    total_fail = sum(1 for r in all_results if r.get("build_failed"))

    score = 0
    evidence = []
    if total_fail > 0:
        score += 40 * total_fail
        evidence.append(f"Build failed for {total_fail} repo(s)")
    if total_success > 0:
        evidence.append(f"Build succeeded for {total_success} repo(s)")
    if total_builds == 0:
        for r in all_results:
            if r.get("install_success"):
                evidence.append(f"Install succeeded for {r['repo']} (no build step)")
                break

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    # Clean up successful detection messages
    for r in all_results:
        if r.get("detected"):
            evidence.append(f"Detected {r['name']} project in {r['repo']}")

    return CheckResult(
        check_name="build-verify", check_category="asset_integrity",
        score=score, status=status,
        details={"results": all_results},
        evidence=evidence,
    )


def _try_build(repo: Path) -> dict:
    """Detect project type and attempt install + build."""
    result = {
        "repo": repo.name if repo.name else str(repo),
        "detected": False,
        "name": None,
        "install_success": None,
        "install_output": "",
        "build_success": None,
        "build_output": "",
        "build_time": 0,
    }

    # Find matching build system
    for detector in BUILD_DETECTORS:
        files_found = []
        for f in detector["files"]:
            matches = list(repo.rglob(f))
            if matches:
                files_found.extend(matches)
        if not files_found:
            continue

        result["detected"] = True
        result["name"] = detector["name"]

        # Try install
        if detector["install"]:
            try:
                t0 = time.monotonic()
                proc = subprocess.run(
                    detector["install"], cwd=repo,
                    capture_output=True, text=True,
                    timeout=detector["timeout"],
                )
                result["install_time"] = round(time.monotonic() - t0, 1)
                result["install_success"] = proc.returncode == 0
                result["install_output"] = (proc.stdout + proc.stderr)[:1000]
            except subprocess.TimeoutExpired:
                result["install_success"] = False
                result["install_output"] = "timeout"
            except FileNotFoundError:
                result["install_success"] = False
                result["install_output"] = f"{detector['name']} not installed"
        else:
            result["install_success"] = True  # no install needed

        # Try build
        if detector["build"]:
            try:
                t0 = time.monotonic()
                proc = subprocess.run(
                    detector["build"], cwd=repo,
                    capture_output=True, text=True,
                    timeout=detector["timeout"],
                )
                result["build_time"] = round(time.monotonic() - t0, 1)
                result["build_success"] = proc.returncode == 0
                result["build_output"] = (proc.stdout + proc.stderr)[:1000]
                result["build_failed"] = proc.returncode != 0
            except subprocess.TimeoutExpired:
                result["build_success"] = False
                result["build_failed"] = True
                result["build_output"] = "timeout"
            except FileNotFoundError:
                result["build_success"] = False
                result["build_failed"] = True
                result["build_output"] = f"{detector['name']} not installed"

        break  # use first matching detector

    return result
