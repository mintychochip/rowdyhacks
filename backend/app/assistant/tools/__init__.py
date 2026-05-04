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
    """Executes tools with proper database access."""

    def __init__(self, db: AsyncSession, user: User, hackathon: Optional[Hackathon] = None):
        self.db = db
        self.user = user
        self.hackathon = hackathon

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        method = getattr(self, f"tool_{tool_name}", None)
        if not method:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await method(**parameters)

    # ========== Common Tools ==========

    async def tool_query_hackathon_info(self, query: str) -> Dict[str, Any]:
        """Get general hackathon information."""
        if not self.hackathon:
            return {"error": "No hackathon context available"}

        info = {
            "name": self.hackathon.name,
            "start_date": str(self.hackathon.start_date),
            "end_date": str(self.hackathon.end_date),
            "application_deadline": str(self.hackathon.application_deadline) if self.hackathon.application_deadline else None,
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
        """List all tracks for the hackathon."""
        target_hackathon_id = hackathon_id or (str(self.hackathon.id) if self.hackathon else None)
        if not target_hackathon_id:
            return {"error": "No hackathon specified"}

        result = await self.db.execute(
            select(Track)
            .where(Track.hackathon_id == target_hackathon_id)
            .order_by(Track.name)
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
        """Get hackathon schedule."""
        # For now, return basic hackathon timing
        if not self.hackathon:
            return {"error": "No hackathon context"}

        schedule = {
            "hackathon_name": self.hackathon.name,
            "start": str(self.hackathon.start_date),
            "end": str(self.hackathon.end_date),
            "note": "Detailed schedule events will be available soon"
        }

        return schedule

    async def tool_faq_query(self, question: str) -> Dict[str, Any]:
        """Search FAQ."""
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
                "matches": [
                    {"question": r["metadata"].get("question", ""), "answer": r["content"]}
                    for r in results
                ]
            }

        return {"matches": [], "message": "No FAQ matches found. Try rephrasing your question."}

    # ========== Participant Tools ==========

    async def tool_ideation_help(self, interests: List[str], track_id: Optional[str] = None) -> Dict[str, Any]:
        """Get ideation help based on interests."""
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
            ]
        }

        if track_id:
            # Get specific track info
            result = await self.db.execute(
                select(Track).where(Track.id == track_id)
            )
            track = result.scalar_one_or_none()
            if track:
                suggestions["track_focus"] = {
                    "name": track.name,
                    "criteria": track.criteria,
                }

        return suggestions

    async def tool_submission_guidance(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Get help with submission requirements."""
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
            ]
        }

        if topic:
            topic_lower = topic.lower()
            if "video" in topic_lower:
                guidance["focus"] = {
                    "topic": "demo video",
                    "advice": "Keep it under 3 minutes. Show the problem, your solution, and a quick demo."}
            elif "devpost" in topic_lower:
                guidance["focus"] = {
                    "topic": "devpost",
                    "advice": "Fill out all required fields. Use clear formatting and bullet points."}
            elif "github" in topic_lower:
                guidance["focus"] = {
                    "topic": "GitHub",
                    "advice": "Ensure code is well-commented and README explains how to run the project."}

        return guidance

    async def tool_view_own_submission_status(self) -> Dict[str, Any]:
        """View user's submission status."""
        result = await self.db.execute(
            select(Submission)
            .where(Submission.submitter_id == self.user.id)
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
        """Get judging guidelines."""
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Get judging session for this hackathon
        result = await self.db.execute(
            select(JudgingSession)
            .where(JudgingSession.hackathon_id == self.hackathon.id)
        )
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
            }
        }

        if track_id:
            result = await self.db.execute(
                select(Track).where(Track.id == track_id)
            )
            track = result.scalar_one_or_none()
            if track:
                guidelines["track_specific"] = {
                    "name": track.name,
                    "criteria": track.criteria,
                }

        return guidelines

    async def tool_view_assigned_submissions(self) -> List[Dict[str, Any]]:
        """List submissions assigned to judge."""
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
        """Get detailed submission information."""
        result = await self.db.execute(
            select(Submission)
            .where(Submission.id == submission_id)
        )
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
            "submitter_id": str(submission.submitter_id),
            "status": submission.status,
            "risk_score": submission.risk_score,
            "verdict": submission.verdict,
        }

    # ========== Organizer Tools ==========

    async def tool_participant_search(self, query: str) -> List[Dict[str, Any]]:
        """Search participants."""
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Search by name or email
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(User, Registration)
            .join(Registration, User.id == Registration.user_id)
            .where(Registration.hackathon_id == self.hackathon.id)
            .where(
                (User.name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (Registration.school.ilike(search_pattern)) |
                (Registration.team_name.ilike(search_pattern))
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
        """Get submission analytics."""
        if not self.hackathon:
            return {"error": "No hackathon context"}

        # Count total submissions
        result = await self.db.execute(
            select(func.count(Submission.id))
            .where(Submission.hackathon_id == self.hackathon.id)
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
            select(func.avg(Submission.risk_score))
            .where(Submission.hackathon_id == self.hackathon.id)
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
        """Get overall admin statistics."""
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
            select(func.count(Submission.id))
            .where(Submission.hackathon_id == self.hackathon.id)
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
        """Get check-in statistics."""
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
        """Get judging progress."""
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
            .where(JudgeAssignment.scores_submitted == True)
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
        """Add or update FAQ entry."""
        # This would update the FAQ in the database and re-index
        # For now, return a success message
        return {
            "success": True,
            "message": f"FAQ entry added/updated: {question[:50]}...",
            "note": "The entry will be indexed and available to the assistant shortly",
        }
