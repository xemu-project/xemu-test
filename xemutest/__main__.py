import argparse
import importlib
import inspect
import logging
import os
import sys

import xemutest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__file__)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('private', help='Path to private data files')
	ap.add_argument('results', help='Path to directory where results should go')
	ap.add_argument('--data', help='Path to test data (e.g., disc images)')
	ap.add_argument('--xemu', help='Path to the xemu binary')
	ap.add_argument('--ffmpeg', help='Path to the ffmpeg binary or DISABLE')
	ap.add_argument('--no-fullscreen', action='store_true', help='Force xemu to run in a window')
	args = ap.parse_args()

	tests = []
	result = True

	sys.path.append(os.path.dirname(os.path.abspath(__file__)))
	for path in os.listdir(os.path.dirname(__file__)):
		if not path.startswith("test_") or path == "test_base.py":
			continue
		if not path.endswith(".py"):
			continue

		module = importlib.import_module(path[:-3])
		for test_name, test_class in inspect.getmembers(module, inspect.isclass):
			if test_name.startswith("Test"):
				tests.append((test_name, test_class))

	results_root = os.path.abspath(os.path.expanduser(args.results))
	if args.data:
		test_data_root = os.path.expanduser(args.data)
	else:
		test_data_root = os.path.join(os.path.dirname(__file__), 'data')
	xemu_path = args.xemu
	if xemu_path:
		xemu_path = os.path.abspath(os.path.expanduser(xemu_path))

	test_env = xemutest.TestEnvironment(
		os.path.abspath(os.path.expanduser(args.private)),
		args.xemu,
		args.ffmpeg,
		args.no_fullscreen)

	for i, (test_name, test_cls) in enumerate(tests):
		log.info('Test %d', i)
		log.info('-'*40)
		
		test_results = os.path.join(results_root, test_name)
		test_data = os.path.join(test_data_root, test_name)
		try:
			test = test_cls(test_env, test_results, test_data)
		except:
			log.exception('Test %d - %s setup failed!', i, test_name)
			result = False
			continue
		try:
			test.run()
			log.info('Test %d - %s passed!', i, test_name)
		except:
			log.exception('Test %d - %s failed!', i, test_name)
			result = False

	exit(0 if result else 1)

if __name__ == '__main__':
	main()
