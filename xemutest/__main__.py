import argparse
import importlib
import inspect
import logging
import os


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__file__)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('private', help='Path to private data files')
	ap.add_argument('results', help='Path to directory where results should go')
	ap.add_argument('--data', help='Path to test data (e.g., disc images)')
	ap.add_argument('--xemu', help='Path to the xemu binary')
	args = ap.parse_args()

	tests = []
	result = True
	for path in os.listdir(os.path.dirname(__file__)):
		if not path.startswith("test_") or path == "test_base.py":
			continue
		if not path.endswith(".py"):
			continue

		module = importlib.import_module(path[:-3])
		for test_name, test_class in inspect.getmembers(module, inspect.isclass):
			if test_name.startswith("Test"):
				tests.append((test_name, test_class))

	private_path = os.path.abspath(os.path.expanduser(args.private))
	results_base = os.path.abspath(os.path.expanduser(args.results))
	if args.data:
		test_data_root = os.path.expanduser(args.data)
	else:
		test_data_root = os.path.join(os.path.dirname(__file__), 'data')
	xemu_path = args.xemu
	if xemu_path:
		xemu_path = os.path.abspath(os.path.expanduser(xemu_path))
	for i, (test_name, test_cls) in enumerate(tests):
		log.info('Test %d', i)
		log.info('-'*40)
		
		test_results = os.path.join(results_base, test_name)
		test_data = os.path.join(test_data_root, test_name)
		try:
			test = test_cls(private_path, test_results, test_data, xemu_path)
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
