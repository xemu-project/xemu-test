import argparse
import importlib
import inspect
import logging
import sys
from pathlib import Path

import xemutest

log = logging.getLogger(__file__)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xemu", help="Path to the xemu binary")
    ap.add_argument("private", help="Path to private data files")
    ap.add_argument("results", help="Path to directory where results should go")
    ap.add_argument("--data", help="Path to test data (e.g., disc images)")
    ap.add_argument("--ffmpeg", help="Path to the ffmpeg binary")
    ap.add_argument(
        "--no-fullscreen", action="store_true", help="Force xemu to run in a window"
    )
    ap.add_argument("--perceptualdiff", help="Path to the perceptualdiff binary")
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Print verbose logging information"
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    this_dir = Path(__file__).resolve().parent
    xemu_path = Path(args.xemu).expanduser().resolve()
    private_path = Path(args.private).expanduser().resolve()
    test_data_root = (
        Path(args.data).expanduser().resolve() if args.data else (this_dir / "data")
    )
    ffmpeg_path = Path(args.ffmpeg).expanduser().resolve() if args.ffmpeg else None
    perceptualdiff_path = (
        Path(args.perceptualdiff).expanduser().resolve()
        if args.perceptualdiff
        else None
    )

    # Validate required paths
    errors = []
    if not xemu_path.is_file():
        errors.append(f"xemu binary not found: {xemu_path}")
    if not private_path.is_dir():
        errors.append(f"Private data directory not found: {private_path}")
    if not test_data_root.is_dir():
        errors.append(f"Test data directory not found: {test_data_root}")
    if ffmpeg_path and not ffmpeg_path.is_file():
        errors.append(f"ffmpeg binary not found: {ffmpeg_path}")
    if perceptualdiff_path and not perceptualdiff_path.is_file():
        errors.append(f"perceptualdiff binary not found: {perceptualdiff_path}")
    if errors:
        for error in errors:
            log.error(error)
        sys.exit(1)

    tests = []
    result = True

    sys.path.append(str(this_dir))
    for path in this_dir.iterdir():
        if not path.name.startswith("test_") or path.name == "test_base.py":
            continue
        if path.suffix != ".py":
            continue

        module = importlib.import_module(path.stem)
        for test_name, test_class in inspect.getmembers(module, inspect.isclass):
            if test_name.startswith("Test"):
                tests.append((test_name, test_class))

    results_root = Path(args.results).expanduser().resolve()
    results_root.mkdir(parents=True, exist_ok=True)

    test_env = xemutest.TestEnvironment(
        private_path,
        xemu_path,
        ffmpeg_path,
        perceptualdiff_path,
        args.no_fullscreen,
    )

    for i, (test_name, test_cls) in enumerate(tests):
        log.info("Test %d", i)
        log.info("-" * 40)

        test_results = results_root / test_name
        test_data = test_data_root / test_name
        try:
            test = test_cls(test_env, test_results, test_data)
        except BaseException:
            log.exception("Test %d - %s setup failed!", i, test_name)
            result = False
            continue
        try:
            test.run()
            log.info("Test %d - %s passed!", i, test_name)
        except BaseException:
            log.exception("Test %d - %s failed!", i, test_name)
            result = False

    exit(0 if result else 1)


if __name__ == "__main__":
    main()
