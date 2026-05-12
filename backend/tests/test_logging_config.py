"""Tests for structured logging configuration."""

from unittest.mock import MagicMock, patch

import pytest

from app.logging_config import (
    add_service_name,
    add_timestamp,
    configure_logging,
    get_logger,
    get_request_context,
    set_request_context,
    timed,
)


class TestAddTimestamp:
    def test_adds_timestamp(self):
        event_dict = {}
        result = add_timestamp(None, "info", event_dict)
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)


class TestAddServiceName:
    def test_adds_service(self):
        event_dict = {}
        result = add_service_name(None, "info", event_dict)
        assert result["service"] == "hackverify"


class TestConfigureLogging:
    def test_json_mode(self):
        with patch("structlog.configure") as mock_configure, patch("logging.basicConfig") as mock_basic:
            configure_logging(log_level="INFO", json_logs=True)
            mock_configure.assert_called_once()
            call = mock_configure.call_args
            processors = call.kwargs["processors"]
            assert any("JSONRenderer" in str(type(p)) or "JSONRenderer" in str(p) for p in processors)
            mock_basic.assert_called_once()

    def test_dev_mode(self):
        with patch("structlog.configure") as mock_configure, patch("logging.basicConfig") as mock_basic:
            configure_logging(log_level="DEBUG", json_logs=False)
            mock_configure.assert_called_once()
            call = mock_configure.call_args
            processors = call.kwargs["processors"]
            assert any("ConsoleRenderer" in str(type(p)) or "ConsoleRenderer" in str(p) for p in processors)


class TestGetLogger:
    def test_returns_structlog_logger(self):
        with patch("structlog.get_logger") as mock_get:
            mock_get.return_value = "logger"
            result = get_logger("test_module")
            assert result == "logger"
            mock_get.assert_called_once_with("test_module")


class TestRequestContext:
    def test_set_and_get(self):
        set_request_context(request_id="req-1", user_id="user-1")
        ctx = get_request_context()
        assert ctx["request_id"] == "req-1"
        assert ctx["user_id"] == "user-1"


class TestTimedDecorator:
    def test_sync_function(self):
        with patch("app.logging_config.get_logger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            @timed("test_op")
            def my_func():
                return 42

            result = my_func()
            assert result == 42
            logger.info.assert_called_once()
            call = logger.info.call_args
            assert call.kwargs["operation"] == "test_op"
            assert "duration_ms" in call.kwargs

    def test_sync_function_error(self):
        with patch("app.logging_config.get_logger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            @timed("fail_op")
            def my_func():
                raise ValueError("boom")

            with pytest.raises(ValueError, match="boom"):
                my_func()

            logger.error.assert_called_once()
            call = logger.error.call_args
            assert call.kwargs["operation"] == "fail_op"
            assert call.kwargs["error"] == "boom"

    @pytest.mark.asyncio
    async def test_async_function(self):
        with patch("app.logging_config.get_logger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            @timed("async_op")
            async def my_async_func():
                return 42

            result = await my_async_func()
            assert result == 42
            logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        with patch("app.logging_config.get_logger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger

            @timed("async_fail")
            async def my_async_func():
                raise RuntimeError("async boom")

            with pytest.raises(RuntimeError, match="async boom"):
                await my_async_func()

            logger.error.assert_called_once()
