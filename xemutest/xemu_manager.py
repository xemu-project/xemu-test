import logging
import platform
import subprocess
import time
from pathlib import Path

if platform.system() == "Windows":
    import pywinauto.application

from .env import Environment
from .video_capture import VideoCapture


log = logging.getLogger(__name__)


class XemuManager:
    """Manages xemu process lifecycle and configuration."""

    def __init__(
        self,
        test_env: Environment,
        hdd_path: Path,
    ):
        self.test_env = test_env
        self.config_path = Path("xemu.toml")
        self.flash_path = test_env.private_path / "bios.bin"
        self.mcpx_path = test_env.private_path / "mcpx.bin"
        self.hdd_path = hdd_path
        self.iso_path: Path | None = None
        self.timeout = 60
        self.exit_status = None
        self.video_capture: VideoCapture | None = None
        self._init_config()

        assert self.flash_path.is_file()
        assert self.mcpx_path.is_file()

        if platform.system() == "Windows":
            self.app: pywinauto.application.Application | None = None

    def set_video_capture(self, video_capture: VideoCapture):
        """Set the video capture manager."""
        self.video_capture = video_capture

    def _init_config(self):
        """Prepare the xemu configuration file."""
        self.config = f"""\
[general]
show_welcome = false
skip_boot_anim = true

[display.ui]
show_menubar = false

[general.updates]
check = false

[net]
enable = false

[sys]
mem_limit = '64'

[sys.files]
bootrom_path = '{self.mcpx_path}'
flashrom_path = '{self.flash_path}'
hdd_path = '{self.hdd_path}'
"""

    def launch(self, log_file):
        """Launch xemu and wait for it to complete or timeout."""
        self.config_path.write_text(self.config)
        c = [str(self.test_env.xemu_path), "-config_path", str(self.config_path)]
        if self.iso_path:
            c += ["-dvd_path", str(self.iso_path)]
        log.info(
            "Launching xemu with command %s from directory %s", repr(c), Path.cwd()
        )
        start = time.time()
        xemu = subprocess.Popen(c, stdout=log_file, stderr=subprocess.STDOUT)

        if platform.system() == "Windows":
            try:
                self.app = pywinauto.application.Application()
                self.app.connect(process=xemu.pid)
                main_window = self.app.window(title_re=r"^xemu \| v.+")
                if main_window is None:
                    raise Exception("Failed to find main xemu window...")

                target_width = 640
                target_height = 480

                rect = main_window.client_area_rect()
                cw, ch = rect.width(), rect.height()
                rect = main_window.rectangle()
                x, y, w, h = rect.left, rect.top, rect.width(), rect.height()

                main_window.move_window(
                    0, 0, target_width + (w - cw), target_height + (h - ch)
                )
                rect = main_window.client_area_rect()
                x, y, w, h = rect.left, rect.top, rect.width(), rect.height()
                log.info("xemu window is at %d,%d w=%d,h=%d", x, y, w, h)

                if self.video_capture:
                    self.video_capture.set_capture_region(x, y, w, h)
            except:  # noqa:E722
                log.exception("Failed to connect to xemu window")
                self.app = None

        if self.video_capture:
            self.video_capture.start(
                self.app if platform.system() == "Windows" else True
            )

        while True:
            status = xemu.poll()
            if status is not None:
                if status:
                    log.error("xemu exited with code %d", status)
                else:
                    log.info("xemu exited with code 0")
                self.exit_status = status
                break
            now = time.time()
            if (now - start) > self.timeout:
                log.warning("Timeout exceeded. Terminating.")
                xemu.kill()
                xemu.wait()
                break
            time.sleep(1)

        if self.video_capture:
            self.video_capture.stop()
