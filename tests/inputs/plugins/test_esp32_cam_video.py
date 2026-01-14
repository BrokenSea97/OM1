import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from inputs.plugins.esp32_cam_video import Esp32CamVideo, Esp32CamVideoConfig


class TestEsp32CamVideoConfig:
    """Test Esp32CamVideoConfig configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Esp32CamVideoConfig()
        assert hasattr(config, "stream_url")
        assert hasattr(config, "stream_type")
        assert hasattr(config, "fps")
        assert hasattr(config, "analyze_with_vlm")


class TestEsp32CamVideo:
    """Test Esp32CamVideo video stream processor."""

    @pytest.fixture
    def mock_cv2(self):
        """Mock cv2 module."""
        with patch("inputs.plugins.esp32_cam_video.cv2") as mock_cv2:
            yield mock_cv2

    @pytest.fixture
    def mock_video_capture(self, mock_cv2):
        """Mock VideoCapture."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cv2.VideoCapture.return_value = mock_cap
        return mock_cap

    def test_init_default_config(self, mock_video_capture):
        """Test initialization with default config."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        assert video.cap is not None
        assert video.fps == 5
        assert video.stream_type == "http"
        assert video.analyze_with_vlm is False

    def test_init_custom_config(self, mock_video_capture):
        """Test initialization with custom config."""
        config_dict = {
            "stream_url": "http://192.168.1.200:81/stream",
            "stream_type": "http",
            "fps": 10,
            "analyze_with_vlm": True,
        }
        config = Esp32CamVideoConfig(**config_dict)
        video = Esp32CamVideo(config)

        assert video.stream_url == "http://192.168.1.200:81/stream"
        assert video.fps == 10
        assert video.analyze_with_vlm is True

    @pytest.mark.asyncio
    async def test_poll_frame(self, mock_video_capture):
        """Test polling for video frame."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        frame = await video._poll()

        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)

    @pytest.mark.asyncio
    async def test_poll_no_frame(self, mock_video_capture):
        """Test polling when no frame is available."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)
        mock_video_capture.read.return_value = (False, None)

        frame = await video._poll()

        assert frame is None

    @pytest.mark.asyncio
    async def test_raw_to_text(self, mock_video_capture):
        """Test converting frame to text."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        message = await video._raw_to_text(frame)

        assert message is not None
        assert "640x480" in message.message
        assert "video frame" in message.message.lower()

    @pytest.mark.asyncio
    async def test_raw_to_text_with_vlm(self, mock_video_capture):
        """Test converting frame to text with VLM enabled."""
        config_dict = {"analyze_with_vlm": True}
        config = Esp32CamVideoConfig(**config_dict)
        video = Esp32CamVideo(config)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        message = await video._raw_to_text(frame)

        assert message is not None
        assert "Ready for VLM analysis" in message.message

    @pytest.mark.asyncio
    async def test_raw_to_text_none(self, mock_video_capture):
        """Test converting None to text."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        message = await video._raw_to_text(None)

        assert message is None

    @pytest.mark.asyncio
    async def test_formatted_latest_buffer(self, mock_video_capture):
        """Test formatting latest buffer."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        await video.raw_to_text(frame)

        formatted = video.formatted_latest_buffer()

        assert formatted is not None
        assert "ESP32-CAM Video" in formatted
        assert "640x480" in formatted

    def test_formatted_latest_buffer_empty(self, mock_video_capture):
        """Test formatting empty buffer."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        formatted = video.formatted_latest_buffer()

        assert formatted is None

    def test_stop(self, mock_video_capture):
        """Test stopping video stream."""
        config = Esp32CamVideoConfig()
        video = Esp32CamVideo(config)

        video.stop()

        mock_video_capture.release.assert_called_once()
