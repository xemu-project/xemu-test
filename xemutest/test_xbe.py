"""Test harness for test-xbe."""

from pathlib import Path

import test_base


class TestXBE(test_base.TestBase):
    """Runs test-xbe and validates output."""

    def __init__(
        self,
        test_env: test_base.TestEnvironment,
        results_path: Path,
        test_data_path: Path,
    ):
        iso_path = test_data_path / "tester.iso"
        if not iso_path.is_file():
            raise FileNotFoundError(
                "Test data was not installed with the package. You need to build it and copy "
                f"to {test_data_path}."
            )

        super().__init__(test_env, "results", results_path, iso_path)

    def analyze_results(self):
        results_file = self.results_out_path / "results.txt"
        assert results_file.read_text().strip() == "Success"
