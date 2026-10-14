"""Test harness for test-xbe."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from xemutest import Environment, TestResult, TestStatus, XemuTestBase

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG: str = """log_path = c:\\results\\results.json
shutdown = true
"""

_RESULT_TO_STATUS: dict[str, TestStatus] = {
    "pass": TestStatus.PASSED,
    "fail": TestStatus.FAILED,
}


class FailureFilter:
    """Filters results for this test suite."""

    def __init__(self, expected_failures: dict[str, list[Any]]) -> None:
        # Map of test name to expected failure matchers.
        self.expected_failures: dict[str, dict[str, Any]] = {}

        if not expected_failures:
            return

        # For convenience, the filter entries associated with this suite are expressed as raw results.
        # Convert the {test: list[states]} to {test: {message: expected_state}}

        for test_key, event_filters in expected_failures.items():
            test_filter = {}
            for event_filter in event_filters:
                scope_name = event_filter.get("scope")
                if not scope_name:
                    test_filter[event_filter["message"]] = event_filter["level"]
                    continue

                # Flatten scoped events.
                if event_filter.get("events") is None:
                    msg = f"Scoped failure filter missing events container. {expected_failures}"
                    raise ValueError(msg)

                for item in event_filter["events"]:
                    event_key = item["message"]
                    test_filter[f"{scope_name}::{event_key}"] = item["level"]

            self.expected_failures[test_key] = test_filter

    def check(
        self, test_name: str, event_key: str, status: TestStatus
    ) -> tuple[TestStatus, str]:
        events = self.expected_failures.get(test_name, {})

        expected = events.get(event_key)
        if expected is None:
            return status, ""

        expected_status = _RESULT_TO_STATUS.get(str(expected))
        if status != expected_status:
            return (
                TestStatus.UNEXPECTED_FILTER_MISMATCH,
                f"Failure filter expected {expected} but status was {status}",
            )

        if status == TestStatus.FAILED:
            return TestStatus.FAILURE_SUPPRESSED, "Failure filter applied"

        return status, ""


def _reduce_test_status(result_count_by_status: dict[TestStatus, int]) -> TestStatus:
    if result_count_by_status.get(TestStatus.FAILED):
        return TestStatus.FAILED
    if result_count_by_status.get(TestStatus.UNEXPECTED_FILTER_MISMATCH):
        return TestStatus.UNEXPECTED_FILTER_MISMATCH
    if result_count_by_status.get(TestStatus.FAILURE_SUPPRESSED):
        return TestStatus.FAILURE_SUPPRESSED

    return TestStatus.PASSED


def _build_result_summary(result_count_by_status: dict[TestStatus, int]) -> str:
    lines = []
    for status in [
        TestStatus.PASSED,
        TestStatus.FAILED,
        TestStatus.UNEXPECTED_FILTER_MISMATCH,
        TestStatus.FAILURE_SUPPRESSED,
    ]:
        count = result_count_by_status.get(status)
        if not count:
            continue

        lines.append(f"{status}: {count}")

    return "<br>".join(lines)


class NxdkLowLevelNV2ATestsBase(XemuTestBase):
    """Base class for tests using nxdk_low_level_nv2a_tests."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        test_data_path: Path,
        iso_filename: Path,
        *args,
        **kwargs,
    ):
        super().__init__(test_env, results_path, *args, **kwargs)
        self.xemu_manager.iso_path = test_data_path / iso_filename
        self.xbox_results_path = "results"

    def analyze_results(self):
        results = self._fetch_results()

        failure_filter = FailureFilter(self.get_failure_filter())

        location_url_base = results.get("location_url_base")

        def build_location_url(source_path: str, line: int = -1) -> str:
            if not location_url_base or not source_path:
                return ""

            location_url = f"{location_url_base}/src/{quote(source_path)}"
            if line != -1:
                location_url += f"#L{line}"
            return location_url

        for test in results["tests"]:
            status = _RESULT_TO_STATUS.get(test["result"], TestStatus.UNVERIFIED)

            duration_str = test.get("duration_ms", "")
            if duration_str:
                duration_str = f"{duration_str} ms"

            location_url = build_location_url(test.get("source"))

            test_case = self.add_subtest_result(
                test["name"],
                status,
                message=test.get("description", ""),
                duration=duration_str,
                location_url=location_url,
            )
            assert test_case is not None

            result_count_by_status = defaultdict(int)

            def _process_event(
                test_case: TestResult,
                result_count_by_status: dict[str, int],
                event: dict[str, Any],
                scope_name: str = "",
            ) -> TestResult:
                status = _RESULT_TO_STATUS.get(event["level"])
                if status is None:
                    return

                event_message = event["message"]
                event_name = (
                    f"{scope_name}::{event_message}" if scope_name else event_message
                )
                adjusted_status, details = failure_filter.check(
                    test_case.name, event_name, status
                )
                result_count_by_status[adjusted_status] += 1

                location_url = build_location_url(
                    event.get("file"), event.get("line", -1)
                )
                duration = event.get("duration_ms", 0)
                event_duration = f"{duration} ms" if duration else ""

                return test_case.add_subresult(
                    event_name,
                    adjusted_status,
                    message=details,
                    duration=event_duration,
                    location_url=location_url,
                )

            for event in test.get("events", []):
                scope_name = event.get("scope")
                if not scope_name:
                    _process_event(test_case, result_count_by_status, event)
                    continue

                for scoped_event in event["events"]:
                    _process_event(
                        test_case,
                        result_count_by_status,
                        scoped_event,
                        scope_name=scope_name,
                    )

            test_case.status = _reduce_test_status(result_count_by_status)
            if test_case.message:
                test_case.message += "<br>"
            test_case.message += f"{_build_result_summary(result_count_by_status)}"

        self.update_test_results_from_subtests()

    def _fetch_results(self) -> dict[str, Any] | None:
        results_file = self.results_path / "results.json"
        if not results_file.exists():
            return None

        with open(results_file) as infile:
            return json.load(infile)

    def _prepare_hdd(self):
        super()._prepare_hdd()

        logger.debug("Writing C:/test_suite_config.ini")
        fs_c = self.hdd_manager.get_filesystem("c")
        fs_c.write("/test_suite_config.ini", _CONFIG.encode())
        del fs_c
