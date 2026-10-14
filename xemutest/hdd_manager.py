import logging
import shutil
import subprocess
import sys
from pathlib import Path

from pyfatx import Fatx

from xemutest.errors import HddSizeMismatchError

log = logging.getLogger(__name__)


class HddManager:
    """Manages HDD image creation, formatting, and mounting."""

    def __init__(self, hdd_path: Path):
        self.hdd_path = hdd_path

    def prepare(self, disk_size: int = 8 * 1024 * 1024 * 1024):
        """Create or format the HDD image."""
        log.debug("Preparing HDD image")
        if self.hdd_path.exists():
            if self.hdd_path.stat().st_size != disk_size:
                raise HddSizeMismatchError
            Fatx.format(str(self.hdd_path))
        else:
            Fatx.create(str(self.hdd_path), disk_size)

    def extract_files_to(self, dest: Path):
        """Mount the HDD image to the filesystem."""
        log.debug("Extracting HDD image files from %s to %s", self.hdd_path, dest)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [sys.executable, "-m", "pyfatx", "-x", str(self.hdd_path)],
            check=True,
            cwd=dest,
        )

    def get_filesystem(self, drive: str = "c") -> Fatx:
        """Get a Fatx filesystem object for the HDD."""
        return Fatx(str(self.hdd_path), drive=drive)
