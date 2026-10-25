# C++ Code Coverage

A small coverage tooling project for generating coverage reports and a static website view from test outputs.

## Overview

This project reads coverage artifacts from tools such as LLVM, Bullseye, and OpenCppCoverage, converts them into a consistent summary format, and generates a local website for exploring the results.

## Example

The example builds a single `coverage_example` executable from `example/src/main.cpp`.

### Constants
```zsh
export root_path=$(pwd)
```

### Setup with Clang Code Coverage

Note: Generates the Xcode project for macOS.

```zsh
export root_path=$(pwd)
cmake -G Xcode -S "$root_path/example" -B "$root_path/build" \
 -DENABLE_COVERAGE=ON \
 -DCOVERAGE_TOOL=llvm
```

### CMake Build, Test, Generate Coverage Data

```zsh
export root_path=$(pwd)
cmake --build "$root_path/build" --target generate_profile_data
```

### Build, Test, Generate Step-by-Step

#### Select Target

```zsh
export target="coverage_example"
```

#### Build by Xcode

```zsh
xcodebuild -project "$root_path/build/test_example.xcodeproj" -scheme "$target"
```

#### Build by CMake

```zsh
cmake --build "$root_path/build" --target "$target"
```

#### Test

```zsh
export test_output_path="$root_path/build/$target""_output"
export LLVM_PROFILE_FILE="$test_output_path/coverage.profraw"
"$root_path/build/Debug/$target"
```

#### Generate Profile & Website

```zsh
python src/generate_profile.py \
 --test-binary="$root_path/build/Debug/$target" \
 --output-directory="$test_output_path"
```

## Coverage of Git Changes

Compare added/modified destination lines with one or more coverage details reports:

```zsh
# Compare a branch/commit with the current tracked working tree (staged + unstaged).
python src/git.py main --coverage build/coverage_example_output

# Compare two commits, or changes since the branches' merge base.
python src/git.py main HEAD --coverage reports/linux reports/macos
python src/git.py main...HEAD --coverage reports/linux/coverage_details.json

# Machine-readable output; --repo can select another repository.
python src/git.py HEAD~1..HEAD --coverage build/coverage_example_output --format json
```

Inputs accept LLVM `coverage_details.json`, an individual split file JSON, a
`code_coverage_details` directory, or a report directory containing either.
Full LLVM exports are recommended. Regenerated LLVM split reports retain the
same function regions and provenance. Split JSON reports produced from Cobertura
can provide line counts, but cannot satisfy region/branch checks if those details
are unavailable. Summary-only reports, HTML, LCOV, and raw XML are not accepted.

Each changed line is labeled `covered` (positive count in any report), `uncovered`
(instrumented but zero hits in all reports), `not_instrumented` (the file is in a
report, but no report maps that line), or `missing` (no report contains the file).
Execution counts are summed across inputs; duplicate report paths are rejected.
LLVM counts follow the same region/line semantics as the website.

By default, `--metrics lines regions branches` checks executable changed lines,
code regions intersecting changed lines, and both outcomes of intersecting
branches. Regions and branch outcomes are combined by source location across
reports, not by averaging coverage percentages. Macro invocation checks include
expanded regions and branches. Changes to a multi-line region/condition check
the entire intersecting region/condition. Use `--metrics lines` for line-only
inputs, or `--scope functions` to check the complete functions containing changes,
including otherwise unchanged regions, branches, and instrumented lines.

```zsh
python src/git.py main...HEAD --coverage reports/linux reports/macos \
 --include 'example/*.cpp' --include 'example/*.hpp' \
 --exclude 'example/generated/*' --scope functions --format json
```

Include/exclude patterns are repository-relative, case-sensitive `fnmatch` globs;
`*` matches path separators too. Options are repeatable; exclusions win.
Scope these explicitly to the languages and targets your reports instrument.
Review any exclusion as a coverage exception, rather than automatically exempting
zero-hit code.

Deleted lines, binary changes, submodules, and untracked files have no destination
lines to analyze and are excluded. Renames are treated as deletion plus addition.
Reports must describe the destination revision being compared. Generation records
`build_info.git_commit` and per-file `source_hashes` (SHA-256). The analyzer checks
both against the destination commit's blobs, or HEAD plus current file bytes for
working-tree comparisons. Missing metadata, stale hashes/revisions, unsupported
LLVM export versions, and unavailable requested metrics are validation failures.
Regenerate older reports to populate metadata. It does not remap stale line numbers.
Hashes attest to source present at export time, not to compiler inputs: CI must
build and run fresh binaries for that exact tree before exporting.
Absolute report paths
are relativized using `build_info.project_root` or the selected repository root.
Other absolute paths remain unmatched rather than guessing by basename.

JSON schema version 1 preserves `summary` and `lines` (line-only classifications)
and adds `regions`, `branches`, `functions`, `function_lines`, per-metric totals,
the comparison/policy, validation errors, and `gate`. Each region/branch finding
includes source coordinates and the changed lines affected. Whole-function gaps
are attributed back to the changed lines in that function.

**CI should block when `gate.uncovered > 0`.** This is the number of unique changed
lines failing any selected metric, missing file coverage, or evidence validation.
It is intentionally different from `summary.uncovered`, which counts only
zero-hit lines. `gate.lines` explains each failure; `gate.errors` also counts
validation errors. `not_instrumented` lines alone do not fail: comments, declarations,
and blank lines have no counters. LLVM cannot distinguish these from executable
code omitted by preprocessing or incomplete instrumentation; build all relevant
targets/configurations and review missing instrumentation. Function instantiations
at identical source ranges are combined; MC/DC and exhaustive path coverage are
not enforced.

Successful analysis exits with 0 regardless of gate findings. Invalid Git refs,
unreadable reports, or malformed data still exit with 2; CI must not ignore that.
For example:

```zsh
python src/git.py main...HEAD --coverage build/coverage_example_output \
 --include 'example/*.cpp' --format json > diff-coverage.json
jq -e '.schema_version == 1 and .gate.uncovered == 0 and .gate.errors == 0' diff-coverage.json
```

The GitHub Actions workflow builds/tests the checked-out PR merge tree, compares
`BASE_SHA...HEAD` against that same tree, and evaluates the JSON gate for
`example/*.cpp` and `example/*.hpp`. It uploads the website and diff findings,
emits file/line annotations, and adds a job summary. Configure the **MacOS Build,
Run Tests, and Generate Coverage Data** check as required in repository branch
protection/rulesets; workflow edits alone do not configure that administrative rule.
Add platform/feature matrix jobs and combine their reports for conditionally
compiled code. Do not reuse profiles from a previous build: generation merges
all `coverage*.profraw` files in the output directory. Parallel tests use
`coverage-%m-%p.profraw` to avoid overwriting each other's profiles.

Run the Python regression tests with:

```zsh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

## View Coverage Website

The published coverage website is available at
[andrewjsender.github.io/cpp-coverage](https://andrewjsender.github.io/cpp-coverage/).

View the [example coverage](https://andrewjsender.github.io/cpp-coverage/?path=./example)
or the [source coverage for my_lib.cpp](https://andrewjsender.github.io/cpp-coverage/?path=./example/src/my_lib.cpp).

The report includes summary cards for line, function, region, and branch coverage.
Use the path table to browse into folders and files; file views also show source
lines with execution counts. The function inventory lists covered and uncovered
functions and can be filtered by status or searched by function name and file.
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

## License

Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
