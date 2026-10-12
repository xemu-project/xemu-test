from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xemutest.errors import RunNotImplementedError
from xemutest.hdd_manager import HddManager
from xemutest.video_capture import VideoCapture
from xemutest.xemu_manager import XemuManager

if TYPE_CHECKING:
    from os import PathLike

    from xemutest.env import Environment

log = logging.getLogger(__name__)


class TestStatus(StrEnum):
    """Status of a test or subtest."""

    RUNNING = auto()  # Test is currently executing
    PASSED = auto()
    FAILED = auto()
    UNVERIFIED = auto()  # Test completed but results not verified
    FAILURE_SUPPRESSED = auto()  # Test failed but matched an expected failure filter
    UNEXPECTED_FILTER_MISMATCH = (
        auto()
    )  # Test matched an expected failure filter but passed

    @property
    def is_failure(self) -> bool:
        return self in (TestStatus.FAILED, TestStatus.UNEXPECTED_FILTER_MISMATCH)


@dataclass
class TestResult:
    """Result of a test."""

    name: str
    status: TestStatus
    message: str = ""
    duration: str = ""  # Duration string (e.g., "43ms")
    location_url: str = ""
    subtests: list[TestResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Returns True if the test did not fail (passed or unverified)."""
        return not self.status.is_failure

    def add_subresult(
        self,
        name: str,
        status: TestStatus,
        message: str = "",
        duration: str = "",
        location_url: str = "",
    ):
        """Add a subresult result to this TestResult."""
        subresult = TestResult(name, status, message, duration, location_url)
        self.subtests.append(subresult)
        if status == TestStatus.FAILED:
            self.status = TestStatus.FAILED

        return subresult


def _load_failure_filters(json_path: PathLike | None) -> dict[str, Any]:
    if not json_path:
        return {}

    with open(json_path) as infile:
        filter_data = json.load(infile)

    return filter_data.get("expected_failures", {})


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

        self._failure_filter_registry = _load_failure_filters(
            self.test_env.failure_filter_path
        )

    def _run(self):
        """Execute the test. Should be implemented by subclass."""
        raise RunNotImplementedError

    def run(self) -> TestResult:
        shutil.rmtree(self.results_path, True)
        self.results_path.mkdir(parents=True, exist_ok=True)
        self._test_result = TestResult(
            name=type(self).__name__, status=TestStatus.RUNNING
        )
        try:
            self._run()
            self.analyze_results()
            if self._test_result.status == TestStatus.RUNNING:
                self._test_result.status = TestStatus.PASSED
        except Exception as e:
            log.exception("Test failed with exception")
            self._test_result.status = TestStatus.FAILED
            self._test_result.message = str(e)
        return self._test_result

    def analyze_results(self):
        """Validate test results.

        This method should be implemented by the subclass to confirm that the output of the test matches expectations.
        """

    def add_subtest_result(
        self,
        name: str,
        status: TestStatus,
        message: str = "",
        duration: str = "",
        location_url: str = "",
    ) -> TestResult | None:
        """Add a subtest result to the test results."""
        if self._test_result is None:
            return None

        return self._test_result.add_subresult(
            name, status, message, duration, location_url
        )

    def get_failure_filter(self) -> dict[str, list[Any]]:
        filt = self._failure_filter_registry.get(type(self).__name__)
        if filt:
            return filt

        return {}

    def update_test_results_from_subtests(self) -> TestStatus:
        if self._test_result is None:
            return TestStatus.UNVERIFIED

        if not self._test_result.subtests:
            return self._test_result.status

        if any(subtest.status.is_failure for subtest in self._test_result.subtests):
            self._test_result.status = TestStatus.FAILED
        elif any(
            subtest.status == TestStatus.FAILURE_SUPPRESSED
            for subtest in self._test_result.subtests
        ):
            self._test_result.status = TestStatus.FAILURE_SUPPRESSED
        elif any(
            subtest.status == TestStatus.PASSED
            for subtest in self._test_result.subtests
        ):
            self._test_result.status = TestStatus.PASSED
        else:
            self._test_result.status = TestStatus.UNVERIFIED

        return self._test_result.status


class XemuTestBase(TestBase):
    """Test framework specifically for xemu-based tests."""

    def __init__(
        self, test_env: Environment, results_path: Path, *, timeout_seconds: int = 60
    ):
        super().__init__(test_env, results_path)

        self.hdd_path = Path.cwd() / "test.img"
        self.xbox_results_path: str | None = None
        self.hdd_manager = HddManager(self.hdd_path)
        self.xemu_manager = XemuManager(
            test_env, self.hdd_path, timeout_seconds=timeout_seconds
        )
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
