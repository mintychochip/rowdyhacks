"""Tracks management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete_pattern, cached
from app.auth import get_current_user
from app.database import get_db
from app.models import Hackathon, Track, User, UserRole

router = APIRouter(prefix="/api/hackathons", tags=["tracks"])

TRACKS_CACHE_TTL = 300  # 5 minutes
CACHE_PFX = "tracks"


async def _get_current_user(db: AsyncSession, user_payload: dict) -> User:
    """Fetch the current user from the database by Clerk sub.

    Behavior:
    1. Query the User table by the Clerk sub (user_id).
    2. Return the matched User ORM object.
    3. Raise 404 if the user is not found.

    Raises: HTTPException(404) if user not found.
    Side Effects: None (read-only).
    Dependencies: app.models.User.
    Consumers: Internal helper used by track routes.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _require_organizer(hackathon_id: str, db: AsyncSession, user_payload: dict) -> Hackathon:
    """Verify the user is an organizer and return the hackathon.

    Behavior:
    1. Fetch the current user and verify role is organizer.
    2. Raise 403 if the user is not an organizer.
    3. Query the hackathon by id.
    4. Raise 404 if the hackathon is not found.
    5. Return the Hackathon ORM object.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if hackathon not found.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.User, app.models.UserRole.
    Consumers: Internal helper used by track management routes.
    """
    user = await _get_current_user(db, user_payload)
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can manage tracks")
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return hackathon


def _track_to_response(t: Track) -> dict:
    """Serialize a Track model to a response dict.

    Behavior:
    1. Extract fields from the Track ORM instance.
    2. Return a dict with all track properties.

    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: Internal helper used by track list/create/update/delete routes.
    """
    return {
        "id": str(t.id),
        "hackathon_id": str(t.hackathon_id),
        "name": t.name,
        "description": t.description,
        "challenge": t.challenge,
        "icon": t.icon,
        "color": t.color,
        "prize": t.prize,
        "track_type": t.track_type,
        "criteria": t.criteria or [],
        "resources": t.resources or [],
        "resources_markdown": t.resources_markdown,
    }


DEFAULT_TRACKS = [
    {
        "name": "Grand Prize",
        "description": "Overall Winner - Best overall project wins the top honor based on impact, execution, and innovation.",
        "challenge": "Build in any track and pitch your best project for the grand prize. The overall winner is selected based on impact, execution, and innovation across all submissions.",
        "icon": "🏆",
        "color": "#f59e0b",
        "prize": "$500",
        "track_type": "prize",
        "criteria": ["Impact", "Execution", "Innovation"],
        "resources": [],
    },
    {
        "name": "AI and Machine Learning",
        "description": "Create intelligent products using models, data pipelines, and automation.",
        "challenge": "Build a project that leverages artificial intelligence or machine learning to solve a problem. This could be anything from a predictive model to a natural language processing app, computer vision project, or automation tool. Judges will look for practical application of AI/ML concepts, model performance, and real-world utility.",
        "icon": "🤖",
        "color": "#10b981",
        "prize": "Track Prize",
        "track_type": "themed",
        "criteria": ["Innovation", "Technical Implementation", "Real-world Utility", "Presentation"],
        "resources": [
            {"name": "OpenAI API", "url": "https://platform.openai.com/"},
            {"name": "Hugging Face", "url": "https://huggingface.co/"},
            {"name": "TensorFlow", "url": "https://www.tensorflow.org/"},
            {"name": "PyTorch", "url": "https://pytorch.org/"},
        ],
    },
    {
        "name": "Social Impact",
        "description": "Develop solutions that support communities and improve quality of life.",
        "challenge": "Create a project that addresses a social or community challenge. Focus on issues like sustainability, accessibility, public health, civic engagement, or community support. Judges will evaluate the potential community benefit, feasibility, and scalability of your solution.",
        "icon": "🌍",
        "color": "#8b5cf6",
        "prize": "Track Prize",
        "track_type": "themed",
        "criteria": ["Social Impact", "Feasibility", "Innovation", "Scalability"],
        "resources": [
            {"name": "UN Sustainable Development Goals", "url": "https://sdgs.un.org/goals"},
            {"name": "Data.gov", "url": "https://www.data.gov/"},
            {"name": "Code for America", "url": "https://www.codeforamerica.org/"},
        ],
    },
    {
        "name": "Education",
        "description": "Build tools that enhance learning, accessibility, and educational outcomes.",
        "challenge": "Develop a project that improves education or learning outcomes. This could be an educational game, a study tool, an accessibility solution for learners with disabilities, a platform for sharing educational resources, or any tool that helps people learn more effectively.",
        "icon": "📚",
        "color": "#06b6d4",
        "prize": "Track Prize",
        "track_type": "themed",
        "criteria": ["Educational Value", "Accessibility", "User Experience", "Innovation"],
        "resources": [
            {"name": "Khan Academy API", "url": "https://api-explorer.khanacademy.org/"},
            {"name": "Google for Education", "url": "https://edu.google.com/"},
            {"name": "EdTech Resources", "url": "https://www.iste.org/"},
        ],
    },
]


def seed_tracks(hackathon_id: uuid.UUID) -> list[Track]:
    """Return default track records for a new hackathon.

    Behavior:
    1. Build Track ORM instances from the DEFAULT_TRACKS list.
    2. Associate each track with the given hackathon_id.
    3. Return the list of pre-filled tracks.

    Side Effects: None (returns new objects, no DB write).
    Dependencies: app.models.Track.
    Consumers: Internal helper used by hackathon creation.
    """
    return [
        Track(
            hackathon_id=hackathon_id,
            name=t["name"],
            description=t["description"],
            challenge=t["challenge"],
            icon=t["icon"],
            color=t["color"],
            prize=t["prize"],
            track_type=t.get("track_type"),
            criteria=t["criteria"],
            resources=t["resources"],
        )
        for t in DEFAULT_TRACKS
    ]


@router.get("/{hackathon_id}/tracks")
@cached(ttl_seconds=TRACKS_CACHE_TTL, key_prefix=CACHE_PFX)
async def list_tracks(hackathon_id: str, db: AsyncSession = Depends(get_db)):
    """List all tracks for a hackathon.

    Behavior:
    1. Query Track rows filtered by hackathon_id, ordered by created_at.
    2. Serialize each track using _track_to_response.
    3. Return a dict with hackathon_id and the tracks list.

    Side Effects: None (read-only).
    Dependencies: app.models.Track.
    Consumers: GET /api/hackathons/{hackathon_id}/tracks, hackathon details.
    """
    result = await db.execute(select(Track).where(Track.hackathon_id == hackathon_id).order_by(Track.created_at))
    tracks = result.scalars().all()
    return {"hackathon_id": hackathon_id, "tracks": [_track_to_response(t) for t in tracks]}


@router.post("/{hackathon_id}/tracks", status_code=201)
async def create_track(
    hackathon_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new track for a hackathon (organizer only).

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Create a Track ORM instance from the request body.
    3. Persist the track to the database.
    4. Reindex hackathon data and bust the tracks cache.
    5. Return the created track details.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if hackathon not found.
    Side Effects: Inserts Track row; reindexes hackathon; busts cache.
    Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
    Consumers: POST /api/hackathons/{hackathon_id}/tracks, organizer dashboard.
    """
    await _require_organizer(hackathon_id, db, user_payload)
    track = Track(
        hackathon_id=hackathon_id,
        name=body["name"],
        description=body.get("description", ""),
        challenge=body.get("challenge", ""),
        icon=body.get("icon", ""),
        color=body.get("color", "#8b5cf6"),
        prize=body.get("prize", ""),
        track_type=body.get("track_type"),
        criteria=body.get("criteria", []),
        resources=body.get("resources", []),
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)

    # Reindex hackathon data (tracks changed)
    try:
        from app.assistant.indexer import DocumentIndexer
        from app.models import Hackathon

        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()
        if hackathon:
            indexer = DocumentIndexer(db)
            await indexer.index_hackathon(hackathon)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to reindex after track creation: {e}")

    await _bust_tracks_cache(hackathon_id)
    return _track_to_response(track)


@router.put("/{hackathon_id}/tracks/{track_id}")
async def update_track(
    hackathon_id: str,
    track_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a track (organizer only).

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Load the track by id and hackathon_id.
    3. Raise 404 if the track is not found.
    4. Update allowed fields from the request body.
    5. Commit changes.
    6. Reindex hackathon data and bust the tracks cache.
    7. Return the updated track details.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if track not found.
    Side Effects: Mutates Track row; reindexes hackathon; busts cache.
    Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
    Consumers: PUT /api/hackathons/{hackathon_id}/tracks/{track_id}, organizer dashboard.
    """
    await _require_organizer(hackathon_id, db, user_payload)
    result = await db.execute(select(Track).where(Track.id == track_id, Track.hackathon_id == hackathon_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    for field in (
        "name",
        "description",
        "challenge",
        "icon",
        "color",
        "prize",
        "track_type",
        "criteria",
        "resources",
        "resources_markdown",
    ):
        if field in body:
            setattr(track, field, body[field])
    await db.commit()
    await db.refresh(track)

    # Reindex hackathon data (tracks changed)
    try:
        from app.assistant.indexer import DocumentIndexer
        from app.models import Hackathon

        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()
        if hackathon:
            indexer = DocumentIndexer(db)
            await indexer.index_hackathon(hackathon)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to reindex after track update: {e}")

    await _bust_tracks_cache(hackathon_id)
    return _track_to_response(track)


@router.delete("/{hackathon_id}/tracks/{track_id}", status_code=200)
async def delete_track(
    hackathon_id: str,
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a track (organizer only).

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Load the track by id and hackathon_id.
    3. Raise 404 if the track is not found.
    4. Delete the track and commit.
    5. Reindex hackathon data and bust the tracks cache.
    6. Return a confirmation dict.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if track not found.
    Side Effects: Deletes Track row; reindexes hackathon; busts cache.
    Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
    Consumers: DELETE /api/hackathons/{hackathon_id}/tracks/{track_id}, organizer dashboard.
    """
    await _require_organizer(hackathon_id, db, user_payload)
    result = await db.execute(select(Track).where(Track.id == track_id, Track.hackathon_id == hackathon_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    await db.delete(track)
    await db.commit()

    # Reindex hackathon data (tracks changed)
    try:
        from app.assistant.indexer import DocumentIndexer
        from app.models import Hackathon

        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()
        if hackathon:
            indexer = DocumentIndexer(db)
            await indexer.index_hackathon(hackathon)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to reindex after track deletion: {e}")

    await _bust_tracks_cache(hackathon_id)
    return {"detail": "ok"}


async def _bust_tracks_cache(hackathon_id: str):
    """Invalidate cached track listings after a mutation.

    Behavior:
    1. Delete cache entries matching the tracks key prefix pattern.

    Side Effects: Deletes cache keys matching the tracks prefix.
    Dependencies: app.cache.cache_delete_pattern.
    Consumers: Internal helper called after track mutations.
    """
    await cache_delete_pattern(f"{CACHE_PFX}:list_tracks:*")
