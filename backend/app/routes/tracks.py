"""Tracks management routes."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.cache import cache_delete_pattern, cached
from app.database import get_db
from app.models import Hackathon, Track, User, UserRole

router = APIRouter(prefix="/api/hackathons", tags=["tracks"])

TRACKS_CACHE_TTL = 300  # 5 minutes
CACHE_PFX = "tracks"


def _get_current_user_payload(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _get_current_user(db: AsyncSession, authorization: str | None) -> User:
    payload = _get_current_user_payload(authorization)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _require_organizer(hackathon_id: str, db: AsyncSession, authorization: str | None) -> Hackathon:
    user = await _get_current_user(db, authorization)
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can manage tracks")
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return hackathon


def _track_to_response(t: Track) -> dict:
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
    result = await db.execute(select(Track).where(Track.hackathon_id == hackathon_id).order_by(Track.created_at))
    tracks = result.scalars().all()
    return {"hackathon_id": hackathon_id, "tracks": [_track_to_response(t) for t in tracks]}


@router.post("/{hackathon_id}/tracks", status_code=201)
async def create_track(
    hackathon_id: str,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    await _require_organizer(hackathon_id, db, authorization)
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
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    await _require_organizer(hackathon_id, db, authorization)
    result = await db.execute(select(Track).where(Track.id == track_id, Track.hackathon_id == hackathon_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    for field in ("name", "description", "challenge", "icon", "color", "prize", "track_type", "criteria", "resources", "resources_markdown"):
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
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    await _require_organizer(hackathon_id, db, authorization)
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
    """Invalidate cached track listings after a mutation."""
    await cache_delete_pattern(f"{CACHE_PFX}:list_tracks:*")
