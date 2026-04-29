"""Judging routes: session config, rubric management, judge assignment, scoring, ELO results."""
import uuid
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Hackathon, Submission, SubmissionStatus,
    JudgingSession, JudgingSessionStatus,
    Rubric, RubricCriterion,
    JudgeAssignment, Score, JudgeRating,
    User, UserRole,
)
from app.schemas import JudgingSessionCreate, SubmitScoreRequest

router = APIRouter(prefix="/api", tags=["judging"])


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_judging_session(hackathon_id: uuid.UUID, db: AsyncSession) -> JudgingSession:
    result = await db.execute(
        select(JudgingSession)
        .where(JudgingSession.hackathon_id == hackathon_id)
        .options(selectinload(JudgingSession.rubric).selectinload(Rubric.criteria))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="No judging session configured for this hackathon")
    return session


def _enforce_time_window(session: JudgingSession):
    """Raise if judging window is not active."""
    now = datetime.now(timezone.utc)
    start = session.start_time.replace(tzinfo=timezone.utc) if session.start_time.tzinfo is None else session.start_time
    end = session.end_time.replace(tzinfo=timezone.utc) if session.end_time.tzinfo is None else session.end_time
    if session.status == JudgingSessionStatus.pending and now < start:
        raise HTTPException(status_code=403, detail="Judging has not opened yet")
    if session.status == JudgingSessionStatus.closed or now > end:
        raise HTTPException(status_code=403, detail="Judging window has closed")


def _compute_raw_score(scores: list[Score], criteria_map: dict) -> float:
    """Weighted raw score 0-100 from a set of scores against rubric criteria."""
    total = 0.0
    for s in scores:
        c = criteria_map.get(s.criterion_id)
        if c and s.score is not None:
            total += (s.score / c.max_score) * c.weight  # weight already 0-100
    return total  # 0-100 scale


# ── session configuration ────────────────────────────────────────────────────

@router.post("/hackathons/{hackathon_id}/judging/session", status_code=201)
async def create_judging_session(
    hackathon_id: uuid.UUID,
    body: JudgingSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or replace a judging session with rubric criteria for a hackathon."""
    # Verify hackathon exists
    hk = await db.get(Hackathon, hackathon_id)
    if not hk:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Validate total weight = 100
    total_weight = sum(c.weight for c in body.criteria)
    if total_weight != 100:
        raise HTTPException(
            status_code=422,
            detail=f"Criteria weights must sum to 100, got {total_weight}",
        )

    # Delete existing session if any (cascade handles rubric/criteria/assignments)
    existing = await db.execute(
        select(JudgingSession).where(JudgingSession.hackathon_id == hackathon_id)
    )
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

    return _session_detail_from_parts(session, rubric, criteria_created)


@router.get("/hackathons/{hackathon_id}/judging/session")
async def get_judging_session_route(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the judging session configuration for a hackathon."""
    session = await _get_judging_session(hackathon_id, db)
    return _session_detail(session, session.rubric)


def _build_criteria_list(criteria) -> list:
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


def _session_detail_from_parts(session: JudgingSession, rubric: Rubric | None, criteria: list) -> dict:
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
            "criteria": _build_criteria_list(criteria),
        } if rubric else None,
    }


def _session_detail(session: JudgingSession, rubric: Rubric | None) -> dict:
    criteria_list = []
    if rubric and rubric.criteria:
        criteria_list = [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "max_score": c.max_score,
                "weight": c.weight,
                "sort_order": c.sort_order,
            }
            for c in sorted(rubric.criteria, key=lambda x: x.sort_order)
        ]
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
        } if rubric else None,
    }


# ── judge assignment ─────────────────────────────────────────────────────────

@router.post("/hackathons/{hackathon_id}/judging/assign", status_code=201)
async def assign_judges(
    hackathon_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Assign judges to submissions. Body: {"judge_ids": [...], "submission_ids": [...]}.

    Creates assignments for every judge×submission pair.
    Automatically creates JudgeRating records for new judges.
    """
    session = await _get_judging_session(hackathon_id, db)

    judge_ids = [uuid.UUID(j) for j in body.get("judge_ids", [])]
    submission_ids = [uuid.UUID(s) for s in body.get("submission_ids", [])]

    if not judge_ids or not submission_ids:
        raise HTTPException(status_code=422, detail="judge_ids and submission_ids required")

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
        raise HTTPException(status_code=422, detail=f"Submissions not in hackathon: {invalid}")

    # Delete existing assignments for this session (replace)
    await db.execute(
        update(JudgeAssignment)
        .where(JudgeAssignment.session_id == session.id)
        .values(is_completed=-1)  # mark old, won't delete scores
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
            db.add(JudgeAssignment(
                session_id=session.id,
                judge_id=judge_id,
                submission_id=submission_id,
            ))
            created += 1

    await db.commit()
    return {"assigned": created, "judges": len(judge_ids), "submissions": len(submission_ids)}


@router.get("/hackathons/{hackathon_id}/judging/assignments")
async def list_judge_assignments(
    hackathon_id: uuid.UUID,
    judge_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List assignments for a judging session. Filter by judge_id query param."""
    session = await _get_judging_session(hackathon_id, db)

    query = select(JudgeAssignment).where(
        JudgeAssignment.session_id == session.id,
        JudgeAssignment.is_completed == 0,
    )
    if judge_id:
        query = query.where(JudgeAssignment.judge_id == uuid.UUID(judge_id))

    result = await db.execute(query)
    assignments = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "judge_id": str(a.judge_id),
            "submission_id": str(a.submission_id),
            "opened_at": a.opened_at.isoformat() if a.opened_at else None,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            "is_completed": bool(a.is_completed),
        }
        for a in assignments
    ]


@router.get("/judging/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full assignment detail including submission info, rubric criteria, and existing scores."""
    result = await db.execute(
        select(JudgeAssignment)
        .where(JudgeAssignment.id == assignment_id)
        .options(
            selectinload(JudgeAssignment.session)
            .selectinload(JudgingSession.rubric)
            .selectinload(Rubric.criteria),
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    session = assignment.session
    _enforce_time_window(session)

    # Load submission
    sub = await db.get(Submission, assignment.submission_id)

    # Load existing scores for this assignment
    scores_result = await db.execute(
        select(Score).where(Score.assignment_id == assignment.id)
    )
    existing_scores = {s.criterion_id: s for s in scores_result.scalars().all()}

    rubric = session.rubric
    criteria = []
    if rubric:
        for c in sorted(rubric.criteria, key=lambda x: x.sort_order):
            s = existing_scores.get(c.id)
            criteria.append({
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "max_score": c.max_score,
                "weight": c.weight,
                "score": s.score if s else None,
            })

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
        } if sub else None,
        "criteria": criteria,
    }


@router.post("/judging/assignments/{assignment_id}/open")
async def open_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark an assignment as opened by the judge (starts the timer)."""
    assignment = await db.get(JudgeAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    session = await db.get(JudgingSession, assignment.session_id)
    _enforce_time_window(session)

    if assignment.opened_at is None:
        assignment.opened_at = datetime.now(timezone.utc)

    # Create blank scores for each criterion if not already present
    rubric = await db.execute(
        select(Rubric).where(Rubric.session_id == session.id)
    )
    rubric_obj = rubric.scalar_one_or_none()
    if rubric_obj:
        criteria_result = await db.execute(
            select(RubricCriterion).where(RubricCriterion.rubric_id == rubric_obj.id)
        )
        existing_scores = await db.execute(
            select(Score.criterion_id).where(Score.assignment_id == assignment.id)
        )
        existing_criteria_ids = {row[0] for row in existing_scores.all()}
        for criterion in criteria_result.scalars().all():
            if criterion.id not in existing_criteria_ids:
                db.add(Score(assignment_id=assignment.id, criterion_id=criterion.id))

    await db.commit()
    return {"opened": True, "opened_at": assignment.opened_at.isoformat()}


@router.post("/judging/assignments/{assignment_id}/score")
async def submit_scores(
    assignment_id: uuid.UUID,
    body: SubmitScoreRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit or update scores for an assignment. Can be called incrementally.

    Auto-submits (marks complete) when all criteria have non-null scores.
    Also checks per_project_seconds soft deadline.
    """
    assignment = await db.get(JudgeAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.is_completed:
        raise HTTPException(status_code=400, detail="Assignment already completed")

    session = await db.get(JudgingSession, assignment.session_id)
    _enforce_time_window(session)

    now = datetime.now(timezone.utc)
    is_late = False
    if assignment.opened_at:
        opened = assignment.opened_at.replace(tzinfo=timezone.utc) if assignment.opened_at.tzinfo is None else assignment.opened_at
        elapsed = (now - opened).total_seconds()
        if elapsed > session.per_project_seconds:
            is_late = True

    # Load rubric to get criteria
    rubric_result = await db.execute(
        select(Rubric).where(Rubric.session_id == session.id)
    )
    rubric = rubric_result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="No rubric found for this session")

    criteria_result = await db.execute(
        select(RubricCriterion).where(RubricCriterion.rubric_id == rubric.id)
    )
    criteria = {c.id: c for c in criteria_result.scalars().all()}

    for item in body.scores:
        cid = uuid.UUID(item["criterion_id"])
        score_val = item["score"]
        if cid not in criteria:
            raise HTTPException(status_code=422, detail=f"Unknown criterion: {cid}")
        if score_val is not None and (score_val < 0 or score_val > criteria[cid].max_score):
            raise HTTPException(
                status_code=422,
                detail=f"Score {score_val} out of range for {criteria[cid].name} (0-{criteria[cid].max_score})",
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
            db.add(Score(
                assignment_id=assignment.id,
                criterion_id=cid,
                score=score_val,
            ))

    if is_late:
        # Auto-submit
        assignment.submitted_at = now
        assignment.is_completed = 1
        # Mark all null scores as 0
        all_scores = await db.execute(
            select(Score).where(Score.assignment_id == assignment.id)
        )
        for s in all_scores.scalars().all():
            if s.score is None:
                s.score = 0
            s.is_auto_submitted = 1
            s.submitted_at = now

    # Check if all criteria scored → auto-complete
    if not is_late:
        scores_result = await db.execute(
            select(Score).where(Score.assignment_id == assignment.id)
        )
        all_scored = all(s.score is not None for s in scores_result.scalars().all())
        if all_scored:
            assignment.submitted_at = now
            assignment.is_completed = 1
            for s in scores_result.scalars().all():
                s.submitted_at = now

    await db.commit()

    return {
        "submitted": True,
        "is_completed": bool(assignment.is_completed),
        "is_late": is_late,
        "is_auto_submitted": is_late,
    }


# ── ELO engine & results ─────────────────────────────────────────────────────

K_FACTOR = 32
BASE_ELO = 1500


def _expected_score(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def _elo_update(elo_a: float, elo_b: float, outcome: float, k: float = K_FACTOR) -> tuple[float, float]:
    """Return (new_elo_a, new_elo_b) after a pairwise comparison.
    outcome: 1.0 = A wins, 0.5 = tie, 0.0 = B wins."""
    e_a = _expected_score(elo_a, elo_b)
    e_b = 1.0 - e_a
    delta_a = k * (outcome - e_a)
    delta_b = k * ((1.0 - outcome) - e_b)
    return elo_a + delta_a, elo_b + delta_b


@router.get("/hackathons/{hackathon_id}/judging/results")
async def get_judging_results(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compute and return ELO rankings for the hackathon.

    Algorithm:
      1. Load all completed assignments with scores.
      2. Compute raw weighted score per (judge, submission).
      3. Z-score normalize within each judge (judge severity correction).
      4. Within-judge pairwise ELO updates.
      5. Cross-judge bridging via submissions scored by multiple judges.
      6. Return final ELO rankings.
    """
    session = await _get_judging_session(hackathon_id, db)

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
    # raw_scores[judge_id][submission_id] = raw_score (0-100)
    raw_scores: dict = {}
    judge_sub_count: dict = {}  # judge_id -> count

    for a in assignments:
        jid = str(a.judge_id)
        sid = str(a.submission_id)
        raw = _compute_raw_score(a.scores, criteria_map)
        raw_scores.setdefault(jid, {})[sid] = raw
        judge_sub_count[jid] = judge_sub_count.get(jid, 0) + 1

    # Step 2: z-score normalize within each judge
    norm_scores: dict = {}  # (judge_id, submission_id) -> z_score
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

                # Determine winner from z-scores
                if abs(z_a - z_b) < 0.1:
                    outcome = 0.5  # tie (within noise threshold)
                elif z_a > z_b:
                    outcome = 1.0
                else:
                    outcome = 0.0

                elo[a_sid], elo[b_sid] = _elo_update(elo[a_sid], elo[b_sid], outcome)

    # Step 5: cross-judge bridging (projects scored by multiple judges get
    # extra pairwise comparisons weighted by the average z-score across judges)
    # Build per-submission z-score averages
    sub_z_scores: dict[str, list[float]] = {}
    for (jid, sid), z in norm_scores.items():
        sub_z_scores.setdefault(sid, []).append(z)

    sub_avg_z = {sid: sum(zs) / len(zs) for sid, zs in sub_z_scores.items()}

    # Cross-compare all submissions that have judges in common
    # (uses average z-score as the comparison basis)
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

            # Smaller K for cross-judge (less confident)
            elo[a_sid], elo[b_sid] = _elo_update(elo[a_sid], elo[b_sid], outcome, k=16)

    # Build rankings
    # Load submission titles
    sub_ids_list = [uuid.UUID(sid) for sid in elo.keys()]
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
                "raw_avg": round(sum(raw_scores.get(jid, {}).get(sid, 0) for jid in raw_scores)
                                 / max(1, sum(1 for jid in raw_scores if sid in raw_scores.get(jid, {}))), 1),
                "judges": sum(1 for jid in raw_scores if sid in raw_scores.get(jid, {})),
            }
            for sid, e in elo.items()
        ],
        key=lambda x: x["elo"],
        reverse=True,
    )

    # Assign ranks
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    # Load judge names for stats
    judge_ids = [uuid.UUID(jid) for jid in judge_stats]
    users_result = await db.execute(
        select(User.id, User.name).where(User.id.in_(judge_ids))
    )
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


# ── session lifecycle ────────────────────────────────────────────────────────

@router.post("/hackathons/{hackathon_id}/judging/activate")
async def activate_judging(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Manually activate judging (or it auto-activates based on start_time)."""
    session = await _get_judging_session(hackathon_id, db)
    session.status = JudgingSessionStatus.active
    await db.commit()
    return {"status": "active"}


@router.post("/hackathons/{hackathon_id}/judging/close")
async def close_judging(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Manually close judging to prevent further scoring."""
    session = await _get_judging_session(hackathon_id, db)
    session.status = JudgingSessionStatus.closed
    await db.commit()
    return {"status": "closed"}
