import logging
import serial
from pydantic import Field

from actions.base import ActionConfig, ActionConnector
from actions.motor.interface import MotorInput, MotorAction

class SerialMotorConfig(ActionConfig):
    port: str = Field(default="COM3", description="ESP32 Port")
    baudrate: int = Field(default=115200, description="Baudrate")

class SerialMotor(ActionConnector[SerialMotorConfig, MotorInput]):
    def __init__(self, config: SerialMotorConfig):
        super().__init__(config)
        self.ser = None
        logging.info(f"SerialMotor initialized in lazy mode. Target: {self.config.port}")

    def _ensure_connection(self) -> bool:
        """Internal Method: Ensure the serial port is open; if not open, attempt to open it."""
        if self.ser is None or not self.ser.is_open:
            try:
                self.ser = serial.Serial(self.config.port, self.config.baudrate, timeout=1)
                logging.info(f"Successfully opened Serial Port: {self.config.port}")
                return True
            except Exception as e:
                logging.error(f"Failed to open Serial Port {self.config.port}: {e}")
                self.ser = None
                return False
        return True

    async def connect(self, output_interface: MotorInput) -> None:
        if not self._ensure_connection():
            return
        
        action_str = str(output_interface.action)
        logging.info(f"Received Motor Command: {action_str}")
        
        signal_map = {
            MotorAction.FORWARD: "F",
            MotorAction.BACK: "B",
            MotorAction.STOP: "S",
            MotorAction.LEFT: "L",
            MotorAction.RIGHT: "R"
        }
        
        signal = signal_map.get(action_str)
        
        if signal:
            try:
                self.ser.write(f"{signal}\n".encode('utf-8'))
                logging.info(f"Executed: {action_str} (Signal: {signal})")
            except Exception as e:
                logging.error(f"Serial Send Error: {e}")
                if self.ser:
                    try:
                        self.ser.close()
                    except:
                        pass
                self.ser = None
        else:
            logging.error(f"Unknown action: {action_str}")
    
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
