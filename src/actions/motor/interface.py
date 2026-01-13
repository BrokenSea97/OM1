from dataclasses import dataclass
from enum import Enum

from actions.base import Interface

class MotorAction(str, Enum):
    FORWARD = "forward"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"

@dataclass
class MotorInput:
    """
    Input interface for the Motor action.
    """
    action: MotorAction

@dataclass
class MotorOutput:
    status: str

class Motor(Interface[MotorInput, MotorOutput]):
    """
    This action allows you to control the movement of the robot.
    """
    input: MotorInput
    output: MotorOutput
