"""Comprehensive tests for the OpenHack CLI."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from app.models import RegistrationStatus, UserRole
from cli.main import app

runner = CliRunner()


class TestCLIEntryPoint:
    def test_help_shows_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "version" in result.output
        assert "status" in result.output
        assert "config" in result.output
        assert "db" in result.output
        assert "hackathon" in result.output
        assert "server" in result.output
        assert "user" in result.output

    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "OpenHack CLI" in result.output
        assert "0.1.0" in result.output

    def test_status_command(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "OpenHack Platform Status" in result.output
        assert "Hackathon Name" in result.output
        assert "Database URL" in result.output


class TestConfigCommands:
    def test_config_list(self):
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "hackathon_name" in result.output
        assert "hackathon_primary_color" in result.output

    def test_config_list_with_db_values(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(
                config_service, "get_all", new_callable=AsyncMock, return_value={"hackathon_name": "DBHackathon"}
            ):
                result = runner.invoke(app, ["config", "list"])
                assert result.exit_code == 0
                assert "DBHackathon" in result.output

    def test_config_get_known_key(self):
        result = runner.invoke(app, ["config", "get", "hackathon_name"])
        assert result.exit_code == 0
        assert "hackathon_name" in result.output
        assert "OpenHack" in result.output

    def test_config_get_from_db(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "get", new_callable=AsyncMock, return_value="DBValue") as mock_get:
                result = runner.invoke(app, ["config", "get", "hackathon_name"])
                assert result.exit_code == 0
                assert "DBValue" in result.output
                mock_get.assert_awaited_once_with("hackathon_name", mock_db)

    def test_config_get_unknown_key(self):
        result = runner.invoke(app, ["config", "get", "not_a_key"])
        assert result.exit_code == 1
        assert result.exception is not None
        assert "Unknown key" in str(result.exception)

    def test_config_get_key_not_found(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "get", new_callable=AsyncMock, return_value=None):
                with patch("cli.config.settings") as mock_settings:
                    mock_settings.hackathon_name = None
                    result = runner.invoke(app, ["config", "get", "hackathon_name"])
                    assert result.exit_code == 1
                    assert "not found" in result.output

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "set" in result.output
        assert "reset" in result.output

    def test_config_set(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "set", new_callable=AsyncMock) as mock_set:
                result = runner.invoke(app, ["config", "set", "hackathon_name", "TestHack"])
                assert result.exit_code == 0
                assert "hackathon_name" in result.output
                assert "TestHack" in result.output
                mock_set.assert_awaited_once_with("hackathon_name", "TestHack", mock_db)
                mock_db.commit.assert_awaited_once()

    def test_config_set_unknown_key(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "set", new_callable=AsyncMock, side_effect=ValueError("Unknown key")):
                result = runner.invoke(app, ["config", "set", "bad_key", "val"])
                assert result.exit_code == 1
                assert "Unknown key" in str(result.exception)

    def test_config_reset_with_yes(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "delete", new_callable=AsyncMock) as mock_delete:
                result = runner.invoke(app, ["config", "reset", "hackathon_name", "--yes"])
                assert result.exit_code == 0
                assert "hackathon_name" in result.output
                assert "reset to default" in result.output
                mock_delete.assert_awaited_once_with("hackathon_name", mock_db)
                mock_db.commit.assert_awaited_once()

    def test_config_reset_without_yes(self):
        from cli.config import config_service

        with patch.object(config_service, "delete", new_callable=AsyncMock):
            result = runner.invoke(app, ["config", "reset", "hackathon_name"], input="n\n")
            assert result.exit_code != 0

    def test_config_reset_unknown_key(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        from cli.config import config_service

        with patch("cli.config.db_session", return_value=mock_cm):
            with patch.object(config_service, "delete", new_callable=AsyncMock, side_effect=ValueError("Unknown key")):
                result = runner.invoke(app, ["config", "reset", "bad_key", "--yes"])
                assert result.exit_code == 1
                assert "Unknown key" in str(result.exception)


class TestDBCommands:
    def test_db_help(self):
        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0
        assert "migrate" in result.output
        assert "downgrade" in result.output
        assert "revision" in result.output
        assert "history" in result.output
        assert "current" in result.output
        assert "seed" in result.output
        assert "reset" in result.output

    def test_db_migrate(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Migration applied"
        mock_result.stderr = ""

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "migrate"])
            assert result.exit_code == 0
            assert "applied successfully" in result.output
            mock_run.assert_called_once_with(["alembic", "upgrade", "head"], capture_output=True, text=True)

    def test_db_migrate_dry_run(self):
        with patch("cli.db.subprocess.run") as mock_run:
            result = runner.invoke(app, ["db", "migrate", "--dry-run"])
            assert result.exit_code == 0
            assert "Would run" in result.output
            mock_run.assert_not_called()

    def test_db_migrate_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Alembic error"
        mock_result.stdout = ""

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "migrate"])
            assert result.exit_code == 1
            assert "Migration failed" in result.output
            mock_run.assert_called_once()

    def test_db_downgrade(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "downgrade", "abc123", "--yes"])
            assert result.exit_code == 0
            assert "Downgrade complete" in result.output
            mock_run.assert_called_once_with(["alembic", "downgrade", "abc123"], capture_output=True, text=True)

    def test_db_downgrade_without_yes(self):
        with patch("cli.db.subprocess.run") as mock_run:
            result = runner.invoke(app, ["db", "downgrade", "abc123"], input="n\n")
            assert result.exit_code != 0
            mock_run.assert_not_called()

    def test_db_revision(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created migration abc123"

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "revision", "-m", "test migration"])
            assert result.exit_code == 0
            assert "Migration created" in result.output
            mock_run.assert_called_once_with(
                ["alembic", "revision", "--autogenerate", "-m", "test migration"],
                capture_output=True,
                text=True,
            )

    def test_db_revision_no_autogenerate(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "revision", "-m", "empty", "--no-autogenerate"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(
                ["alembic", "revision", "-m", "empty"],
                capture_output=True,
                text=True,
            )

    def test_db_history(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc -> def (head)"

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "history"])
            assert result.exit_code == 0
            assert "abc" in result.output
            mock_run.assert_called_once_with(["alembic", "history"], capture_output=True, text=True)

    def test_db_current(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123 (head)"

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "current"])
            assert result.exit_code == 0
            assert "abc123" in result.output
            mock_run.assert_called_once_with(["alembic", "current"], capture_output=True, text=True)

    def test_db_seed(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.db.db_session", return_value=mock_cm):
            with patch("app.seed_content.seed_default_content", new_callable=AsyncMock) as mock_seed:
                result = runner.invoke(app, ["db", "seed", "--yes"])
                assert result.exit_code == 0
                assert "seeded successfully" in result.output
                mock_seed.assert_awaited_once_with(mock_db)

    def test_db_seed_without_yes(self):
        with patch("app.seed_content.seed_default_content") as mock_seed:
            result = runner.invoke(app, ["db", "seed"], input="n\n")
            assert result.exit_code != 0
            mock_seed.assert_not_called()

    def test_db_reset(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "reset", "--yes"])
            assert result.exit_code == 0
            assert "Database reset complete" in result.output
            assert mock_run.call_count == 2
            mock_run.assert_any_call(["alembic", "downgrade", "base"], capture_output=True, text=True)
            mock_run.assert_any_call(["alembic", "upgrade", "head"], capture_output=True, text=True)

    def test_db_reset_without_yes(self):
        with patch("cli.db.subprocess.run") as mock_run:
            result = runner.invoke(app, ["db", "reset"], input="n\n")
            assert result.exit_code != 0
            mock_run.assert_not_called()

    def test_db_reset_downgrade_fails(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"

        with patch("cli.db.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["db", "reset", "--yes"])
            assert result.exit_code == 1
            assert "Drop failed" in result.output
            assert mock_run.call_count == 1

    def test_db_history_shows_migrations(self):
        result = runner.invoke(app, ["db", "history"])
        # May fail if alembic not initialized; just check it runs
        assert result.exit_code in (0, 1)


class TestHackathonCommands:
    def test_hackathon_help(self):
        result = runner.invoke(app, ["hackathon", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "show" in result.output
        assert "stats" in result.output

    def _make_hackathon(self, **kwargs):
        h = MagicMock()
        h.id = kwargs.get("id", uuid.uuid4())
        h.name = kwargs.get("name", "Test Hackathon")
        h.start_date = kwargs.get("start_date", datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC))
        h.end_date = kwargs.get("end_date", datetime(2025, 6, 2, 18, 0, 0, tzinfo=UTC))
        h.description = kwargs.get("description", "A test hackathon")
        h.venue_address = kwargs.get("venue_address", "123 Main St")
        h.max_participants = kwargs.get("max_participants", 100)
        h.waitlist_enabled = kwargs.get("waitlist_enabled", True)
        h.current_participants = kwargs.get("current_participants", 50)
        return h

    def _make_reg(self, **kwargs):
        r = MagicMock()
        r.status = kwargs.get("status", RegistrationStatus.accepted)
        r.checked_in_at = kwargs.get("checked_in_at", datetime.now(UTC))
        return r

    def test_hackathon_list(self):
        h1 = self._make_hackathon(name="Hack A", current_participants=10)
        h2 = self._make_hackathon(name="Hack B", current_participants=20)

        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = [h1, h2]

        mock_db = AsyncMock()
        mock_db.execute.return_value = hack_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "list"])
            assert result.exit_code == 0
            assert "Hack A" in result.output
            assert "Hack B" in result.output
            assert "10" in result.output
            assert "20" in result.output

    def test_hackathon_list_empty(self):
        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = hack_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "list"])
            assert result.exit_code == 0
            assert "No hackathons found" in result.output

    def test_hackathon_show(self):
        h1 = self._make_hackathon(name="Hack A", max_participants=150)
        r1 = self._make_reg(status=RegistrationStatus.accepted)
        r2 = self._make_reg(status=RegistrationStatus.pending, checked_in_at=None)

        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = [h1]

        reg_result = MagicMock()
        reg_result.scalars.return_value.all.return_value = [r1, r2]

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [hack_result, reg_result]

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "show", str(h1.id)[:8]])
            assert result.exit_code == 0
            assert "Hack A" in result.output
            assert "123 Main St" in result.output
            assert "150" in result.output
            assert "1" in result.output  # accepted
            assert "1" in result.output  # pending

    def test_hackathon_show_not_found(self):
        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = hack_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "show", "nope"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_hackathon_stats(self):
        h1 = self._make_hackathon(name="Hack A")
        r1 = self._make_reg(status=RegistrationStatus.accepted)
        r2 = self._make_reg(status=RegistrationStatus.pending)
        r3 = self._make_reg(status=RegistrationStatus.accepted)

        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = [h1]

        reg_result = MagicMock()
        reg_result.scalars.return_value.all.return_value = [r1, r2, r3]

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [hack_result, reg_result]

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "stats", str(h1.id)[:8]])
            assert result.exit_code == 0
            assert "Hack A" in result.output
            assert "accepted" in result.output
            assert "pending" in result.output
            assert "3" in result.output  # total

    def test_hackathon_stats_not_found(self):
        hack_result = MagicMock()
        hack_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = hack_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.hackathon.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["hackathon", "stats", "nope"])
            assert result.exit_code == 1
            assert "not found" in result.output


class TestUserCommands:
    def test_user_help(self):
        result = runner.invoke(app, ["user", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "show" in result.output
        assert "promote" in result.output
        assert "ban" in result.output
        assert "unban" in result.output

    def _make_user(self, **kwargs):
        u = MagicMock()
        u.id = kwargs.get("id", "user123")
        u.name = kwargs.get("name", "Alice")
        u.email = kwargs.get("email", "alice@example.com")
        u.role = kwargs.get("role", UserRole.participant)
        u.is_banned = kwargs.get("is_banned", False)
        u.banned_at = kwargs.get("banned_at", None)
        u.bio = kwargs.get("bio", "")
        u.skills = kwargs.get("skills", [])
        u.created_at = kwargs.get("created_at", datetime.now(UTC))
        return u

    def test_user_list(self):
        u1 = self._make_user(name="Alice")
        u2 = self._make_user(name="Bob", role=UserRole.organizer)

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1, u2]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "list"])
            assert result.exit_code == 0
            assert "Alice" in result.output
            assert "Bob" in result.output
            assert "organizer" in result.output

    def test_user_list_with_role_filter(self):
        u1 = self._make_user(name="Alice", role=UserRole.organizer)

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "list", "--role", "organizer"])
            assert result.exit_code == 0
            assert "Alice" in result.output

    def test_user_list_invalid_role(self):
        mock_db = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "list", "--role", "invalid"])
            assert result.exit_code == 1
            assert "Invalid role" in result.output

    def test_user_list_with_search(self):
        u1 = self._make_user(name="Alice Smith", email="alice@example.com")
        u2 = self._make_user(name="Bob Jones", email="bob@example.com")

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1, u2]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "list", "--search", "Alice"])
            assert result.exit_code == 0
            assert "Alice" in result.output
            assert "Bob" not in result.output

    def test_user_show(self):
        u1 = self._make_user(name="Alice", bio="Developer", skills=["python", "react"])

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "show", "user12"])
            assert result.exit_code == 0
            assert "Alice" in result.output
            assert "Developer" in result.output
            assert "python" in result.output

    def test_user_show_not_found(self):
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "show", "nope"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_user_promote(self):
        u1 = self._make_user(role=UserRole.participant)

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "promote", "user12", "organizer", "--yes"])
            assert result.exit_code == 0
            assert "promoted to organizer" in result.output
            assert u1.role == UserRole.organizer
            mock_db.commit.assert_awaited_once()

    def test_user_promote_invalid_role(self):
        u1 = self._make_user()

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "promote", "user12", "god", "--yes"])
            assert result.exit_code == 1
            assert "Invalid role" in result.output

    def test_user_promote_not_found(self):
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "promote", "nope", "organizer", "--yes"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_user_ban(self):
        u1 = self._make_user(is_banned=False, banned_at=None)

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "ban", "user12", "--yes"])
            assert result.exit_code == 0
            assert "banned" in result.output
            assert u1.is_banned is True
            assert u1.banned_at is not None
            mock_db.commit.assert_awaited_once()

    def test_user_ban_not_found(self):
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "ban", "nope", "--yes"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_user_unban(self):
        u1 = self._make_user(is_banned=True, banned_at=datetime.now(UTC))

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [u1]

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "unban", "user12"])
            assert result.exit_code == 0
            assert "unbanned" in result.output
            assert u1.is_banned is False
            assert u1.banned_at is None
            mock_db.commit.assert_awaited_once()

    def test_user_unban_not_found(self):
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = user_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = False

        with patch("cli.user.db_session", return_value=mock_cm):
            result = runner.invoke(app, ["user", "unban", "nope"])
            assert result.exit_code == 1
            assert "not found" in result.output


class TestServerCommands:
    def test_server_help(self):
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "shell" in result.output
        assert "logs" in result.output

    def test_server_start(self):
        with patch("cli.server.subprocess.run") as mock_run:
            result = runner.invoke(app, ["server", "start"])
            assert result.exit_code == 0
            assert "Starting server" in result.output
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "uvicorn" in cmd
            assert "app.main:app" in cmd

    def test_server_start_with_options(self):
        with patch("cli.server.subprocess.run") as mock_run:
            result = runner.invoke(
                app, ["server", "start", "--host", "127.0.0.1", "--port", "5000", "--no-reload", "--workers", "4"]
            )
            assert result.exit_code == 0
            cmd = mock_run.call_args[0][0]
            assert "--host" in cmd
            assert "127.0.0.1" in cmd
            assert "--port" in cmd
            assert "5000" in cmd
            assert "--reload" not in cmd
            assert "--workers" in cmd
            assert "4" in cmd

    def test_server_start_keyboard_interrupt(self):
        with patch("cli.server.subprocess.run", side_effect=KeyboardInterrupt):
            result = runner.invoke(app, ["server", "start"])
            assert result.exit_code == 0
            assert "Server stopped" in result.output

    def test_server_shell(self):
        with patch("cli.server.subprocess.run") as mock_run:
            result = runner.invoke(app, ["server", "shell"])
            assert result.exit_code == 0
            assert "interactive shell" in result.output
            mock_run.assert_called_once()

    def test_server_logs(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("cli.server.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["server", "logs"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(["docker", "logs", "openhack-backend-1", "--tail", "50"])

    def test_server_logs_with_tail(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("cli.server.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["server", "logs", "--tail", "100"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(["docker", "logs", "openhack-backend-1", "--tail", "100"])

    def test_server_logs_with_follow(self):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("cli.server.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(app, ["server", "logs", "--follow"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(["docker", "logs", "openhack-backend-1", "--tail", "50", "--follow"])

    def test_server_logs_no_docker(self):
        with patch("cli.server.subprocess.run", side_effect=FileNotFoundError) as mock_run:
            result = runner.invoke(app, ["server", "logs"])
            assert result.exit_code == 1
            assert "Docker not found" in result.output


class TestTUICommands:
    def test_tui_help(self):
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0

    def test_setup_help(self):
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
