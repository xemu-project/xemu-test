xemu Automated Testing
======================

Performs a suite of tests against a build of xemu, capturing test results and
footage of the runs. Primarily used for CI testing of xemu.

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
