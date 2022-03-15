"""Test harness for nxdk_pgraph_tests."""

import logging
import os

from pyfatx import Fatx
import test_base

log = logging.getLogger(__file__)

class TestNXDKPgraphTests(test_base.TestBase):
    """Runs the nxdk_pgraph_tests suite and validates output."""

    def __init__(self, test_env: test_base.TestEnvironment, results_path: str, test_data_path: str):
        self.config_file_path = os.path.join(test_data_path, 'config.cnf')
        if not self.config_file_path:
            raise FileNotFoundError(
                'Test data was not installed with the package. You need to copy '
                f'config.cnf to {test_data_path}.')

        iso_path = os.path.join(test_data_path, 'nxdk_pgraph_tests.iso')
        if not os.path.isfile(iso_path):
            raise FileNotFoundError('Test data was not installed with the package. You need to build it and copy '
                                    f'to {test_data_path}.')

        self.golden_results_path = os.path.join(test_data_path, "golden_results")

        timeout_seconds = 5 * 60
        super().__init__(test_env, 'nxdk_pgraph_tests', results_path, iso_path, timeout_seconds)

    def setup_hdd_files(self, fs: Fatx):
        with open(self.config_file_path, 'r') as config_file:
            config_data = config_file.read()
        fs.write('/pgraph_tests.cnf', config_data.encode('ascii'))

    def analyze_results(self):
        diff_dir = '_diffs'
        diff_results_dir = os.path.join(self.results_out_path, diff_dir)
        os.makedirs(diff_results_dir, exist_ok=True)

        failed_comparisons = {}

        for root, dirnames, files in os.walk(self.results_out_path):
            root = os.path.relpath(root, self.results_out_path)
            if diff_dir in dirnames:
                dirnames.remove(diff_dir)

            for file in files:
                file_path = os.path.join(root, file)
                expected_path = os.path.abspath(os.path.join(self.golden_results_path, file_path))
                actual_path = os.path.abspath(file_path)
                diff_path = os.path.join(diff_results_dir, file_path)

                if not os.path.isfile(expected_path):
                    log.warning(f"Missing golden image {expected_path}")
                    continue

                match, message = self.compare_images(expected_path, actual_path, diff_path)
                if not match:
                    failed_comparisons[file_path] = message

        if failed_comparisons:
            raise Exception(f"Failed comparisons: {failed_comparisons}")

    def teardown_hdd_files(self, fs: Fatx):
        try:
            fs.unlink('/pgraph_tests.cnf')
        except AssertionError:
            pass
