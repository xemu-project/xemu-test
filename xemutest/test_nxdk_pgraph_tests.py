"""Test harness for nxdk_pgraph_tests."""

import json
import shutil
import re
import logging
from dataclasses import dataclass, field
import sys
from typing import NamedTuple
from pathlib import Path

import test_base
from pyfatx import Fatx

log = logging.getLogger(__file__)

TIMEOUT_SECONDS = 10 * 60
STARTING_RE = re.compile(r"^Starting (?P<suite>.*?)::(?P<test>.*)")
COMPLETED_RE = re.compile(r"Completed '(?P<test>.*?)' in (?P<duration>.*)")


class PgraphTestId(NamedTuple):
    suite: str
    name: str


@dataclass
class PgraphTestSuiteAnalysis:
    tests_completed: list[PgraphTestId] = field(default_factory=list)
    tests_failed: list[PgraphTestId] = field(default_factory=list)


class NxdkPgraphTestExecutor(test_base.TestBase):
    """Runs the nxdk_pgraph_tests suite."""

    def __init__(
        self,
        test_env: test_base.TestEnvironment,
        results_path: Path,
        test_data_path: Path,
        suite_config,
    ) -> None:
        iso_path = test_data_path / "nxdk_pgraph_tests_xiso.iso"
        if not iso_path.is_file():
            msg = f"{iso_path} was not installed with the package. You need to build or download it."
            raise FileNotFoundError(msg)
        self.suite_config = suite_config

        super().__init__(
            test_env, "nxdk_pgraph_tests", results_path, iso_path, TIMEOUT_SECONDS
        )

    def setup_hdd_files(self, fs: test_base.Fatx):
        super().setup_hdd_files(fs)  # Releases fs

        log.info("Writing config: %r", self.suite_config)
        fs_e = Fatx(str(self.hdd_path), drive="e")
        fs_e.mkdir("/nxdk_pgraph_tests")
        fs_e.write(
            "/nxdk_pgraph_tests/nxdk_pgraph_tests_config.json",
            json.dumps(self.suite_config, indent=2).encode("utf-8"),
        )
        del fs_e

    def analyze_results(self):
        """Check xemu exit status."""
        if self.xemu_exit_status is None:
            log.warning("xemu exited due to timeout, results are likely partial")
        elif self.xemu_exit_status:
            log.warning(
                "xemu terminated due to error (%d), results may be partial due to a crash",
                self.xemu_exit_status,
            )


class TestNxdkPgraphTests(test_base.TestBase):
    """Exhaustively runs the nxdk_pgraph_tests suite and validates output."""

    test_env: test_base.TestEnvironment
    results_path: Path
    test_data_path: Path

    def __init__(
        self,
        test_env: test_base.TestEnvironment,
        results_path: Path,
        test_data_path: Path,
    ) -> None:
        self.test_env = test_env
        self.results_path = results_path
        self.test_data_path = test_data_path

        test_data_path = Path(test_data_path)
        iso_path = test_data_path / "nxdk_pgraph_tests_xiso.iso"
        if not iso_path.is_file():
            msg = f"{iso_path} was not installed with the package. You need to build or download it."
            raise FileNotFoundError(msg)

        self.golden_results_path = (
            test_data_path / "nxdk_pgraph_tests_golden_results" / "results"
        )
        if not self.golden_results_path.is_dir():
            msg = f"{self.golden_results_path} was not installed with the package. Please check it out from Github."
            raise FileNotFoundError(msg)

        super().__init__(
            test_env, "nxdk_pgraph_tests", results_path, iso_path, TIMEOUT_SECONDS
        )

    def run(self):
        renderers_to_test = ["OPENGL"]
        if sys.platform != "darwin":
            renderers_to_test.append("VULKAN")

        for renderer in renderers_to_test:
            xemu_config_addend = f"""
[display]
renderer = '{renderer}'
"""

            run_name = renderer.lower()
            self.run_suite(run_name, xemu_config_addend)

    def run_suite(self, run_name, xemu_config_addend=""):
        num_iterations = 0
        tests_completed = []
        tests_failed = []
        tests_ran = []
        should_run = True

        while should_run:
            results_path = self.results_path / run_name / f"iteration_{num_iterations}"

            executor = NxdkPgraphTestExecutor(
                self.test_env,
                results_path,
                self.test_data_path,
                suite_config=self._build_pgraph_test_config(tests_to_skip=tests_ran),
            )
            executor.xemu_config_addend = xemu_config_addend
            executor.run()

            progress_analysis = self._analyze_pgraph_progress_log(
                results_path / "pgraph_progress_log.txt"
            )
            tests_completed.extend(progress_analysis.tests_completed)
            tests_failed.extend(progress_analysis.tests_failed)
            tests_ran.extend(progress_analysis.tests_completed)
            tests_ran.extend(progress_analysis.tests_failed)

            num_iterations += 1
            should_run = bool(
                progress_analysis.tests_failed or progress_analysis.tests_completed
            )

        for test in tests_failed:
            log.error("%s::%s failed", test.suite, test.name)

        self.analyze_results()

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
                    test = completed_matches.group("test")
                    assert (
                        test_started is not None and test_started.name == test
                    ), "Unmatched starting/completed sequence"
                    analysis.tests_completed.append(test_started)
                    test_started = None
                else:
                    log.warning("Unexpected log entry: %s", line)
        if test_started:
            log.warning("Test %r was not completed! Assumed crashed.", test_started)
            analysis.tests_failed.append(test_started)
        return analysis

    def analyze_results(self):
        """Processes the generated image files, diffing against the golden result set."""

        if not self.test_env.perceptualdiff_enabled:
            log.warning("Missing perceptual diff, skipping result analysis")
            return

        diff_dir = "_diffs"
        diff_results_dir = self._prepare_diff_dir(diff_dir)

        failed_comparisons = {}

        # Walk all directories including root
        dirs_to_check = [self.results_out_path]
        dirs_to_check.extend(
            d
            for d in self.results_out_path.rglob("*")
            if d.is_dir() and diff_dir not in d.parts
        )

        for dir_path in dirs_to_check:
            root_relative_to_out_path = dir_path.relative_to(self.results_out_path)
            files = [f.name for f in dir_path.iterdir() if f.is_file()]

            failed_comparisons.update(
                self._compare_results(
                    root_relative_to_out_path, diff_results_dir, files
                )
            )

        if failed_comparisons:
            msg = f"Failed {len(failed_comparisons)} comparisons: {failed_comparisons}"
            raise Exception(msg)

    def _compare_results(
        self, root_relative_to_out_path: Path, diff_results_dir: Path, files: list[str]
    ) -> dict[str, str]:
        failed_comparisons: dict[str, str] = {}

        for file in files:
            if not file.endswith(".png"):
                continue

            path_relative_to_iteration = Path(*root_relative_to_out_path.parts[2:])
            expected_path = (
                self.golden_results_path / path_relative_to_iteration / file
            ).resolve()

            relative_file_path = root_relative_to_out_path / file
            actual_path = (self.results_out_path / relative_file_path).resolve()
            diff_path = diff_results_dir / relative_file_path
            diff_path.parent.mkdir(parents=True, exist_ok=True)

            if not expected_path.is_file():
                log.warning(
                    "Missing golden image %s for output %s", expected_path, actual_path
                )
                continue

            match, message = self.compare_images(expected_path, actual_path, diff_path)
            if not match:
                log.warning("Generated image %s does not match golden", actual_path)
                failed_comparisons[str(relative_file_path)] = message

        return failed_comparisons

    def _prepare_diff_dir(self, diff_dir: str) -> Path:
        diff_results_dir = (self.results_out_path / diff_dir).resolve()
        if diff_results_dir.exists():
            shutil.rmtree(diff_results_dir)
        diff_results_dir.mkdir(parents=True, exist_ok=True)
        return diff_results_dir
