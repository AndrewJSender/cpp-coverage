# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import contextlib
import asyncio
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from git import (
    added_lines, analyze_details, changed_lines, compare_coverage, line_counts, load_coverage,
    main, normalize_filename, run_git, source_digest,
)
from profile import adjust_json_file, split_details


class CoverageTests(unittest.TestCase):
    def test_llvm_baseline_counts(self):
        segments = [
            [7, 33, 1, True, True, False],
            [10, 9, 1, True, True, False],
            [10, 16, 1, True, False, False],
            [10, 20, 0, True, True, False],
            [10, 36, 1, True, False, False],
            [10, 38, 1, True, True, False],
            [12, 6, 0, True, False, True],
            [12, 12, 0, True, True, False],
            [14, 6, 1, True, False, False],
            [15, 1, 0, False, True, False],
            [15, 1, 1, True, False, False],
            [16, 12, 0, True, False, True],
            [17, 5, 0, True, True, False],
            [18, 2, 0, False, False, False],
            [20, 36, 0, True, True, False],
            [20, 38, 0, False, False, False],
        ]
        counts = line_counts(segments)
        self.assertEqual(list(counts.values()), [
            None, None, None, None, None, None, 1, 1, 1, 1,
            1, 1, 0, 0, None, 1, 0, 0, None, 0,
        ])

    def test_independent_line_records(self):
        self.assertEqual(line_counts([
            [2, 0, 3, True, False, False],
            [4, 0, 0, True, False, False],
        ]), {2: 3, 4: 0})
        self.assertEqual(line_counts([]), {})

    def test_invalid_segments(self):
        for segments in (
            None, [[0, 1, 0, True, True, False]],
            [[1, 1, -1, True, True, False]], [[1]],
            [[2, 1, 0, True, True, False], [1, 1, 0, True, True, False]],
        ):
            with self.subTest(segments=segments), self.assertRaises(ValueError):
                line_counts(segments)

    def test_patch_ignores_deletions_and_keeps_destination_numbers(self):
        patch = (
            "--- a/a.cpp\n+++ b/a.cpp\n"
            "@@ -2,2 +2,3 @@\n-old\n-old\n+new\n+++content\n+last\n"
            "@@ -9 +10,0 @@\n-deleted\n"
        )
        self.assertEqual(added_lines(patch), {2: "new", 3: "++content", 4: "last"})

    def test_union_and_all_classifications(self):
        changes = {"a.cpp": {1: "one", 2: "two", 3: "three"}, "b.cpp": {4: "four"}}
        result = compare_coverage(changes, {"a.cpp": [{1: 0, 2: 0}, {1: 4}]})
        self.assertEqual(result["summary"], {
            "covered": 1, "uncovered": 1, "not_instrumented": 1, "missing": 1,
        })
        self.assertEqual(result["lines"][0]["count"], 4)
        self.assertEqual(result["lines"][0]["source"], "one")

    def test_normalize_paths(self):
        self.assertEqual(normalize_filename(r"C:\work\repo\src\a.cpp", ["C:/work/repo"]), "src/a.cpp")
        self.assertEqual(normalize_filename("./src/a.cpp", []), "src/a.cpp")
        self.assertEqual(normalize_filename("/other/src/a.cpp", ["/work"]), "/other/src/a.cpp")

    def test_load_full_and_split_reports_and_reject_summaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            details = {
                "data": [{"files": [{
                    "filename": "/old/repo/a.cpp",
                    "segments": [[1, 0, 2, True, False, False]],
                }]}],
                "build_info": {"project_root": "/old/repo"},
            }
            full = root / "coverage_details.json"
            full.write_text(json.dumps(details), encoding="utf-8")
            self.assertEqual(load_coverage([root], root), {"a.cpp": [{1: 2}]})
            split = root / "split"
            split.mkdir()
            (split / "a.json").write_text(json.dumps({
                "filename": "./a.cpp", "segments": [[1, 0, 0, True, False, False]],
            }), encoding="utf-8")
            self.assertEqual(load_coverage([root, split], root), {"a.cpp": [{1: 2}, {1: 0}]})
            full.write_text(json.dumps({"data": [{"files": [{
                "filename": "a.cpp", "summary": {},
            }]}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "summary-only"):
                load_coverage([full], root)

    def test_load_cobertura_and_lcov_line_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "a.cpp"
            xml_path = repo / "coverage.xml"
            xml_path.write_text(
                f"""<?xml version="1.0"?>
                <coverage><sources><source>{repo}</source></sources><packages><package>
                  <classes><class filename="a.cpp"><lines>
                    <line number="1" hits="3"/><line number="2" hits="0"/>
                  </lines></class></classes>
                </package></packages></coverage>""",
                encoding="utf-8",
            )
            lcov_path = repo / "coverage.lcov"
            lcov_path.write_text(
                f"TN:\nSF:{source}\nDA:1,0\nDA:2,4\nend_of_record\n",
                encoding="utf-8",
            )
            evidence = []
            coverage = load_coverage([xml_path, lcov_path], repo, evidence)
            self.assertEqual(coverage, {"a.cpp": [{1: 3, 2: 0}, {1: 0, 2: 4}]})
            self.assertEqual(len(evidence), 2)
            self.assertTrue(all(report["line_only"] for report in evidence))
            discovered = load_coverage([repo], repo)
            self.assertEqual(
                sorted(discovered["a.cpp"], key=lambda report: sorted(report.items())),
                sorted(coverage["a.cpp"], key=lambda report: sorted(report.items())),
            )
            result = compare_coverage({"a.cpp": {1: "old"}}, coverage)
            self.assertEqual(result["summary"]["covered"], 1)

    def test_cobertura_resolves_source_relative_and_absolute_class_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "example" / "src").mkdir(parents=True)
            report_path = repo / "coverage.xml"
            report_path.write_text(
                f"""<coverage><sources><source>{repo}/example</source></sources>
                <packages><package><classes>
                  <class filename="src/main.cpp"><lines><line number="1" hits="1"/></lines></class>
                  <class filename="{repo}/example/src/other.cpp">
                    <lines><line number="2" hits="0"/></lines>
                  </class>
                </classes></package></packages></coverage>""",
                encoding="utf-8",
            )
            self.assertEqual(load_coverage([report_path], repo), {
                "example/src/main.cpp": [{1: 1}],
                "example/src/other.cpp": [{2: 0}],
            })

    def test_reject_malformed_cobertura_and_lcov_line_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            xml_path = root / "coverage.xml"
            xml_path.write_text("<not-coverage/>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cobertura"):
                load_coverage([xml_path], root)

            lcov_path = root / "coverage.lcov"
            lcov_path.write_text("DA:1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "before a source"):
                load_coverage([lcov_path], root)

    def test_invalid_reports_have_explicit_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "details.json"
            for data in (
                [], {"data": None}, {"data": [None]}, {"data": [{"files": [None]}]},
                {"build_info": None}, {"build_info": {"project_root": 42}},
            ):
                with self.subTest(data=data):
                    report.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_coverage([report], root)
            with self.assertRaises(ValueError):
                load_coverage([root / "missing"], root)


class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.email", "test@example.invalid")
        run_git(self.repo, "config", "user.name", "Coverage tests")
        self.source = self.repo / "file [1].cpp"
        self.source.write_text("old\nkeep\nremoved\n", encoding="utf-8")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "initial")
        self.base = run_git(self.repo, "rev-parse", "HEAD").strip()

    def details(self):
        return {
            "type": "llvm.coverage.json.export", "version": "3.0.1",
            "build_info": {
                "git_commit": self.base, "project_root": str(self.repo),
                "source_hashes": {self.source.name: source_digest(self.repo, self.source.name, None)},
            },
            "data": [{
                "files": [{
                    "filename": self.source.name,
                    "segments": [[1, 1, 1, True, True, False], [3, 8, 0, False, False, False]],
                    "branches": [[1, 1, 1, 4, 1, 0, 0, 0, 4]],
                    "expansions": [],
                }],
                "functions": [{
                    "name": "function", "count": 1, "filenames": [self.source.name],
                    "regions": [[1, 1, 3, 8, 1, 0, 0, 0], [1, 2, 1, 4, 0, 0, 0, 0]],
                }],
            }],
        }

    def test_line_only_report_metric_compatibility(self):
        report_path = self.repo / "coverage.xml"
        report_path.write_text(
            f"""<coverage><sources><source>{self.repo}</source></sources>
            <packages><package><classes><class filename="{self.source.name}">
            <lines><line number="1" hits="1"/></lines></class></classes>
            </package></packages></coverage>""",
            encoding="utf-8",
        )
        evidence = []
        coverage = load_coverage([report_path], self.repo, evidence)
        changes = {self.source.name: {1: "old"}}
        result = compare_coverage(changes, coverage)
        analyze_details(self.repo, ["HEAD"], changes, evidence, result, ["lines"], "diff")
        self.assertEqual(result["gate"]["errors"], 0)

        result = compare_coverage(changes, coverage)
        analyze_details(
            self.repo, ["HEAD"], changes, evidence, result,
            ["lines", "regions", "branches"], "diff",
        )
        self.assertEqual(result["gate"]["errors"], 1)
        self.assertIn(
            "region, branch coverage unavailable",
            result["validation"]["errors"][0]["message"],
        )

    def analyze(self, reports, changed=None, scope="diff", metrics=None):
        paths = []
        for index, report in enumerate(reports):
            path = self.repo / f"coverage-{index}.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            paths.append(path)
        changes = {self.source.name: changed or {1: "old"}}
        evidence = []
        counts = load_coverage(paths, self.repo, evidence)
        result = compare_coverage(changes, counts)
        analyze_details(self.repo, ["HEAD"], changes, evidence, result,
                        metrics or ["lines", "regions", "branches"], scope)
        return result

    def test_regions_and_branches_fail_a_covered_line_without_double_counting(self):
        result = self.analyze([self.details()])
        self.assertEqual(result["summary"]["uncovered"], 0)
        self.assertEqual(result["metrics"]["regions"]["uncovered"], 1)
        self.assertEqual(result["metrics"]["branches"]["uncovered"], 1)
        self.assertEqual(result["gate"]["uncovered"], 1)
        self.assertEqual(result["gate"]["errors"], 0)
        self.assertEqual(len(result["gate"]["lines"][0]["reasons"]), 2)

    def test_matching_regions_and_branch_outcomes_union_across_reports(self):
        first = self.details()
        second = self.details()
        second["data"][0]["functions"][0]["regions"][1][4] = 1
        second["data"][0]["files"][0]["branches"][0][4:6] = [0, 1]
        result = self.analyze([first, second])
        self.assertEqual(result["gate"]["uncovered"], 0)
        self.assertEqual(len(result["branches"]), 1)
        self.assertEqual(result["branches"][0]["true_count"], 1)
        self.assertEqual(result["branches"][0]["false_count"], 1)

    def test_multiple_exports_in_one_report_combine_branch_outcomes(self):
        report = self.details()
        other = self.details()["data"][0]
        other["files"][0]["branches"][0][4:6] = [0, 1]
        other["functions"][0]["regions"][1][4] = 1
        report["data"].append(other)
        self.assertEqual(self.analyze([report])["gate"]["uncovered"], 0)

    def test_revision_hash_version_and_capability_errors_fail_closed(self):
        for defect in ("commit", "hash", "version", "functions", "branches", "expansions"):
            with self.subTest(defect=defect):
                report = self.details()
                if defect == "commit":
                    report["build_info"]["git_commit"] = "wrong"
                elif defect == "hash":
                    report["build_info"]["source_hashes"] = {}
                elif defect == "version":
                    report["version"] = "99.0.0"
                elif defect == "functions":
                    del report["data"][0]["functions"]
                elif defect == "branches":
                    del report["data"][0]["files"][0]["branches"]
                else:
                    del report["data"][0]["files"][0]["expansions"]
                result = self.analyze([report])
                self.assertGreater(result["gate"]["errors"], 0)
                self.assertEqual(result["gate"]["uncovered"], 1)

    def test_whole_function_mode_attributes_unchanged_gaps_to_changed_line(self):
        self.assertEqual(self.analyze([self.details()], {2: "keep"})["gate"]["uncovered"], 0)
        result = self.analyze([self.details()], {2: "keep"}, scope="functions")
        self.assertEqual(result["gate"]["uncovered"], 1)
        self.assertEqual(result["gate"]["lines"][0]["line"], 2)
        self.assertEqual(len(result["function_lines"]), 3)

    def test_missing_is_gate_failure_but_uninstrumented_lines_are_separate(self):
        report = self.details()
        file = report["data"][0]["files"][0]
        file["segments"] = []
        file["branches"] = []
        report["data"][0]["functions"] = []
        result = self.analyze([report])
        self.assertEqual(result["summary"]["not_instrumented"], 1)
        self.assertEqual(result["gate"]["uncovered"], 0)
        file["filename"] = "other.cpp"
        result = self.analyze([report])
        self.assertEqual(result["summary"]["missing"], 1)
        self.assertEqual(result["gate"]["uncovered"], 1)

    def test_regions_exclude_gaps_and_end_column_one_does_not_touch_next_line(self):
        report = self.details()
        report["data"][0]["functions"][0]["regions"] = [
            [1, 1, 2, 1, 0, 0, 0, 0],
            [2, 1, 2, 3, 0, 0, 0, 3],
        ]
        result = self.analyze([report], {2: "keep"}, metrics=["regions"])
        self.assertEqual(result["regions"], [])
        self.assertEqual(result["gate"]["uncovered"], 0)

    def test_provenance_and_split_generation_preserve_evidence(self):
        report = self.details()
        path = self.repo / "coverage_details.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        asyncio.run(adjust_json_file(path, report["build_info"]))
        asyncio.run(split_details(path))
        split_path = self.repo / "code_coverage_details" / (self.source.name + ".json")
        split = json.loads(split_path.read_text())
        self.assertEqual(split["build_info"]["source_hashes"], report["build_info"]["source_hashes"])
        self.assertEqual(split["functions"], report["data"][0]["functions"])
        self.assertEqual(split["version"], "3.0.1")
        evidence = []
        load_coverage([split_path], self.repo, evidence)
        result = compare_coverage({self.source.name: {1: "old"}}, load_coverage([split_path], self.repo))
        analyze_details(self.repo, ["HEAD"], {self.source.name: {1: "old"}}, evidence, result,
                        ["lines", "regions", "branches"], "diff")
        self.assertEqual(result["gate"]["errors"], 0)

    def test_split_generation_preserves_duplicate_exports_and_only_their_hash(self):
        report = self.details()
        report["build_info"]["source_hashes"]["other.cpp"] = "unused"
        second_export = self.details()["data"][0]
        second_export["files"][0]["segments"][0][2] = 0
        report["data"].append(second_export)
        path = self.repo / "coverage_details.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        asyncio.run(split_details(path))

        split_paths = sorted((self.repo / "code_coverage_details").glob("*.json"))
        self.assertEqual(len(split_paths), 2)
        self.assertEqual(
            [json.loads(split_path.read_text())["build_info"]["source_hashes"]
             for split_path in split_paths],
            [{self.source.name: report["build_info"]["source_hashes"][self.source.name]}] * 2,
        )
        changes = {self.source.name: {1: "old"}}
        full_evidence = []
        full = compare_coverage(changes, load_coverage([path], self.repo, full_evidence))
        analyze_details(
            self.repo, ["HEAD"], changes, full_evidence, full,
            ["lines", "regions", "branches"], "diff",
        )
        split_evidence = []
        split = compare_coverage(
            changes,
            load_coverage([self.repo / "code_coverage_details"], self.repo, split_evidence),
        )
        analyze_details(
            self.repo, ["HEAD"], changes, split_evidence, split,
            ["lines", "regions", "branches"], "diff",
        )
        self.assertEqual(full, split)
        self.assertEqual(split["summary"]["covered"], 1)

    def test_source_hash_uses_git_cleaned_bytes_but_detects_edits(self):
        run_git(self.repo, "config", "core.autocrlf", "true")
        self.source.write_bytes(b"old\r\nkeep\r\nremoved\r\n")
        report = self.details()
        path = self.repo / "coverage_details.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        asyncio.run(adjust_json_file(path, report["build_info"]))
        adjusted = json.loads(path.read_text())
        blob = subprocess.run(
            ["git", "-C", str(self.repo), "show", f"{self.base}:{self.source.name}"],
            check=True, capture_output=True,
        ).stdout
        self.assertEqual(
            adjusted["build_info"]["source_hashes"][self.source.name],
            hashlib.sha256(blob).hexdigest(),
        )

        self.source.write_bytes(b"edited\r\nkeep\r\nremoved\r\n")
        asyncio.run(adjust_json_file(path, adjusted["build_info"]))
        evidence = []
        counts = load_coverage([path], self.repo, evidence)
        result = compare_coverage({self.source.name: {1: "old"}}, counts)
        analyze_details(
            self.repo, [self.base, self.base], {self.source.name: {1: "old"}},
            evidence, result, ["lines"], "diff",
        )
        self.assertEqual(result["gate"]["errors"], 1)

    def test_include_exclude_and_success_exit_for_uncovered_gate(self):
        self.source.write_text("changed\nkeep\nremoved\n", encoding="utf-8")
        report = self.details()
        path = self.repo / "details.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        for patterns, expected in (([], 1), (["--exclude", "*.cpp"], 0),
                                   (["--include", "*.hpp"], 0), (["--include", "*.cpp"], 1)):
            with self.subTest(patterns=patterns):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(["HEAD", "--coverage", str(path), "--repo", str(self.repo),
                                   "--format", "json", *patterns])
                self.assertEqual(status, 0)
                self.assertEqual(json.loads(output.getvalue())["gate"]["uncovered"], expected)

    def test_reject_duplicate_and_malformed_branch_inputs(self):
        path = self.repo / "details.json"
        path.write_text(json.dumps(self.details()), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_coverage([path, path], self.repo)
        report = self.details()
        report["data"][0]["files"][0]["branches"] = [[1]]
        with self.assertRaisesRegex(ValueError, "Invalid coverage region"):
            self.analyze([report])

    def test_macro_invocation_checks_expanded_regions_and_branches(self):
        report = self.details()
        report["data"][0]["files"][0]["expansions"] = [{
            "source_region": [2, 1, 2, 4, 1, 0, 1, 1],
            "filenames": [self.source.name, "macro.hpp"],
            "target_regions": [[20, 1, 20, 8, 0, 1, 0, 0]],
            "branches": [[20, 2, 20, 5, 1, 0, 1, 0, 4]],
        }]
        result = self.analyze([report], {2: "keep"})
        self.assertEqual(result["gate"]["uncovered"], 1)
        expanded = [region for region in result["regions"] if "definition_file" in region]
        self.assertEqual(expanded[0]["definition_file"], "macro.hpp")
        self.assertEqual(result["branches"][0]["changed_lines"], [2])

    def test_target_commit_hash_is_not_taken_from_worktree(self):
        report = self.details()
        path = self.repo / "coverage.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        self.source.write_text("dirty worktree\n", encoding="utf-8")
        evidence = []
        counts = load_coverage([path], self.repo, evidence)
        changes = {self.source.name: {1: "old"}}
        result = compare_coverage(changes, counts)
        analyze_details(self.repo, [self.base, self.base], changes, evidence, result,
                        ["lines"], "diff")
        self.assertEqual(result["gate"]["errors"], 0)

    def test_worktree_and_staged_changes_exclude_untracked_files(self):
        self.source.write_text("changed\nkeep\n", encoding="utf-8")
        new = self.repo / "new ü.cpp"
        new.write_text("new\n", encoding="utf-8")
        run_git(self.repo, "add", ".")
        new.write_text("new\nunstaged\n", encoding="utf-8")
        (self.repo / "untracked.cpp").write_text("untracked\n", encoding="utf-8")
        self.assertEqual(changed_lines(self.repo, ["HEAD"]), {
            "file [1].cpp": {1: "changed"}, "new ü.cpp": {1: "new", 2: "unstaged"},
        })

    def test_two_refs_ranges_and_deleted_files(self):
        self.source.unlink()
        (self.repo / "new.cpp").write_text("new\n", encoding="utf-8")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "change")
        for revisions in ([self.base, "HEAD"], [f"{self.base}..HEAD"], [f"{self.base}...HEAD"]):
            with self.subTest(revisions=revisions):
                self.assertEqual(changed_lines(self.repo, revisions), {"new.cpp": {1: "new"}})

    def test_three_dot_uses_merge_base(self):
        run_git(self.repo, "checkout", "-qb", "base-branch")
        self.source.write_text("base branch\nkeep\nremoved\n", encoding="utf-8")
        run_git(self.repo, "commit", "-qam", "base branch")
        run_git(self.repo, "checkout", "-qb", "topic", self.base)
        (self.repo / "topic.cpp").write_text("topic\n", encoding="utf-8")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "topic")
        self.assertEqual(changed_lines(self.repo, ["base-branch...HEAD"]), {"topic.cpp": {1: "topic"}})

    def test_cli_json_and_error_exit(self):
        self.source.write_text("changed\nkeep\nremoved\n", encoding="utf-8")
        report = self.repo / "details.json"
        report.write_text(json.dumps({
            "filename": self.source.name,
            "segments": [[1, 0, 4, True, False, False]],
        }), encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main([
                "HEAD", "--coverage", str(report), "--repo", str(self.repo), "--format", "json",
            ]), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["summary"]["covered"], 1)
        self.assertEqual(result["lines"][0]["line"], 1)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["invalid-ref", "--coverage", str(report), "--repo", str(self.repo)])
        self.assertEqual(error.exception.code, 2)

    def test_no_changes_and_binary_changes_have_no_lines(self):
        self.assertEqual(changed_lines(self.repo, ["HEAD"]), {})
        (self.repo / "binary").write_bytes(b"\0binary")
        run_git(self.repo, "add", ".")
        self.assertEqual(changed_lines(self.repo, ["HEAD"]), {})

    def test_rename_is_an_addition(self):
        destination = self.repo / "renamed.cpp"
        self.source.rename(destination)
        run_git(self.repo, "add", ".")
        self.assertEqual(changed_lines(self.repo, ["HEAD"]), {
            "renamed.cpp": {1: "old", 2: "keep", 3: "removed"},
        })


if __name__ == "__main__":
    unittest.main()
