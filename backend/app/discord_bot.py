"""
Discord bot for managing hackathon applications.
Uses discord.py (official SDK) with slash commands and interactive buttons.
"""

import asyncio
import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import async_session
from app.models import Hackathon, Registration, RegistrationStatus, Submission, SubmissionStatus, Verdict

logger = logging.getLogger("discord_bot")


class ApplicationView(discord.ui.View):
    """Buttons for reviewing / accepting / rejecting a single application."""

    def __init__(self, registration_id: str, hackathon_id: str):
        """Initialize interactive action buttons for a registration review message.

        Behavior:
        1. Call the parent View constructor with no timeout.
        2. Store the registration and hackathon IDs.
        3. Create Review, Accept, and Reject buttons and attach their callbacks.
        4. Add the buttons to the view.

        Raises: None
        Side Effects: Adds discord.ui.Button items to the view.
        Dependencies: discord.ui.View, discord.ui.Button.
        Consumers: post_application_to_discord when building the application embed.
        """
        super().__init__(timeout=None)
        self.registration_id = registration_id
        self.hackathon_id = hackathon_id

        review_btn = discord.ui.Button(
            label="Review",
            style=discord.ButtonStyle.primary,
            custom_id=f"app_review_{registration_id}",
        )
        review_btn.callback = self._review_callback
        self.add_item(review_btn)

        accept_btn = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.green,
            custom_id=f"app_accept_{registration_id}",
        )
        accept_btn.callback = self._accept_callback
        self.add_item(accept_btn)

        reject_btn = discord.ui.Button(
            label="Reject",
            style=discord.ButtonStyle.red,
            custom_id=f"app_reject_{registration_id}",
        )
        reject_btn.callback = self._reject_callback
        self.add_item(reject_btn)

    async def _review_callback(self, interaction: discord.Interaction):
        """Show the full application details in an ephemeral message.

        Behavior:
        1. Open an async database session.
        2. Load the registration with its user eagerly loaded.
        3. If the registration is missing, reply with an error and return.
        4. Build a Discord embed with all applicant fields.
        5. Send the embed as an ephemeral reply.

        Raises: None
        Side Effects: Sends an ephemeral Discord message.
        Dependencies: app.database.async_session, sqlalchemy.orm.selectinload, discord.Embed.
        Consumers: Discord UI button callback triggered by the Review button.
        """
        async with async_session() as db:
            result = await db.execute(
                select(Registration)
                .where(Registration.id == self.registration_id)
                .options(selectinload(Registration.user))
            )
            reg = result.scalar_one_or_none()
            if not reg:
                await interaction.response.send_message("Registration not found.", ephemeral=True)
                return

        detail = discord.Embed(
            title=f"Application: {reg.team_name or reg.user.name}",
            color=discord.Color.blue(),
        )
        detail.add_field(name="Name", value=reg.user.name, inline=True)
        detail.add_field(name="Email", value=reg.user.email, inline=True)
        detail.add_field(name="Phone", value=reg.phone or "—", inline=True)
        detail.add_field(name="Age", value=str(reg.age) if reg.age else "—", inline=True)
        detail.add_field(name="Pronouns", value=reg.pronouns or "—", inline=True)
        detail.add_field(name="School", value=reg.school or "—", inline=True)
        detail.add_field(name="Major", value=reg.major or "—", inline=True)
        detail.add_field(name="Status", value=f"`{reg.status.value}`", inline=True)
        detail.add_field(name="Experience", value=reg.experience_level or "—", inline=True)
        skills = ", ".join(reg.skills) if reg.skills else "—"
        detail.add_field(name="Skills", value=skills, inline=False)
        detail.add_field(name="GitHub", value=reg.github_url or "—", inline=True)
        detail.add_field(name="LinkedIn", value=reg.linkedin_url or "—", inline=True)
        detail.add_field(name="Resume", value=reg.resume_url or "—", inline=True)
        detail.add_field(name="T-Shirt", value=reg.t_shirt_size or "—", inline=True)
        detail.add_field(name="Dietary", value=reg.dietary_restrictions or "—", inline=True)
        detail.add_field(
            name="Emergency Contact",
            value=f"{reg.emergency_contact_name or '—'}\n{reg.emergency_contact_phone or '—'}",
            inline=True,
        )
        if reg.team_name:
            detail.add_field(name="Team", value=reg.team_name, inline=True)
        if reg.team_members:
            detail.add_field(name="Members", value=", ".join(reg.team_members), inline=True)
        detail.add_field(
            name="What They'll Build",
            value=reg.what_build or "—",
            inline=False,
        )
        detail.add_field(
            name="Why Participate",
            value=reg.why_participate or "—",
            inline=False,
        )
        detail.set_footer(text=f"ID: {reg.id}")

        await interaction.response.send_message(embed=detail, ephemeral=True)

    async def _accept_callback(self, interaction: discord.Interaction):
        """Accept the registration and generate a QR token.

        Behavior:
        1. Open an async database session.
        2. Load the registration with its user eagerly loaded.
        3. Validate the registration exists and is still pending.
        4. Update the status to ``accepted`` and set the accepted timestamp.
        5. Generate a QR token bound to the registration, user, and hackathon.
        6. Commit the transaction.
        7. Update the original Discord embed to show Accepted and remove the action view.
        8. Send an ephemeral confirmation reply.

        Raises: None
        Side Effects: Updates a Registration row; edits a Discord message; sends a Discord reply.
        Dependencies: app.database.async_session, app.auth.create_qr_token, sqlalchemy.orm.selectinload.
        Consumers: Discord UI button callback triggered by the Accept button.
        """
        async with async_session() as db:
            result = await db.execute(
                select(Registration)
                .where(Registration.id == self.registration_id)
                .options(selectinload(Registration.user))
            )
            reg = result.scalar_one_or_none()
            if not reg:
                await interaction.response.send_message("Registration not found.", ephemeral=True)
                return
            if reg.status != RegistrationStatus.pending:
                await interaction.response.send_message(f"Already {reg.status.value}.", ephemeral=True)
                return

            reg.status = RegistrationStatus.accepted
            reg.accepted_at = datetime.now(UTC)
            await db.commit()

            # Generate QR token
            from app.auth import create_qr_token

            result2 = await db.execute(select(Hackathon).where(Hackathon.id == self.hackathon_id))
            hackathon = result2.scalar_one()
            reg.qr_token = create_qr_token(str(reg.id), str(reg.user_id), str(hackathon.id), hackathon.end_date)
            await db.commit()

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(0, name="Status", value="Accepted", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            f"**{reg.user.name}** accepted! QR token generated.",
            ephemeral=True,
        )

    async def _reject_callback(self, interaction: discord.Interaction):
        """Reject the registration and update the message embed.

        Behavior:
        1. Open an async database session.
        2. Load the registration with its user eagerly loaded.
        3. Validate the registration exists and is still pending.
        4. Update the status to ``rejected``.
        5. Commit the transaction.
        6. Update the original Discord embed to show Rejected and remove the action view.
        7. Send an ephemeral confirmation reply.

        Raises: None
        Side Effects: Updates a Registration row; edits a Discord message; sends a Discord reply.
        Dependencies: app.database.async_session, sqlalchemy.orm.selectinload.
        Consumers: Discord UI button callback triggered by the Reject button.
        """
        async with async_session() as db:
            result = await db.execute(
                select(Registration)
                .where(Registration.id == self.registration_id)
                .options(selectinload(Registration.user))
            )
            reg = result.scalar_one_or_none()
            if not reg:
                await interaction.response.send_message("Registration not found.", ephemeral=True)
                return
            if reg.status != RegistrationStatus.pending:
                await interaction.response.send_message(f"Already {reg.status.value}.", ephemeral=True)
                return

            reg.status = RegistrationStatus.rejected
            await db.commit()

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_field_at(0, name="Status", value="Rejected", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            f"**{reg.user.name}** rejected.",
            ephemeral=True,
        )


class HackathonBot(discord.Client):
    """Discord client with slash commands for hackathon management."""

    def __init__(self):
        """Set up default intents and the command tree."""
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Sync slash commands after login."""
        await self.tree.sync()
        logger.info("Discord bot commands synced")

    async def on_ready(self):
        """Log bot connection details on startup."""
        print(f"[BOT] on_ready: {self.user}, guilds={len(self.guilds)}")
        logger.info(f"Discord bot logged in as {self.user}")


bot = HackathonBot()


@bot.tree.command(name="applications", description="List pending hackathon applications")
@app_commands.describe(status="Filter by status: pending, accepted, all")
async def list_applications(interaction: discord.Interaction, status: str = "pending"):
    """List hackathon registrations filtered by status.

    Behavior:
    1. Defer the interaction response.
    2. Open an async database session.
    3. Find the most recently created hackathon.
    4. Build a query filtering registrations by hackathon and optional status.
    5. Load up to 25 registrations with eagerly loaded users.
    6. Count total matching registrations.
    7. Build Discord embeds for each registration.
    8. Send embeds in batches of 10 (Discord limit).

    Raises: None
    Side Effects: Sends Discord follow-up messages with embeds.
    Dependencies: app.database.async_session, app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus, sqlalchemy.orm.selectinload.
    Consumers: Discord /applications slash command.
    """
    await interaction.response.defer(ephemeral=False)

    async with async_session() as db:
        # Get latest hackathon
        hk_result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
        hackathon = hk_result.scalars().first()
        if not hackathon:
            await interaction.followup.send("No hackathon found.")
            return

        filters = [Registration.hackathon_id == hackathon.id]
        if status != "all":
            try:
                filters.append(Registration.status == RegistrationStatus(status))
            except ValueError:
                await interaction.followup.send(f"Invalid status: {status}")
                return

        result = await db.execute(
            select(Registration)
            .where(*filters)
            .options(selectinload(Registration.user))
            .order_by(Registration.registered_at.desc())
            .limit(25)
        )
        registrations = result.scalars().all()

        count_result = await db.execute(select(func.count(Registration.id)).where(*filters))
        total = count_result.scalar() or 0

    if not registrations:
        await interaction.followup.send(f"No {status} applications.")
        return

    embeds = []
    for reg in registrations:
        embed = discord.Embed(
            title=reg.team_name or reg.user.name,
            description=f"**{hackathon.name}**",
            color=discord.Color.blue() if reg.status == RegistrationStatus.pending else discord.Color.green(),
            timestamp=reg.registered_at,
        )
        embed.add_field(name="Status", value=f"`{reg.status.value}`", inline=False)
        embed.add_field(name="Email", value=reg.user.email, inline=True)
        if reg.team_members:
            embed.add_field(name="Team", value=", ".join(reg.team_members), inline=True)
        embed.set_footer(text=f"ID: {reg.id}")
        embeds.append(embed)

    # Send in batches of 10 (Discord limit)
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        if i == 0:
            await interaction.followup.send(
                f"**{total} {status} application(s)** for {hackathon.name}:",
                embeds=batch,
            )
        else:
            await interaction.followup.send(embeds=batch)


@bot.tree.command(name="stats", description="Show hackathon statistics")
async def show_stats(interaction: discord.Interaction):
    """Display registration and submission statistics for the latest hackathon.

    Behavior:
    1. Defer the interaction response.
    2. Open an async database session.
    3. Find the most recently created hackathon.
    4. Count registrations grouped by status.
    5. Load submissions and compute average risk score and verdict breakdown.
    6. Build a Discord embed with all statistics.
    7. Send the embed as a follow-up message.

    Raises: None
    Side Effects: Sends a Discord follow-up message with an embed.
    Dependencies: app.database.async_session, app.models.Hackathon, app.models.Registration, app.models.Submission, app.models.Verdict, sqlalchemy.func.count.
    Consumers: Discord /stats slash command.
    """
    await interaction.response.defer()

    async with async_session() as db:
        hk_result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
        hackathon = hk_result.scalars().first()
        if not hackathon:
            await interaction.followup.send("No hackathon found.")
            return

        # Registration stats
        reg_counts = {}
        for s in RegistrationStatus:
            count = (
                await db.execute(
                    select(func.count(Registration.id)).where(
                        Registration.hackathon_id == hackathon.id,
                        Registration.status == s,
                    )
                )
            ).scalar() or 0
            reg_counts[s.value] = count

        # Submission stats
        sub_result = await db.execute(select(Submission).where(Submission.hackathon_id == hackathon.id))
        subs = sub_result.scalars().all()
        completed = [s for s in subs if s.status == SubmissionStatus.completed]
        avg_risk = sum(s.risk_score or 0 for s in completed) / len(completed) if completed else 0
        clean = sum(1 for s in completed if s.verdict == Verdict.clean)
        review = sum(1 for s in completed if s.verdict == Verdict.review)
        flagged = sum(1 for s in completed if s.verdict == Verdict.flagged)

    embed = discord.Embed(
        title=f"Stats: {hackathon.name}",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Total Registered", value=str(sum(reg_counts.values())), inline=True)
    embed.add_field(name="Accepted", value=str(reg_counts.get("accepted", 0)), inline=True)
    embed.add_field(name="Checked In", value=str(reg_counts.get("checked_in", 0)), inline=True)
    embed.add_field(name="Pending", value=str(reg_counts.get("pending", 0)), inline=True)
    embed.add_field(name="Rejected", value=str(reg_counts.get("rejected", 0)), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Submissions", value=str(len(subs)), inline=True)
    embed.add_field(name="Completed", value=str(len(completed)), inline=True)
    embed.add_field(name="Avg Risk Score", value=f"{avg_risk:.1f}", inline=True)
    embed.add_field(name="By Verdict", value=f"✅ {clean}  ⚠️ {review}  🚩 {flagged}", inline=False)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="accept", description="Accept a pending application by ID")
@app_commands.describe(registration_id="The registration ID to accept")
async def accept_application(interaction: discord.Interaction, registration_id: str):
    """Accept a pending registration by ID via Discord slash command.

    Behavior:
    1. Defer the interaction as ephemeral.
    2. Open an async database session.
    3. Load the registration with eagerly loaded user and hackathon.
    4. Validate the registration exists and is still pending.
    5. Update the status to ``accepted`` and set the accepted timestamp.
    6. Generate a QR token bound to the registration, user, and hackathon end date.
    7. Commit the transaction.
    8. Send an ephemeral confirmation follow-up.

    Raises: None
    Side Effects: Updates a Registration row; sends a Discord follow-up message.
    Dependencies: app.database.async_session, app.auth.create_qr_token, sqlalchemy.orm.selectinload.
    Consumers: Discord /accept slash command.
    """
    await interaction.response.defer(ephemeral=True)

    async with async_session() as db:
        result = await db.execute(
            select(Registration)
            .where(Registration.id == registration_id)
            .options(selectinload(Registration.user))
            .options(selectinload(Registration.hackathon))
        )
        reg = result.scalar_one_or_none()
        if not reg:
            await interaction.followup.send("Registration not found.", ephemeral=True)
            return
        if reg.status != RegistrationStatus.pending:
            await interaction.followup.send(f"Already {reg.status.value}.", ephemeral=True)
            return

        reg.status = RegistrationStatus.accepted
        reg.accepted_at = datetime.now(UTC)

        from app.auth import create_qr_token

        reg.qr_token = create_qr_token(str(reg.id), str(reg.user_id), str(reg.hackathon_id), reg.hackathon.end_date)
        await db.commit()

    await interaction.followup.send(
        f"✅ **{reg.user.name}** (`{reg.team_name or 'solo'}`) accepted!",
        ephemeral=True,
    )


@bot.tree.command(name="reject", description="Reject a pending application by ID")
@app_commands.describe(registration_id="The registration ID to reject")
async def reject_application(interaction: discord.Interaction, registration_id: str):
    """Reject a pending registration by ID via Discord slash command.

    Behavior:
    1. Defer the interaction as ephemeral.
    2. Open an async database session.
    3. Load the registration with eagerly loaded user.
    4. Validate the registration exists and is still pending.
    5. Update the status to ``rejected``.
    6. Commit the transaction.
    7. Send an ephemeral confirmation follow-up.

    Raises: None
    Side Effects: Updates a Registration row; sends a Discord follow-up message.
    Dependencies: app.database.async_session, sqlalchemy.orm.selectinload.
    Consumers: Discord /reject slash command.
    """
    await interaction.response.defer(ephemeral=True)

    async with async_session() as db:
        result = await db.execute(
            select(Registration).where(Registration.id == registration_id).options(selectinload(Registration.user))
        )
        reg = result.scalar_one_or_none()
        if not reg:
            await interaction.followup.send("Registration not found.", ephemeral=True)
            return
        if reg.status != RegistrationStatus.pending:
            await interaction.followup.send(f"Already {reg.status.value}.", ephemeral=True)
            return

        reg.status = RegistrationStatus.rejected
        await db.commit()

    await interaction.followup.send(
        f"❌ **{reg.user.name}** (`{reg.team_name or 'solo'}`) rejected.",
        ephemeral=True,
    )


async def post_application_to_discord(registration_id: str) -> bool:
    """Post a new application to a Discord channel with Accept/Reject buttons.

    Behavior:
    1. Return False immediately if no Discord bot token is configured.
    2. Open an async database session.
    3. Load the registration with eagerly loaded user and hackathon.
    4. Build a rich Discord embed with applicant details.
    5. Instantiate an ApplicationView with action buttons.
    6. If a channel ID is configured, attempt to send the embed with buttons via the bot.
    7. On failure, fall back to a webhook (text-only, no buttons).
    8. Return True if any delivery method succeeds.

    Raises: None (exceptions are caught and logged).
    Side Effects: Sends a Discord message or webhook request.
    Dependencies: app.database.async_session, app.models.Registration, app.models.Hackathon, discord.Embed, discord.SyncWebhook.
    Consumers: Registration creation route to notify organizers.
    """
    # Skip if Discord bot not configured (test environments)
    if not settings.discord_bot_token:
        return False

    async with async_session() as db:
        result = await db.execute(
            select(Registration)
            .where(Registration.id == registration_id)
            .options(selectinload(Registration.user))
            .options(selectinload(Registration.hackathon))
        )
        reg = result.scalar_one_or_none()
        if not reg or not reg.hackathon:
            return False

        hackathon = reg.hackathon
        channel_id = hackathon.discord_application_channel_id

    embed = discord.Embed(
        title="New Application",
        description=f"**{reg.team_name or reg.user.name}** applied to **{hackathon.name}**",
        color=discord.Color.blue(),
        timestamp=reg.registered_at,
    )
    embed.add_field(name="Status", value="`pending`", inline=False)

    # Personal info
    embed.add_field(name="Name", value=reg.user.name, inline=True)
    embed.add_field(name="Email", value=reg.user.email, inline=True)
    embed.add_field(name="Phone", value=reg.phone or "—", inline=True)
    embed.add_field(name="Age", value=str(reg.age) if reg.age else "—", inline=True)
    embed.add_field(name="Pronouns", value=reg.pronouns or "—", inline=True)

    # Academic
    embed.add_field(name="School", value=reg.school or "—", inline=True)
    embed.add_field(name="Major", value=reg.major or "—", inline=True)

    # Skills & Links
    embed.add_field(name="Experience", value=reg.experience_level or "—", inline=True)
    skills = ", ".join(reg.skills) if reg.skills else "—"
    embed.add_field(name="Skills", value=skills[:200] + ("..." if len(skills) > 200 else ""), inline=True)
    embed.add_field(name="GitHub", value=reg.github_url or "—", inline=True)
    embed.add_field(name="LinkedIn", value=reg.linkedin_url or "—", inline=True)
    embed.add_field(name="Resume", value=reg.resume_url or "—", inline=True)

    # Logistics
    embed.add_field(name="T-Shirt", value=reg.t_shirt_size or "—", inline=True)
    embed.add_field(name="Dietary", value=reg.dietary_restrictions or "—", inline=True)
    embed.add_field(
        name="Emergency Contact",
        value=f"{reg.emergency_contact_name or '—'}\n{reg.emergency_contact_phone or '—'}",
        inline=True,
    )

    # Team (if applicable)
    if reg.team_name:
        embed.add_field(name="Team", value=reg.team_name, inline=True)
    if reg.team_members:
        embed.add_field(name="Members", value=", ".join(reg.team_members), inline=True)

    # Short answers
    what = reg.what_build or "—"
    embed.add_field(name="What They'll Build", value=what[:200] + ("..." if len(what) > 200 else ""), inline=False)
    why = reg.why_participate or "—"
    embed.add_field(name="Why Participate", value=why[:200] + ("..." if len(why) > 200 else ""), inline=False)

    embed.add_field(
        name="Actions",
        value="Click **Review** for full details, then **Accept** or **Reject**",
        inline=False,
    )
    embed.set_footer(text=f"ID: {reg.id}")

    view = ApplicationView(str(reg.id), str(hackathon.id))

    # Try bot first (supports interactive buttons)
    if channel_id:
        try:
            channel = await bot.fetch_channel(int(channel_id))
            msg = await channel.send(embed=embed, view=view)
            bot.add_view(view, message_id=msg.id)
            print(f"[BOT] Posted to channel {channel_id}", flush=True)
            return True
        except Exception as e:
            print(f"[BOT] Channel send failed, falling back to webhook: {e}", flush=True)

    # Fallback to webhook (text-only, no interactive buttons)
    webhook_url = hackathon.discord_webhook_url
    if webhook_url:
        try:
            webhook = discord.SyncWebhook.from_url(webhook_url)
            webhook.send(embed=embed)
            logger.info(f"Posted application {registration_id} via webhook")
            return True
        except Exception as e:
            logger.error(f"Webhook also failed: {e}")

    return False


def get_bot_invite_url() -> str | None:
    """Generate the Discord bot OAuth invite URL with required permissions.

    Behavior:
    1. Read the Discord client ID from settings.
    2. Return None if the client ID is not configured.
    3. Build a Permissions object with send_messages, embed_links, and read_messages enabled.
    4. Assemble the standard Discord OAuth2 bot invite URL with the permission value and scope.
    5. Return the invite URL string.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: discord.Permissions, app.config.settings.discord_client_id.
    Consumers: GET /api/discord/invite-url and app.discord_bot.start_bot console output.
    """
    client_id = settings.discord_client_id
    if not client_id:
        return None
    permissions = discord.Permissions()
    permissions.send_messages = True
    permissions.embed_links = True
    permissions.read_messages = True
    return (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&permissions={permissions.value}"
        "&scope=bot%20applications.commands"
    )


async def start_bot():
    """Start the Discord bot if a token is configured and wait for readiness.

    Behavior:
    1. Read the Discord bot token from settings.
    2. If no token is configured, print a skip message and return None.
    3. Print the invite URL if the client ID is configured.
    4. Spawn an asyncio task to start the bot connection.
    5. Yield to the event loop so the task can schedule.
    6. Wait up to 15 seconds for the bot to become ready.
    7. Log timeout or runtime errors without crashing the app.
    8. Return the bot instance.

    Raises: None (exceptions are caught and logged).
    Side Effects: Spawns a background asyncio task; connects to the Discord gateway.
    Dependencies: discord.Client.start, app.config.settings.discord_bot_token, app.discord_bot.get_bot_invite_url.
    Consumers: app.main.lifespan startup sequence.
    """
    token = settings.discord_bot_token
    if not token:
        print("[BOT] No token configured, skipping")
        return None

    invite_url = get_bot_invite_url()
    if invite_url:
        print(f"[BOT] Invite URL: {invite_url}")

    asyncio.create_task(bot.start(token))

    # Let the event loop schedule the task before waiting
    await asyncio.sleep(0)

    # Wait up to 15 seconds for the bot to connect
    try:
        await asyncio.wait_for(bot.wait_until_ready(), timeout=15.0)
        print(f"[BOT] Ready! Logged in as {bot.user}, guilds: {len(bot.guilds)}")
    except TimeoutError:
        print("[BOT] Timed out waiting to connect")
        logger.error("Discord bot did not become ready within 15s")
    except RuntimeError as e:
        print(f"[BOT] Runtime error during startup: {e}")
        logger.error(f"Bot startup error: {e}")

    return bot
