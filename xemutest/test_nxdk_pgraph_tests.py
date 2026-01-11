"""Test harness for nxdk_pgraph_tests."""

import logging
import shutil
from pathlib import Path

import test_base

log = logging.getLogger(__file__)

TIMEOUT_SECONDS = 10 * 60


class TestNXDKPgraphTests(test_base.TestBase):
    """Runs the nxdk_pgraph_tests suite and validates output."""

    def __init__(
        self,
        test_env: test_base.TestEnvironment,
        results_path: str | Path,
        test_data_path: str | Path,
    ) -> None:
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

            relative_file_path = root_relative_to_out_path / file
            expected_path = (self.golden_results_path / relative_file_path).resolve()
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
