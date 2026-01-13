import logging
import os
import platform
import subprocess
from pathlib import Path

from .env import Environment


log = logging.getLogger(__name__)


class VideoCapture:
    """Manages video capture of xemu execution using ffmpeg."""

    def __init__(self, test_env: Environment, video_capture_path: Path):
        self.test_env = test_env
        self.video_capture_path = video_capture_path
        self.ffmpeg = None
        self.record_x: int = 0
        self.record_y: int = 0
        self.record_w: int = 0
        self.record_h: int = 0

    def set_capture_region(self, x: int, y: int, w: int, h: int):
        """Set the screen region to capture (Windows only)."""
        self.record_x = x
        self.record_y = y
        self.record_w = w
        self.record_h = h

    def start(self, app_window=None):
        """Start video capture."""
        if not self.test_env.video_capture_enabled:
            return

        ffmpeg_path = self.test_env.ffmpeg_path
        if platform.system() == "Windows":
            if app_window is None:
                log.info("Video capture disabled because app window could not be found")
                return
            if not ffmpeg_path:
                ffmpeg_path = "ffmpeg.exe"
            c = [
                ffmpeg_path,
                "-loglevel",
                "error",
                "-framerate",
                "60",
                "-video_size",
                f"{self.record_w}x{self.record_h}",
                "-f",
                "gdigrab",
                "-offset_x",
                f"{self.record_x}",
                "-offset_y",
                f"{self.record_y}",
                "-i",
                "desktop",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(self.video_capture_path),
                "-y",
            ]
        else:
            if not ffmpeg_path:
                ffmpeg_path = "ffmpeg"
            c = [
                ffmpeg_path,
                "-loglevel",
                "error",
                "-video_size",
                "640x480",
                "-f",
                "x11grab",
                "-i",
                os.environ.get("DISPLAY", ":0"),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-profile:v",
                "baseline",
                "-pix_fmt",
                "yuv420p",
                str(self.video_capture_path),
                "-y",
            ]

        log.info(
            "Launching FFMPEG (capturing to %s) with %s",
            self.video_capture_path,
            repr(c),
        )
        self.ffmpeg = subprocess.Popen(c, stdin=subprocess.PIPE)

    def stop(self):
        """Stop video capture."""
        if not self.test_env.video_capture_enabled or self.ffmpeg is None:
            return
        log.info("Shutting down FFMPEG")
        self.ffmpeg.communicate(b"q\n", timeout=5)
