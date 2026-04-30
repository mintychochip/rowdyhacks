"""Forensic analysis of commit timestamps to detect manipulation."""
import subprocess
import re
from datetime import datetime, timezone
from collections import defaultdict
from app.checks.interface import CheckContext, CheckResult


def _parse_git_date(date_str: str) -> datetime:
    """Parse a Git date string to datetime."""
    # Git dates can be in various formats
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        try:
            # Try Unix timestamp
            return datetime.fromtimestamp(int(date_str), tz=timezone.utc)
        except:
            return datetime.now(timezone.utc)


async def check_commit_forensics(context: CheckContext) -> CheckResult:
    """Perform forensic analysis on commit history to detect manipulation."""
    if not context.repo_path:
        return CheckResult(
            check_name="commit-forensics",
            check_category="timeline",
            score=0,
            status="pass",
            details={"reason": "No repo available"},
        )
    
    try:
        # Get detailed commit log with author date, commit date, and author
        result = subprocess.run(
            ["git", "-C", str(context.repo_path), "log", "--format=%H|%ai|%ci|%an|%ae|%s"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return CheckResult(
                check_name="commit-forensics",
                check_category="timeline",
                score=10,
                status="pass",
                details={"reason": "Git log failed"},
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return CheckResult(
            check_name="commit-forensics",
            check_category="timeline",
            score=10,
            status="pass",
            details={"reason": "Git command error"},
        )
    
    commits = []
    for line in result.stdout.strip().split("\n"):
        if "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            try:
                commit_hash = parts[0]
                author_date = parts[1]  # When the code was originally written
                commit_date = parts[2]  # When it was committed to this repo
                author_name = parts[3]
                author_email = parts[4]
                message = "|".join(parts[5:]) if len(parts) > 5 else ""
                
                commits.append({
                    "hash": commit_hash,
                    "author_date": author_date,
                    "commit_date": commit_date,
                    "author_name": author_name,
                    "author_email": author_email,
                    "message": message,
                })
            except:
                pass
    
    if not commits:
        return CheckResult(
            check_name="commit-forensics",
            check_category="timeline",
            score=10,
            status="pass",
            details={"reason": "No commits found"},
        )
    
    score = 0
    details = {
        "total_commits": len(commits),
        "author_date_mismatches": 0,
        "suspicious_author_patterns": [],
        "backdated_commits": 0,
        "future_commits": 0,
        "rapid_commit_spike": False,
        "single_author": False,
    }
    evidence = []
    
    # 1. Check for author date vs commit date mismatches
    # This indicates `git commit --date=` manipulation
    mismatches = 0
    for commit in commits:
        try:
            ad = datetime.fromisoformat(commit["author_date"].replace(' ', 'T').replace('+', '+'))
            cd = datetime.fromisoformat(commit["commit_date"].replace(' ', 'T').replace('+', '+'))
            
            # If author date is significantly different from commit date
            diff_hours = abs((cd - ad).total_seconds() / 3600)
            if diff_hours > 24:
                mismatches += 1
        except:
            pass
    
    details["author_date_mismatches"] = mismatches
    if mismatches > 0:
        pct_mismatch = mismatches / len(commits) * 100
        if pct_mismatch > 50:
            score += 40
            evidence.append(f"{pct_mismatch:.0f}% of commits have author/commit date mismatches — likely backdated")
        elif pct_mismatch > 20:
            score += 25
            evidence.append(f"{pct_mismatch:.0f}% of commits show date manipulation")
        else:
            score += 10
            evidence.append(f"{mismatches} commits have suspicious date patterns")
    
    # 2. Check for commits in the future (impossible without clock manipulation)
    now = datetime.now(timezone.utc)
    future_commits = 0
    for commit in commits:
        try:
            cd = datetime.fromisoformat(commit["commit_date"].replace(' ', 'T').replace('+', '+'))
            if cd > now:
                future_commits += 1
        except:
            pass
    
    details["future_commits"] = future_commits
    if future_commits > 0:
        score += 50
        evidence.append(f"{future_commits} commit(s) dated in the future — system clock manipulation")
    
    # 3. Check for rapid commit spikes (copy-paste detection)
    if len(commits) >= 3:
        # Sort by commit date
        sorted_commits = sorted(commits, key=lambda x: x["commit_date"])
        
        # Look for bursts (many commits within short time window)
        time_windows = []
        for i in range(len(sorted_commits) - 1):
            try:
                c1 = datetime.fromisoformat(sorted_commits[i]["commit_date"].replace(' ', 'T').replace('+', '+'))
                c2 = datetime.fromisoformat(sorted_commits[i+1]["commit_date"].replace(' ', 'T').replace('+', '+'))
                diff_minutes = (c2 - c1).total_seconds() / 60
                time_windows.append(diff_minutes)
            except:
                pass
        
        if time_windows:
            avg_gap = sum(time_windows) / len(time_windows)
            # If average gap is very small but commits contain lots of code
            if avg_gap < 1:  # Less than 1 minute average
                details["rapid_commit_spike"] = True
                score += 30
                evidence.append(f"Rapid commit pattern ({avg_gap:.1f} min avg gap) — possible copy-paste rush")
    
    # 4. Check for single author (normal for hackathons, but with other flags = suspicious)
    authors = set()
    author_emails = set()
    for commit in commits:
        authors.add(commit["author_name"])
        author_emails.add(commit["author_email"])
    
    details["unique_authors"] = len(authors)
    details["unique_author_emails"] = len(author_emails)
    
    if len(authors) == 1 and len(commits) > 20:
        details["single_author"] = True
        # Not automatically suspicious for solo hackathon projects
    
    # 5. Check for suspicious author email patterns
    suspicious_emails = []
    for email in author_emails:
        # Check for generic/temp email patterns
        if any(domain in email.lower() for domain in ["tempmail", "10minutemail", "guerrillamail", "throwaway"]):
            suspicious_emails.append(email)
        # Check for GitHub noreply (not suspicious, just noting)
        elif "noreply@github.com" in email:
            pass  # Normal for GitHub web commits
    
    if suspicious_emails:
        score += 25
        evidence.append(f"Suspicious/temporary email addresses used: {', '.join(suspicious_emails[:3])}")
    
    # 6. Compare against hackathon window if available
    if context.hackathon:
        try:
            hack_start = datetime.fromisoformat(context.hackathon.start_date[:19])
            hack_end = datetime.fromisoformat(context.hackathon.end_date[:19])
            
            commits_before = 0
            commits_during = 0
            commits_after = 0
            
            for commit in commits:
                try:
                    cd = datetime.fromisoformat(commit["commit_date"].replace(' ', 'T').replace('+', '+'))
                    # Strip timezone for comparison
                    cd_naive = cd.replace(tzinfo=None)
                    hack_start_naive = hack_start.replace(tzinfo=None)
                    hack_end_naive = hack_end.replace(tzinfo=None)
                    
                    if cd_naive < hack_start_naive:
                        commits_before += 1
                    elif cd_naive > hack_end_naive:
                        commits_after += 1
                    else:
                        commits_during += 1
                except:
                    pass
            
            details["commits_before_hackathon"] = commits_before
            details["commits_during_hackathon"] = commits_during
            details["commits_after_hackathon"] = commits_after
            
            # If more commits before than during, very suspicious
            if commits_before > commits_during:
                score += 30
                evidence.append(f"More commits before hackathon ({commits_before}) than during ({commits_during})")
            
            # If significant commits after deadline
            if commits_after > 5:
                score += 15
                evidence.append(f"{commits_after} commits after hackathon deadline — possible late work")
                
        except:
            pass
    
    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"
    
    return CheckResult(
        check_name="commit-forensics",
        check_category="timeline",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
