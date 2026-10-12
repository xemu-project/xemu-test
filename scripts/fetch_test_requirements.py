#!/usr/bin/env python3

# ruff: noqa: T201 `print` found
# ruff: noqa: S310 Audit URL open for permitted schemes.

"""
Downloads and prepares test artifacts for xemutest.
Used by both Dockerfile and GitHub Actions runners.
"""

import sys
import urllib.request
from pathlib import Path

NV2A_TAG = "v2026-10-14_14-04-36-282794375"
NV2A_TESTS = [
    "m2mf_test_xiso",
]

CPU_TAG = "v2026-10-14_14-16-39-135792892"
CPU_TESTS = [
    "fpu_test_xiso",
    "mmx_test_xiso",
    "sse_test_xiso",
    "testfloat_test_xiso",
]


def _download_file(url: str, dest_path: Path, tag: str):
    version_file = dest_path.parent / ".version"
    if dest_path.exists() and version_file.exists():
        if version_file.read_text().strip() == tag:
            print(f"[Up-to-date] {dest_path}")
            return
        print(f"[Out-of-date] {dest_path} (updating to {tag})")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[Download] {url} -> {dest_path}")
    urllib.request.urlretrieve(url, dest_path)
    version_file.write_text(tag)


def _to_camel_case(snake_str: str) -> str:
    return "".join(part.capitalize() for part in snake_str.split("_"))


def main():
    target_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data").resolve()

    for test in NV2A_TESTS:
        url = f"https://github.com/abaire/nxdk_low_level_nv2a_tests/releases/download/{NV2A_TAG}/{test}.iso"
        dest_dir = target_dir / f"TestNxdkLowLevelNV2ATests__{_to_camel_case(test)}"
        _download_file(url, dest_dir / f"{test}.iso", NV2A_TAG)

    for test in CPU_TESTS:
        url = f"https://github.com/abaire/nxdk_low_level_cpu_tests/releases/download/{CPU_TAG}/{test}.iso"
        dest_dir = target_dir / f"TestNxdkLowLevelCPUTests__{_to_camel_case(test)}"
        _download_file(url, dest_dir / f"{test}.iso", CPU_TAG)


if __name__ == "__main__":
    main()
