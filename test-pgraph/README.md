# test-pgraph

Runs the [nxdk_pgraph_tests](https://github.com/abaire/nxdk_pgraph_tests) suite and
validates the generated images against golden expectation files.

# Configuration

The subset of `nxdk_pgraph_tests` that will be executed is determined by the
`config.cnf` file in this directory. A default version of this file may be generated
using the appropriate build flag in the `nxdk_pgraph_tests` project and then copied
from the HDD. See the relevant build parameter in the Makefile to trigger config file
generation.
