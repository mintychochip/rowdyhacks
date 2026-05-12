#!/usr/bin/env python3
"""Standalone script to seed default resource markdown files into MinIO/S3.

Usage:
    python scripts/seed-resources.py

Requires:
    - HACKVERIFY_S3_ENDPOINT, HACKVERIFY_S3_BUCKET, etc. from .env
    - Or run inside the Docker backend container where env vars are already set.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.storage import StorageService


FILES = {
    "resources/getting-started.md": """---
title: Getting Started
tab_group: Guides
sort_order: 1
tab_group_order: 1
---

# Getting Started

Welcome to the hackathon! This guide will help you hit the ground running.

## What to Bring

- Laptop and charger
- Student ID for check-in
- Water bottle and snacks
- Any hardware you want to hack on

## Schedule Overview

| Time | Event |
|------|-------|
| 09:00 | Check-in & Breakfast |
| 10:00 | Opening Ceremony |
| 11:00 | Hacking Begins! |
| 20:00 | Dinner |
| 23:00 | Midnight Snack |

## Quick Links

- [Submit your project](../resources/apis)
- [Hardware lab hours](../resources/hardware)
- [Discord community](https://discord.gg)

Have fun and build something amazing!
""",
    "resources/apis.md": """---
title: APIs
tab_group: Guides
sort_order: 2
tab_group_order: 1
---

# APIs & Services

A curated list of free APIs and services you can use during the hackathon.

## Web APIs

- **OpenWeatherMap** -- Real-time weather data
- **NewsAPI** -- Headlines and news articles
- **GitHub API** -- Repositories, issues, and user data
- **Twilio** -- SMS and voice messaging

## AI / ML

- **OpenAI API** -- GPT-4, embeddings, DALL-E
- **Hugging Face** -- Open-source model inference
- **Google Cloud Vision** -- Image analysis

## Databases

- **Firebase** -- Real-time NoSQL database
- **Supabase** -- Open-source Firebase alternative
- **PlanetScale** -- Serverless MySQL

Check the documentation for rate limits and authentication requirements.
""",
    "resources/hardware.md": """---
title: Hardware
tab_group: Guides
sort_order: 3
tab_group_order: 1
---

# Hardware Lab

The hardware lab is open 24/7 during the hackathon. Come build something physical!

## Available Equipment

- Arduino Uno & Mega boards
- Raspberry Pi 4 (4GB)
- Sensors: temperature, humidity, motion, distance
- Motors, servos, and motor drivers
- Breadboards, jumper wires, resistors, LEDs
- Soldering stations (supervised use)

## Checkout Process

1. Visit the hardware desk near the main stage.
2. Show your hackathon badge.
3. Sign out items on the checkout sheet.
4. Return all equipment before the closing ceremony.

## Getting Help

Hardware mentors are available:
- **Friday 2PM--6PM**
- **Saturday 10AM--8PM**

Ask in the #hardware channel on Discord for quick questions.
""",
}


async def main():
    storage = StorageService()

    # Skip if already seeded
    if await storage.object_exists("resources/getting-started.md"):
        print("Resources already seeded (getting-started.md exists).")
        return

    for key, body in FILES.items():
        await storage.put_object(
            key,
            body.encode("utf-8"),
            content_type="text/markdown; charset=utf-8",
        )
        print(f"  Uploaded {key}")

    print("Done! 3 resource files seeded to MinIO.")


if __name__ == "__main__":
    asyncio.run(main())
