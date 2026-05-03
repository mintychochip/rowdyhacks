"""Cross-reference Devpost team members against actual git commit authors."""

import subprocess

from app.checks.interface import CheckContext, CheckResult


async def check_contributors(context: CheckContext) -> CheckResult:
    """Compare Devpost-listed team members to actual repo committers.

    Red flags:
    - Ghost contributors: people who committed but aren't on Devpost
    - MIA members: team members with zero commits (didn't actually build it)
    - Suspicious patterns: single-use accounts, generic names
    """
    repos = [context.repo_path] if context.repo_path else []
    if context.repo_paths:
        repos = context.repo_paths
    if not repos:
        return CheckResult(
            check_name="contributor-audit",
            check_category="submission_history",
            score=30,
            status="warn",
            details={"reason": "No repo available"},
        )

    if not context.scraped.team_members:
        return CheckResult(
            check_name="contributor-audit",
            check_category="submission_history",
            score=0,
            status="pass",
            details={"reason": "No team member data from Devpost"},
        )

    # 1. Get all git commit authors from ALL repos
    all_lines = []
    repo_count = 0
    for repo in repos:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "log", "--format=%an|%ae|%cn|%ce"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                all_lines.extend(result.stdout.strip().split("\n"))
                repo_count += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    if not all_lines:
        return CheckResult(
            check_name="contributor-audit",
            check_category="submission_history",
            score=20,
            status="pass",
            details={"reason": "Git log failed across all repos"},
        )

    # Parse authors: count commits per author + extract names and emails
    raw_authors: set[str] = set()
    author_emails: set[str] = set()
    commit_counts: dict[str, int] = {}
    total_commits = 0

    for line in all_lines:
        if not line.strip():
            continue
        total_commits += 1
        parts = line.split("|")
        if len(parts) >= 1:
            author = parts[0].strip().lower()
            raw_authors.add(author)
            commit_counts[author] = commit_counts.get(author, 0) + 1
        if len(parts) >= 2:
            email = parts[1].strip().lower()
            if "@" in email:
                author_emails.add(email)
        if len(parts) >= 4:
            email = parts[3].strip().lower()
            if "@" in email:
                author_emails.add(email)

    # Calculate commit percentages
    commit_pct: dict[str, int] = {}
    if total_commits > 0:
        for author, count in commit_counts.items():
            commit_pct[author] = round(count / total_commits * 100)

    # 2. Extract known identities from team members
    team_githubs = set()
    team_names = set()
    for m in context.scraped.team_members:
        name = m.get("name", "").strip().lower()
        if name:
            team_names.add(name)
        gh = (m.get("github") or "").strip()
        if gh and "github.com/" in gh:
            # Extract username from https://github.com/username
            username = gh.rstrip("/").split("/")[-1].lower()
            if username and "user/" not in gh:  # skip unresolved github_uid refs
                team_githubs.add(username)

    # 3. Cross-reference
    details: dict = {
        "repos_analyzed": repo_count,
        "repo_authors": sorted(raw_authors),
        "team_names": sorted(team_names),
        "team_githubs": sorted(team_githubs),
        "total_commits": total_commits,
        "commit_percentages": commit_pct,
        "ghost_contributors": [],
        "mia_members": [],
    }
    evidence: list[str] = []
    score = 0

    # Find ghost contributors (committed but not on Devpost)
    for author in raw_authors:
        # Check if author name matches any team member name or github username
        found = author in team_names
        if not found:
            # Try fuzzy: author first/last name in any team member name or vice versa
            author_parts = author.split()
            for tname in team_names:
                tparts = tname.split()
                if any(ap in tparts for ap in author_parts) or any(tp in author_parts for tp in tparts):
                    found = True
                    break
        if not found:
            for gh in team_githubs:
                if gh in author:
                    found = True
                    break
        if not found:
            details["ghost_contributors"].append(author)

    # Find MIA members (listed on Devpost but zero commits)
    for tname in team_names:
        found = tname in raw_authors
        if not found:
            author_parts = tname.split()
            for author in raw_authors:
                ra_parts = author.split()
                if any(ap in ra_parts for ap in author_parts) or any(rp in author_parts for rp in ra_parts):
                    found = True
                    break
        if not found:
            # Also check if their GitHub username appears in author names or emails
            for gh in team_githubs:
                if gh in raw_authors or any(gh in e for e in author_emails):
                    found = True
                    break
        if not found:
            details["mia_members"].append(tname)

    ghost_count = len(details["ghost_contributors"])
    mia_count = len(details["mia_members"])

    # Scoring
    if ghost_count > 0:
        score += min(ghost_count * 15, 50)
        ghost_pcts = {g: commit_pct.get(g, 0) for g in details["ghost_contributors"]}
        evidence.append(
            f"Found {ghost_count} repo contributor(s) not on Devpost: {', '.join(f'{g} ({ghost_pcts.get(g, 0)}%)' for g in details['ghost_contributors'][:5])}"
        )

    if mia_count > 0:
        score += min(mia_count * 20, 40)
        evidence.append(
            f"Devpost lists {mia_count} team member(s) with no commits: {', '.join(details['mia_members'])}"
        )

    # Contribution imbalance: one person dominates
    if commit_pct and team_names:
        max_pct = max(commit_pct.values()) if commit_pct else 0
        max_author = max(commit_pct, key=commit_pct.get) if commit_pct else ""
        if max_pct >= 90 and len(team_names) >= 2 and len(raw_authors) == 1:
            score += 25
            evidence.append(f"{max_author} wrote {max_pct}% of commits — team imbalance (1 person did all the work)")
        elif max_pct >= 80 and len(team_names) >= 3:
            score += 15
            evidence.append(
                f"{max_author} wrote {max_pct}% of commits — heavily imbalanced ({len(team_names)} members listed)"
            )

    # All commits from one person but team claims multiple members
    if len(raw_authors) == 1 and len(team_names) > 2:
        score += 20
        details["sole_contributor"] = True
        evidence.append(f"Only 1 committer ({list(raw_authors)[0]}) but Devpost lists {len(team_names)} team members")

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="contributor-audit",
        check_category="submission_history",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
