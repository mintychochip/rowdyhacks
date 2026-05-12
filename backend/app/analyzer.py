"""Backward-compatible wrapper for the submission analysis pipeline.

The actual implementation lives in ``app.services.submission_service.SubmissionService``.
This module re-exports ``analyze_submission`` so existing imports do not break.
"""

import uuid

from app.services.submission_service import SubmissionService

_service = SubmissionService()


async def analyze_submission(submission_id: uuid.UUID) -> None:
    """Run the full submission integrity analysis pipeline.

    Delegates to ``SubmissionService.analyze_submission``.
    """
    await _service.analyze_submission(submission_id)
