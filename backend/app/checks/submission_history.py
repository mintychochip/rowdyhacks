"""Check for prior submissions by team members."""
import re
from pathlib import Path
from app.checks.interface import CheckContext, CheckResult


async def check_history(context: CheckContext) -> CheckResult:
    """Check if team or project has been submitted before."""
    score = 0
    details = {"prior_flags": [], "wrong_readme": False}
    evidence = []

    # Check if repo has README referencing another hackathon
    if context.repo_path:
        readme_paths = list(context.repo_path.glob("README*")) + list(
            context.repo_path.glob("readme*")
        )
        hackathon_names = [
            "hackmit",
            "pennapps",
            "treehacks",
            "calhacks",
            "hacknyu",
            "hackthe",
            "mhacks",
            "yhack",
            "boilermake",
            "hackgt",
            "hacktx",
            "hackuci",
            "hacksc",
            "hacklahacks",
            "hackumass",
        ]
        for rp in readme_paths:
            content = rp.read_text(errors="ignore").lower()
            for name in hackathon_names:
                if name in content:
                    details["wrong_readme"] = True
                    score += 15
                    evidence.append(f"README mentions '{name}'")
                    break

    # Stub: prior member flags would require DB access
    # This is handled by the analyzer which injects DB-dependent checks
    if not context.scraped.team_members:
        details["no_team_data"] = True

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="submission-history",
        check_category="submission_history",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
