# Coverage Website

The published coverage website is available at
[andrewjsender.github.io/cpp-coverage](https://andrewjsender.github.io/cpp-coverage/).

View the [example coverage](https://andrewjsender.github.io/cpp-coverage/?path=./example)
or the [source coverage for my_lib.cpp](https://andrewjsender.github.io/cpp-coverage/?path=./example/src/my_lib.cpp).

The report includes summary cards for line, function, region, and branch coverage.
Use the path table to browse into folders and files; file views also show source
lines with execution counts. The function inventory lists covered and uncovered
functions and can be filtered by status or searched by function name and file.
Source ranges can be highlighted with the `lnStart`, `colStart`, `lnEnd`, and
`colEnd` query parameters when viewing a file, for example
`?path=./example/src/my_lib.cpp&lnStart=5&colStart=1&lnEnd=6&colEnd=12`.
Selecting source text updates the address to this format so the selection can
be shared or revisited. Line positions and UTF-8 byte columns are 1-based, and
the end column is exclusive.
The source view follows LLVM's line-count semantics: counts carry across
multi-line regions, and multiple regions on a line use the maximum execution
count rather than a sum. Red source highlights mark uncovered regions, including
within otherwise covered lines; blank counts indicate non-instrumented lines.
Select an individual source report to compare it with its LLVM HTML output, or
use "All reports (summed)" to add execution counts across loaded reports (not
deduplicated coverage).
Function-level details are shown when the selected coverage report provides them
(including LLVM reports); other formats may not export this information.
LLVM report generation uses the platform's `c++filt` or `llvm-cxxfilt` executable
to add readable C++ function names to `coverage_details.json`, preserving the
original symbols. The website displays the readable names when available, with
the original symbol in a tooltip. Regenerate existing reports to populate these
names.

### Run Website Locally

```zsh
open "http://localhost:8000/website/?path=./example"
python -m http.server
```

The optional `source_root` field in `website/data/files.json` specifies the source
directory URL relative to the website page. It should end with `/`. When omitted,
the viewer retains the existing local source prefix, `../../../../`.
The Deploy Pages job copies `example/` into each published site and sets
`source_root` to `./` in the deployed metadata only, including for PR previews
(for example, `pr/4/?path=./example/src/my_lib.cpp`).

### Test the Website Viewer

With the local server running from the repository root, open
<http://localhost:8000/tests/coverage.test.html> to run the browser-based source
coverage regression tests.
