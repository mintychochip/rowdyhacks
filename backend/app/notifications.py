"""Discord webhook notifications for hackathon events."""

import httpx


async def send_discord_webhook(webhook_url: str, content: str, username: str = "Hack the Valley") -> bool:
    """Send a message to a Discord webhook. Returns True on success."""
    if not webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                webhook_url,
                json={
                    "content": content,
                    "username": username,
                },
            )
            return resp.status_code == 204
    except Exception:
        return False


def format_application_notification(name: str, email: str, team_name: str | None, hackathon_name: str) -> str:
    """Format a Discord message for a new application."""
    display = team_name or name
    return (
        f"📨 **New Application**\n"
        f"**{display}** applied to **{hackathon_name}**\n"
        f"Email: `{email}`\n"
        f"Review: use the organizer dashboard to accept or reject"
    )


def format_submission_notification(
    project_title: str, team_name: str | None, name: str, verdict: str, risk: int
) -> str:
    """Format a Discord message for a completed project submission."""
    display = team_name or name
    emoji = {"clean": "✅", "review": "⚠️", "flagged": "🚩"}.get(verdict, "❓")
    return (
        f"{emoji} **Project Submitted**\n"
        f"**{project_title}** by **{display}**\n"
        f"Risk Score: `{risk}` | Verdict: `{verdict}`"
    )
