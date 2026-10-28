# Changed-Code Coverage

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
`code_coverage_details` directory, Cobertura XML, or LCOV files (`.lcov` or
`.info`). When a report directory has no JSON reports, its XML and LCOV reports
are discovered automatically. Full LLVM exports are recommended. Regenerated
LLVM split reports retain the same function regions and provenance. Cobertura
XML and LCOV provide line coverage only; select `--metrics lines` to use them.
They cannot provide region, branch, or function checks, nor the revision and
source-hash validation available from detailed JSON. Summary-only JSON, HTML,
and raw XML are not accepted.

```zsh
# Line-only comparison against Cobertura XML and/or LCOV.
python src/git.py main --coverage build/coverage_example_output/coverage.xml --metrics lines
python src/git.py main --coverage reports/coverage.lcov --metrics lines
```

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
