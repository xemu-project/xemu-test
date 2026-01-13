import logging
import subprocess
from pathlib import Path

from .env import Environment


log = logging.getLogger(__name__)


class GoldenImageComparator:
    """Compares generated images against golden reference images."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        golden_results_path: Path,
    ):
        self.test_env = test_env
        self.results_path = results_path
        self.golden_results_path = golden_results_path

    def compare_all(
        self,
        path_transform=None,
        diff_dir_name: str = "_diffs",
    ) -> dict[str, str]:
        """Compare all images in results_path against golden_results_path."""
        if not self.test_env.perceptualdiff_enabled:
            log.warning("Missing perceptual diff, skipping result analysis")
            return {}

        diff_results_dir = (self.results_path / diff_dir_name).resolve()
        diff_results_dir.mkdir(parents=True, exist_ok=True)

        failed_comparisons = {}

        # Walk all directories including root
        dirs_to_check = [self.results_path]
        dirs_to_check.extend(
            d
            for d in self.results_path.rglob("*")
            if d.is_dir() and diff_dir_name not in d.parts
        )

        for dir_path in dirs_to_check:
            root_relative_to_out_path = dir_path.relative_to(self.results_path)
            files = [f.name for f in dir_path.iterdir() if f.is_file()]

            failed_comparisons.update(
                self._compare_directory(
                    root_relative_to_out_path,
                    diff_results_dir,
                    files,
                    path_transform,
                )
            )

        return failed_comparisons

    def _compare_directory(
        self,
        root_relative_to_out_path: Path,
        diff_results_dir: Path,
        files: list[str],
        path_transform=None,
    ) -> dict[str, str]:
        """
        Compare all images in a single directory.

        Args:
            root_relative_to_out_path: Path of the directory relative to results_path
            diff_results_dir: Directory where diff images should be stored
            files: List of filenames in the directory
            path_transform: Optional callable to transform paths

        Returns:
            Dictionary mapping failed image paths to error messages
        """
        failed_comparisons: dict[str, str] = {}

        for file in files:
            if not file.endswith(".png"):
                continue

            relative_file_path = root_relative_to_out_path / file
            actual_path = (self.results_path / relative_file_path).resolve()

            # Transform path if transformer provided, otherwise use as-is
            if path_transform:
                golden_relative_path = path_transform(root_relative_to_out_path)
            else:
                golden_relative_path = root_relative_to_out_path

            expected_path = (
                self.golden_results_path / golden_relative_path / file
            ).resolve()

            diff_path = diff_results_dir / relative_file_path
            diff_path.parent.mkdir(parents=True, exist_ok=True)

            if not expected_path.is_file():
                log.warning(
                    "Missing golden image %s for output %s", expected_path, actual_path
                )
                continue

            match, message = self._compare_images(expected_path, actual_path, diff_path)
            if not match:
                log.warning("Generated image %s does not match golden", actual_path)
                failed_comparisons[str(relative_file_path)] = message

        return failed_comparisons

    def _compare_images(
        self,
        expected_path: Path,
        actual_path: Path,
        diff_path: Path,
    ) -> tuple[bool, str]:
        """Compare two images using perceptualdiff."""
        log.debug("Comparing %s vs %s", actual_path, expected_path)
        c = [self.test_env.perceptualdiff_path, "--verbose"]
        c.extend(["--output", str(diff_path)])
        c.extend([str(expected_path), str(actual_path)])
        result = subprocess.run(c, capture_output=True)
        return result.returncode == 0, result.stderr.decode("utf-8")
