"""Tool implementations for the assistant."""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    JudgingSession,
    JudgeAssignment,
    Registration,
    Score,
    Submission,
    Track,
    User,
)
from app.models_assistant import DocumentType

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Dispatcher that runs assistant tools with database and user context.

    Each public ``tool_*`` method maps to a registered tool name. The
    ``execute()`` method routes incoming tool calls to the correct
    implementation while injecting the current DB session, user, and
    hackathon objects automatically.
    """

    def __init__(self, db: AsyncSession, user: User, hackathon: Optional[Hackathon] = None):
        """Initialize the tool executor.

        Behavior:
        1. Store the database session, user, and optional hackathon as instance attributes.

        Raises: None
        Side Effects: Mutates instance state (sets ``self.db``, ``self.user``, ``self.hackathon``).
        Dependencies: None
        Consumers: Assistant endpoint that instantiates ToolExecutor per request.
        """
        self.db = db
        self.user = user
        self.hackathon = hackathon

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Dispatch a tool call by name.

        Behavior:
        1. Look up the method named ``tool_{tool_name}`` on this instance.
        2. If no such method exists, raise ``ValueError``.
        3. Await and return the method's result.

        Raises: ValueError if the requested tool is not registered.
        Side Effects: None beyond the invoked tool's own effects.
        Dependencies: None
        Consumers: Assistant response pipeline, tool-calling loop.
        """
        method = getattr(self, f"tool_{tool_name}", None)
        if not method:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await method(**parameters)

    # ========== Common Tools ==========

    async def tool_query_hackathon_info(self, query: str) -> Dict[str, Any]:
        """Return general information about the current hackathon.

        Behavior:
        1. Verify a hackathon is attached to the executor context.
        2. Build an info dict with dates, venue, WiFi, parking, Discord, and Devpost URLs.
        3. Return the dict wrapped under a ``hackathon`` key.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None
        Consumers: Assistant ``query_hackathon_info`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context available"}

        info = {
            "name": self.hackathon.name,
            "start_date": str(self.hackathon.start_date),
            "end_date": str(self.hackathon.end_date),
            "application_deadline": str(self.hackathon.application_deadline)
            if self.hackathon.application_deadline
            else None,
            "venue": self.hackathon.venue,
            "address": self.hackathon.address,
            "wifi_ssid": self.hackathon.wifi_ssid,
            "wifi_password": self.hackathon.wifi_password,
            "parking_info": self.hackathon.parking_info,
            "discord_invite": self.hackathon.discord_invite_url,
            "devpost_url": self.hackathon.devpost_url,
        }

        return {"hackathon": info}

    async def tool_get_tracks(self, hackathon_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all prize tracks for a hackathon.

        Behavior:
        1. Resolve the target hackathon ID from the parameter or the current context.
        2. Query the database for Track rows scoped to that hackathon, ordered by name.
        3. Map each track to a dict with ``id``, ``name``, ``description``,
           ``criteria``, ``resources``, ``prize``, and ``color``.
        4. Return the list of track dicts.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, app.models.Track.
        Consumers: Assistant ``get_tracks`` tool.
        """
        target_hackathon_id = hackathon_id or (str(self.hackathon.id) if self.hackathon else None)
        if not target_hackathon_id:
            return {"error": "No hackathon specified"}

        result = await self.db.execute(
            select(Track).where(Track.hackathon_id == target_hackathon_id).order_by(Track.name)
        )
        tracks = result.scalars().all()

        return [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "criteria": t.criteria,
                "resources": t.resources,
                "prize": t.prize,
                "color": t.color,
            }
            for t in tracks
        ]

    async def tool_view_schedule(self, day: Optional[str] = None) -> Dict[str, Any]:
        """Return the hackathon schedule.

        Behavior:
        1. Verify a hackathon is attached to the executor context.
        2. Build a schedule dict with ``hackathon_name``, ``start``, ``end``, and a note.
        3. Return the dict.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None
        Consumers: Assistant ``view_schedule`` tool.
        """
        # For now, return basic hackathon timing
        if not self.hackathon:
            return {"error": "No hackathon context"}

        schedule = {
            "hackathon_name": self.hackathon.name,
            "start": str(self.hackathon.start_date),
            "end": str(self.hackathon.end_date),
            "note": "Detailed schedule events will be available soon",
        }

        return schedule

    async def tool_faq_query(self, question: str) -> Dict[str, Any]:
        """Search the FAQ knowledge base by semantic similarity.

        Behavior:
        1. Embed the user's question using the sentence-transformers embedder.
        2. Search the vector store for FAQ documents scoped to the current hackathon and user role.
        3. Map the top matches into ``{question, answer}`` dicts.
        4. Return the matches, or an empty list with a guidance message if nothing is found.

        Raises: None
        Side Effects: None (read-only vector search).
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: Assistant ``faq_query`` tool.
        """
        # Search through indexed FAQ documents
        from app.assistant.embedder import embedder
        from app.assistant.vector_store import vector_store

        query_embedding = embedder.embed_text(question)
        results = await vector_store.search_documents(
            query_embedding=query_embedding,
            hackathon_id=str(self.hackathon.id) if self.hackathon else None,
            doc_type="faq",
            role=self.user.role,
            limit=3,
            score_threshold=0.7,
        )

        if results:
            return {
                "matches": [{"question": r["metadata"].get("question", ""), "answer": r["content"]} for r in results]
            }

        return {"matches": [], "message": "No FAQ matches found. Try rephrasing your question."}

    # ========== Participant Tools ==========

    async def tool_ideation_help(self, interests: List[str], track_id: Optional[str] = None) -> Dict[str, Any]:
        """Provide project ideation suggestions based on user interests.

        Behavior:
        1. Build a base suggestions dict with generic advice and resources.
        2. If ``track_id`` is provided, query the matching Track and append
           track-specific criteria into ``track_focus``.
        3. Return the suggestions dict.

        Raises: None
        Side Effects: None (read-only database query if track_id is given).
        Dependencies: sqlalchemy.select, app.models.Track.
        Consumers: Assistant ``ideation_help`` tool.
        """
        suggestions = {
            "interests": interests,
            "suggestions": [
                f"Consider building something that combines {interests[0]} with social good",
                f"Look at past hackathon winners in the {interests[0]} space for inspiration",
                "Think about what judges would find impressive: innovation, technical complexity, presentation",
            ],
            "resources": [
                "Check the hackathon's track descriptions for specific criteria",
                "Review the judging rubric to understand what scores well",
            ],
        }

        if track_id:
            # Get specific track info
            result = await self.db.execute(select(Track).where(Track.id == track_id))
            track = result.scalar_one_or_none()
            if track:
                suggestions["track_focus"] = {
                    "name": track.name,
                    "criteria": track.criteria,
                }

        return suggestions

    async def tool_submission_guidance(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Return guidance for hackathon submission requirements.

        Behavior:
        1. Build a guidance dict with general requirements and tips.
        2. If ``topic`` is provided, append a focused advice block for
           ``video``, ``devpost``, or ``github``.
        3. Return the guidance dict.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None
        Consumers: Assistant ``submission_guidance`` tool.
        """
        guidance = {
            "general_requirements": [
                "Submit via Devpost before the deadline",
                "Include a demo video (2-3 minutes recommended)",
                "Provide GitHub repository link",
                "Write a clear project description",
                "List all team members",
            ],
            "tips": [
                "Start your submission early - you can edit it later",
                "Test your demo video link before submitting",
                "Make sure your GitHub repo is public",
                "Include screenshots if applicable",
            ],
        }

        if topic:
            topic_lower = topic.lower()
            if "video" in topic_lower:
                guidance["focus"] = {
                    "topic": "demo video",
                    "advice": "Keep it under 3 minutes. Show the problem, your solution, and a quick demo.",
                }
            elif "devpost" in topic_lower:
                guidance["focus"] = {
                    "topic": "devpost",
                    "advice": "Fill out all required fields. Use clear formatting and bullet points.",
                }
            elif "github" in topic_lower:
                guidance["focus"] = {
                    "topic": "GitHub",
                    "advice": "Ensure code is well-commented and README explains how to run the project.",
                }

        return guidance

    async def tool_view_own_submission_status(self) -> Dict[str, Any]:
        """Return the current user's submission status for the active hackathon.

        Behavior:
        1. Query Submission rows scoped to the current user and hackathon.
        2. If no submissions exist, return a prompt to submit.
        3. Otherwise map each submission into a dict and return under a ``submissions`` key.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, app.models.Submission.
        Consumers: Assistant ``view_own_submission_status`` tool.
        """
        result = await self.db.execute(
            select(Submission)
            .where(Submission.submitted_by == self.user.id)
            .where(Submission.hackathon_id == self.hackathon.id if self.hackathon else True)
        )
        submissions = result.scalars().all()

        if not submissions:
            return {"status": "No submissions found", "action": "Submit your project on Devpost!"}

        return {
            "submissions": [
                {
                    "id": str(s.id),
                    "devpost_url": s.devpost_url,
                    "github_url": s.github_url,
                    "project_name": s.project_name,
                    "status": s.status,
                    "risk_score": s.risk_score,
                    "submitted_at": str(s.submitted_at) if s.submitted_at else None,
                }
                for s in submissions
            ]
        }

    # ========== Judge Tools ==========

    async def tool_judging_guidelines(self, track_id: Optional[str] = None) -> Dict[str, Any]:
        """Return judging guidelines for the active hackathon.

        Behavior:
        1. Verify a hackathon context exists.
        2. Query the JudgingSession for the hackathon.
        3. Build a guidelines dict with ``general_principles`` and ``session_info``.
        4. If ``track_id`` is provided, append track-specific criteria.
        5. Return the guidelines dict.

        Raises: None
        Side Effects: None (read-only database queries).
        Dependencies: sqlalchemy.select, app.models.JudgingSession, app.models.Track.
        Consumers: Assistant ``judging_guidelines`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Get judging session for this hackathon
        result = await self.db.execute(select(JudgingSession).where(JudgingSession.hackathon_id == self.hackathon.id))
        session = result.scalar_one_or_none()

        if not session:
            return {"error": "No judging session configured yet"}

        guidelines = {
            "general_principles": [
                "Be fair and consistent",
                "Focus on the criteria, not personal preferences",
                "Provide constructive feedback",
                "Complete all assigned submissions",
            ],
            "session_info": {
                "name": session.name,
                "description": session.description,
            },
        }

        if track_id:
            result = await self.db.execute(select(Track).where(Track.id == track_id))
            track = result.scalar_one_or_none()
            if track:
                guidelines["track_specific"] = {
                    "name": track.name,
                    "criteria": track.criteria,
                }

        return guidelines

    async def tool_view_assigned_submissions(self) -> List[Dict[str, Any]]:
        """List all submissions assigned to the current judge.

        Behavior:
        1. Verify a hackathon context exists.
        2. Query JudgeAssignment rows joined to Submission for the current judge and hackathon.
        3. Map each row into a dict with ``assignment_id``, ``submission_id``,
           ``project_name``, ``devpost_url``, ``status``, and ``scores_submitted``.
        4. Return the list.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, app.models.JudgeAssignment, app.models.Submission.
        Consumers: Assistant ``view_assigned_submissions`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        result = await self.db.execute(
            select(JudgeAssignment, Submission)
            .join(Submission, JudgeAssignment.submission_id == Submission.id)
            .where(JudgeAssignment.judge_id == self.user.id)
            .where(Submission.hackathon_id == self.hackathon.id)
        )
        assignments = result.all()

        return [
            {
                "assignment_id": str(a.id),
                "submission_id": str(s.id),
                "project_name": s.project_name,
                "devpost_url": s.devpost_url,
                "status": a.status,
                "scores_submitted": a.scores_submitted,
            }
            for a, s in assignments
        ]

    async def tool_view_submission_details(self, submission_id: str) -> Dict[str, Any]:
        """Return detailed metadata for a specific submission.

        Behavior:
        1. Query the Submission row by ``submission_id``.
        2. If not found, return an error dict.
        3. Otherwise map the submission fields into a dict and return it.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, app.models.Submission.
        Consumers: Assistant ``view_submission_details`` tool.
        """
        result = await self.db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()

        if not submission:
            return {"error": "Submission not found"}

        return {
            "id": str(submission.id),
            "project_name": submission.project_name,
            "description": submission.project_description,
            "devpost_url": submission.devpost_url,
            "github_url": submission.github_url,
            "demo_url": submission.demo_url,
            "submitted_by": str(submission.submitted_by),
            "status": submission.status,
            "risk_score": submission.risk_score,
            "verdict": submission.verdict,
        }

    # ========== Organizer Tools ==========

    async def tool_participant_search(self, query: str) -> List[Dict[str, Any]]:
        """Search participants by name, email, school, or team.

        Behavior:
        1. Verify a hackathon context exists.
        2. Build an ILIKE search pattern from ``query``.
        3. Query User rows joined to Registration, filtering by hackathon and matching
           name, email, school, or team name.
        4. Map results into participant dicts and return the list.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, app.models.User, app.models.Registration.
        Consumers: Assistant ``participant_search`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Search by name or email
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(User, Registration)
            .join(Registration, User.id == Registration.user_id)
            .where(Registration.hackathon_id == self.hackathon.id)
            .where(
                (User.name.ilike(search_pattern))
                | (User.email.ilike(search_pattern))
                | (Registration.school.ilike(search_pattern))
                | (Registration.team_name.ilike(search_pattern))
            )
            .limit(20)
        )
        rows = result.all()

        return [
            {
                "user_id": str(u.id),
                "name": u.name,
                "email": u.email,
                "school": r.school,
                "team_name": r.team_name,
                "status": r.status,
            }
            for u, r in rows
        ]

    async def tool_submission_analytics(self, track_id: Optional[str] = None) -> Dict[str, Any]:
        """Return aggregate submission statistics.

        Behavior:
        1. Verify a hackathon context exists.
        2. Count total submissions for the hackathon.
        3. Count submissions grouped by status.
        4. Compute the average risk score.
        5. Assemble and return the analytics dict.

        Raises: None
        Side Effects: None (read-only database queries).
        Dependencies: sqlalchemy.select, sqlalchemy.func, app.models.Submission.
        Consumers: Assistant ``submission_analytics`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Count total submissions
        result = await self.db.execute(
            select(func.count(Submission.id)).where(Submission.hackathon_id == self.hackathon.id)
        )
        total = result.scalar()

        # Count by status
        result = await self.db.execute(
            select(Submission.status, func.count(Submission.id))
            .where(Submission.hackathon_id == self.hackathon.id)
            .group_by(Submission.status)
        )
        by_status = {status: count for status, count in result.all()}

        # Average risk score
        result = await self.db.execute(
            select(func.avg(Submission.risk_score)).where(Submission.hackathon_id == self.hackathon.id)
        )
        avg_risk = result.scalar()

        analytics = {
            "total_submissions": total,
            "by_status": by_status,
            "average_risk_score": round(float(avg_risk), 2) if avg_risk else None,
        }

        if track_id:
            # Filter by track (would need track_id on submissions)
            pass

        return analytics

    async def tool_admin_stats(self) -> Dict[str, Any]:
        """Return overall admin statistics for the hackathon.

        Behavior:
        1. Verify a hackathon context exists.
        2. Count registrations grouped by status.
        3. Count total submissions.
        4. Compute checked-in vs. eligible numbers and format the check-in rate string.
        5. Return the combined stats dict.

        Raises: None
        Side Effects: None (read-only database queries).
        Dependencies: sqlalchemy.select, sqlalchemy.func, app.models.Registration, app.models.Submission.
        Consumers: Assistant ``admin_stats`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Registration stats
        result = await self.db.execute(
            select(Registration.status, func.count(Registration.id))
            .where(Registration.hackathon_id == self.hackathon.id)
            .group_by(Registration.status)
        )
        registration_stats = {status: count for status, count in result.all()}

        # Submission stats
        result = await self.db.execute(
            select(func.count(Submission.id)).where(Submission.hackathon_id == self.hackathon.id)
        )
        submission_count = result.scalar()

        # Check-in stats
        checked_in = registration_stats.get("checked_in", 0)
        total_accepted = sum(v for k, v in registration_stats.items() if k in ["accepted", "checked_in", "offered"])

        return {
            "registrations": registration_stats,
            "total_submissions": submission_count,
            "check_in_rate": f"{checked_in}/{total_accepted}" if total_accepted > 0 else "N/A",
        }

    async def tool_check_in_status(self) -> Dict[str, Any]:
        """Return real-time check-in statistics.

        Behavior:
        1. Verify a hackathon context exists.
        2. Count registrations grouped by status.
        3. Compute ``checked_in``, ``accepted_not_checked_in``, ``offered``, ``pending``,
           and ``total_eligible`` values.
        4. Return the status dict.

        Raises: None
        Side Effects: None (read-only database query).
        Dependencies: sqlalchemy.select, sqlalchemy.func, app.models.Registration.
        Consumers: Assistant ``check_in_status`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        result = await self.db.execute(
            select(Registration.status, func.count(Registration.id))
            .where(Registration.hackathon_id == self.hackathon.id)
            .group_by(Registration.status)
        )
        by_status = {status: count for status, count in result.all()}

        checked_in = by_status.get("checked_in", 0)
        accepted = by_status.get("accepted", 0)
        offered = by_status.get("offered", 0)

        return {
            "checked_in": checked_in,
            "accepted_not_checked_in": accepted,
            "offered": offered,
            "pending": by_status.get("pending", 0),
            "total_eligible": accepted + offered + checked_in,
        }

    async def tool_judging_progress(self) -> Dict[str, Any]:
        """Return judging completion metrics.

        Behavior:
        1. Verify a hackathon context exists.
        2. Count total judge assignments for the hackathon.
        3. Count completed assignments (where scores have been submitted).
        4. Count distinct active judges.
        5. Compute the completion rate string and return the metrics dict.

        Raises: None
        Side Effects: None (read-only database queries).
        Dependencies: sqlalchemy.select, sqlalchemy.func, app.models.JudgeAssignment, app.models.Submission.
        Consumers: Assistant ``judging_progress`` tool.
        """
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Get total assignments
        result = await self.db.execute(
            select(func.count(JudgeAssignment.id))
            .join(Submission, JudgeAssignment.submission_id == Submission.id)
            .where(Submission.hackathon_id == self.hackathon.id)
        )
        total_assignments = result.scalar()

        # Get completed assignments
        result = await self.db.execute(
            select(func.count(JudgeAssignment.id))
            .join(Submission, JudgeAssignment.submission_id == Submission.id)
            .where(Submission.hackathon_id == self.hackathon.id)
            .where(JudgeAssignment.is_completed == 1)
        )
        completed = result.scalar()

        # Get judge count
        result = await self.db.execute(
            select(func.count(func.distinct(JudgeAssignment.judge_id)))
            .join(Submission, JudgeAssignment.submission_id == Submission.id)
            .where(Submission.hackathon_id == self.hackathon.id)
        )
        judge_count = result.scalar()

        return {
            "total_assignments": total_assignments,
            "completed": completed,
            "pending": total_assignments - completed,
            "completion_rate": f"{completed}/{total_assignments}" if total_assignments > 0 else "N/A",
            "active_judges": judge_count,
        }

    async def tool_modify_faq(self, question: str, answer: str) -> Dict[str, Any]:
        """Add or update an FAQ entry.

        Behavior:
        1. Accept the question and answer text.
        2. Return a success dict with a preview of the added question.

        Raises: None
        Side Effects: None (does not yet persist to the database or vector store in this stub).
        Dependencies: None
        Consumers: Assistant ``modify_faq`` tool.
        """
        # This would update the FAQ in the database and re-index
        # For now, return a success message
        return {
            "success": True,
            "message": f"FAQ entry added/updated: {question[:50]}...",
            "note": "The entry will be indexed and available to the assistant shortly",
        }

    # ========== Site Navigation Tool ==========

    async def tool_query_site_pages(self, query: str) -> Dict[str, Any]:
        """Search site pages relevant to the user's query.

        Behavior:
        1. Embed the user's query using the sentence-transformers embedder.
        2. Search the vector store for ``site_page`` documents, filtered by user role.
        3. Map each result into a page dict with ``title``, ``url``, ``description``, and ``relevance``.
        4. Return the pages list and a guidance message.

        Raises: None
        Side Effects: None (read-only vector search).
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: Assistant ``query_site_pages`` tool.
        """
        from app.assistant.embedder import embedder
        from app.assistant.vector_store import vector_store

        query_embedding = embedder.embed_text(query)
        results = await vector_store.search_documents(
            query_embedding=query_embedding,
            doc_type="site_page",
            role=self.user.role,
            limit=5,
            score_threshold=0.5,
        )

        if not results:
            return {"pages": [], "message": "No relevant pages found. Try a different search."}

        pages = []
        for r in results:
            path = r.get("metadata", {}).get("path", "")
            pages.append(
                {
                    "title": r.get("title", ""),
                    "url": path,
                    "description": r.get("metadata", {}).get("description", ""),
                    "relevance": round(r.get("score", 0), 3),
                }
            )

        return {
            "pages": pages,
            "message": f"Found {len(pages)} relevant page(s). You can share the URLs with the user.",
        }
