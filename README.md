xemu Automated Testing
======================

Performs a suite of tests against a build of xemu, capturing test results and
footage of the runs. Currently that suite consists of 1 test: boot to a custom
executable that writes a file to the disk. This is a useful test, but
there are many tests left to add, and you can help! Pull requests welcome.

This is primarily used for automated testing of xemu pull requests. The xemu CI
system uses this repository for testing. The goal is to have a large set of
tests that can exercise xemu across a varienty of different platforms/hardware
configurations for every change made to xemu. See GitHub Issues on this
repository for list of areas that need attention.

Containerized Testing
---------------------
This testing system is intended to be able to be run inside a container for
reproducability and for regular testing on cheap cloud VMs.

To build the container image:

	docker build -t xemu-test .

This repository also has GitHub actions set up to automatically build and
publish the container image to the GitHub container registry, so you can pull
that image for testing:

	docker pull ghcr.io/mborgerson/xemu-test:master

Set up the following dir structure:

- /work/results: Results will be copied here
- /work/private: Directory for ROMs and other files
  - /work/private/mcpx.bin
  - /work/private/bios.bin
- /work/inputs: Directory containing xemu build to test
  - /work/xemu.deb

Then run with something like:

	docker run --rm -it \
		-v $PWD/results:/work/results \
		-v $PWD/private:/work/private \
		-v $PWD/inputs:/work/inputs \
		-p 5900:5900 \
		ghcr.io/mborgerson/xemu-test:master

xemu is running headless when in the container, so if you need to interact with
it you can connect to the container VNC server with:

	xtightvncviewer 127.0.0.1

Native Testing
--------------
Containers are a great solution generally, but they aren't available on every
platform that xemu runs on. The tester can be run outside of a container,
provided you have set up the environment correctly. It is a goal for this project
to support running the tests natively on all platforms.
