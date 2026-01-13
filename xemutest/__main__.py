import argparse
import importlib
import inspect
import logging
import sys
from pathlib import Path

from xemutest import Environment, TestBase
from xemutest import ci

log = logging.getLogger(__name__)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xemu", help="Path to the xemu binary")
    ap.add_argument("private", help="Path to private data files")
    ap.add_argument("results", help="Path to directory where results should go")
    ap.add_argument("--ffmpeg", help="Path to the ffmpeg binary")
    ap.add_argument("--perceptualdiff", help="Path to the perceptualdiff binary")
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Print verbose logging information"
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger("pyfatx").setLevel(logging.WARNING)

    # Add GitHub Actions annotation handler for warnings/errors
    if ci.is_github_actions():
        logging.getLogger().addHandler(ci.GitHubActionsHandler())

    this_dir = Path(__file__).resolve().parent
    xemu_path = Path(args.xemu).expanduser().resolve()
    private_path = Path(args.private).expanduser().resolve()
    test_data_root = this_dir / "data"
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

    tests_dir = this_dir / "tests"
    sys.path.append(str(tests_dir))
    for path in tests_dir.iterdir():
        if not path.name.startswith("test_") or path.suffix != ".py":
            continue

        module = importlib.import_module(path.stem)
        for test_name, test_class in inspect.getmembers(module, inspect.isclass):
            if (
                test_name.startswith("Test")
                and issubclass(test_class, TestBase)
                and test_class is not TestBase
            ):
                tests.append((test_name, test_class))

    results_root = Path(args.results).expanduser().resolve()
    results_root.mkdir(parents=True, exist_ok=True)

    test_env = Environment(
        private_path,
        xemu_path,
        ffmpeg_path,
        perceptualdiff_path,
    )

    test_results_summary: dict[str, bool] = {}

    for i, (test_name, test_cls) in enumerate(tests):
        test_results = results_root / test_name
        test_data = test_data_root / test_name
        with ci.log_group(f"Test {i}: {test_name}"):
            try:
                log.info("Test %d - %s: Starting", i, test_name)
                test = test_cls(test_env, test_results, test_data)
                test.run()
                log.info("Test %d - %s: Finished", i, test_name)
                test_results_summary[test_name] = True
            except BaseException:
                log.exception("Test %d - %s: Failed", i, test_name)
                test_results_summary[test_name] = False
                result = False

    # Write job summary for GitHub Actions
    if ci.is_github_actions():
        summary = ci.JobSummary()
        summary.add_heading("xemu Test Results")
        summary.add_table(
            headers=["Test", "Status"],
            rows=[
                [name, "✅ Passed" if passed else "❌ Failed"]
                for name, passed in test_results_summary.items()
            ],
        )
        summary.write()

    exit(0 if result else 1)


if __name__ == "__main__":
    main()
