"""Test harness for nxdk_pgraph_tests."""

import logging
import os
import shutil

import test_base

log = logging.getLogger(__file__)

TIMEOUT_SECONDS = 10 * 60


class TestNXDKPgraphTests(test_base.TestBase):
    """Runs the nxdk_pgraph_tests suite and validates output."""

    def __init__(
        self,
        test_env: test_base.TestEnvironment,
        results_path: str,
        test_data_path: str,
    ) -> None:
        iso_path = os.path.join(test_data_path, "nxdk_pgraph_tests_xiso.iso")
        if not os.path.isfile(iso_path):
            msg = f"{iso_path} was not installed with the package. You need to build or download it."
            raise FileNotFoundError(msg)

        self.golden_results_path = os.path.join(
            test_data_path, "nxdk_pgraph_tests_golden_results"
        )
        if not os.path.isdir(self.golden_results_path):
            msg = f"{self.golden_results_path} was not installed with the package. Please check it out from Github."
            raise FileNotFoundError(msg)

        super().__init__(
            test_env, "nxdk_pgraph_tests", results_path, iso_path, TIMEOUT_SECONDS
        )

    def analyze_results(self):
        """Processes the generated image files, diffing against the golden result set."""
        if self.xemu_exit_status is None:
            log.warning("xemu exited due to timeout, results are likely partial")
        elif self.xemu_exit_status:
            log.warning(
                "xemu terminated due to error (%d), results may be partial due to a crash",
                self.xemu_exit_status,
            )

        diff_dir = "_diffs"
        diff_results_dir = self._prepare_diff_dir(diff_dir)

        failed_comparisons = {}

        for root, dirnames, files in os.walk(self.results_out_path):
            root_relative_to_out_path = os.path.relpath(root, self.results_out_path)
            if diff_dir in dirnames:
                dirnames.remove(diff_dir)

            failed_comparisons.update(
                self._compare_results(
                    root_relative_to_out_path, diff_results_dir, files
                )
            )

        if failed_comparisons:
            msg = f"Failed {len(failed_comparisons)} comparisons: {failed_comparisons}"
            raise Exception(msg)

    def _compare_results(
        self, root_relative_to_out_path: str, diff_results_dir: str, files: list[str]
    ) -> dict[str, str]:
        failed_comparisons: dict[str, str] = {}

        for file in files:
            if not file.endswith(".png"):
                continue

            relative_file_path = os.path.join(root_relative_to_out_path, file)
            expected_path = os.path.abspath(
                os.path.join(self.golden_results_path, relative_file_path)
            )
            actual_path = os.path.abspath(
                os.path.join(self.results_out_path, relative_file_path)
            )
            diff_path = os.path.join(diff_results_dir, relative_file_path)
            os.makedirs(os.path.dirname(diff_path), exist_ok=True)

            if not os.path.isfile(expected_path):
                log.warning(
                    "Missing golden image %s for output %s", expected_path, actual_path
                )
                continue

            match, message = self.compare_images(expected_path, actual_path, diff_path)
            if not match:
                log.warning("Generated image %s does not match golden", actual_path)
                failed_comparisons[relative_file_path] = message

        return failed_comparisons

    def _prepare_diff_dir(self, diff_dir: str) -> str:
        diff_results_dir = os.path.abspath(
            os.path.join(self.results_out_path, diff_dir)
        )
        if os.path.exists(diff_results_dir):
            shutil.rmtree(diff_results_dir)
        os.makedirs(diff_results_dir, exist_ok=True)
        return diff_results_dir
