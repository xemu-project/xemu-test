"""Test harness for test-xbe."""

import os

import test_base

class TestXBE(test_base.TestBase):
    """Runs test-xbe and validates output."""

    def __init__(self, test_env: test_base.TestEnvironment, results_path: str, test_data_path: str):
        iso_path = os.path.join(test_data_path, 'tester.iso')
        if not os.path.isfile(iso_path):
            raise FileNotFoundError('Test data was not installed with the package. You need to build it and copy '
                                    f'to {test_data_path}.')

        super().__init__(test_env, 'results', results_path, iso_path)

    def analyze_results(self):
        with open(os.path.join(self.results_out_path, 'results.txt')) as f:
            assert(f.read().strip() == 'Success')
