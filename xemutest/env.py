from dataclasses import dataclass
from pathlib import Path


@dataclass
class Environment:
    """Encapsulates environment information needed to run the tests."""

    private_path: Path
    xemu_path: Path
    ffmpeg_path: Path | None = None
    perceptualdiff_path: Path | None = None

    @property
    def video_capture_enabled(self) -> bool:
        return self.ffmpeg_path is not None

    @property
    def perceptualdiff_enabled(self) -> bool:
        return self.perceptualdiff_path is not None
