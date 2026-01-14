import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from .env import Environment
from .video_capture import VideoCapture
from .hdd_manager import HddManager
from .xemu_manager import XemuManager


log = logging.getLogger(__name__)


class TestStatus(Enum):
    """Status of a test or subtest."""

    RUNNING = auto()  # Test is currently executing
    PASSED = auto()
    FAILED = auto()
    UNVERIFIED = auto()  # Test completed but results not verified


@dataclass
class TestResult:
    """Result of a test."""

    name: str
    status: TestStatus
    message: str = ""
    duration: str = ""  # Duration string (e.g., "43ms")
    subtests: list["TestResult"] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Returns True if the test did not fail (passed or unverified)."""
        return self.status in (TestStatus.PASSED, TestStatus.UNVERIFIED)


class TestBase:
    """Minimal generic test framework for managing test execution and results."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
    ):
        self.test_env = test_env
        self.results_path = Path(results_path)
        self._test_result: TestResult | None = None

    def _run(self):
        """Execute the test. Should be implemented by subclass."""
        raise NotImplementedError("Subclass must implement run() method")

    def run(self) -> TestResult:
        shutil.rmtree(self.results_path, True)
        self.results_path.mkdir(parents=True, exist_ok=True)
        self._test_result = TestResult(
            name=type(self).__name__, status=TestStatus.RUNNING
        )
        self._run()
        self.analyze_results()
        if self._test_result.status == TestStatus.RUNNING:
            self._test_result.status = TestStatus.PASSED
        return self._test_result

    def analyze_results(self):
        """Validate test results.

        This method should be implemented by the subclass to confirm that the output of the test matches expectations.
        """
        pass

    def add_subtest_result(
        self, name: str, status: TestStatus, message: str = "", duration: str = ""
    ):
        """Add a subtest result to the test results."""
        if self._test_result is None:
            return
        self._test_result.subtests.append(TestResult(name, status, message, duration))
        if status == TestStatus.FAILED:
            self._test_result.status = TestStatus.FAILED


class XemuTestBase(TestBase):
    """Test framework specifically for xemu-based tests."""

    def __init__(self, test_env: Environment, results_path: Path):
        super().__init__(test_env, results_path)

        self.hdd_path = Path.cwd() / "test.img"
        self.xbox_results_path: str | None = None
        self.hdd_manager = HddManager(self.hdd_path)
        self.xemu_manager = XemuManager(test_env, self.hdd_path)
        self.video_capture = VideoCapture(test_env, self.results_path / "capture.mp4")
        self.xemu_manager.set_video_capture(self.video_capture)

    def _prepare_hdd(self):
        """Prepare the HDD image for testing."""
        self.hdd_manager.prepare()

    def _launch_xemu(self):
        """Launch xemu and wait for it to complete or timeout."""
        with open(self.results_path / "xemu.log", "w") as log_file:
            self.xemu_manager.launch(log_file)

    def _copy_results(self):
        """Copy test results from the mounted HDD and xemu configuration."""
        log.info("Copying test results...")
        if self.xbox_results_path:
            temp_extract_path = Path.cwd() / "xemu-hdd-mount"
            self.hdd_manager.extract_files_to(temp_extract_path)
            shutil.copytree(
                temp_extract_path / self.xbox_results_path,
                self.results_path,
                dirs_exist_ok=True,
            )
        shutil.copy2(self.xemu_manager.config_path, self.results_path)

    def _run(self):
        """Execute the xemu test."""
        self._prepare_hdd()
        self._launch_xemu()
        self._copy_results()
