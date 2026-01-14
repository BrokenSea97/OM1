import asyncio
import logging
import time
from typing import Optional

import cv2
import numpy as np
from pydantic import Field

from inputs.base import Message, SensorConfig
from inputs.base.loop import FuserInput
from providers.io_provider import IOProvider


class Esp32CamVideoConfig(SensorConfig):
    """
    Configuration for ESP32-CAM Video Stream input.

    Parameters
    ----------
    stream_url : str
        URL of video stream from ESP32-CAM.
        For HTTP stream: "http://<ESP32_IP>:81/stream"
        For RTSP stream: "rtsp://<ESP32_IP>:8554/stream"
    stream_type : str
        Type of the video stream ("http" or "rtsp"). Defaults to "http".
    fps : int
        Frames per second for processing. Defaults to 5 (lower fps to reduce CPU load).
    analyze_with_vlm : bool
        Whether to send frames to VLM for analysis. Defaults to False.
    """

    stream_url: str = Field(
        default="http://192.168.1.100:81/stream", description="URL of video stream"
    )
    stream_type: str = Field(default="http", description="Type of video stream")
    fps: int = Field(default=5, description="Frames per second for processing")
    analyze_with_vlm: bool = Field(
        default=False, description="Whether to send frames to VLM for analysis"
    )


class Esp32CamVideo(FuserInput[Esp32CamVideoConfig, Optional[np.ndarray]]):
    """
    ESP32-CAM video stream receiver and processor.

    This class receives video stream from ESP32-CAM and processes it for
    display or analysis. It supports both HTTP and RTSP stream formats.

    The reader maintains a connection to the ESP32-CAM video stream and
    continuously captures frames at the specified fps rate.
    """

    def __init__(self, config: Esp32CamVideoConfig):
        """
        Initialize the ESP32-CAM video stream receiver.

        Sets up the video stream connection, initializes the message buffer,
        and configures the IO provider for tracking video data.

        Parameters
        ----------
        config : Esp32CamVideoConfig
            Configuration object containing video stream settings.

        Notes
        -----
        The video stream connection is attempted during initialization. If the
        connection fails (e.g., wrong URL, network issue), an error is logged
        but the initialization continues.

        ESP32-CAM typically provides video stream at:
        - HTTP: http://<IP>:81/stream (MJPG stream)
        - RTSP: rtsp://<IP>:8554/stream (requires additional setup)
        """
        super().__init__(config)

        self.stream_url = config.stream_url
        self.stream_type = config.stream_type
        self.fps = config.fps
        self.analyze_with_vlm = config.analyze_with_vlm

        self.cap = None

        try:
            self.cap = cv2.VideoCapture(self.stream_url)
            if self.cap.isOpened():
                logging.info(f"Connected to ESP32-CAM stream: {self.stream_url}")
            else:
                logging.error(f"Failed to open video stream: {self.stream_url}")
        except Exception as e:
            logging.error(f"Error connecting to video stream: {e}")

        self.io_provider = IOProvider()
        self.messages: list[Message] = []
        self.descriptor_for_LLM = "ESP32-CAM Video"

    async def _poll(self) -> Optional[np.ndarray]:
        """
        Poll for new video frame from ESP32-CAM stream.

        Returns
        -------
        Optional[np.ndarray]
            The latest video frame as a numpy array, or None if no frame
        """
        await asyncio.sleep(1.0 / self.fps)

        if self.cap is None or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            logging.warning("Failed to read frame from video stream")
            return None

    async def _raw_to_text(self, raw_input: Optional[np.ndarray]) -> Optional[Message]:
        """
        Process video frame to generate a text description.

        Analyzes the video frame to extract relevant information for
        the LLM context. Currently provides basic frame information.

        Parameters
        ----------
        raw_input : Optional[np.ndarray]
            Video frame as a numpy array

        Returns
        -------
        Optional[Message]
            A timestamped message containing the processed frame description
        """
        if raw_input is None:
            return None

        height, width = raw_input.shape[:2]
        timestamp = time.strftime("%H:%M:%S")

        if self.analyze_with_vlm:
            message = (
                f"Received video frame at {timestamp} "
                f"({width}x{height} pixels). Ready for VLM analysis."
            )
        else:
            message = (
                f"Received video frame at {timestamp} "
                f"({width}x{height} pixels). Video stream active."
            )

        return Message(timestamp=time.time(), message=message)

    async def raw_to_text(self, raw_input: Optional[np.ndarray]):
        """
        Update message buffer with processed frame.

        Parameters
        ----------
        raw_input : Optional[np.ndarray]
            Raw video frame to be processed, or None if no frame is available
        """
        pending_message = await self._raw_to_text(raw_input)

        if pending_message is not None:
            self.messages.append(pending_message)

    def formatted_latest_buffer(self) -> Optional[str]:
        """
        Format and clear the latest buffer contents.

        Formats the most recent message with timestamp and descriptor,
        adds it to the IO provider, then clears the buffer.

        Returns
        -------
        Optional[str]
            Formatted string of buffer contents or None if buffer is empty
        """
        if len(self.messages) == 0:
            return None

        latest_message = self.messages[-1]

        result = f"""
INPUT: {self.descriptor_for_LLM}
// START
{latest_message.message}
// END
"""

        self.io_provider.add_input(
            self.__class__.__name__, latest_message.message, latest_message.timestamp
        )
        self.messages = []

        return result

    def stop(self):
        """
        Stop the video stream and release resources.

        Closes the video capture and releases the camera resources.
        """
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            logging.info("ESP32-CAM video stream stopped")
