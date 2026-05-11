"""Hackathon backup and restore service."""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    Prize,
    Registration,
    RegistrationStatus,
    Sponsor,
    Team,
    TeamMember,
    Track,
    Workshop,
)


class _HackathonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, RegistrationStatus):
            return obj.value
        return super().default(obj)


def _serialize(obj: dict) -> str:
    return json.dumps(obj, cls=_HackathonEncoder)


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class BackupService:
    """Export and restore hackathon data."""

    async def export_hackathon(self, db: AsyncSession, hackathon_id) -> dict:
        """Export a hackathon and all related data."""
        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()
        if not hackathon:
            raise ValueError("Hackathon not found")

        data = {
            "hackathon": {
                "name": hackathon.name,
                "start_date": hackathon.start_date,
                "end_date": hackathon.end_date,
                "application_deadline": hackathon.application_deadline,
                "max_participants": hackathon.max_participants,
                "waitlist_enabled": hackathon.waitlist_enabled,
                "description": hackathon.description,
                "schedule": hackathon.schedule,
                "venue_address": hackathon.venue_address,
                "parking_info": hackathon.parking_info,
                "wifi_ssid": hackathon.wifi_ssid,
                "wifi_password": hackathon.wifi_password,
                "discord_invite_url": hackathon.discord_invite_url,
                "devpost_url": hackathon.devpost_url,
            },
            "tracks": [],
            "teams": [],
            "workshops": [],
            "sponsors": [],
            "prizes": [],
            "registrations": [],
        }

        tracks_result = await db.execute(select(Track).where(Track.hackathon_id == hackathon_id))
        for track in tracks_result.scalars().all():
            data["tracks"].append(
                {
                    "id": str(track.id),
                    "name": track.name,
                    "description": track.description,
                    "challenge": track.challenge,
                    "icon": track.icon,
                    "color": track.color,
                    "prize": track.prize,
                    "track_type": track.track_type,
                    "criteria": track.criteria,
                    "resources": track.resources,
                    "resources_markdown": track.resources_markdown,
                }
            )

        teams_result = await db.execute(select(Team).where(Team.hackathon_id == hackathon_id))
        for team in teams_result.scalars().all():
            members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))
            members = [{"user_id": m.user_id, "joined_at": m.joined_at} for m in members_result.scalars().all()]
            data["teams"].append(
                {
                    "id": str(team.id),
                    "name": team.name,
                    "join_code": team.join_code,
                    "captain_id": team.captain_id,
                    "created_at": team.created_at,
                    "members": members,
                }
            )

        workshops_result = await db.execute(select(Workshop).where(Workshop.hackathon_id == hackathon_id))
        for ws in workshops_result.scalars().all():
            data["workshops"].append(
                {
                    "title": ws.title,
                    "description": ws.description,
                    "start_time": ws.start_time,
                    "end_time": ws.end_time,
                    "location": ws.location,
                    "speaker_name": ws.speaker_name,
                }
            )

        sponsors_result = await db.execute(select(Sponsor).where(Sponsor.hackathon_id == hackathon_id))
        for sp in sponsors_result.scalars().all():
            data["sponsors"].append(
                {
                    "name": sp.name,
                    "tier": sp.tier,
                    "logo_url": sp.logo_url,
                    "website_url": sp.website_url,
                    "description": sp.description,
                }
            )

        prizes_result = await db.execute(select(Prize).where(Prize.hackathon_id == hackathon_id))
        for prize in prizes_result.scalars().all():
            data["prizes"].append(
                {
                    "name": prize.name,
                    "description": prize.description,
                    "amount": prize.amount,
                    "currency": prize.currency,
                    "track_id": str(prize.track_id) if prize.track_id else None,
                }
            )

        reg_result = await db.execute(select(Registration).where(Registration.hackathon_id == hackathon_id))
        for reg in reg_result.scalars().all():
            data["registrations"].append(
                {
                    "user_id": reg.user_id,
                    "status": reg.status,
                    "created_at": reg.created_at,
                }
            )

        return data

    async def restore_hackathon(
        self,
        db: AsyncSession,
        organizer_id: str,
        data: dict,
    ) -> Hackathon:
        """Restore a hackathon from exported data."""
        h_data = data.get("hackathon", {})
        hackathon = Hackathon(
            name=h_data.get("name", "Restored Hackathon"),
            start_date=_parse_dt(h_data.get("start_date")),
            end_date=_parse_dt(h_data.get("end_date")),
            application_deadline=_parse_dt(h_data.get("application_deadline")),
            max_participants=h_data.get("max_participants"),
            waitlist_enabled=h_data.get("waitlist_enabled", False),
            description=h_data.get("description"),
            schedule=h_data.get("schedule"),
            venue_address=h_data.get("venue_address"),
            parking_info=h_data.get("parking_info"),
            wifi_ssid=h_data.get("wifi_ssid"),
            wifi_password=h_data.get("wifi_password"),
            discord_invite_url=h_data.get("discord_invite_url"),
            devpost_url=h_data.get("devpost_url"),
            organizer_id=organizer_id,
        )
        db.add(hackathon)
        await db.commit()
        await db.refresh(hackathon)

        # Restore tracks
        for t_data in data.get("tracks", []):
            track = Track(
                hackathon_id=hackathon.id,
                name=t_data["name"],
                description=t_data.get("description"),
                challenge=t_data.get("challenge"),
                icon=t_data.get("icon"),
                color=t_data.get("color"),
                prize=t_data.get("prize"),
                track_type=t_data.get("track_type"),
                criteria=t_data.get("criteria"),
                resources=t_data.get("resources"),
                resources_markdown=t_data.get("resources_markdown"),
            )
            db.add(track)

        await db.commit()

        # Restore workshops
        for w_data in data.get("workshops", []):
            ws = Workshop(
                hackathon_id=hackathon.id,
                title=w_data["title"],
                description=w_data.get("description"),
                start_time=_parse_dt(w_data.get("start_time")),
                end_time=_parse_dt(w_data.get("end_time")),
                location=w_data.get("location"),
                speaker_name=w_data.get("speaker_name"),
            )
            db.add(ws)

        # Restore sponsors
        for s_data in data.get("sponsors", []):
            sp = Sponsor(
                hackathon_id=hackathon.id,
                name=s_data["name"],
                tier=s_data.get("tier", "silver"),
                logo_url=s_data.get("logo_url"),
                website_url=s_data.get("website_url"),
                description=s_data.get("description"),
            )
            db.add(sp)

        # Restore prizes
        for p_data in data.get("prizes", []):
            prize = Prize(
                hackathon_id=hackathon.id,
                name=p_data["name"],
                description=p_data.get("description"),
                amount=p_data.get("amount"),
                currency=p_data.get("currency", "USD"),
                track_id=p_data.get("track_id"),
            )
            db.add(prize)

        await db.commit()
        await db.refresh(hackathon)
        return hackathon
