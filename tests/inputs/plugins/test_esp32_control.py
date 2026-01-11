import pytest
import asyncio
import threading
from unittest.mock import MagicMock, patch
from queue import Queue
from dataclasses import dataclass
from typing import Optional

from inputs.base import Message
from inputs.plugins.esp32_control import Esp32Control, Esp32ControlConfig


class TestEsp32ControlConfig:
    def test_default_config(self):
        config = Esp32ControlConfig()
        assert config.api_key is None

    def test_config_with_api_key(self):
        config = Esp32ControlConfig(api_key="test_key")
        assert config.api_key == "test_key"


class TestEsp32Control:
    @pytest.fixture
    def mock_teleops_provider(self):
        with patch("inputs.plugins.esp32_control.TeleopsConversationProvider") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_io_provider(self):
        with patch("inputs.plugins.esp32_control.IOProvider") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def esp32_control(self, mock_teleops_provider, mock_io_provider):
        config = Esp32ControlConfig(api_key="test_key")
        control = Esp32Control(config)
        yield control
        control.stop()
        control.input_thread.join(timeout=2)

    def test_initialization(self, esp32_control, mock_teleops_provider):
        assert esp32_control.config.api_key == "test_key"
        assert isinstance(esp32_control.messages, list)
        assert esp32_control.descriptor_for_LLM == "User"
        assert esp32_control.running is True

    def test_message_buffer_initialized(self, esp32_control):
        assert isinstance(esp32_control.message_buffer, Queue)

    def test_poll_returns_message_from_buffer(self, esp32_control):
        esp32_control.message_buffer.put("forward")
        result = asyncio.run(esp32_control._poll())
        assert result == "forward"

    def test_poll_returns_none_when_empty(self, esp32_control):
        esp32_control.stop()
        result = asyncio.run(esp32_control._poll())
        assert result is None

    def test_raw_to_text_with_message(self):
        config = Esp32ControlConfig()
        control = Esp32Control(config)
        try:
            result = asyncio.run(control._raw_to_text("test command"))
            assert result is not None
            assert result.message == "test command"
            assert isinstance(result.timestamp, float)
        finally:
            control.stop()

    def test_formatted_latest_buffer_empty(self, esp32_control):
        result = esp32_control.formatted_latest_buffer()
        assert result is None

    def test_stop_sets_running_false(self, esp32_control):
        esp32_control.stop()
        assert esp32_control.running is False


class TestEsp32ControlIntegration:
    @pytest.fixture
    def mock_dependencies(self):
        with (
            patch(
                "inputs.plugins.esp32_control.TeleopsConversationProvider"
            ) as mock_teleops,
            patch("inputs.plugins.esp32_control.IOProvider") as mock_io,
        ):
            teleops_instance = MagicMock()
            io_instance = MagicMock()
            mock_teleops.return_value = teleops_instance
            mock_io.return_value = io_instance
            yield teleops_instance, io_instance

    def test_message_buffer_handling(self, mock_dependencies):
        config = Esp32ControlConfig(api_key="test")
        control = Esp32Control(config)
        try:
            control.message_buffer.put("forward")
            control.message_buffer.put("back")

            import asyncio

            first_msg = asyncio.run(control._poll())
            second_msg = asyncio.run(control._poll())

            assert first_msg == "forward"
            assert second_msg == "back"
        finally:
            control.stop()

    def test_stores_user_message_in_provider(self, mock_dependencies):
        teleops_instance, io_instance = mock_dependencies
        config = Esp32ControlConfig(api_key="test")
        control = Esp32Control(config)
        try:
            control.messages.append("move forward")
            control.formatted_latest_buffer()

            teleops_instance.store_user_message.assert_called_once_with("move forward")
            io_instance.add_input.assert_called_once()
        finally:
            control.stop()
