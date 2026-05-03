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
    }


DEFAULT_TRACKS = [
    {
        "name": "Deep Space Exploration",
        "description": "Push the boundaries of space technology. Build tools for satellite data analysis, mission planning, orbital mechanics simulations, or astronaut support systems.",
        "challenge": "Your mission: create a working prototype that solves a real problem in space exploration. This could be a satellite trajectory planner, a telemetry dashboard, a radiation exposure calculator for astronauts, or an AI system that classifies celestial objects from telescope imagery.\n\nLooking for projects that demonstrate technical depth — bonus points for using real NASA/ESA datasets, simulating realistic physics, or building hardware prototypes with sensors.",
        "icon": "\U0001f680",
        "color": "#8b5cf6",
        "prize": "$1,000 + SpaceX Tour",
        "track_type": "prize",
        "criteria": ["Innovation", "Technical Complexity", "Space Applicability", "Use of Real Data"],
        "resources": [
            {"name": "NASA Open APIs", "url": "https://api.nasa.gov/"},
            {"name": "Space-Track.org", "url": "https://www.space-track.org/"},
            {"name": "ESA Sky", "url": "https://sky.esa.int/"},
            {"name": "Celestrak Satellite Data", "url": "https://celestrak.org/"},
        ],
    },
    {
        "name": "Orbital Commerce",
        "description": "Create the future of the space economy. Develop marketplace platforms, logistics coordination tools, supply chain trackers, or financial systems for the growing orbital industry.",
        "challenge": "The commercialization of low Earth orbit is accelerating. Your challenge: build a tool, platform, or system that enables commerce in space. Ideas: a marketplace for satellite services, a launch logistics scheduler, a space debris cleanup bidding platform, or a DeFi protocol for satellite time-sharing.\n\nJudges are looking for viable business models and clean UX — this track rewards product thinking as much as technical execution.",
        "icon": "\U0001f48e",
        "color": "#06b6d4",
        "prize": "$800 + Starlink Kit",
        "track_type": "prize",
        "criteria": ["Business Viability", "UX Design", "Market Potential", "Technical Execution"],
        "resources": [
            {"name": "Space Economy Report", "url": "https://spacefoundation.org/research/"},
            {"name": "AWS Ground Station", "url": "https://aws.amazon.com/ground-station/"},
            {"name": "Orbital Mechanics Docs", "url": "https://docs.astropy.org/"},
        ],
    },
    {
        "name": "Cosmic Commons",
        "description": "Democratize access to space. Build educational platforms, citizen science tools, community-driven research initiatives, or accessibility solutions that bring space exploration to everyone.",
        "challenge": "Space shouldn't just be for billionaires and government agencies. Your task: create something that makes space more accessible. A VR planetarium for schools, a mobile app that lets anyone contribute to astronomy research, a translation layer for scientific papers, or a platform connecting amateur astronomers with professional researchers.\n\nImpact matters here — judges weigh social good and accessibility as highly as technical complexity.",
        "icon": "\U0001f30c",
        "color": "#fbbf24",
        "prize": "$600 + Celestron Telescope",
        "track_type": "themed",
        "criteria": ["Social Impact", "Accessibility", "Community Engagement", "Innovation"],
        "resources": [
            {"name": "Zooniverse Projects", "url": "https://www.zooniverse.org/"},
            {"name": "NASA Citizen Science", "url": "https://science.nasa.gov/citizen-science/"},
            {"name": "Stellarium Web", "url": "https://stellarium-web.org/"},
        ],
    },
    {
        "name": "Nebula Arts",
        "description": "Where space meets creativity. Develop immersive visualizations, space-themed games, generative art from astronomical data, or interactive experiences inspired by the cosmos.",
        "challenge": "Art and science are two sides of the same coin. For this track, create something beautiful that's grounded in real space data or physics. A WebGL nebula renderer, a procedural planet generator, a sonification of solar wind data, a space exploration game with realistic orbital mechanics, or a mixed reality stargazing app.\n\nWe're looking for aesthetic impact AND technical craft — make it gorgeous and make it work.",
        "icon": "\u2728",
        "color": "#ec4899",
        "prize": "$500 + Wacom Tablet",
        "track_type": "themed",
        "criteria": ["Aesthetic Quality", "Technical Execution", "Concept Originality", "Emotional Impact"],
        "resources": [
            {"name": "Three.js Docs", "url": "https://threejs.org/"},
            {"name": "ESA Image Archive", "url": "https://www.esa.int/ESA_Multimedia/Images"},
            {"name": "Hubble Gallery", "url": "https://hubblesite.org/resource-gallery/images"},
            {"name": "OpenGL Shader Resources", "url": "https://www.shadertoy.com/"},
        ],
    },
    {
        "name": "Mission Control AI",
        "description": "Apply artificial intelligence to space operations. Build ML models for anomaly detection, predictive maintenance, autonomous navigation, mission scheduling, or spacecraft health monitoring.",
        "challenge": "AI is transforming how we operate in space. Your challenge: apply machine learning to a real space operations problem. Train a model to detect anomalies in telemetry data, build a reinforcement learning agent for autonomous docking, create an LLM-powered mission planning assistant, or develop a computer vision system for satellite inspection.\n\nUse any ML framework. Bonus for live demos, real datasets, or creative model architectures suited to edge deployment.",
        "icon": "\U0001f916",
        "color": "#10b981",
        "prize": "$1,200 + NVIDIA Jetson Kit",
        "track_type": "prize",
        "criteria": ["AI Innovation", "Model Performance", "Problem Relevance", "Presentation Clarity"],
        "resources": [
            {"name": "NASA Telemetry Datasets", "url": "https://data.nasa.gov/"},
            {"name": "ESA Gaia Archive", "url": "https://gea.esac.esa.int/archive/"},
            {"name": "TensorFlow Docs", "url": "https://www.tensorflow.org/"},
            {"name": "PyTorch Documentation", "url": "https://pytorch.org/docs/"},
        ],
    },
    {
        "name": "Lunar Settlements",
        "description": "Design for life beyond Earth. Create habitat concepts, life support system simulations, resource utilization tools, agricultural tech for microgravity, or urban planning for off-world colonies.",
        "challenge": "If we're going to stay on the Moon (and eventually Mars), we need to figure out how to live there. Your mission: design and prototype a system for sustaining human life off-world. A hydroponics controller for microgravity, a 3D habitat layout tool using ISRU (in-situ resource utilization), a water recycling system simulator, or a crew psychology dashboard.\n\nThis track values systems thinking — how does your solution fit into the bigger picture of a self-sustaining settlement?",
        "icon": "\U0001f315",
        "color": "#f97316",
        "prize": "$900 + 3D Printer",
        "track_type": "themed",
        "criteria": ["Systems Thinking", "Feasibility", "Innovation", "Sustainability"],
        "resources": [
            {"name": "NASA Artemis Program", "url": "https://www.nasa.gov/artemis/"},
            {"name": "Lunar ISRU Papers", "url": "https://www.lpi.usra.edu/"},
            {"name": "Mars Habitat Research", "url": "https://www.nasa.gov/hrp/"},
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


# ── Routes ────────────────────────────────────────────────


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

    for field in ("name", "description", "challenge", "icon", "color", "prize", "track_type", "criteria", "resources"):
        if field in body:
            setattr(track, field, body[field])
    await db.commit()
    await db.refresh(track)
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
    await _bust_tracks_cache(hackathon_id)
    return {"detail": "ok"}


async def _bust_tracks_cache(hackathon_id: str):
    """Invalidate cached track listings after a mutation."""
    await cache_delete_pattern(f"{CACHE_PFX}:list_tracks:*")
