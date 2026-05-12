"""Judging service: session management, rubrics, judge assignment, scoring, and ELO rankings.

Extracted from app.routes.judging to provide a clean service layer for all
judging-related business logic. Routes should remain thin, handling only
HTTP concerns (auth, validation, response formatting).
"""

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Hackathon,
    JudgeAssignment,
    JudgeRating,
    JudgingSession,
    JudgingSessionStatus,
    Rubric,
    RubricCriterion,
    Score,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)
from app.schemas import JudgingSessionCreate
from app.services.event_service import publish_event


K_FACTOR = 32
BASE_ELO = 1500


class JudgingService:
    """Service for managing hackathon judging sessions, assignments, and rankings.

    Provides CRUD operations for judging sessions with rubric criteria, judge
    assignment to submissions, score entry with time-window enforcement, ELO-based
    ranking computation, and priority queue generation for judges.
    """

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def get_session(self, db: AsyncSession, hackathon_id: uuid.UUID) -> JudgingSession | None:
        """Load the judging session for a hackathon with rubric and criteria.

        Behavior:
        1. Query the database for a JudgingSession matching ``hackathon_id``.
        2. Eagerly load the rubric and its criteria via ``selectinload``.
        3. Return the session object or None if not found.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, sqlalchemy.orm.selectinload, app.models.JudgingSession, app.models.Rubric.
        Consumers: Judging route handlers, internal helpers.
        """
        result = await db.execute(
            select(JudgingSession)
            .where(JudgingSession.hackathon_id == hackathon_id)
            .options(selectinload(JudgingSession.rubric).selectinload(Rubric.criteria))
        )
        return result.scalar_one_or_none()

    async def create_or_replace_session(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        body: JudgingSessionCreate,
    ) -> dict:
        """Create or replace a judging session with rubric criteria for a hackathon.

        Behavior:
        1. Verify the hackathon exists.
        2. Validate that criteria weights sum to exactly 100.
        3. Delete any existing JudgingSession (cascade deletes rubric, criteria, assignments).
        4. Create a new JudgingSession with timing and leaderboard settings.
        5. Create a Rubric and linked RubricCriterion rows.
        6. Commit, publish an event, and return the full session configuration.

        Raises: ValueError if hackathon not found or weights do not sum to 100.
        Side Effects: Deletes old session cascade; inserts JudgingSession, Rubric, and RubricCriterion rows.
        Dependencies: app.models.Hackathon, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.schemas.JudgingSessionCreate.
        Consumers: POST /api/hackathons/{hackathon_id}/judging/session.
        """
        # Verify hackathon exists
        hk = await db.get(Hackathon, hackathon_id)
        if not hk:
            raise ValueError("Hackathon not found")

        # Validate total weight = 100
        total_weight = sum(c.weight for c in body.criteria)
        if total_weight != 100:
            raise ValueError(f"Criteria weights must sum to 100, got {total_weight}")

        # Delete existing session if any (cascade handles rubric/criteria/assignments)
        existing = await db.execute(select(JudgingSession).where(JudgingSession.hackathon_id == hackathon_id))
        old = existing.scalar_one_or_none()
        if old:
            await db.delete(old)
            await db.flush()

        # Create session
        session = JudgingSession(
            hackathon_id=hackathon_id,
            start_time=body.start_time,
            end_time=body.end_time,
            per_project_seconds=body.per_project_seconds,
            leaderboard_public=body.leaderboard_public,
        )
        db.add(session)
        await db.flush()

        # Create rubric
        rubric = Rubric(session_id=session.id, name=f"Rubric for {hk.name}")
        db.add(rubric)
        await db.flush()

        # Create criteria
        criteria_created = []
        for i, c in enumerate(body.criteria):
            criterion = RubricCriterion(
                rubric_id=rubric.id,
                name=c.name,
                description=c.description,
                max_score=c.max_score,
                weight=c.weight,
                sort_order=c.sort_order or i,
            )
            db.add(criterion)
            criteria_created.append(criterion)
        await db.commit()

        await publish_event(
            db,
            "judging.session_started",
            {"hackathon_id": str(hackathon_id), "session_id": str(session.id)},
        )

        return self._session_detail_from_parts(session, rubric, criteria_created)

    async def close_session(self, db: AsyncSession, hackathon_id: uuid.UUID) -> dict:
        """Manually close a judging session to prevent further scoring.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Set session status to closed.
        3. Commit and return the closed state.

        Raises: ValueError if no judging session exists.
        Side Effects: Mutates JudgingSession.status.
        Consumers: POST /api/hackathons/{hackathon_id}/judging/close.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")
        session.status = JudgingSessionStatus.closed
        await db.commit()
        return {"status": "closed"}

    # ------------------------------------------------------------------
    # Judge assignment
    # ------------------------------------------------------------------

    async def assign_judges(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        judge_ids: list[uuid.UUID],
        submission_ids: list[uuid.UUID],
    ) -> dict:
        """Assign judges to submissions for a hackathon judging session.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Verify all submission IDs belong to this hackathon.
        3. Mark existing assignments for this session as old (is_completed = -1).
        4. Ensure each judge has a JudgeRating record, creating one if missing.
        5. Create new JudgeAssignment rows for every judge x submission pair.
        6. Commit and return the count of created assignments.

        Raises: ValueError if no session exists, judge_ids or submission_ids are empty, or submissions are invalid.
        Side Effects: Updates existing JudgeAssignment rows; inserts JudgeRating and JudgeAssignment rows.
        Consumers: POST /api/hackathons/{hackathon_id}/judging/assign.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        if not judge_ids or not submission_ids:
            raise ValueError("judge_ids and submission_ids required")

        # Verify submissions belong to this hackathon
        result = await db.execute(
            select(Submission.id).where(
                Submission.id.in_(submission_ids),
                Submission.hackathon_id == hackathon_id,
            )
        )
        valid_ids = {row[0] for row in result.all()}
        invalid = [s for s in submission_ids if s not in valid_ids]
        if invalid:
            raise ValueError(f"Submissions not in hackathon: {invalid}")

        # Delete existing assignments for this session (replace)
        await db.execute(
            update(JudgeAssignment).where(JudgeAssignment.session_id == session.id).values(is_completed=-1)
        )

        created = 0
        for judge_id in judge_ids:
            # Ensure judge rating record exists
            existing_rating = await db.execute(
                select(JudgeRating).where(
                    JudgeRating.judge_id == judge_id,
                    JudgeRating.hackathon_id == hackathon_id,
                )
            )
            if not existing_rating.scalar_one_or_none():
                db.add(JudgeRating(judge_id=judge_id, hackathon_id=hackathon_id))

            for submission_id in submission_ids:
                db.add(
                    JudgeAssignment(
                        session_id=session.id,
                        judge_id=judge_id,
                        submission_id=submission_id,
                    )
                )
                created += 1

        await db.commit()
        return {"assigned": created, "judges": len(judge_ids), "submissions": len(submission_ids)}

    async def list_assignments(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        judge_id: str | None = None,
        include_completed: bool = False,
    ) -> list[dict]:
        """List judge assignments for a hackathon judging session.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Build a query filtering by session, optionally by judge_id, and optionally excluding completed assignments.
        3. Load related Submission details for each assignment.
        4. Return serialized assignment list with project metadata.

        Raises: ValueError if no judging session exists.
        Side Effects: None (read-only).
        Consumers: GET /api/hackathons/{hackathon_id}/judging/assignments.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        query = select(JudgeAssignment).where(JudgeAssignment.session_id == session.id)
        if not include_completed:
            query = query.where(JudgeAssignment.is_completed == 0)
        if judge_id:
            query = query.where(JudgeAssignment.judge_id == judge_id)

        result = await db.execute(query)
        assignments = result.scalars().all()

        # Fetch submission details for each assignment
        sub_ids = [a.submission_id for a in assignments]
        submissions = {}
        if sub_ids:
            sub_result = await db.execute(select(Submission).where(Submission.id.in_(sub_ids)))
            for s in sub_result.scalars().all():
                submissions[str(s.id)] = s

        return [
            {
                "id": str(a.id),
                "judge_id": str(a.judge_id),
                "submission_id": str(a.submission_id),
                "opened_at": a.opened_at.isoformat() if a.opened_at else None,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "is_completed": bool(a.is_completed),
                "project_title": submissions.get(str(a.submission_id)).project_title
                if submissions.get(str(a.submission_id))
                else None,
                "devpost_url": submissions.get(str(a.submission_id)).devpost_url
                if submissions.get(str(a.submission_id))
                else None,
                "github_url": submissions.get(str(a.submission_id)).github_url
                if submissions.get(str(a.submission_id))
                else None,
            }
            for a in assignments
        ]

    # ------------------------------------------------------------------
    # Assignment detail / open / score
    # ------------------------------------------------------------------

    async def get_assignment_detail(self, db: AsyncSession, assignment_id: uuid.UUID) -> dict:
        """Get full assignment detail including submission info, rubric criteria, and existing scores.

        Behavior:
        1. Load the JudgeAssignment by ID with eager-loaded session, rubric, and criteria.
        2. Enforce the judging time window.
        3. Load the related Submission.
        4. Load existing Score rows and map them by criterion_id.
        5. Build the criteria list with current scores.
        6. Return the complete assignment payload.

        Raises: ValueError if assignment not found. PermissionError if outside time window.
        Side Effects: None (read-only).
        Consumers: GET /api/judging/assignments/{assignment_id}.
        """
        result = await db.execute(
            select(JudgeAssignment)
            .where(JudgeAssignment.id == assignment_id)
            .options(
                selectinload(JudgeAssignment.session).selectinload(JudgingSession.rubric).selectinload(Rubric.criteria),
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ValueError("Assignment not found")

        session = assignment.session
        self._enforce_time_window(session)

        # Load submission
        sub = await db.get(Submission, assignment.submission_id)

        # Load existing scores for this assignment
        scores_result = await db.execute(select(Score).where(Score.assignment_id == assignment.id))
        existing_scores = {s.criterion_id: s for s in scores_result.scalars().all()}

        rubric = session.rubric
        criteria = []
        if rubric:
            for c in sorted(rubric.criteria, key=lambda x: x.sort_order):
                s = existing_scores.get(c.id)
                criteria.append(
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "description": c.description,
                        "max_score": c.max_score,
                        "weight": c.weight,
                        "score": s.score if s else None,
                    }
                )

        return {
            "id": str(assignment.id),
            "judge_id": str(assignment.judge_id),
            "opened_at": assignment.opened_at.isoformat() if assignment.opened_at else None,
            "is_completed": bool(assignment.is_completed),
            "per_project_seconds": session.per_project_seconds,
            "submission": {
                "id": str(sub.id),
                "project_title": sub.project_title,
                "devpost_url": sub.devpost_url,
                "github_url": sub.github_url,
                "claimed_tech": sub.claimed_tech,
                "team_members": sub.team_members,
            }
            if sub
            else None,
            "criteria": criteria,
        }

    async def open_assignment(self, db: AsyncSession, assignment_id: uuid.UUID) -> dict:
        """Mark a judge assignment as opened and initialize blank score records.

        Behavior:
        1. Load the JudgeAssignment by ID.
        2. Load the parent JudgingSession and enforce the time window.
        3. Set opened_at to now if not already set.
        4. Create blank Score rows for each rubric criterion if not already present.
        5. Commit and return the opened state.

        Raises: ValueError if assignment not found. PermissionError if outside time window.
        Side Effects: Mutates JudgeAssignment.opened_at; inserts Score rows.
        Consumers: POST /api/judging/assignments/{assignment_id}/open.
        """
        assignment = await db.get(JudgeAssignment, assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")

        session = await db.get(JudgingSession, assignment.session_id)
        self._enforce_time_window(session)

        if assignment.opened_at is None:
            assignment.opened_at = datetime.now(UTC)

        # Create blank scores for each criterion if not already present
        rubric = await db.execute(select(Rubric).where(Rubric.session_id == session.id))
        rubric_obj = rubric.scalar_one_or_none()
        if rubric_obj:
            criteria_result = await db.execute(
                select(RubricCriterion).where(RubricCriterion.rubric_id == rubric_obj.id)
            )
            existing_scores = await db.execute(select(Score.criterion_id).where(Score.assignment_id == assignment.id))
            existing_criteria_ids = {row[0] for row in existing_scores.all()}
            for criterion in criteria_result.scalars().all():
                if criterion.id not in existing_criteria_ids:
                    db.add(Score(assignment_id=assignment.id, criterion_id=criterion.id))

        await db.commit()
        return {"opened": True, "opened_at": assignment.opened_at.isoformat()}

    async def submit_scores(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        scores_data: list,
    ) -> dict:
        """Submit or update scores for a judge assignment.

        Behavior:
        1. Load the JudgeAssignment by ID.
        2. Reject if the assignment is already completed.
        3. Load the parent JudgingSession and enforce its time window.
        4. Flag as late if elapsed time exceeds per_project_seconds.
        5. Load the Rubric and validate each criterion ID and score range.
        6. Upsert Score rows for each criterion.
        7. If all criteria now have scores, mark the assignment completed.
        8. Commit, publish event, and return the updated assignment state.

        Raises: ValueError if assignment not found, already completed, or scores are invalid. PermissionError if outside time window.
        Side Effects: Inserts or updates Score rows; may mutate JudgeAssignment.is_completed, submitted_at.
        Consumers: POST /api/judging/assignments/{assignment_id}/score.
        """
        assignment = await db.get(JudgeAssignment, assignment_id)
        if not assignment:
            raise ValueError("Assignment not found")
        if assignment.is_completed:
            raise ValueError("Assignment already completed")

        session = await db.get(JudgingSession, assignment.session_id)
        self._enforce_time_window(session)

        now = datetime.now(UTC)
        is_late = False
        if assignment.opened_at:
            opened = (
                assignment.opened_at.replace(tzinfo=UTC)
                if assignment.opened_at.tzinfo is None
                else assignment.opened_at
            )
            elapsed = (now - opened).total_seconds()
            if elapsed > session.per_project_seconds:
                is_late = True

        # Load rubric to get criteria
        rubric_result = await db.execute(select(Rubric).where(Rubric.session_id == session.id))
        rubric = rubric_result.scalar_one_or_none()
        if not rubric:
            raise ValueError("No rubric found for this session")

        criteria_result = await db.execute(select(RubricCriterion).where(RubricCriterion.rubric_id == rubric.id))
        criteria = {str(c.id): c for c in criteria_result.scalars().all()}

        for item in scores_data:
            cid = str(item["criterion_id"])
            score_val = item["score"]
            if cid not in criteria:
                raise ValueError(f"Unknown criterion: {cid}")
            if score_val is not None and (score_val < 0 or score_val > criteria[cid].max_score):
                raise ValueError(
                    f"Score {score_val} out of range for {criteria[cid].name} (0-{criteria[cid].max_score})"
                )

            # Upsert score
            existing = await db.execute(
                select(Score).where(
                    Score.assignment_id == assignment.id,
                    Score.criterion_id == cid,
                )
            )
            score_row = existing.scalar_one_or_none()
            if score_row:
                score_row.score = score_val
            else:
                db.add(
                    Score(
                        assignment_id=assignment.id,
                        criterion_id=cid,
                        score=score_val,
                    )
                )

        if is_late:
            # Auto-submit
            assignment.submitted_at = now
            assignment.is_completed = 1
            # Mark all null scores as 0
            all_scores = await db.execute(select(Score).where(Score.assignment_id == assignment.id))
            for s in all_scores.scalars().all():
                if s.score is None:
                    s.score = 0
                s.is_auto_submitted = 1
                s.submitted_at = now

        # Check if all criteria scored -> auto-complete
        if not is_late:
            scores_result = await db.execute(select(Score).where(Score.assignment_id == assignment.id))
            scores_list = scores_result.scalars().all()
            all_scored = all(s.score is not None for s in scores_list)
            if all_scored:
                assignment.submitted_at = now
                assignment.is_completed = 1
                for s in scores_list:
                    s.submitted_at = now

        await db.commit()

        await publish_event(
            db,
            "submission.scored",
            {
                "assignment_id": str(assignment.id),
                "submission_id": str(assignment.submission_id),
                "judge_id": str(assignment.judge_id),
                "is_completed": bool(assignment.is_completed),
            },
        )

        return {
            "submitted": True,
            "is_completed": bool(assignment.is_completed),
            "is_late": is_late,
            "is_auto_submitted": is_late,
        }

    # ------------------------------------------------------------------
    # Results / ELO
    # ------------------------------------------------------------------

    async def compute_results(self, db: AsyncSession, hackathon_id: uuid.UUID) -> dict:
        """Compute and return ELO rankings for a hackathon.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Load all completed assignments with eager-loaded scores.
        3. Compute raw weighted scores per (judge, submission) using rubric criteria weights.
        4. Z-score normalize within each judge to correct for severity bias.
        5. Run within-judge pairwise ELO updates.
        6. Bridge across judges via submissions scored by multiple judges.
        7. Return final ELO rankings sorted by score descending.

        Raises: ValueError if no judging session exists.
        Side Effects: None (read-only).
        Consumers: GET /api/hackathons/{hackathon_id}/judging/results.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        # Load all completed assignments with scores
        assignments_result = await db.execute(
            select(JudgeAssignment)
            .where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.is_completed == 1,
            )
            .options(selectinload(JudgeAssignment.scores))
        )
        assignments = assignments_result.scalars().all()

        if not assignments:
            return {"hackathon_id": str(hackathon_id), "rankings": [], "error": "No completed scores yet"}

        # Build criteria map
        criteria_map = {}
        if session.rubric:
            for c in session.rubric.criteria:
                criteria_map[c.id] = c

        # Step 1: raw weighted scores per (judge, submission)
        raw_scores: dict = {}
        judge_sub_count: dict = {}

        for a in assignments:
            jid = str(a.judge_id)
            sid = str(a.submission_id)
            raw = self._compute_raw_score(a.scores, criteria_map)
            raw_scores.setdefault(jid, {})[sid] = raw
            judge_sub_count[jid] = judge_sub_count.get(jid, 0) + 1

        # Step 2: z-score normalize within each judge
        norm_scores: dict = {}
        judge_stats: dict = {}

        for jid, scores_map in raw_scores.items():
            vals = list(scores_map.values())
            n = len(vals)
            mean = sum(vals) / n
            variance = sum((v - mean) ** 2 for v in vals) / n
            stddev = math.sqrt(variance) if variance > 0 else 1.0

            judge_stats[jid] = {"mean": round(mean, 2), "stddev": round(stddev, 2), "n_projects": n}

            for sid, raw in scores_map.items():
                z = (raw - mean) / stddev if stddev > 0 else 0.0
                norm_scores[(jid, sid)] = z

        # Step 3: initialize ELO for all submissions at BASE_ELO
        all_submissions = set()
        for jid, scores_map in raw_scores.items():
            all_submissions.update(scores_map.keys())

        elo = {sid: float(BASE_ELO) for sid in all_submissions}

        # Step 4: within-judge pairwise ELO updates
        for jid, scores_map in raw_scores.items():
            sub_list = list(scores_map.keys())
            for i in range(len(sub_list)):
                for j in range(i + 1, len(sub_list)):
                    a_sid, b_sid = sub_list[i], sub_list[j]
                    z_a = norm_scores.get((jid, a_sid), 0.0)
                    z_b = norm_scores.get((jid, b_sid), 0.0)

                    if abs(z_a - z_b) < 0.1:
                        outcome = 0.5
                    elif z_a > z_b:
                        outcome = 1.0
                    else:
                        outcome = 0.0

                    elo[a_sid], elo[b_sid] = self._elo_update(elo[a_sid], elo[b_sid], outcome)

        # Step 5: cross-judge bridging
        sub_z_scores: dict[str, list[float]] = {}
        for (jid, sid), z in norm_scores.items():
            sub_z_scores.setdefault(sid, []).append(z)

        sub_avg_z = {sid: sum(zs) / len(zs) for sid, zs in sub_z_scores.items()}

        sub_ids = list(elo.keys())
        for i in range(len(sub_ids)):
            for j in range(i + 1, len(sub_ids)):
                a_sid, b_sid = sub_ids[i], sub_ids[j]
                z_a = sub_avg_z.get(a_sid, 0.0)
                z_b = sub_avg_z.get(b_sid, 0.0)

                if abs(z_a - z_b) < 0.05:
                    outcome = 0.5
                elif z_a > z_b:
                    outcome = 1.0
                else:
                    outcome = 0.0

                elo[a_sid], elo[b_sid] = self._elo_update(elo[a_sid], elo[b_sid], outcome, k=16)

        # Build rankings
        sub_ids_list = list(elo.keys())
        subs_result = await db.execute(
            select(Submission.id, Submission.project_title).where(Submission.id.in_(sub_ids_list))
        )
        sub_titles = {str(row[0]): row[1] for row in subs_result.all()}

        rankings = sorted(
            [
                {
                    "submission_id": sid,
                    "project_title": sub_titles.get(sid, "Unknown"),
                    "elo": round(e, 1),
                    "raw_avg": round(
                        sum(raw_scores.get(jid, {}).get(sid, 0) for jid in raw_scores)
                        / max(1, sum(1 for jid in raw_scores if sid in raw_scores.get(jid, {}))),
                        1,
                    ),
                    "judges": sum(1 for jid in raw_scores if sid in raw_scores.get(jid, {})),
                }
                for sid, e in elo.items()
            ],
            key=lambda x: x["elo"],
            reverse=True,
        )

        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        # Load judge names for stats
        judge_ids = list(judge_stats.keys())
        users_result = await db.execute(select(User.id, User.name).where(User.id.in_(judge_ids)))
        user_names = {str(row[0]): row[1] for row in users_result.all()}

        judge_stats_detail = [
            {
                "judge_id": jid,
                "name": user_names.get(jid, "Unknown"),
                **stats,
            }
            for jid, stats in judge_stats.items()
        ]

        return {
            "hackathon_id": str(hackathon_id),
            "rankings": rankings,
            "judge_stats": judge_stats_detail,
        }

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    async def get_queue(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        judge_id: str,
        min_judges: int = 3,
    ) -> dict:
        """Return a priority-ordered list of submissions that need more judging.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Load all completed assignments with scores and build submission coverage maps.
        3. Identify pending assignments for the requesting judge.
        4. Compute uncertainty metrics (variance, proximity, coverage) per submission.
        5. Sort by uncertainty total descending (higher = needs judging more urgently).
        6. Return the queue, count already scored by this judge, and a message if empty.

        Raises: ValueError if no judging session exists.
        Side Effects: None (read-only).
        Consumers: GET /api/hackathons/{hackathon_id}/judging/queue.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        # Build criteria map
        criteria_map = {}
        if session.rubric:
            for c in session.rubric.criteria:
                criteria_map[c.id] = c

        # Load all completed assignments with scores
        assignments_result = await db.execute(
            select(JudgeAssignment)
            .where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.is_completed == 1,
            )
            .options(selectinload(JudgeAssignment.scores))
        )
        assignments = assignments_result.scalars().all()

        # Get all completed submissions for this hackathon
        subs_result = await db.execute(
            select(Submission).where(
                Submission.hackathon_id == hackathon_id,
                Submission.status == SubmissionStatus.completed,
            )
        )
        all_submissions = {str(s.id): s for s in subs_result.scalars().all()}

        if not all_submissions:
            return {"queue": [], "scored_by_you": 0, "message": "No completed submissions yet"}

        # Look up pending assignments for this judge
        pending_assignments_result = await db.execute(
            select(JudgeAssignment).where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.judge_id == judge_id,
                JudgeAssignment.is_completed == 0,
            )
        )
        pending_assignment_map = {str(a.submission_id): str(a.id) for a in pending_assignments_result.scalars().all()}

        if not assignments:
            queue = []
            for sid, sub in all_submissions.items():
                queue.append(
                    {
                        "assignment_id": pending_assignment_map.get(sid),
                        "submission_id": sid,
                        "project_title": sub.project_title,
                        "devpost_url": sub.devpost_url,
                        "github_url": sub.github_url,
                        "elo": 1500.0,
                        "uncertainty": {
                            "total": 100.0,
                            "variance": 0.0,
                            "proximity": 0.0,
                            "coverage": 100.0,
                        },
                        "judge_count": 0,
                        "reasons": ["needs_coverage"],
                    }
                )
            return {"queue": queue, "min_judges": min_judges, "total_submissions": len(queue), "scored_by_you": 0}

        # Step 1: raw weighted scores per (judge, submission)
        raw_scores: dict = {}
        for a in assignments:
            jid = str(a.judge_id)
            sid = str(a.submission_id)
            raw = self._compute_raw_score(a.scores, criteria_map)
            raw_scores.setdefault(jid, {})[sid] = raw

        # Step 2: z-score normalize within each judge
        norm_scores: dict = {}
        for jid, scores_map in raw_scores.items():
            vals = list(scores_map.values())
            n = len(vals)
            mean = sum(vals) / n
            variance = sum((v - mean) ** 2 for v in vals) / n
            stddev = math.sqrt(variance) if variance > 0 else 1.0
            for sid, raw in scores_map.items():
                norm_scores[(jid, sid)] = (raw - mean) / stddev if stddev > 0 else 0.0

        # Step 3: compute ELO
        all_scored_ids = set()
        for jid, scores_map in raw_scores.items():
            all_scored_ids.update(scores_map.keys())

        elo = {sid: float(BASE_ELO) for sid in all_scored_ids}

        for jid, scores_map in raw_scores.items():
            sub_list = list(scores_map.keys())
            for i in range(len(sub_list)):
                for j in range(i + 1, len(sub_list)):
                    a_sid, b_sid = sub_list[i], sub_list[j]
                    z_a = norm_scores.get((jid, a_sid), 0.0)
                    z_b = norm_scores.get((jid, b_sid), 0.0)
                    if abs(z_a - z_b) < 0.1:
                        outcome = 0.5
                    elif z_a > z_b:
                        outcome = 1.0
                    else:
                        outcome = 0.0
                    elo[a_sid], elo[b_sid] = self._elo_update(elo[a_sid], elo[b_sid], outcome)

        # Cross-judge bridging
        sub_z_scores: dict[str, list[float]] = {}
        for (jid, sid), z in norm_scores.items():
            sub_z_scores.setdefault(sid, []).append(z)
        sub_avg_z = {sid: sum(zs) / len(zs) for sid, zs in sub_z_scores.items()}

        sub_ids = list(elo.keys())
        for i in range(len(sub_ids)):
            for j in range(i + 1, len(sub_ids)):
                a_sid, b_sid = sub_ids[i], sub_ids[j]
                z_a = sub_avg_z.get(a_sid, 0.0)
                z_b = sub_avg_z.get(b_sid, 0.0)
                if abs(z_a - z_b) < 0.05:
                    outcome = 0.5
                elif z_a > z_b:
                    outcome = 1.0
                else:
                    outcome = 0.0
                elo[a_sid], elo[b_sid] = self._elo_update(elo[a_sid], elo[b_sid], outcome, k=16)

        # Step 4: find submissions the requesting judge has already scored
        scored_by_judge = set()
        for a in assignments:
            if str(a.judge_id) == judge_id:
                scored_by_judge.add(str(a.submission_id))

        # Step 5: compute uncertainty scores
        elo_sorted = sorted(elo.items(), key=lambda x: x[1])

        sub_z_variance: dict[str, float] = {}
        for sid, zs in sub_z_scores.items():
            if len(zs) > 1:
                mean_z = sum(zs) / len(zs)
                sub_z_variance[sid] = sum((z - mean_z) ** 2 for z in zs) / len(zs)
            else:
                sub_z_variance[sid] = 0.0

        judge_counts: dict[str, int] = {}
        for jid, sid in norm_scores:
            judge_counts[sid] = judge_counts.get(sid, 0) + 1

        queue_items = []
        max_variance = max(sub_z_variance.values()) if sub_z_variance else 1.0
        max_proximity = 0.0

        proximity_scores: dict[str, float] = {}
        for idx, (sid, e) in enumerate(elo_sorted):
            if idx == 0:
                gap = elo_sorted[1][1] - e if len(elo_sorted) > 1 else 0
            elif idx == len(elo_sorted) - 1:
                gap = e - elo_sorted[-2][1]
            else:
                gap = min(e - elo_sorted[idx - 1][1], elo_sorted[idx + 1][1] - e)
            proximity_scores[sid] = max(0.0, 25.0 - gap) / 25.0
            max_proximity = max(max_proximity, proximity_scores[sid])

        for sid, sub in all_submissions.items():
            if sid in scored_by_judge:
                continue

            judge_count = judge_counts.get(sid, 0)

            variance_raw = sub_z_variance.get(sid, 0.0)
            variance_score = variance_raw / max(max_variance, 0.001)

            proximity_score = proximity_scores.get(sid, 0.0)
            if max_proximity > 0:
                proximity_score = proximity_score / max_proximity

            coverage_score = max(0.0, 1.0 - judge_count / min_judges)

            total = variance_score * 35.0 + proximity_score * 30.0 + coverage_score * 35.0

            reasons = []
            if variance_raw > 0.3:
                reasons.append("high_variance")
            if proximity_score > 0.5:
                reasons.append("close_race")
            if judge_count < min_judges:
                reasons.append("needs_coverage")
            if not reasons:
                reasons.append("low_priority")

            queue_items.append(
                {
                    "assignment_id": pending_assignment_map.get(sid),
                    "submission_id": sid,
                    "project_title": sub.project_title,
                    "devpost_url": sub.devpost_url,
                    "github_url": sub.github_url,
                    "elo": round(elo.get(sid, BASE_ELO), 1),
                    "uncertainty": {
                        "total": round(total, 1),
                        "variance": round(variance_score * 100, 1),
                        "proximity": round(proximity_score * 100, 1),
                        "coverage": round(coverage_score * 100, 1),
                    },
                    "judge_count": judge_count,
                    "reasons": reasons,
                }
            )

        queue_items.sort(key=lambda x: x["uncertainty"]["total"], reverse=True)

        return {
            "queue": queue_items,
            "min_judges": min_judges,
            "total_submissions": len(all_submissions),
            "scored_by_you": len(scored_by_judge),
        }

    # ------------------------------------------------------------------
    # Rerun / Activate
    # ------------------------------------------------------------------

    async def rerun_judging(self, db: AsyncSession, hackathon_id: uuid.UUID) -> dict:
        """Create new assignments for projects flagged by the ELO uncertainty engine.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Load all judge IDs with role=judge.
        3. Load all completed submission IDs for the hackathon.
        4. Load completed assignments and build a map of who scored what.
        5. Flag submissions with fewer than min_judges scores or high score variance.
        6. Create new JudgeAssignments for judges who haven't scored flagged submissions.
        7. Commit and return the count of newly created assignments.

        Raises: ValueError if no judging session exists.
        Side Effects: Inserts new JudgeAssignment rows.
        Consumers: POST /api/hackathons/{hackathon_id}/judging/rerun.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        judges_result = await db.execute(select(User.id).where(User.role == UserRole.judge))
        all_judge_ids = [row[0] for row in judges_result.all()]

        if not all_judge_ids:
            return {"created": 0, "message": "No judges found"}

        subs_result = await db.execute(
            select(Submission.id).where(
                Submission.hackathon_id == hackathon_id,
                Submission.status == SubmissionStatus.completed,
            )
        )
        all_submission_ids = [row[0] for row in subs_result.all()]

        if not all_submission_ids:
            return {"created": 0, "message": "No completed submissions"}

        assignments_result = await db.execute(
            select(JudgeAssignment)
            .where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.is_completed == 1,
            )
            .options(selectinload(JudgeAssignment.scores))
        )
        completed_assignments = assignments_result.scalars().all()

        scored_by: dict = {}
        for a in completed_assignments:
            scored_by.setdefault(a.submission_id, set()).add(a.judge_id)

        criteria_map = {}
        if session.rubric:
            for c in session.rubric.criteria:
                criteria_map[c.id] = c

        min_judges = 3
        flagged_submissions = []
        for sid in all_submission_ids:
            count = len(scored_by.get(sid, set()))
            if count < min_judges:
                flagged_submissions.append((sid, count))

        if completed_assignments:
            sub_z_scores: dict = {}
            for a in completed_assignments:
                raw = self._compute_raw_score(a.scores, criteria_map)
                sub_z_scores.setdefault(a.submission_id, []).append(raw)

            for sid, raws in sub_z_scores.items():
                if len(raws) >= 2 and sid not in {fs[0] for fs in flagged_submissions}:
                    mean = sum(raws) / len(raws)
                    stddev = math.sqrt(sum((r - mean) ** 2 for r in raws) / len(raws))
                    cv = stddev / mean if mean > 0 else 0
                    if cv > 0.15:
                        flagged_submissions.append((sid, len(raws)))

        existing_pending = await db.execute(
            select(JudgeAssignment.judge_id, JudgeAssignment.submission_id).where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.is_completed == 0,
            )
        )
        existing_pairs = {(row[0], row[1]) for row in existing_pending.all()}

        created = 0
        for submission_id, current_count in flagged_submissions:
            judges_who_scored = scored_by.get(submission_id, set())
            for judge_id in all_judge_ids:
                if judge_id not in judges_who_scored and (judge_id, submission_id) not in existing_pairs:
                    db.add(
                        JudgeAssignment(
                            session_id=session.id,
                            judge_id=judge_id,
                            submission_id=submission_id,
                        )
                    )
                    existing_pairs.add((judge_id, submission_id))
                    created += 1

        await db.commit()

        return {
            "created": created,
            "flagged_submissions": len(flagged_submissions),
            "details": [{"submission_id": str(sid), "current_judges": count} for sid, count in flagged_submissions],
        }

    async def activate_session(self, db: AsyncSession, hackathon_id: uuid.UUID) -> dict:
        """Activate a judging session and auto-assign all judges to completed submissions.

        Behavior:
        1. Load the JudgingSession for the hackathon.
        2. Set session status to active.
        3. Load all judge IDs and all completed submission IDs for the hackathon.
        4. Ensure each judge has a JudgeRating record.
        5. Create pending JudgeAssignment rows for every judge x submission pair not already assigned.
        6. Commit and return activation summary.

        Raises: ValueError if no judging session exists.
        Side Effects: Mutates JudgingSession.status; inserts JudgeAssignment and JudgeRating rows.
        Consumers: POST /api/hackathons/{hackathon_id}/judging/activate.
        """
        session = await self.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")

        session.status = JudgingSessionStatus.active
        await db.flush()

        judges_result = await db.execute(select(User.id).where(User.role == UserRole.judge))
        judge_ids = [row[0] for row in judges_result.all()]

        subs_result = await db.execute(
            select(Submission.id).where(
                Submission.hackathon_id == hackathon_id,
                Submission.status == SubmissionStatus.completed,
            )
        )
        submission_ids = [row[0] for row in subs_result.all()]

        created = 0
        if judge_ids and submission_ids:
            existing_result = await db.execute(
                select(JudgeAssignment.judge_id, JudgeAssignment.submission_id).where(
                    JudgeAssignment.session_id == session.id,
                    JudgeAssignment.is_completed == 0,
                )
            )
            existing_pairs = {(row[0], row[1]) for row in existing_result.all()}

            for judge_id in judge_ids:
                rating_result = await db.execute(
                    select(JudgeRating).where(
                        JudgeRating.judge_id == judge_id,
                        JudgeRating.hackathon_id == hackathon_id,
                    )
                )
                if not rating_result.scalar_one_or_none():
                    db.add(JudgeRating(judge_id=judge_id, hackathon_id=hackathon_id))

                for submission_id in submission_ids:
                    if (judge_id, submission_id) not in existing_pairs:
                        db.add(
                            JudgeAssignment(
                                session_id=session.id,
                                judge_id=judge_id,
                                submission_id=submission_id,
                            )
                        )
                        created += 1

        await db.commit()
        return {
            "status": "active",
            "auto_assigned": created,
            "judges": len(judge_ids),
            "submissions": len(submission_ids),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enforce_time_window(session: JudgingSession):
        """Enforce that the judging session is within its active time window.

        Behavior:
        1. Get current UTC time.
        2. Normalize session start and end times to UTC.
        3. Raise PermissionError if judging has not opened yet or window has closed.

        Raises: PermissionError if outside the active judging window.
        Side Effects: None (pure validation).
        """
        now = datetime.now(UTC)
        start = session.start_time.replace(tzinfo=UTC) if session.start_time.tzinfo is None else session.start_time
        end = session.end_time.replace(tzinfo=UTC) if session.end_time.tzinfo is None else session.end_time
        if session.status == JudgingSessionStatus.pending and now < start:
            raise PermissionError("Judging has not opened yet")
        if session.status == JudgingSessionStatus.closed or now > end:
            raise PermissionError("Judging window has closed")

    @staticmethod
    def _compute_raw_score(scores: list[Score], criteria_map: dict) -> float:
        """Compute a weighted raw score (0-100) from Score rows against RubricCriterion weights.

        Behavior:
        1. Iterate over provided scores.
        2. For each score, look up the matching criterion in the criteria_map.
        3. Normalize the score by max_score and multiply by criterion weight.
        4. Sum and return the total weighted score.

        Raises: None
        Side Effects: None (pure function).
        """
        total = 0.0
        for s in scores:
            c = criteria_map.get(s.criterion_id)
            if c and s.score is not None:
                total += (s.score / c.max_score) * c.weight
        return total

    @staticmethod
    def _build_criteria_list(criteria) -> list[dict]:
        """Serialize rubric criteria into response dicts, sorted by order.

        Behavior:
        1. Sort the criteria iterable by ``sort_order``.
        2. Map each criterion to a dict.
        3. Return the list.

        Raises: None
        Side Effects: None (read-only).
        """
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "max_score": c.max_score,
                "weight": c.weight,
                "sort_order": c.sort_order,
            }
            for c in sorted(criteria, key=lambda x: x.sort_order)
        ]

    @classmethod
    def _session_detail_from_parts(cls, session: JudgingSession, rubric: Rubric | None, criteria: list) -> dict:
        """Build a session detail dict from pre-fetched parts.

        Behavior:
        1. Assemble a dict with session id, hackathon_id, timing, status, and rubric info.
        2. If a rubric is provided, embed its criteria via ``_build_criteria_list``.
        3. Return the assembled dict.

        Raises: None
        Side Effects: None (read-only).
        """
        return {
            "id": str(session.id),
            "hackathon_id": str(session.hackathon_id),
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat(),
            "per_project_seconds": session.per_project_seconds,
            "status": session.status.value,
            "rubric": {
                "id": str(rubric.id) if rubric else None,
                "name": rubric.name if rubric else None,
                "criteria": cls._build_criteria_list(criteria),
            }
            if rubric
            else None,
        }

    @classmethod
    def _session_detail(cls, session: JudgingSession, rubric: Rubric | None) -> dict:
        """Build a session detail dict from a loaded session and rubric.

        Behavior:
        1. If the rubric has loaded criteria, serialize them into a list.
        2. Assemble and return the session detail dict.

        Raises: None
        Side Effects: None (read-only).
        """
        criteria_list = []
        if rubric and rubric.criteria:
            criteria_list = cls._build_criteria_list(rubric.criteria)
        return {
            "id": str(session.id),
            "hackathon_id": str(session.hackathon_id),
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat(),
            "per_project_seconds": session.per_project_seconds,
            "status": session.status.value,
            "rubric": {
                "id": str(rubric.id) if rubric else None,
                "name": rubric.name if rubric else None,
                "criteria": criteria_list,
            }
            if rubric
            else None,
        }

    @staticmethod
    def _expected_score(elo_a: float, elo_b: float) -> float:
        """Compute expected ELO outcome probability for player A vs B.

        Behavior:
        1. Apply the standard ELO expected-score formula.
        2. Return the resulting probability.

        Raises: None
        Side Effects: None (read-only).
        """
        return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))

    @classmethod
    def _elo_update(cls, elo_a: float, elo_b: float, outcome: float, k: float = K_FACTOR) -> tuple[float, float]:
        """Return (new_elo_a, new_elo_b) after a pairwise ELO comparison.

        Behavior:
        1. Compute expected scores e_a and e_b from the current ratings.
        2. Calculate rating deltas using the K-factor and actual outcome.
        3. Return updated ratings as a tuple.

        Raises: None
        Side Effects: None (pure function).
        """
        e_a = cls._expected_score(elo_a, elo_b)
        e_b = 1.0 - e_a
        delta_a = k * (outcome - e_a)
        delta_b = k * ((1.0 - outcome) - e_b)
        return elo_a + delta_a, elo_b + delta_b
