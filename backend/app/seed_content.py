"""Seed default content pages for resources.

This module provides functions to seed default content pages on application startup.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentPage, User, UserRole


DEFAULT_CONTENT_PAGES = [
    {
        "slug": "getting-started",
        "title": "Getting Started",
        "content": """# Getting Started

Welcome to the hackathon! This guide will help you get up and running quickly.

## Pre-event Checklist

- [ ] Join our Discord server
- [ ] Set up your development environment
- [ ] Form a team or find teammates
- [ ] Review the tracks and choose your challenge
- [ ] Read the judging criteria

## Quick Links

- **Discord**: Connect with other hackers and mentors
- **Devpost**: Submit your project here
- **Tracks**: Explore the challenge tracks
- **Resources**: Check out APIs and tools

## Schedule Overview

| Time | Activity |
|------|----------|
| Day 1 - 9:00 AM | Opening Ceremony |
| Day 1 - 10:00 AM | Hacking Begins |
| Day 2 - 10:00 AM | Project Submissions Due |
| Day 2 - 2:00 PM | Judging Begins |
| Day 2 - 5:00 PM | Closing Ceremony |

## Need Help?

- Ask in the #help channel on Discord
- Find a mentor wearing a yellow lanyard
- Check the FAQ section

Happy hacking!""",
        "tab_group": "resources",
        "sort_order": 0,
        "tab_group_order": 0,
        "is_published": True,
    },
    {
        "slug": "apis",
        "title": "APIs & Tools",
        "content": """# APIs & Tools

A curated list of APIs and tools available for your project.

## Recommended APIs

### Data & AI
- **OpenAI API** - GPT-4, DALL-E, embeddings
- **Hugging Face** - Open-source ML models
- **Google Cloud AI** - Vision, NLP, Speech

### Communication
- **Twilio** - SMS, voice, and video
- **SendGrid** - Email delivery
- **Stream** - Chat and activity feeds

### Storage & Databases
- **Firebase** - Real-time database and auth
- **Supabase** - Open-source Firebase alternative
- **PlanetScale** - Serverless MySQL

### Maps & Location
- **Google Maps API** - Maps and geocoding
- **Mapbox** - Custom maps and navigation

## Development Tools

### Free Tier Cloud Credits
- GitHub Student Pack - $100+ in credits
- AWS Educate - $100-150 in credits
- Azure for Students - $100 in credits

### Useful Libraries
- **Frontend**: React, Vue, Svelte
- **Backend**: FastAPI, Express, Django
- **ML**: PyTorch, TensorFlow, scikit-learn

## Workshop Recordings

Workshop recordings will be posted here after each session.

---

*Last updated: Check back during the event for more resources!*""",
        "tab_group": "resources",
        "sort_order": 1,
        "tab_group_order": 0,
        "is_published": True,
    },
    {
        "slug": "hardware",
        "title": "Hardware",
        "content": """# Hardware

Hardware available for loan during the hackathon.

## Available Hardware

### Microcontrollers
- Arduino Uno (20 available)
- Raspberry Pi 4 (10 available)
- ESP32 Dev Boards (15 available)

### Sensors
- Temperature/Humidity sensors
- Accelerometers
- Light sensors
- Ultrasonic distance sensors

### Other Equipment
- VR Headsets (Meta Quest 2)
- Webcams
- USB Microphones
- LED strips and components

## Borrowing Process

1. Visit the hardware desk (Main Hall, Table 5)
2. Present your hacker badge
3. Fill out the hardware loan form
4. Return by 9:00 AM on Day 2

## Hardware Workshops

- **Intro to Arduino** - Day 1, 2:00 PM
- **IoT with ESP32** - Day 1, 4:00 PM
- **VR Development** - Day 1, 6:00 PM

## Project Ideas

- Smart room monitoring system
- Wearable fitness tracker
- Automated plant watering system
- VR data visualization

---

**Note**: You are responsible for any damage to borrowed hardware. Please handle with care!""",
        "tab_group": "resources",
        "sort_order": 2,
        "tab_group_order": 0,
        "is_published": True,
    },
]


async def seed_default_content(db: AsyncSession) -> None:
    """Seed default content pages if they don't exist.

    Requires at least one organizer user to exist in the database.
    """
    # Find an organizer to use as the creator
    result = await db.execute(
        select(User).where(User.role == UserRole.organizer).limit(1)
    )
    organizer = result.scalar_one_or_none()

    if not organizer:
        # If no organizer, try to find any user
        result = await db.execute(select(User).limit(1))
        organizer = result.scalar_one_or_none()

    if not organizer:
        # No users exist yet, skip seeding
        return

    for page_data in DEFAULT_CONTENT_PAGES:
        # Check if page already exists
        result = await db.execute(
            select(ContentPage).where(ContentPage.slug == page_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing page if content changed
            existing.title = page_data["title"]
            existing.content = page_data["content"]
            existing.tab_group = page_data["tab_group"]
            existing.sort_order = page_data["sort_order"]
            existing.tab_group_order = page_data["tab_group_order"]
            existing.is_published = page_data["is_published"]
            existing.updated_at = datetime.now(UTC)
        else:
            # Create new page
            page = ContentPage(
                slug=page_data["slug"],
                title=page_data["title"],
                content=page_data["content"],
                tab_group=page_data["tab_group"],
                sort_order=page_data["sort_order"],
                tab_group_order=page_data["tab_group_order"],
                is_published=page_data["is_published"],
                created_by=organizer.id,
            )
            db.add(page)

    await db.commit()
