# Coverage Tools and Report Formats

This reference currently documents the LLVM/Clang workflow. Bullseye and
OpenCppCoverage documentation is TBD. The example's CMake integration is in
[example/CMakeLists.txt](../example/CMakeLists.txt); backend selection constants
are in [src/options.py](../src/options.py).

## Coverage backends

| Backend | Status | Instrumentation and input | Notes |
| --- | --- | --- | --- |
| LLVM/Clang (`llvm`) | Documented | Compile and link with `-fprofile-instr-generate -fcoverage-mapping`; collect a `.profraw` file. | Report generation uses `llvm-profdata` and `llvm-cov`. On macOS, the scripts can locate these through `xcrun`. |
| Bullseye (`bullseye`) | TBD | TBD | Documentation to be added. |
| OpenCppCoverage (`open_cpp_coverage`) | TBD | TBD | Documentation to be added. |
| gcov | Reference | See the [GCC gcov documentation](https://gcc.gnu.org/onlinedocs/gcc/Gcov.html). | Integration with this project is TBD. |
| Visual Studio | Reference | See [Microsoft Code Coverage console tool](https://learn.microsoft.com/en-us/visualstudio/test/microsoft-code-coverage-console-tool?view=visualstudio). | Integration with this project is TBD. |

The reusable report-generation dispatch is in
[src/profile.py](../src/profile.py). The standalone
[src/generate_profile.py](../src/generate_profile.py) command is used by the
LLVM example workflow; it expects `coverage.profraw` in its output directory
and requires an instrumented test executable.

## Generated files

The LLVM workflow generates:

- `coverage.profdata`: merged LLVM profile data.
- `coverage_details.json`: per-file coverage details.
- `coverage_summary.json`: summary coverage data used by the website.
- `coverage.lcov` and `coverage.xml`: interchange exports.
- `coverage_html/`: LLVM's HTML report.

Bullseye and OpenCppCoverage report formats are TBD.
The website's data layout and local viewing instructions are in
[Coverage Website](./coverage-website.md).
