"""Full judging system integration test — can be run with pytest tests/test_judging.py -v"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, UserRole, Hackathon, Submission, SubmissionStatus,
    JudgingSession, Rubric, RubricCriterion,
    JudgeAssignment, Score, JudgeRating, JudgingSessionStatus,
)
from app.auth import hash_password


async def _create_user(db: AsyncSession, email: str, name: str, role: UserRole) -> User:
    user = User(email=email, name=name, role=role, password_hash=hash_password("test1234"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_hackathon(db: AsyncSession, name: str, organizer_id=None) -> Hackathon:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    h = Hackathon(
        name=name,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        organizer_id=organizer_id,
    )
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return h


async def _create_submission(db: AsyncSession, hackathon_id, title: str, url: str) -> Submission:
    s = Submission(
        devpost_url=url,
        project_title=title,
        hackathon_id=hackathon_id,
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


# ── full judging flow ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_judging_flow(client: AsyncClient, db_session: AsyncSession):
    """End-to-end: create session, assign judges, score, compute rankings."""

    # 1. Create organizer, judges, hackathon, and submissions
    organizer = await _create_user(db_session, "org@test.com", "Organizer", UserRole.organizer)
    judge1 = await _create_user(db_session, "judge1@test.com", "Judge Alice", UserRole.judge)
    judge2 = await _create_user(db_session, "judge2@test.com", "Judge Bob", UserRole.judge)
    hackathon = await _create_hackathon(db_session, "Test Hackathon 2026", organizer_id=organizer.id)

    sub_a = await _create_submission(db_session, hackathon.id, "Project Alpha", "https://devpost.com/alpha")
    sub_b = await _create_submission(db_session, hackathon.id, "Project Beta", "https://devpost.com/beta")
    sub_c = await _create_submission(db_session, hackathon.id, "Project Gamma", "https://devpost.com/gamma")

    # 2. Create judging session with rubric
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/session",
        json={
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "per_project_seconds": 300,
            "criteria": [
                {"name": "Innovation", "description": "Originality", "max_score": 10, "weight": 40, "sort_order": 0},
                {"name": "Execution", "description": "Technical quality", "max_score": 10, "weight": 30, "sort_order": 1},
                {"name": "Design", "description": "UI/UX", "max_score": 10, "weight": 30, "sort_order": 2},
            ],
        },
    )
    assert resp.status_code == 201
    session_data = resp.json()
    assert session_data["status"] == "pending"
    assert len(session_data["rubric"]["criteria"]) == 3
    criteria_map = {c["name"]: c for c in session_data["rubric"]["criteria"]}
    print("  [OK] Created judging session with rubric")

    # 3. Assign judges to all submissions
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/assign",
        json={
            "judge_ids": [str(judge1.id), str(judge2.id)],
            "submission_ids": [str(sub_a.id), str(sub_b.id), str(sub_c.id)],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["assigned"] == 6  # 2 judges * 3 submissions
    print(f"  [OK] Assigned {data['assigned']} judge-submission pairs")

    # 4. Get judge1's assignments
    resp = await client.get(
        f"/api/hackathons/{hackathon.id}/judging/assignments?judge_id={judge1.id}"
    )
    assert resp.status_code == 200
    assignments = resp.json()
    assert len(assignments) == 3

    # 5. Score each assignment for judge1
    for assignment in assignments:
        aid = assignment["id"]

        # Open the assignment
        resp = await client.post(f"/api/judging/assignments/{aid}/open")
        assert resp.status_code == 200

        # Get detail to see criteria
        resp = await client.get(f"/api/judging/assignments/{aid}")
        assert resp.status_code == 200
        detail = resp.json()
        assert len(detail["criteria"]) == 3

        # Submit scores
        innovation_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Innovation")
        execution_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Execution")
        design_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Design")

        # Score differently per project so rankings are meaningful
        if "Alpha" in detail["submission"]["project_title"]:
            innov, exec_, des = 9, 8, 7  # Total raw: 9*0.4 + 8*0.3 + 7*0.3 = 81
        elif "Beta" in detail["submission"]["project_title"]:
            innov, exec_, des = 7, 9, 8  # Total raw: 7*0.4 + 9*0.3 + 8*0.3 = 79
        else:
            innov, exec_, des = 5, 6, 5  # Total raw: 5*0.4 + 6*0.3 + 5*0.3 = 53

        resp = await client.post(
            f"/api/judging/assignments/{aid}/score",
            json={
                "scores": [
                    {"criterion_id": innovation_id, "score": innov},
                    {"criterion_id": execution_id, "score": exec_},
                    {"criterion_id": design_id, "score": des},
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True
        print(f"  [OK] Judge 1 scored {detail['submission']['project_title']}: innov={innov}, exec={exec_}, design={des}")

    # 6. Score for judge2 (harsher judge — scores lower across the board)
    resp = await client.get(
        f"/api/hackathons/{hackathon.id}/judging/assignments?judge_id={judge2.id}"
    )
    assert resp.status_code == 200
    assignments_j2 = resp.json()

    for assignment in assignments_j2:
        aid = assignment["id"]
        await client.post(f"/api/judging/assignments/{aid}/open")
        resp = await client.get(f"/api/judging/assignments/{aid}")
        detail = resp.json()

        innovation_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Innovation")
        execution_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Execution")
        design_id = next(c["id"] for c in detail["criteria"] if c["name"] == "Design")

        if "Alpha" in detail["submission"]["project_title"]:
            innov, exec_, des = 7, 6, 5  # Harsher: 7*0.4 + 6*0.3 + 5*0.3 = 61
        elif "Beta" in detail["submission"]["project_title"]:
            innov, exec_, des = 5, 7, 6  # 5*0.4 + 7*0.3 + 6*0.3 = 59
        else:
            innov, exec_, des = 3, 4, 3  # 3*0.4 + 4*0.3 + 3*0.3 = 33

        await client.post(
            f"/api/judging/assignments/{aid}/score",
            json={
                "scores": [
                    {"criterion_id": innovation_id, "score": innov},
                    {"criterion_id": execution_id, "score": exec_},
                    {"criterion_id": design_id, "score": des},
                ],
            },
        )
    print("  [OK] Judge 2 (harsh) scored all 3 projects")

    # 7. Try scoring after completing (should fail)
    resp = await client.post(
        f"/api/judging/assignments/{assignments[0]['id']}/score",
        json={"scores": [{"criterion_id": "00000000-0000-0000-0000-000000000001", "score": 5}]},
    )
    assert resp.status_code == 400  # assignment already completed
    print("  [OK] Re-scoring completed assignment correctly rejected")

    # 8. Get results
    resp = await client.get(f"/api/hackathons/{hackathon.id}/judging/results")
    assert resp.status_code == 200
    results = resp.json()

    rankings = results["rankings"]
    assert len(rankings) == 3

    # Alpha should rank #1 (best from both judges despite the harshness)
    print(f"\n  Rankings:")
    for r in rankings:
        print(f"    #{r['rank']} {r['project_title']}: ELO={r['elo']}, raw_avg={r['raw_avg']}, judges={r['judges']}")

    assert rankings[0]["project_title"] == "Project Alpha"
    assert rankings[0]["rank"] == 1
    assert rankings[0]["elo"] > 1500  # Above baseline

    # Gamma should be last
    assert rankings[2]["project_title"] == "Project Gamma"
    assert rankings[2]["rank"] == 3

    # Judge stats should show judge2 as harsher
    judge_stats = results["judge_stats"]
    assert len(judge_stats) == 2

    judge1_stats = next(s for s in judge_stats if s["name"] == "Judge Alice")
    judge2_stats = next(s for s in judge_stats if s["name"] == "Judge Bob")
    assert judge1_stats["mean"] > judge2_stats["mean"]  # Alice is more generous
    print(f"\n  Judge severity: Alice mean={judge1_stats['mean']}, Bob mean={judge2_stats['mean']}")
    print("  [OK] ELO corrected for harsh judge — Alpha still won")


@pytest.mark.asyncio
async def test_weight_validation(client: AsyncClient, db_session: AsyncSession):
    """Criteria weights must sum to 100."""
    organizer = await _create_user(db_session, "weightorg@test.com", "Org", UserRole.organizer)
    hackathon = await _create_hackathon(db_session, "Weight Test", organizer_id=organizer.id)
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/session",
        json={
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-02T00:00:00Z",
            "per_project_seconds": 300,
            "criteria": [
                {"name": "A", "max_score": 10, "weight": 40},
                {"name": "B", "max_score": 10, "weight": 40},
            ],
        },
    )
    assert resp.status_code == 422
    assert "100" in resp.json()["detail"]
    print("  [OK] Weight validation works")


@pytest.mark.asyncio
async def test_judging_window_enforcement(client: AsyncClient, db_session: AsyncSession):
    """Scores rejected before start_time and after end_time."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    window_org = await _create_user(db_session, "windoworg@test.com", "Window Org", UserRole.organizer)
    hackathon = await _create_hackathon(db_session, "Window Test", organizer_id=window_org.id)
    sub = await _create_submission(db_session, hackathon.id, "Project X", "https://devpost.com/x")

    # Create session that opens in the future
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/session",
        json={
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "per_project_seconds": 300,
            "criteria": [{"name": "Innovation", "max_score": 10, "weight": 100}],
        },
    )
    assert resp.status_code == 201

    # Assign judge
    judge = await _create_user(db_session, "timejudge@test.com", "Time Judge", UserRole.judge)
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/assign",
        json={"judge_ids": [str(judge.id)], "submission_ids": [str(sub.id)]},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["assigned"]

    # Try to open — should fail (window not open)
    resp = await client.get(
        f"/api/hackathons/{hackathon.id}/judging/assignments?judge_id={judge.id}"
    )
    aid = resp.json()[0]["id"]
    resp = await client.get(f"/api/judging/assignments/{aid}")
    assert resp.status_code == 403
    assert "not opened yet" in resp.json()["detail"]
    print("  [OK] Judging window enforcement: before start rejected")

    # Create session in the past (closed)
    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/session",
        json={
            "start_time": (now - timedelta(hours=3)).isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
            "per_project_seconds": 300,
            "criteria": [{"name": "Innovation", "max_score": 10, "weight": 100}],
        },
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/assign",
        json={"judge_ids": [str(judge.id)], "submission_ids": [str(sub.id)]},
    )
    resp = await client.get(
        f"/api/hackathons/{hackathon.id}/judging/assignments?judge_id={judge.id}"
    )
    aid2 = resp.json()[0]["id"]
    resp = await client.get(f"/api/judging/assignments/{aid2}")
    assert resp.status_code == 403
    assert "closed" in resp.json()["detail"]
    print("  [OK] Judging window enforcement: after end rejected")


@pytest.mark.asyncio
async def test_soft_deadline_auto_submit(client: AsyncClient, db_session: AsyncSession):
    """Scores submitted after per_project_seconds are auto-submitted."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    deadline_org = await _create_user(db_session, "deadlineorg@test.com", "Deadline Org", UserRole.organizer)
    hackathon = await _create_hackathon(db_session, "Deadline Test", organizer_id=deadline_org.id)
    sub = await _create_submission(db_session, hackathon.id, "Project T", "https://devpost.com/t")
    judge = await _create_user(db_session, "deadlinejudge@test.com", "Deadline Judge", UserRole.judge)

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/session",
        json={
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "per_project_seconds": 1,  # 1 second — tiny window
            "criteria": [{"name": "Innovation", "max_score": 10, "weight": 100}],
        },
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/judging/assign",
        json={"judge_ids": [str(judge.id)], "submission_ids": [str(sub.id)]},
    )
    resp = await client.get(
        f"/api/hackathons/{hackathon.id}/judging/assignments?judge_id={judge.id}"
    )
    aid = resp.json()[0]["id"]

    # Open the assignment
    await client.post(f"/api/judging/assignments/{aid}/open")

    # Wait 2 seconds (past the 1-second per_project_seconds)
    import asyncio
    await asyncio.sleep(2)

    # Get detail to get criterion ID
    resp = await client.get(f"/api/judging/assignments/{aid}")
    detail = resp.json()
    cid = detail["criteria"][0]["id"]

    # Submit — should be auto-submitted as late
    resp = await client.post(
        f"/api/judging/assignments/{aid}/score",
        json={"scores": [{"criterion_id": cid, "score": 5}]},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["is_late"] is True
    assert result["is_auto_submitted"] is True
    print("  [OK] Soft deadline: scores auto-submitted when past time limit")
