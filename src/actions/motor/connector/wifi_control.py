import socket
import logging
from pydantic import Field

from actions.base import ActionConfig, ActionConnector
from actions.motor.interface import MotorInput, MotorAction

class WifiMotorConfig(ActionConfig):
    ip_address: str = Field(description="ESP32 IP Address")
    port: int = Field(default=8888, description="UDP Port")

class WifiMotor(ActionConnector[WifiMotorConfig, MotorInput]):
    def __init__(self, config: WifiMotorConfig):
        super().__init__(config)
        self.sock = None
        logging.info(f"WifiMotor initialized in lazy mode. Target: {self.config.ip_address}:{self.config.port}")

    def _ensure_connection(self) -> bool:
        """Internal method: Ensure the socket is available; if not connected, attempt to connect."""
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.settimeout(1.0)
                logging.info("UDP Socket created successfully.")
                return True
            except Exception as e:
                logging.error(f"Failed to create UDP socket: {e}")
                self.sock = None
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
                target = (self.config.ip_address, self.config.port)
                self.sock.sendto(signal.encode(), target)
                logging.info(f"Sent UDP: {signal}")
            except Exception as e:
                logging.error(f"UDP Send Error: {e}")
                if self.sock:
                    self.sock.close()
                self.sock = None
        else:
            logging.error(f"Unknown action: {action_str}")
    
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
