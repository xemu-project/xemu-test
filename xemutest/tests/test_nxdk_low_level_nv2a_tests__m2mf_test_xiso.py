"""Test harness for test-xbe."""

# ruff: noqa: N801 Class name should use CapWords convention

import logging
from pathlib import Path

from xemutest import Environment
from xemutest.tests.nxdk_low_level_nv2a_tests import NxdkLowLevelNV2ATestsBase

logger = logging.getLogger(__name__)


class TestNxdkLowLevelNV2ATests__M2mfTestXiso(NxdkLowLevelNV2ATestsBase):
    """Runs m2mf_test_xiso and validates output."""

    def __init__(
        self,
        test_env: Environment,
        results_path: Path,
        test_data_path: Path,
    ):
        super().__init__(
            test_env,
            results_path,
            test_data_path,
            Path("m2mf_test_xiso.iso"),
            timeout_seconds=30,
        )
