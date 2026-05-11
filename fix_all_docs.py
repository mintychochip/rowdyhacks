import os

HERE = os.path.dirname(os.path.abspath(__file__))

REPLACEMENTS = {
    "backend/app/routes/checkin.py": [
        (
            '    """Scan a QR code to check in. Token is validated from JWT signature."""',
            '''    """Scan a QR code to check in a registered participant.

    Behavior:
    1. Decode and validate the QR JWT token.
    2. Extract reg_id from the token payload.
    3. Load the registration by ID.
    4. Validate registration state (accepted, not already checked in, not rejected).
    5. Update status to checked_in and set checked_in_at timestamp.
    6. Commit and return registration details.

    Raises: HTTPException(401) for invalid token, HTTPException(410) for missing or revoked registration, HTTPException(409) for already checked in or not active.
    Side Effects: Mutates Registration.status and Registration.checked_in_at; commits to DB.
    Dependencies: app.auth.decode_qr_token, app.models.Registration, app.models.RegistrationStatus.
    Consumers: POST /api/checkin/scan, check-in scanner UI.
    """''',
        ),
    ],
    "backend/app/routes/checks.py": [
        (
            '    """Submit a Devpost or GitHub URL for analysis."""',
            '''    """Submit a Devpost or GitHub URL for automated integrity analysis.

    Behavior:
    1. Extract client IP and enforce rate limiting (10/min).
    2. Validate the URL is a Devpost or GitHub link.
    3. Auto-link to the existing hackathon if none specified.
    4. Create a pending Submission with an anonymous access token.
    5. Persist the submission to the database.
    6. Trigger background analysis via analyze_submission.

    Raises: HTTPException(429) if rate limited, HTTPException(400) if URL invalid.
    Side Effects: Inserts Submission row; spawns background asyncio task.
    Dependencies: app.analyzer.analyze_submission, app.auth.create_anonymous_token, app.scraper.is_devpost_url, app.scraper.is_github_url.
    Consumers: POST /api/check, public submission form.
    """''',
        ),
        (
            '    """Get submission status and check results."""',
            '''    """Get submission status, metadata, and all check results.

    Behavior:
    1. Load the submission with eager-loaded check_results.
    2. Return 404 if the submission does not exist.
    3. Return the submission state including progress, risk score, verdict, and detailed check results.

    Raises: HTTPException(404) if submission not found.
    Side Effects: None (read-only).
    Dependencies: app.models.Submission, sqlalchemy.orm.selectinload.
    Consumers: GET /api/check/{submission_id}, status polling UI.
    """''',
        ),
        (
            '    """Get full report JSON for a submission.\n\n    Access rules:\n    - If no access_token is set on submission: public\n    - If token query param matches: access granted\n    - If Authorization header has valid organizer JWT: access granted\n    - Otherwise: access denied\n    """',
            '''    """Get full analysis report JSON for a submission.

    Behavior:
    1. Load the submission with eager-loaded check_results.
    2. Return 404 if the submission does not exist.
    3. Determine if the requester is an organizer via Clerk JWT.
    4. Enforce access control (organizer bypass, token match, or public if no token set).
    5. Return submission metadata, check results, and scoring weights.

    Raises: HTTPException(404) if submission not found, HTTPException(403) if access denied.
    Side Effects: None (read-only).
    Dependencies: app.clerk_auth.is_clerk_token, app.clerk_auth.decode_clerk_token, app.models.Submission, app.models.User, app.checks.WEIGHTS.
    Consumers: GET /api/check/{submission_id}/report, report viewer.
    """''',
        ),
        (
            '    """Retry a failed submission."""',
            '''    """Retry analysis for a failed or completed submission.

    Behavior:
    1. Load the submission by ID; 404 if not found.
    2. Delete all existing CheckResult rows for the submission.
    3. Reset submission status to pending and clear risk_score, verdict, completed_at, stage, and check_progress.
    4. Commit the reset.
    5. Trigger a new background analysis task.

    Raises: HTTPException(404) if submission not found.
    Side Effects: Deletes CheckResult rows; mutates Submission fields; spawns background asyncio task.
    Dependencies: app.analyzer.analyze_submission, app.models.Submission, app.models.SubmissionStatus, app.models.CheckResultModel.
    Consumers: POST /api/check/{submission_id}/retry, organizer dashboard.
    """''',
        ),
    ],
    "backend/app/routes/crawler.py": [
        (
            '    """Manually add a crawled hackathon (admin/debug use)."""',
            '''    """Manually add a crawled hackathon entry (admin/debug use).

    Behavior:
    1. Parse start_date and optional end_date from ISO strings.
    2. Create a CrawledHackathon record with the provided URL, name, and dates.
    3. Set last_crawled_at to now.
    4. Persist and return the created record ID.

    Raises: HTTPException(400) if date format is invalid.
    Side Effects: Inserts CrawledHackathon row.
    Dependencies: app.models.CrawledHackathon.
    Consumers: POST /hackathons, admin/debug panel.
    """''',
        ),
        (
            '    """List all crawled hackathons with project counts."""',
            '''    """List all crawled hackathons with associated project counts.

    Behavior:
    1. Query all CrawledHackathon records with an outer join to CrawledProject.
    2. Aggregate project counts per hackathon.
    3. Order results by last_crawled_at descending (nulls last).
    4. Return serialized list with IDs, dates, URLs, and counts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.CrawledHackathon, app.models.CrawledProject, sqlalchemy.func.count.
    Consumers: GET /hackathons, organizer crawler dashboard.
    """''',
        ),
        (
            '    """List projects for a specific crawled hackathon."""',
            '''    """List projects for a specific crawled hackathon with pagination.

    Behavior:
    1. Validate the hackathon_id as a UUID.
    2. Verify the hackathon exists; 404 if not found.
    3. Query CrawledProject rows for the hackathon ordered by created_at descending.
    4. Apply offset/limit pagination.
    5. Return the total count and paginated project list.

    Raises: HTTPException(400) for invalid UUID, HTTPException(404) if hackathon not found.
    Side Effects: None (read-only).
    Dependencies: app.models.CrawledHackathon, app.models.CrawledProject.
    Consumers: GET /hackathons/{hackathon_id}/projects, organizer project browser.
    """''',
        ),
        (
            '    """Search crawled projects by title."""',
            '''    """Search crawled projects by title with pagination.

    Behavior:
    1. Apply an optional case-insensitive title filter if q is provided.
    2. Query CrawledProject rows ordered by created_at descending.
    3. Apply offset/limit pagination.
    4. Return matching projects with hackathon linkage.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.CrawledProject.
    Consumers: GET /projects, organizer project search.
    """''',
        ),
    ],
    "backend/app/routes/hackathons.py": [
        (
            '    """Verify user is the organizer or a co-organizer of the hackathon."""',
            '''    """Verify the requesting user is the primary or co-organizer of a hackathon.

    Behavior:
    1. Return immediately if the user is the primary organizer.
    2. Query HackathonOrganizer for a matching (hackathon_id, user_id) row.
    3. Return if a co-organizer record exists.
    4. Raise 403 if neither condition is met.

    Raises: HTTPException(403) if user lacks organizer privileges.
    Side Effects: None (read-only).
    Dependencies: app.models.HackathonOrganizer, app.models.UserRole.
    Consumers: Internal helper used by multiple hackathon route guards.
    """''',
        ),
        (
            '    """Create a new hackathon."""',
            '''    """Create a new hackathon (organizer-only, one per portal).

    Behavior:
    1. Verify the user is an organizer.
    2. Reject if a hackathon already exists (portal limit).
    3. Build and persist a Hackathon record from the request body.
    4. Seed default tracks for the hackathon.
    5. Index hackathon data for the assistant.
    6. Bust the hackathon list cache.
    7. Return the created hackathon summary.

    Raises: HTTPException(403) if not organizer, HTTPException(400) if hackathon already exists.
    Side Effects: Inserts Hackathon and Track rows; mutates cache; triggers assistant indexing.
    Dependencies: app.models.Hackathon, app.models.UserRole, app.routes.tracks.seed_tracks, app.cache.cache_delete_pattern.
    Consumers: POST /api/hackathons, organizer setup wizard.
    """''',
        ),
        (
            '    """List all hackathons."""',
            '''    """List all hackathons with caching.

    Behavior:
    1. Query all Hackathon records ordered by created_at descending.
    2. Return serialized summaries with participant counts and deadlines.

    Raises: None
    Side Effects: None (read-only, cached).
    Dependencies: app.models.Hackathon, app.cache.cached.
    Consumers: GET /api/hackathons, public hackathon listing.
    """''',
        ),
        (
            '    """Get a single hackathon by ID."""',
            '''    """Get a single hackathon by ID with caching.

    Behavior:
    1. Query the Hackathon record by UUID.
    2. Return 404 if not found.
    3. Return full hackathon details including schedule, venue, and Discord info.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: None (read-only, cached).
    Dependencies: app.models.Hackathon, app.cache.cached.
    Consumers: GET /api/hackathons/{hackathon_id}, hackathon detail page.
    """''',
        ),
        (
            '    """Get aggregate stats for a hackathon."""',
            '''    """Get aggregate statistics for a hackathon.

    Behavior:
    1. Load all submissions for the hackathon and compute totals, completion rate, average risk, and verdict breakdown.
    2. Load registration status counts from the database.
    3. Compute check-in rate from accepted vs checked-in counts.
    4. Return the aggregated stats object.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.Submission, app.models.Registration, app.models.Verdict, app.models.SubmissionStatus, sqlalchemy.func.count.
    Consumers: GET /api/hackathons/{hackathon_id}/stats, organizer dashboard.
    """''',
        ),
        (
            '    """Get meal and swag planning counts (organizer only)."""',
            '''    """Get meal and swag planning counts for accepted participants (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Query all accepted and checked-in registrations.
    3. Aggregate counts for t-shirt sizes, dietary restrictions, and experience levels.
    4. Return the aggregated planning data.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: GET /api/hackathons/{hackathon_id}/swag-counts, organizer logistics panel.
    """''',
        ),
        (
            '    """List submissions for a hackathon."""',
            '''    """List all submissions for a hackathon.

    Behavior:
    1. Query Submission rows for the hackathon.
    2. Return serialized summaries with project titles, URLs, team info, risk scores, and verdicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.Submission.
    Consumers: GET /api/hackathons/{hackathon_id}/submissions, submissions browser.
    """''',
        ),
        (
            '    """Update hackathon settings (schedule, wifi, discord, webhook, deadline, capacity)."""',
            '''    """Update hackathon settings (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Apply updates only to allowed fields from the request body.
    3. Commit changes and bust relevant caches if any field was updated.
    4. Return the updated field list.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Hackathon fields; deletes cache keys.
    Dependencies: app.models.Hackathon, app.cache.cache_delete_pattern.
    Consumers: PUT /api/hackathons/{hackathon_id}, organizer settings form.
    """''',
        ),
        (
            '    """Bulk accept pending registrations."""',
            '''    """Bulk accept pending registrations with capacity and waitlist handling (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. For each pending registration ID:
       a. Skip if not pending or not in this hackathon.
       b. If at capacity and waitlist enabled, move to waitlisted.
       c. If at capacity and waitlist disabled, skip.
       d. Otherwise accept, increment current_participants, and set accepted_at.
    3. Commit and return accepted and waitlisted counts.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Registration rows and Hackathon.current_participants.
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-accept, organizer registration panel.
    """''',
        ),
        (
            '    """Bulk reject pending/waitlisted registrations."""',
            '''    """Bulk reject pending or waitlisted registrations (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. For each registration ID, skip if not pending or waitlisted.
    3. Set status to rejected for matching registrations.
    4. Commit and return the rejected count.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Registration.status.
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-reject, organizer registration panel.
    """''',
        ),
        (
            '    """Bulk waitlist pending registrations."""',
            '''    """Bulk waitlist pending registrations (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Reject if waitlist is not enabled for the hackathon.
    3. For each pending registration ID, skip if not pending.
    4. Set status to waitlisted.
    5. Commit and return the waitlisted count.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer, HTTPException(400) if waitlist disabled.
    Side Effects: Mutates Registration.status.
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-waitlist, organizer registration panel.
    """''',
        ),
        (
            '    """Export all registrations to CSV (organizer only)."""',
            '''    """Export all hackathon registrations to CSV (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Query all registrations joined with user info, ordered by registration date.
    3. Write CSV rows with full registration and user fields.
    4. Return the CSV as a StreamingResponse download.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only, generates CSV in memory).
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.User, fastapi.responses.StreamingResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations/export, organizer data export.
    """''',
        ),
        (
            '    """Create and send an announcement to all hackathon participants (organizer only)."""',
            '''    """Create and broadcast an announcement to all hackathon participants (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Create an Announcement record from the request body.
    3. Persist and return the announcement.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Inserts Announcement row.
    Dependencies: app.models.Hackathon, app.models.Announcement, app.schemas.AnnouncementCreate, app.schemas.AnnouncementResponse.
    Consumers: POST /api/hackathons/{hackathon_id}/announcements, organizer communication panel.
    """''',
        ),
        (
            '    """List announcements for a hackathon. Organizers see all, participants see accepted ones."""',
            '''    """List announcements for a hackathon with role-based filtering.

    Behavior:
    1. Verify the user has access (organizer or registered participant).
    2. Load all announcements for the hackathon.
    3. Filter out draft announcements for non-organizers.
    4. Order by sent_at descending and return.

    Raises: HTTPException(403) if user lacks access.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.Announcement, app.schemas.AnnouncementResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/announcements, participant and organizer announcement feeds.
    """''',
        ),
        (
            '    """Declare a conflict of interest for a submission (judge only)."""',
            '''    """Declare a conflict of interest for a submission (judge only).

    Behavior:
    1. Verify the user is a judge.
    2. Verify the hackathon and submission exist.
    3. Reject if a conflict already exists for this judge and submission.
    4. Create and persist the ConflictOfInterest record.
    5. Return the created conflict.

    Raises: HTTPException(403) if not a judge, HTTPException(404) if hackathon or submission not found, HTTPException(409) if conflict already declared.
    Side Effects: Inserts ConflictOfInterest row.
    Dependencies: app.models.Hackathon, app.models.Submission, app.models.ConflictOfInterest, app.models.UserRole, app.schemas.ConflictOfInterestCreate, app.schemas.ConflictOfInterestResponse.
    Consumers: POST /api/hackathons/{hackathon_id}/conflicts-of-interest, judge dashboard.
    """''',
        ),
        (
            '    """List all conflicts of interest for a hackathon (organizer only)."""',
            '''    """List all conflicts of interest for a hackathon (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Query all ConflictOfInterest rows for the hackathon.
    3. Return serialized conflict records.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.schemas.ConflictOfInterestResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/conflicts-of-interest, organizer judging panel.
    """''',
        ),
        (
            '    """Remove a conflict of interest declaration (organizer or the judge who created it)."""',
            '''    """Remove a conflict of interest declaration.

    Behavior:
    1. Load the conflict record by ID and hackathon ID.
    2. Verify the requesting user is either the hackathon organizer or the judge who created the conflict.
    3. Delete the record and commit.
    4. Return confirmation.

    Raises: HTTPException(404) if conflict not found, HTTPException(403) if user unauthorized.
    Side Effects: Deletes ConflictOfInterest row.
    Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.models.UserRole.
    Consumers: DELETE /api/hackathons/{hackathon_id}/conflicts-of-interest/{coi_id}, organizer or judge dashboard.
    """''',
        ),
        (
            '    """List all organizers for a hackathon (primary + co-organizers)."""',
            '''    """List all organizers for a hackathon (primary + co-organizers).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Load the primary organizer user record.
    3. Load all co-organizers joined with their user records.
    4. Return a consolidated list with roles and metadata.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
    Consumers: GET /api/hackathons/{hackathon_id}/organizers, organizer team management page.
    """''',
        ),
        (
            '    """Add a co-organizer to the hackathon (primary organizer only)."""',
            '''    """Add a co-organizer to the hackathon (primary organizer only).

    Behavior:
    1. Verify the hackathon exists and the requesting user is the primary organizer.
    2. Require an email in the request body.
    3. Lookup the target user by email.
    4. Reject if target is the primary organizer or already a co-organizer.
    5. Create a HackathonOrganizer record and commit.
    6. Return the new co-organizer summary.

    Raises: HTTPException(404) if hackathon or user not found, HTTPException(403) if not primary organizer, HTTPException(400) for self-add, HTTPException(409) if already co-organizer.
    Side Effects: Inserts HackathonOrganizer row.
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
    Consumers: POST /api/hackathons/{hackathon_id}/organizers, organizer team management page.
    """''',
        ),
        (
            '    """Remove a co-organizer (primary organizer only)."""',
            '''    """Remove a co-organizer from the hackathon (primary organizer only).

    Behavior:
    1. Verify the hackathon exists and the requesting user is the primary organizer.
    2. Reject if attempting to remove the primary organizer.
    3. Find and delete the HackathonOrganizer record for the target user.
    4. Commit and return confirmation.

    Raises: HTTPException(404) if hackathon or co-organizer not found, HTTPException(403) if not primary organizer, HTTPException(400) if attempting self-removal.
    Side Effects: Deletes HackathonOrganizer row.
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer.
    Consumers: DELETE /api/hackathons/{hackathon_id}/organizers/{user_id}, organizer team management page.
    """''',
        ),
        (
            '    """Scrape the Devpost hackathon gallery and import project URLs for analysis."""',
            '''    """Scrape a Devpost hackathon gallery and import project URLs for analysis (organizer only).

    Behavior:
    1. Verify the user is an organizer and the hackathon exists with a configured Devpost URL.
    2. Paginate through the Devpost project gallery up to 20 pages.
    3. Extract all unique project URLs using regex and CSS selectors.
    4. Skip URLs already imported for this hackathon.
    5. Create pending Submission records with anonymous tokens.
    6. Trigger background analysis for each new submission.
    7. Return import counts (found, imported, skipped).

    Raises: HTTPException(403) if not organizer, HTTPException(404) if hackathon not found or no Devpost URL, HTTPException(404) if no projects found, HTTPException(502) if gallery fetch fails.
    Side Effects: Inserts Submission rows; spawns background asyncio tasks.
    Dependencies: app.models.Hackathon, app.models.Submission, app.models.SubmissionStatus, app.analyzer.analyze_submission, app.auth.create_anonymous_token, httpx.AsyncClient, bs4.BeautifulSoup.
    Consumers: POST /api/hackathons/{hackathon_id}/import-devpost, organizer submission import tool.
    """''',
        ),
    ],
    "backend/app/routes/judging.py": [
        (
            '    """Raise if judging window is not active."""',
            '''    """Enforce that the judging session is within its active time window.

    Behavior:
    1. Get current UTC time.
    2. Normalize session start and end times to UTC.
    3. Raise 403 if judging has not opened yet (pending and now < start).
    4. Raise 403 if judging window has closed (status closed or now > end).

    Raises: HTTPException(403) if outside the active judging window.
    Side Effects: None (pure validation).
    Dependencies: app.models.JudgingSession, app.models.JudgingSessionStatus.
    Consumers: Internal helper used by assignment opening, scoring, and detail routes.
    """''',
        ),
        (
            '    """Weighted raw score 0-100 from a set of scores against rubric criteria."""',
            '''    """Compute a weighted raw score (0-100) from Score rows against RubricCriterion weights.

    Behavior:
    1. Iterate over provided scores.
    2. For each score, look up the matching criterion in the criteria_map.
    3. Normalize the score by max_score and multiply by criterion weight.
    4. Sum and return the total weighted score.

    Raises: None
    Side Effects: None (pure function).
    Dependencies: app.models.Score, app.models.RubricCriterion.
    Consumers: _elo_update pipeline, get_judging_results, get_judging_queue.
    """''',
        ),
        (
            '    """Create or replace a judging session with rubric criteria for a hackathon."""',
            '''    """Create or replace a judging session with rubric criteria for a hackathon (organizer only).

    Behavior:
    1. Verify the hackathon exists.
    2. Validate that criteria weights sum to exactly 100.
    3. Delete any existing JudgingSession (cascade deletes rubric, criteria, assignments).
    4. Create a new JudgingSession with timing and leaderboard settings.
    5. Create a Rubric and linked RubricCriterion rows.
    6. Commit and return the full session configuration.

    Raises: HTTPException(404) if hackathon not found, HTTPException(422) if weights do not sum to 100.
    Side Effects: Deletes old session cascade; inserts JudgingSession, Rubric, and RubricCriterion rows.
    Dependencies: app.models.Hackathon, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.schemas.JudgingSessionCreate.
    Consumers: POST /api/hackathons/{hackathon_id}/judging/session, organizer judging setup.
    """''',
        ),
        (
            '    """Get the judging session configuration for a hackathon."""',
            '''    """Get the judging session configuration for a hackathon.

    Behavior:
    1. Load the JudgingSession for the hackathon via _get_judging_session.
    2. Return the full session detail including rubric and criteria.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: None (read-only).
    Dependencies: _get_judging_session, _session_detail.
    Consumers: GET /api/hackathons/{hackathon_id}/judging/session, judging config UI.
    """''',
        ),
        (
            '    """Assign judges to submissions. Body: {"judge_ids": [...], "submission_ids": [...]}.\n\n    Creates assignments for every judge×submission pair.\n    Automatically creates JudgeRating records for new judges.\n    """',
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
            '    """List assignments for a judging session. Filter by judge_id query param."""',
            '''    """List judge assignments for a hackathon judging session.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Build a query filtering by session, optionally by judge_id, and optionally excluding completed assignments.
    3. Load related Submission details for each assignment.
    4. Return serialized assignment list with project metadata.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: None (read-only).
    Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.Submission.
    Consumers: GET /hackathons/{hackathon_id}/judging/assignments, judge and organizer dashboards.
    """''',
        ),
        (
            '    """Get full assignment detail including submission info, rubric criteria, and existing scores."""',
            '''    """Get full assignment detail including submission info, rubric criteria, and existing scores.

    Behavior:
    1. Load the JudgeAssignment by ID with eager-loaded session, rubric, and criteria.
    2. Return 404 if assignment not found.
    3. Enforce the judging time window.
    4. Load the related Submission.
    5. Load existing Score rows and map them by criterion_id.
    6. Build the criteria list with current scores.
    7. Return the complete assignment payload.

    Raises: HTTPException(404) if assignment not found, HTTPException(403) if outside time window.
    Side Effects: None (read-only).
    Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, app.models.Submission, _enforce_time_window.
    Consumers: GET /judging/assignments/{assignment_id}, frontend judging form.
    """''',
        ),
        (
            '    """Mark an assignment as opened by the judge (starts the timer)."""',
            '''    """Mark a judge assignment as opened and initialize blank score records.

    Behavior:
    1. Load the JudgeAssignment by ID; 404 if not found.
    2. Load the parent JudgingSession and enforce the time window.
    3. Set opened_at to now if not already set.
    4. Create blank Score rows for each rubric criterion if not already present.
    5. Commit and return the opened state.

    Raises: HTTPException(404) if assignment not found, HTTPException(403) if outside time window.
    Side Effects: Mutates JudgeAssignment.opened_at; inserts Score rows.
    Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, _enforce_time_window.
    Consumers: POST /judging/assignments/{assignment_id}/open, frontend judging flow.
    """''',
        ),
        (
            '    """Submit or update scores for an assignment. Can be called incrementally.\n\n    Auto-submits (marks complete) when all criteria have non-null scores.\n    Also checks per_project_seconds soft deadline.\n    """',
            '''    """Submit or update scores for a judge assignment.

    Behavior:
    1. Load the JudgeAssignment by ID; 404 if not found.
    2. Reject if the assignment is already completed (400).
    3. Load the parent JudgingSession and enforce its time window.
    4. Flag as late if elapsed time exceeds per_project_seconds.
    5. Load the Rubric and validate each criterion ID and score range (0–max_score).
    6. Upsert Score rows for each criterion.
    7. If all criteria now have scores, mark the assignment completed and update submitted_at.
    8. Commit and return the updated assignment state.

    Raises: HTTPException(404, 400, 422)
    Side Effects: Inserts or updates Score rows; may mutate JudgeAssignment.is_completed, submitted_at, and auto-submit null scores as 0 when late.
    Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, _enforce_time_window.
    Consumers: POST /judging/assignments/{assignment_id}/score, frontend judging form.
    """''',
        ),
        (
            '    """Return (new_elo_a, new_elo_b) after a pairwise comparison.\n    outcome: 1.0 = A wins, 0.5 = tie, 0.0 = B wins."""',
            '''    """Return (new_elo_a, new_elo_b) after a pairwise ELO comparison.

    Behavior:
    1. Compute expected scores e_a and e_b from the current ratings.
    2. Calculate rating deltas using the K-factor and actual outcome.
    3. Return updated ratings as a tuple.

    Raises: None
    Side Effects: None (pure function).
    Dependencies: _expected_score.
    Consumers: _update_elo_pairwise, get_judging_results, get_judging_queue.
    """''',
        ),
        (
            '    """Compute and return ELO rankings for the hackathon.\n\n    Algorithm:\n      1. Load all completed assignments with scores.\n      2. Compute raw weighted score per (judge, submission).\n      3. Z-score normalize within each judge (judge severity correction).\n      4. Within-judge pairwise ELO updates.\n      5. Cross-judge bridging via submissions scored by multiple judges.\n      6. Return final ELO rankings.\n    """',
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
            '    """Return a priority-ordered list of submissions that need more judging.\n\n    Query params:\n      - judge_id (required): only return projects this judge hasn\'t scored\n      - min_judges (default 3): minimum judge count before coverage is satisfied\n\n    Each item includes:\n      - submission info (id, title, url)\n      - current ELO\n      - uncertainty breakdown (variance, proximity, coverage)\n      - priority score (higher = needs judging more urgently)\n    """',
            '''    """Return a priority-ordered list of submissions that need more judging.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Parse judge_id from query param.
    3. Load all completed assignments with scores and build submission coverage maps.
    4. Identify pending assignments for the requesting judge.
    5. Compute uncertainty metrics (variance, proximity, coverage) per submission.
    6. Sort by uncertainty total descending (higher = needs judging more urgently).
    7. Return the queue, count already scored by this judge, and a message if empty.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: None (read-only).
    Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.Submission, app.models.Score, _compute_raw_score, _elo_update.
    Consumers: GET /hackathons/{hackathon_id}/judging/queue, frontend judge dashboard.
    """''',
        ),
        (
            '    """Create new assignments for projects flagged by the ELO uncertainty engine.\n\n    For each submission with fewer than min_judges scores, creates a new\n    JudgeAssignment for every judge who hasn\'t scored it yet.\n    Preserves existing scores (each round gets new assignment records).\n    """',
            '''    """Create new assignments for projects flagged by the ELO uncertainty engine.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Load all judge IDs with role=judge.
    3. Load all completed submission IDs for the hackathon.
    4. Load completed assignments and build a map of who scored what.
    5. For each submission with fewer than min_judges scores, create new JudgeAssignments for judges who haven't scored it.
    6. Also flag submissions with high score variance (>15% CV) among existing judges.
    7. Commit and return the count of newly created assignments.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: Inserts new JudgeAssignment rows.
    Dependencies: _get_judging_session, app.models.User, app.models.Submission, app.models.JudgeAssignment, app.models.JudgeRating.
    Consumers: POST /hackathons/{hackathon_id}/judging/rerun, organizer judging panel.
    """''',
        ),
        (
            '    """Activate judging and auto-assign all judges to all completed submissions."""',
            '''    """Activate a judging session and auto-assign all judges to completed submissions.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Set session status to active.
    3. Load all judge IDs and all completed submission IDs for the hackathon.
    4. Ensure each judge has a JudgeRating record.
    5. Create pending JudgeAssignment rows for every judge×submission pair not already assigned.
    6. Commit and return activation summary.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: Mutates JudgingSession.status; inserts JudgeAssignment and JudgeRating rows.
    Dependencies: _get_judging_session, app.models.User, app.models.Submission, app.models.JudgeAssignment, app.models.JudgeRating, app.models.JudgingSessionStatus.
    Consumers: POST /hackathons/{hackathon_id}/judging/activate, organizer judging setup.
    """''',
        ),
        (
            '    """Manually close judging to prevent further scoring."""',
            '''    """Manually close a judging session to prevent further scoring.

    Behavior:
    1. Load the JudgingSession for the hackathon; 404 if missing.
    2. Set session status to closed.
    3. Commit and return the closed state.

    Raises: HTTPException(404) if no judging session exists.
    Side Effects: Mutates JudgingSession.status.
    Dependencies: _get_judging_session, app.models.JudgingSession, app.models.JudgingSessionStatus.
    Consumers: POST /hackathons/{hackathon_id}/judging/close, organizer judging setup.
    """''',
        ),
    ],
}


def apply_replacements():
    for rel_path, fixes in REPLACEMENTS.items():
        path = os.path.join(HERE, rel_path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        applied = 0
        for old, new in fixes:
            if old in content:
                content = content.replace(old, new)
                applied += 1
            else:
                print(f"MISSING in {rel_path}: {old[:80]}...")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{rel_path}: applied {applied}/{len(fixes)}")


if __name__ == "__main__":
    apply_replacements()
