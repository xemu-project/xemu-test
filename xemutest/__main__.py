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
    ap.add_argument("private", help="Path to private data files")
    ap.add_argument("results", help="Path to directory where results should go")
    ap.add_argument("--data", help="Path to test data (e.g., disc images)")
    ap.add_argument("--xemu", help="Path to the xemu binary")
    ap.add_argument("--ffmpeg", help="Path to the ffmpeg binary or DISABLE")
    ap.add_argument(
        "--no-fullscreen", action="store_true", help="Force xemu to run in a window"
    )
    ap.add_argument(
        "--perceptualdiff", help="Path to the perceptualdiff binary or DISABLE"
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Print verbose logging information"
    )
    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    tests = []
    result = True

    this_dir = Path(__file__).resolve().parent
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

    log_file_name = results_root / "xemutest.log"
    logging.basicConfig(filename=str(log_file_name), filemode="w", level=logging.INFO)

    if args.data:
        test_data_root = Path(args.data).expanduser()
    else:
        test_data_root = this_dir / "data"
    xemu_path = args.xemu
    if xemu_path:
        xemu_path = Path(xemu_path).expanduser().resolve()

    test_env = xemutest.TestEnvironment(
        Path(args.private).expanduser().resolve(),
        xemu_path,
        args.ffmpeg,
        args.perceptualdiff,
        args.no_fullscreen,
    )

    for i, (test_name, test_cls) in enumerate(tests):
        log.info("Test %d", i)
        log.info("-" * 40)

        test_results = results_root / test_name
        test_data = test_data_root / test_name
        try:
            test = test_cls(test_env, test_results, test_data)
        except:
            log.exception("Test %d - %s setup failed!", i, test_name)
            result = False
            continue
        try:
            test.run()
            log.info("Test %d - %s passed!", i, test_name)
        except:
            log.exception("Test %d - %s failed!", i, test_name)
            result = False

    exit(0 if result else 1)


if __name__ == "__main__":
    main()
