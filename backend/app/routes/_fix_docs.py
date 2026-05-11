import os

HERE = os.path.dirname(os.path.abspath(__file__))


def fix_crawler():
    path = os.path.join(HERE, "crawler.py")
    with open(path) as f:
        content = f.read()
    old = '''    """Manually trigger a full crawl cycle (organizer-only).

    Returns 409 if a crawl is already running.
    """'''
    new = '''    """Manually trigger a full crawl cycle (organizer-only).

    Behavior:
    1. Check if a crawl is already in progress via is_crawling.
    2. Return 409 if a crawl is already running.
    3. Spawn run_crawl as an asyncio background task.
    4. Attach a done callback that logs exceptions.
    5. Return {"status": "started"}.

    Raises: HTTPException(409) if crawl already in progress.
    Side Effects: Spawns a background asyncio task.
    Dependencies: app.crawler.scheduler.is_crawling, app.crawler.scheduler.run_crawl.
    Consumers: POST /trigger, organizer dashboard.
    """'''
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False


def fix_hackathons():
    path = os.path.join(HERE, "hackathons.py")
    with open(path) as f:
        content = f.read()
    old = '''    """Run cross-team similarity checks for all completed submissions.

    Detects duplicate GitHub URLs, same repo name patterns, and overlapping
    commit hashes. Stores results in the database and updates risk scores /
    verdicts on flagged submissions.
    """'''
    new = '''    """Run cross-team similarity checks for all completed submissions.

    Behavior:
    1. Verify the hackathon exists; return 404 if not found.
    2. Delegate to run_similarity(hackathon_id) for batch analysis.
    3. Return the similarity summary.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: run_similarity manages its own DB session for mutations.
    Dependencies: app.checks.similarity.run_similarity, app.models.Hackathon.
    Consumers: POST /api/hackathons/{hackathon_id}/similarity, organizer fraud panel.
    """'''
    if old in content:
        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False


def fix_judging():
    path = os.path.join(HERE, "judging.py")
    with open(path) as f:
        content = f.read()

    fixes = [
        (
            '''    """Assign judges to submissions. Body: {"judge_ids": [...], "submission_ids": [...]}.

    Creates assignments for every judge×submission pair.
    Automatically creates JudgeRating records for new judges.
    """''',
            '''    """Assign judges to submissions for a hackathon judging session.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Parse judge_ids and submission_ids from the request body; 422 if either is empty.
    3. Verify all submission IDs belong to this hackathon; 422 if any are invalid.
    4. Mark existing assignments for this session as old (is_completed = -1).
    5. Ensure each judge has a JudgeRating record, creating one if missing.
    6. Create new JudgeAssignment rows for every judge×submission pair.
    7. Commit and return the count of created assignments.

    Raises: HTTPException(404, 422)
    Side Effects: Updates existing JudgeAssignment rows; inserts JudgeRating and JudgeAssignment rows.
    Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.JudgeRating, app.models.Submission.
    Consumers: POST /hackathons/{hackathon_id}/judging/assign, organizer judging setup.
    """''',
        ),
        (
            '''    """Submit or update scores for an assignment. Can be called incrementally.

    Auto-submits (marks complete) when all criteria have non-null scores.
    Also checks per_project_seconds soft deadline.
    """''',
            '''    """Submit or update scores for a judge assignment.

    Behavior:
    1. Load the JudgeAssignment by ID; 404 if not found.
    2. Reject if the assignment is already completed (400).
    3. Load the parent JudgingSession and enforce its time window.
    4. Flag as late if elapsed time exceeds per_project_seconds.
    5. Load the Rubric and validate each criterion ID and score range (0–max_score).
    6. Upsert Score rows for each criterion.
    7. If all criteria now have scores, mark the assignment completed and update opened_at.
    8. Commit and return the updated assignment with scores.

    Raises: HTTPException(404, 400, 422)
    Side Effects: Inserts or updates Score rows; may mutate JudgeAssignment.is_completed and opened_at.
    Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score.
    Consumers: POST /judging/assignments/{assignment_id}/score, frontend judging form.
    """''',
        ),
        (
            '''    """Return (new_elo_a, new_elo_b) after a pairwise comparison.
    outcome: 1.0 = A wins, 0.5 = tie, 0.0 = B wins."""''',
            '''    """Return (new_elo_a, new_elo_b) after a pairwise ELO comparison.

    Behavior:
    1. Compute expected scores e_a and e_b from the current ratings.
    2. Calculate rating deltas using the K-factor and actual outcome.
    3. Return updated ratings as a tuple.

    Raises: None
    Side Effects: None (pure function).
    Dependencies: _expected_score.
    Consumers: _update_elo_pairwise.
    """''',
        ),
        (
            '''    """Compute and return ELO rankings for the hackathon.

    Algorithm:
      1. Load all completed assignments with scores.
      2. Compute raw weighted score per (judge, submission).
      3. Z-score normalize within each judge (judge severity correction).
      4. Within-judge pairwise ELO updates.
      5. Cross-judge bridging via submissions scored by multiple judges.
      6. Return final ELO rankings.
    """''',
            '''    """Compute and return ELO rankings for a hackathon.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Load all completed assignments with eager-loaded scores.
    3. Compute raw weighted scores per (judge, submission) using rubric criteria weights.
    4. Z-score normalize within each judge to correct for severity bias.
    5. Run within-judge pairwise ELO updates.
    6. Bridge across judges via submissions scored by multiple judges.
    7. Return final ELO rankings sorted by score descending.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: None (read-only).
    Dependencies: _get_judging_session, _expected_score, _elo_update, app.models.JudgeAssignment, app.models.Submission.
    Consumers: GET /hackathons/{hackathon_id}/judging/results, leaderboard page.
    """''',
        ),
        (
            '''    """Return a priority-ordered list of submissions that need more judging.

    Query params:
      - judge_id (required): only return projects this judge hasn't scored
      - min_judges (default 3): minimum judge count before coverage is satisfied

    Each item includes:
      - submission info (id, title, url)
      - current ELO
      - uncertainty breakdown (variance, proximity, coverage)
      - priority score (higher = needs judging more urgently)
    """''',
            '''    """Return a priority-ordered list of submissions that need more judging.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Parse judge_id as UUID.
    3. Load all completed assignments with scores and build submission coverage maps.
    4. Identify pending assignments for the requesting judge.
    5. Compute uncertainty metrics (variance, proximity, coverage) per submission.
    6. Sort by priority score descending (higher = needs judging more urgently).
    7. Return the queue, count already scored by this judge, and a message if empty.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: None (read-only).
    Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.Submission, app.models.Score.
    Consumers: GET /hackathons/{hackathon_id}/judging/queue, frontend judge dashboard.
    """''',
        ),
        (
            '''    """Create new assignments for projects flagged by the ELO uncertainty engine.

    For each submission with fewer than min_judges scores, creates a new
    JudgeAssignment for every judge who hasn't scored it yet.
    Preserves existing scores (each round gets new assignment records).
    """''',
            '''    """Create new assignments for projects flagged by the ELO uncertainty engine.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Load all judge IDs with role=judge.
    3. Load all completed submission IDs for the hackathon.
    4. Load completed assignments and build a map of who scored what.
    5. For each submission with fewer than min_judges scores, create new JudgeAssignments for judges who haven't scored it.
    6. Commit and return the count of newly created assignments.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: Inserts new JudgeAssignment rows.
    Dependencies: _get_judging_session, app.models.User, app.models.Submission, app.models.JudgeAssignment.
    Consumers: POST /hackathons/{hackathon_id}/judging/rerun, organizer judging panel.
    """''',
        ),
    ]

    fixed = []
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            fixed.append(True)
        else:
            fixed.append(False)

    with open(path, "w") as f:
        f.write(content)
    return fixed


print("crawler:", fix_crawler())
print("hackathons:", fix_hackathons())
print("judging:", fix_judging())
