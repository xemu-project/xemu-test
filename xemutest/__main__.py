import logging
import argparse

from xemutest import Test


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__file__)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('private', help='Path to private data files')
	ap.add_argument('results', help='Path to directory where results should go')
	args = ap.parse_args()

	result = True
	tests = [Test]
	for i, test_cls in enumerate(tests):
		log.info('Test %d', i)
		log.info('-'*40)
		try:
			test_cls(args.private, args.results).run()
			log.info('Test %d passed!', i)
		except:
			log.exception('Test %d failed!', i)
			result = False

	exit(0 if result else 1)

if __name__ == '__main__':
	main()
