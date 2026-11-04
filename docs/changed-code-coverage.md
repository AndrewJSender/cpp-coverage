# Changed-Code Coverage

Compare added/modified destination lines with one or more coverage details reports.
Install the CLI with `pip install cpp-coverage` (or `pip install -e .` from
a checkout):

```zsh
# Compare a branch/commit with the current tracked working tree (staged + unstaged).
coverage-analytics diff main --coverage build/coverage_example_output

# Compare two commits, or changes since the branches' merge base.
coverage-analytics diff main HEAD --coverage reports/linux reports/macos
coverage-analytics diff main...HEAD --coverage reports/linux/coverage_details.json

# Machine-readable output; --repo can select another repository.
coverage-analytics diff HEAD~1..HEAD --coverage build/coverage_example_output --format json
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
coverage-analytics diff main --coverage build/coverage_example_output/coverage.xml --metrics lines
coverage-analytics diff main --coverage reports/coverage.lcov --metrics lines
```

## Why not use diff-cover?

[diff-cover](https://pypi.org/project/diff_cover/) is a good fit for a
line-only changed-coverage check and supports common formats including Cobertura
XML and LCOV. This project uses `coverage-analytics diff` because its CI gate also checks LLVM
regions, branch outcomes, and whole functions, and validates that reports match
the destination revision and source hashes. Those checks are not provided by
diff-cover. The XML and LCOV support here is for line-only comparisons; it does
not replace the LLVM details and provenance needed for the full gate. Using
diff-cover for that mode would mean maintaining a second comparison and gate
path without replacing these project-specific checks.

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
coverage-analytics diff main...HEAD --coverage reports/linux reports/macos \
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
are attributed back to the changed lines in that function. With `--link-base`,
uncovered findings and every `gate.lines` entry also carry a `url` that opens
the coverage website with the exact source range highlighted:

```zsh
coverage-analytics diff main...HEAD --coverage build/coverage_example_output \
 --link-base "https://andrewjsender.github.io/cpp-coverage/pr/4/" --format json
```

Pass the website URL that serves this revision's reports (for example the
GitHub Pages PR preview). Region and branch findings link with column
precision; line, function, and gate findings highlight whole lines.

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
coverage-analytics diff main...HEAD --coverage build/coverage_example_output \
 --include 'example/*.cpp' --format json > diff-coverage.json
jq -e '.schema_version == 1 and .gate.uncovered == 0 and .gate.errors == 0' diff-coverage.json
```

The GitHub Actions workflow builds/tests the checked-out PR merge tree, compares
`BASE_SHA...HEAD` against that same tree, and evaluates the JSON gate for
`example/*.cpp` and `example/*.hpp`. It uploads the website and diff findings,
emits file/line annotations, and adds a job summary where each failing line
links to the Pages PR preview with the uncovered source highlighted. Coverage
generation and analysis do not fail on uncovered findings, so the preview can
deploy before enforcement. The separate **PR coverage gate** job waits for all
three platform jobs and Pages deployment, then downloads and enforces the JSON.
Failed coverage generation or deployment fails this check explicitly. For fork
PRs, Pages deployment is skipped; the gate still runs, without preview links.
Add platform/feature matrix jobs and combine their reports for conditionally
compiled code. Do not reuse profiles from a previous build: generation merges
all `coverage*.profraw` files in the output directory. Parallel tests use
`coverage-%m-%p.profraw` to avoid overwriting each other's profiles.

## Require the PR coverage gate

The workflow creates a **PR coverage gate** check for pull requests. It fails
when changed code is uncovered or coverage validation fails. To have GitHub
block merging until the gate passes:

1. Open the repository **Settings** and go to **Rules > Rulesets**.
2. Open or create a ruleset that targets the branch you want to protect.
3. Under **Require status checks to pass**, add **PR coverage gate** as a
   required check, then save the ruleset.

The check is the workflow job named **PR coverage gate**, not an individual
step. A workflow change by itself does not make this check required; the
ruleset must be updated.

For example, [PR #25](https://github.com/AndrewJSender/cpp-coverage/pull/25)
added a `failingFunction` without adding a test that covered it. The Linux,
macOS, and Windows coverage jobs and Pages deployment succeeded, but
**PR coverage gate** failed because the changed code was not covered. With the
check required by the target branch's ruleset, GitHub prevents merging that PR
until the coverage gap is addressed and the check passes.

Run the Python regression tests with:

```zsh
pip install -e .
python -m unittest discover -s tests -p 'test_*.py' -v
```
