"""Test harness for test-xbe."""

from pathlib import Path

from xemutest import Environment, XemuTestBase


class TestXBE(XemuTestBase):
    """Runs test-xbe and validates output."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        test_data_path: Path,
    ):
        super().__init__(test_env, results_path)
        self.xemu_manager.iso_path = test_data_path / "tester.iso"
        self.xbox_results_path = "results"

    def analyze_results(self):
        results_file = self.results_path / "results.txt"
        assert results_file.read_text().strip() == "Success"
