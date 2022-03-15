"""Test harness for test-xbe."""

import os
from typing import Optional

import test_base

class TestXBE(test_base.TestBase):
    """Runs test-xbe and validates output."""

    def __init__(self, private_path: str, results_path: str, test_data_path: str, xemu_path: Optional[str]):
        iso_path = os.path.join(test_data_path, 'tester.iso')
        if not os.path.isfile(iso_path):
            raise FileNotFoundError('Test data was not installed with the package. You need to build it and copy '
                                    f'to {test_data_path}.')

        super().__init__(private_path, results_path, iso_path, xemu_path)

    def analyze_results(self):
        with open(os.path.join(self.results_out_path, 'results.txt')) as f:
            assert(f.read().strip() == 'Success')
