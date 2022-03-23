# test-pgraph

Runs the [nxdk_pgraph_tests](https://github.com/abaire/nxdk_pgraph_tests) suite and
validates the generated images against golden expectation files.

# Configuration

The subset of `nxdk_pgraph_tests` that will be executed is determined by the
`config.cnf` file in this directory. A default version of this file may be generated
using the appropriate build flag in the `nxdk_pgraph_tests` project and then copied
from the HDD. See the relevant build parameter in the Makefile to trigger config file
generation.

# Adding golden_results

Expected outputs are placed into the `golden_results` directory. It is extremely
important that the files in these directories capture the expected results,
which may be different from the output. To facilitate this, the results from
running on hardware may be used
[from this repository](https://github.com/abaire/nxdk_pgraph_tests_golden_results).

[This example script](https://gist.github.com/abaire/f566977419b3b3eb0537d3b4246de22f)
compares the output of a `xemu-test` CI run against the HW results, generating
diff files for any results that differ significantly. Note that minor,
imperceptible differences are expected, so
[perceptualdiff](https://github.com/myint/perceptualdiff) is used so that only
significant differences are flagged.
