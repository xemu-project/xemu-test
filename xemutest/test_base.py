#!/usr/bin/env python3

import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from pyfatx import Fatx


if platform.system() == "Windows":
    import pywinauto.application


log = logging.getLogger(__file__)


class TestEnvironment:
    """Encapsulates environment information needed to run the tests."""

    def __init__(
        self,
        private_path: str | Path,
        xemu_path: str | Path,
        ffmpeg_path: Path | None,
        perceptualdiff_path: Path | None,
    ):
        self.private_path = Path(private_path)
        self.xemu_path = Path(xemu_path)
        self.ffmpeg_path = ffmpeg_path
        self.perceptualdiff_path = perceptualdiff_path

    @property
    def video_capture_enabled(self) -> bool:
        return self.ffmpeg_path is not None

    @property
    def perceptualdiff_enabled(self) -> bool:
        return self.perceptualdiff_path is not None


class TestBase:
    """
    Provides a basic framework that:
    - Starts FFMPEG to record footage of xemu while it runs
    - Launches xemu with a test XBE loaded from a disc image
    - Waits for xemu to shutdown or timeout
    - Inspect the filesystem for test results

    Tester runs in current working directory and will generate some working files.
    """

    def __init__(
        self,
        test_env: TestEnvironment,
        xbox_results_path: str,
        results_out_path: str | Path,
        iso_path: str | Path,
        timeout: int = 60,
    ):
        cur_dir = Path.cwd()

        self.flash_path = test_env.private_path / "bios.bin"
        self.mcpx_path = test_env.private_path / "mcpx.bin"
        self.hdd_path = cur_dir / "test.img"
        self.mount_path = cur_dir / "xemu-hdd-mount"
        self.iso_path = Path(iso_path)
        self.results_in_path = self.mount_path / xbox_results_path
        self.results_out_path = Path(results_out_path)
        self.video_capture_path = self.results_out_path / "capture.mp4"
        self.timeout = timeout
        self.test_env = test_env
        self.ffmpeg = None
        self.xemu_exit_status = None

        assert self.flash_path.is_file()
        assert self.mcpx_path.is_file()
        assert self.iso_path.is_file()

        if platform.system() == "Windows":
            self.app: pywinauto.application.Application | None = None
            self.record_x: int = 0
            self.record_y: int = 0
            self.record_w: int = 0
            self.record_h: int = 0

        shutil.rmtree(results_out_path, True)

    def _prepare_roms(self):
        log.info("Preparing ROM images")
        # Nothing to do here yet

    def _prepare_hdd(self):
        log.info("Preparing HDD image")
        disk_size = 8 * 1024 * 1024 * 1024
        if self.hdd_path.exists():
            if self.hdd_path.stat().st_size != disk_size:
                raise FileExistsError(
                    "Target image path exists and is not expected size"
                )
            Fatx.format(str(self.hdd_path))
        else:
            Fatx.create(str(self.hdd_path), disk_size)

        self.setup_hdd_files(Fatx(str(self.hdd_path)))

    def _prepare_config(self):
        config = (
            "[general]\n"
            "show_welcome = false\n"
            "skip_boot_anim = true\n"
            "[general.updates]\n"
            "check = false\n"
            "[net]\n"
            "enable = false\n"
            "[sys]\n"
            "mem_limit = '64'\n"
            "[sys.files]\n"
            f"bootrom_path = '{self.mcpx_path}'\n"
            f"flashrom_path = '{self.flash_path}'\n"
            f"hdd_path = '{self.hdd_path}'\n"
        )
        log.info("Prepared config file:\n%s", config)
        Path("xemu.toml").write_text(config)

    def _launch_video_capture(self):
        if not self.test_env.video_capture_enabled:
            return
        ffmpeg_path = self.test_env.ffmpeg_path
        if platform.system() == "Windows":
            if self.app is None:
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

    def _terminate_video_capture(self):
        if not self.test_env.video_capture_enabled or self.ffmpeg is None:
            return
        log.info("Shutting down FFMPEG")
        self.ffmpeg.communicate(b"q\n", timeout=5)

    def _launch_xemu(self):
        c = [
            str(self.test_env.xemu_path),
            "-config_path",
            "./xemu.toml",
            "-dvd_path",
            str(self.iso_path),
        ]
        log.info(
            "Launching xemu with command %s from directory %s", repr(c), Path.cwd()
        )
        start = time.time()
        xemu = subprocess.Popen(c)

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
                self.record_x = x
                self.record_y = y
                self.record_w = w
                self.record_h = h
            except:  # noqa:E722
                log.exception("Failed to connect to xemu window")
                self.app = None

        self._launch_video_capture()

        while True:
            status = xemu.poll()
            if status is not None:
                log.info("xemu exited %d", status)
                self.xemu_exit_status = status
                break
            now = time.time()
            if (now - start) > self.timeout:
                log.warning("Timeout exceeded. Terminating.")
                xemu.kill()
                xemu.wait()
                break
            time.sleep(1)

        self._terminate_video_capture()

    def _mount_hdd(self):
        log.info(f"Mounting HDD image {self.hdd_path} at {self.mount_path}")
        if self.mount_path.exists():
            shutil.rmtree(self.mount_path)
        self.mount_path.mkdir(parents=True, exist_ok=True)

        # FIXME: Don't need to run here
        subprocess.run(
            [sys.executable, "-m", "pyfatx", "-x", str(self.hdd_path)],
            check=True,
            cwd=self.mount_path,
        )

    def _copy_results(self):
        log.info("Copying test results...")
        shutil.copytree(self.results_in_path, self.results_out_path, dirs_exist_ok=True)

    def _unmount_hdd(self):
        log.info("Unmounting HDD image")
        # Nothing to do

    def compare_images(
        self,
        expected_path: str | Path,
        actual_path: str | Path,
        diff_result_path: str | Path | None = None,
    ) -> tuple[bool, str]:
        """Perform a perceptual diff of the given images."""
        if not self.test_env.perceptualdiff_enabled:
            return True, ""

        perceptualdiff_path = self.test_env.perceptualdiff_path
        if not perceptualdiff_path:
            if platform.system() == "Windows":
                perceptualdiff_path = "perceptualdiff.exe"
            else:
                perceptualdiff_path = "perceptualdiff"

        c = [perceptualdiff_path, "--verbose"]
        if diff_result_path:
            c.extend(["--output", str(diff_result_path)])
        c.extend([str(expected_path), str(actual_path)])
        result = subprocess.run(c, capture_output=True)
        return result.returncode == 0, result.stderr.decode("utf-8")

    def setup_hdd_files(self, fs: Fatx):
        """Configure any files on the hard disk that are needed for the test.

        This method may be implemented by the subclass.
        """
        del fs

    def analyze_results(self):
        """Validate any files retrieved from the HDD.

        This method should be implemented by the subclass to confirm that the output of the test matches expectations.
        """
        pass

    def teardown_hdd_files(self, fs: Fatx):
        """Clean up any files on the hard disk that should not outlive the test.

        This method may be implemented by the subclass.
        """
        del fs

    def run(self):
        self.results_out_path.mkdir(parents=True, exist_ok=True)
        self._prepare_roms()
        self._prepare_hdd()
        self._prepare_config()
        self._launch_xemu()
        self._mount_hdd()
        self._copy_results()
        self._unmount_hdd()
        try:
            self.analyze_results()
        finally:
            self.teardown_hdd_files(Fatx(str(self.hdd_path)))
