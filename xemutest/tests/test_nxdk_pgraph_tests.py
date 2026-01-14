"""Test harness for nxdk_pgraph_tests."""

import json
import re
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
import sys
from typing import NamedTuple
from pathlib import Path

from xemutest import (
    ci,
    GoldenImageComparator,
    TestBase,
    TestStatus,
    Environment,
    XemuTestBase,
)

log = logging.getLogger(__name__)

STARTING_RE = re.compile(r"^Starting (?P<suite>.*?)::(?P<test>.*)")
COMPLETED_RE = re.compile(r"Completed '(?P<test>.*?)' in (?P<duration>.*)")


class PgraphTestId(NamedTuple):
    suite: str
    name: str


class PgraphTestStatus(Enum):
    INCOMPLETE = auto()  # Test did not complete execution
    COMPLETED = auto()  # Test completed, awaiting comparison
    DIFFERED = auto()  # Test completed but output differs from golden
    MATCHED = auto()  # Test completed and matches golden


@dataclass
class PgraphTestResult:
    test_id: PgraphTestId
    renderer: str
    status: PgraphTestStatus
    message: str = ""
    duration: str = ""  # Duration string from progress log (e.g., "43ms")


@dataclass
class PgraphTestSuiteAnalysis:
    tests_completed: list[tuple[PgraphTestId, str]] = field(
        default_factory=list
    )  # (test_id, duration)
    tests_incomplete: list[PgraphTestId] = field(default_factory=list)


class NxdkPgraphTestExecutor(XemuTestBase):
    """Runs the nxdk_pgraph_tests suite."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        test_data_path: Path,
        suite_config,
    ):
        super().__init__(test_env, results_path)
        self.xemu_manager.iso_path = test_data_path / "nxdk_pgraph_tests_xiso.iso"
        self.xemu_manager.timeout = 30 * 60
        self.xbox_results_path = "nxdk_pgraph_tests"
        self.suite_config = suite_config

    def _prepare_hdd(self):
        super()._prepare_hdd()

        log.debug(
            "Writing E:/nxdk_pgraph_tests/nxdk_pgraph_tests_config.json: %r",
            self.suite_config,
        )
        fs_e = self.hdd_manager.get_filesystem("e")
        fs_e.mkdir("/nxdk_pgraph_tests")
        fs_e.write(
            "/nxdk_pgraph_tests/nxdk_pgraph_tests_config.json",
            json.dumps(self.suite_config, indent=2).encode("utf-8"),
        )
        del fs_e


class TestNxdkPgraphTests(TestBase):
    """Exhaustively runs the nxdk_pgraph_tests suite and validates output."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        test_data_path: Path,
    ):
        super().__init__(test_env, results_path)
        self.test_data_path = test_data_path
        self.golden_results_path = (
            test_data_path / "nxdk_pgraph_tests_golden_results" / "results"
        )
        if not self.golden_results_path.is_dir():
            msg = f"{self.golden_results_path} was not installed with the package. Please check it out from Github."
            raise FileNotFoundError(msg)
        self._pgraph_results: dict[tuple[str, PgraphTestId], PgraphTestResult] = {}

    @staticmethod
    def _get_xemu_config_addend(renderer):
        return f"""
[display]
renderer = '{renderer.upper()}'
"""

    def _run(self):
        renderers_to_test = ["opengl"]
        if sys.platform != "darwin":
            renderers_to_test.append("vulkan")

        for renderer in renderers_to_test:
            num_iterations = 0
            tests_ran = []
            should_run = True

            with ci.log_group(f"Renderer: {renderer}"):
                while should_run:
                    results_path = (
                        self.results_path / renderer / f"iteration_{num_iterations}"
                    )

                    executor = NxdkPgraphTestExecutor(
                        self.test_env,
                        results_path,
                        self.test_data_path,
                        suite_config=self._build_pgraph_test_config(
                            tests_to_skip=tests_ran
                        ),
                    )
                    executor.xemu_manager.config += self._get_xemu_config_addend(
                        renderer
                    )
                    executor.run()

                    progress_analysis = self._analyze_pgraph_progress_log(
                        results_path / "pgraph_progress_log.txt"
                    )

                    # Track completed tests (pending comparison)
                    for test_id, duration in progress_analysis.tests_completed:
                        self._pgraph_results[(renderer, test_id)] = PgraphTestResult(
                            test_id=test_id,
                            renderer=renderer,
                            status=PgraphTestStatus.COMPLETED,
                            duration=duration,
                        )

                    # Track incomplete tests
                    for test_id in progress_analysis.tests_incomplete:
                        self._pgraph_results[(renderer, test_id)] = PgraphTestResult(
                            test_id=test_id,
                            renderer=renderer,
                            status=PgraphTestStatus.INCOMPLETE,
                            message="Test did not complete",
                        )

                    tests_ran.extend(
                        test_id for test_id, _ in progress_analysis.tests_completed
                    )
                    tests_ran.extend(progress_analysis.tests_incomplete)

                    log.info(
                        "Iteration %d: %d completed, %d incomplete",
                        num_iterations,
                        len(progress_analysis.tests_completed),
                        len(progress_analysis.tests_incomplete),
                    )

                    num_iterations += 1
                    should_run = bool(
                        progress_analysis.tests_incomplete
                        or progress_analysis.tests_completed
                    )

    @staticmethod
    def _build_pgraph_test_config(
        tests_to_skip: list[PgraphTestId] | None = None,
    ) -> dict:
        config = {
            "settings": {
                "enable_progress_log": True,
                "disable_autorun": False,
                "enable_autorun_immediately": True,
                "enable_shutdown_on_completion": True,
                "enable_pgraph_region_diff": False,
                "skip_tests_by_default": False,
                "delay_milliseconds_between_tests": 0,
                "network": {
                    "enable": False,
                    "config_automatic": False,
                    "config_dhcp": False,
                    "static_ip": "",
                    "static_netmask": "",
                    "static_gateway": "",
                    "static_dns_1": "",
                    "static_dns_2": "",
                    "ftp": {
                        "ftp_ip": "",
                        "ftp_port": 0,
                        "ftp_user": "",
                        "ftp_password": "",
                        "ftp_timeout_milliseconds": 0,
                    },
                },
                "output_directory_path": "c:/nxdk_pgraph_tests",
            },
            "test_suites": {},
        }

        if tests_to_skip:
            for test in tests_to_skip:
                if test.suite not in config["test_suites"]:
                    config["test_suites"][test.suite] = {}
                if test.name not in config["test_suites"][test.suite]:
                    config["test_suites"][test.suite][test.name] = {}
                config["test_suites"][test.suite][test.name]["skipped"] = True

        return config

    @staticmethod
    def _analyze_pgraph_progress_log(path: Path) -> PgraphTestSuiteAnalysis:
        """Analyze the nxdk_pgraph_tests progress log to determine which tests ran."""
        analysis = PgraphTestSuiteAnalysis()
        with open(path) as file:
            test_started: PgraphTestId | None = None
            for line in file.readlines():
                line = line.strip()
                if starting_matches := STARTING_RE.match(line):
                    assert test_started is None, "Unmatched starting/completed sequence"
                    suite, test = starting_matches.group("suite", "test")
                    test_started = PgraphTestId(suite, test)
                elif completed_matches := COMPLETED_RE.match(line):
                    test, duration = completed_matches.group("test", "duration")
                    assert (
                        test_started is not None and test_started.name == test
                    ), "Unmatched starting/completed sequence"
                    analysis.tests_completed.append((test_started, duration))
                    test_started = None
                elif line == "Testing completed normally, closing log.":
                    continue
                else:
                    log.warning("Unexpected log entry: %s", line)
        if test_started:
            log.warning("Test %r was not completed!", test_started)
            analysis.tests_incomplete.append(test_started)
        return analysis

    def _get_test_id_from_image_path(
        self, path: Path
    ) -> tuple[str, PgraphTestId] | None:
        """Extract renderer and test ID from an image path like 'opengl/iteration_0/Suite/Test.png'."""
        parts = path.parts
        if len(parts) < 4:
            return None
        renderer = parts[0]
        suite = parts[2]
        test_name = parts[3].rsplit(".", 1)[0]  # Remove .png extension
        return (renderer, PgraphTestId(suite, test_name))

    def analyze_results(self):
        """Processes the generated image files, diffing against the golden result set."""
        with ci.log_group("Analyzing results (golden image comparison)"):

            def path_transform(root_relative_to_out_path: Path) -> Path:
                """Transform results path to golden path by skipping renderer/iteration dirs."""
                return Path(*root_relative_to_out_path.parts[2:])

            comparator = GoldenImageComparator(
                self.test_env,
                self.results_path,
                self.golden_results_path,
            )

            failed_comparisons = comparator.compare_all(path_transform=path_transform)

            # Update status for differing tests
            for path_str, message in failed_comparisons.items():
                path = Path(path_str)
                key = self._get_test_id_from_image_path(path)
                if key and key in self._pgraph_results:
                    self._pgraph_results[key].status = PgraphTestStatus.DIFFERED
                    self._pgraph_results[key].message = message

            # Mark remaining COMPLETED tests as MATCHED only if comparison was performed
            # If perceptualdiff is not available, leave them as COMPLETED (-> UNVERIFIED)
            if self.test_env.perceptualdiff_enabled:
                for result in self._pgraph_results.values():
                    if result.status == PgraphTestStatus.COMPLETED:
                        result.status = PgraphTestStatus.MATCHED

            # Generate subtest results from unified tracking
            has_failures = False
            for result in self._pgraph_results.values():
                test_name = (
                    f"{result.renderer}::{result.test_id.suite}::{result.test_id.name}"
                )
                match result.status:
                    case PgraphTestStatus.MATCHED:
                        status = TestStatus.PASSED
                    case PgraphTestStatus.COMPLETED:
                        status = TestStatus.UNVERIFIED  # Completed but not compared
                    case _:
                        status = TestStatus.FAILED
                message = result.message if status != TestStatus.PASSED else ""
                if status == TestStatus.FAILED:
                    has_failures = True
                    log.error("%s: %s", test_name, result.status.name)
                self.add_subtest_result(test_name, status, message, result.duration)

            if has_failures:
                failed_count = sum(
                    1
                    for r in self._pgraph_results.values()
                    if r.status != PgraphTestStatus.MATCHED
                )
                raise Exception(f"{failed_count} test(s) failed")
