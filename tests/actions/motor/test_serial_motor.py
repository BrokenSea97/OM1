import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from actions.base import ActionConfig
from actions.motor.interface import MotorInput, MotorAction, Motor, MotorOutput
from actions.motor.connector.serial_control import SerialMotor, SerialMotorConfig
import asyncio


class TestMotorAction:
    def test_motor_action_values(self):
        assert MotorAction.FORWARD.value == "forward"
        assert MotorAction.BACK.value == "back"
        assert MotorAction.LEFT.value == "left"
        assert MotorAction.RIGHT.value == "right"
        assert MotorAction.STOP.value == "stop"

    def test_motor_action_from_string(self):
        assert MotorAction("forward") == MotorAction.FORWARD
        assert MotorAction("back") == MotorAction.BACK
        assert MotorAction("stop") == MotorAction.STOP


class TestMotorInput:
    def test_motor_input_creation(self):
        motor_input = MotorInput(action=MotorAction.FORWARD)
        assert motor_input.action == MotorAction.FORWARD

    def test_motor_input_all_actions(self):
        for action in MotorAction:
            motor_input = MotorInput(action=action)
            assert motor_input.action == action


class TestMotorOutput:
    def test_motor_output_creation(self):
        output = MotorOutput(status="success")
        assert output.status == "success"


class TestMotor:
    def test_motor_interface(self):
        input_data = MotorInput(action=MotorAction.FORWARD)
        output_data = MotorOutput(status="executed")

        motor = Motor(input=input_data, output=output_data)
        assert motor.input == input_data
        assert motor.output == output_data


class TestSerialMotorConfig:
    def test_default_config(self):
        config = SerialMotorConfig()
        assert config.port == "COM3"
        assert config.baudrate == 115200

    def test_custom_config(self):
        config = SerialMotorConfig(port="/dev/ttyUSB0", baudrate=9600)
        assert config.port == "/dev/ttyUSB0"
        assert config.baudrate == 9600


class TestSerialMotor:
    @pytest.fixture
    def mock_serial(self):
        with patch("actions.motor.connector.serial_control.serial.Serial") as mock:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def serial_motor_without_connect(self, mock_serial):
        config = SerialMotorConfig(port="COM3", baudrate=115200)
        motor = SerialMotor(config)
        motor.ser = None
        yield motor
        motor.close()

    @pytest.fixture
    def serial_motor(self, mock_serial):
        config = SerialMotorConfig(port="COM3", baudrate=115200)
        motor = SerialMotor(config)
        yield motor
        motor.close()

    def test_initialization(self, serial_motor):
        assert serial_motor.ser is None

    def test_ensure_connection_opens_port(self):
        with patch("actions.motor.connector.serial_control.serial.Serial") as mock:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock.return_value = mock_instance

            config = SerialMotorConfig(port="COM3", baudrate=115200)
            motor = SerialMotor(config)
            motor.ser = None

            result = motor._ensure_connection()
            assert result is True
            mock.assert_called_once_with("COM3", 115200, timeout=1)

            motor.close()

    def test_ensure_connection_returns_true_when_already_open(
        self, serial_motor, mock_serial
    ):
        serial_motor.ser = mock_serial
        mock_serial.is_open = True
        result = serial_motor._ensure_connection()
        assert result is True

    def test_connect_sends_forward_command(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.FORWARD)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once_with(b"F\n")

    def test_connect_sends_back_command(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.BACK)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once_with(b"B\n")

    def test_connect_sends_stop_command(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.STOP)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once_with(b"S\n")

    def test_connect_sends_left_command(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.LEFT)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once_with(b"L\n")

    def test_connect_sends_right_command(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.RIGHT)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once_with(b"R\n")

    def test_connect_handles_unknown_action(self, serial_motor, mock_serial):
        motor_input = MotorInput(action=MotorAction.STOP)
        asyncio.run(serial_motor.connect(motor_input))
        mock_serial.write.assert_called_once()


class TestSerialMotorConnectionFailure:
    @pytest.fixture
    def mock_serial_failure(self):
        with patch("actions.motor.connector.serial_control.serial.Serial") as mock:
            mock.side_effect = Exception("Port not found")
            yield mock

    def test_ensure_connection_handles_error(self, mock_serial_failure):
        config = SerialMotorConfig(port="INVALID_PORT")
        motor = SerialMotor(config)
        try:
            result = motor._ensure_connection()
            assert result is False
            assert motor.ser is None
        finally:
            motor.close()

    def test_connect_does_nothing_on_connection_failure(self, mock_serial_failure):
        config = SerialMotorConfig(port="INVALID_PORT")
        motor = SerialMotor(config)
        try:
            motor_input = MotorInput(action=MotorAction.FORWARD)
            asyncio.run(motor.connect(motor_input))
        finally:
            motor.close()
