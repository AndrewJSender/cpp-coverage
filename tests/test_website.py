# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import asyncio
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from coverage_analytics.archived.website import (
    copy_local_data,
    function_declarator,
    generate_function_manifest,
    generate_website,
    split_function_scope,
    update_file_manifest,
    update_function_manifest,
)


class StubContext:
    def __init__(self, test_output_directory: Path):
        self.args = {"test_output_directory": str(test_output_directory)}

    async def copy(self, source: Path, destination: Path) -> None:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)


class UpdateFileManifestTests(unittest.TestCase):
    def test_nests_files_by_directory(self):
        manifest = {".": {}, "files": {}}
        root = Path("/repo")
        update_file_manifest(manifest, root, Path("/repo/example/src"), "main.cpp")
        self.assertEqual(
            manifest["."]["example"]["src"]["files"],
            {"main.cpp": "./example/src/main.cpp"},
        )

    def test_skips_finder_metadata(self):
        manifest = {".": {}, "files": {}}
        update_file_manifest(manifest, Path("/repo"), Path("/repo/example"), ".DS_Store")
        self.assertEqual(manifest["."], {})


class GenerateWebsiteTests(unittest.TestCase):
    def test_writes_files_json_for_sources(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "example" / "src").mkdir(parents=True)
        (root / "example" / "src" / "main.cpp").write_text("int main() {}")
        website_data = root / "website" / "data"

        asyncio.run(generate_website(None, ["example"], root, website_data))

        manifest = json.loads((website_data / "files.json").read_text())
        self.assertEqual(
            manifest["."]["example"]["src"]["files"],
            {"main.cpp": "./example/src/main.cpp"},
        )


class SplitFunctionScopeTests(unittest.TestCase):
    def test_splits_on_scope_separators(self):
        self.assertEqual(
            split_function_scope("CoverageClass::functionCovered()"),
            ["CoverageClass", "functionCovered()"],
        )
        self.assertEqual(split_function_scope("main"), ["main"])
        self.assertEqual(
            split_function_scope("outer::inner::call()"),
            ["outer", "inner", "call()"],
        )

    def test_ignores_separators_inside_nesting(self):
        self.assertEqual(
            split_function_scope("std::vector<std::pair<int, int>>::size()"),
            ["std", "vector<std::pair<int, int>>", "size()"],
        )
        self.assertEqual(
            split_function_scope("ns::compare(std::pair<int, int> const&)"),
            ["ns", "compare(std::pair<int, int> const&)"],
        )
        self.assertEqual(
            split_function_scope("(anonymous namespace)::helper()"),
            ["(anonymous namespace)", "helper()"],
        )

    def test_strips_return_types_from_function_scopes(self):
        self.assertEqual(function_declarator("void ns::helper<int>()"), "ns::helper<int>()")
        self.assertEqual(
            function_declarator("unsigned long ns::helper<int>()"),
            "ns::helper<int>()",
        )
        self.assertEqual(
            split_function_scope("void ns::helper<int>()"),
            ["ns", "helper<int>()"],
        )


class UpdateFunctionManifestTests(unittest.TestCase):
    def test_nests_functions_by_scope(self):
        manifest = {".": {"functions": {}, "scopes": {}}}
        update_function_manifest(manifest, "CoverageClass::functionCovered()")
        update_function_manifest(manifest, "CoverageClass::functionNotCovered()")
        update_function_manifest(manifest, "main")
        self.assertEqual(
            manifest["."],
            {
                "functions": {"main": "main"},
                "scopes": {
                    "CoverageClass": {
                        "functions": {
                            "functionCovered()": "CoverageClass::functionCovered()",
                            "functionNotCovered()": "CoverageClass::functionNotCovered()",
                        },
                        "scopes": {},
                    }
                },
            },
        )

    def test_scope_named_functions_does_not_collide_with_function_leaves(self):
        manifest = {".": {"functions": {}, "scopes": {}}}
        update_function_manifest(manifest, "functions::helper()")
        self.assertEqual(
            manifest["."],
            {
                "functions": {},
                "scopes": {
                    "functions": {
                        "functions": {"helper()": "functions::helper()"},
                        "scopes": {},
                    }
                },
            },
        )

    def test_return_type_is_preserved_in_function_index_value(self):
        manifest = {".": {"functions": {}, "scopes": {}}}
        update_function_manifest(manifest, "void ns::helper<int>()")
        self.assertEqual(
            manifest["."]["scopes"]["ns"]["functions"],
            {
                "helper<int>()": "void ns::helper<int>()",
            },
        )


class GenerateFunctionManifestTests(unittest.TestCase):
    def test_writes_functions_json_from_manifest_reports(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        website_data = Path(directory.name) / "website" / "data"
        report_dir = website_data / "local" / "coverage_example_output"
        report_dir.mkdir(parents=True)
        (website_data / "manifest.json").write_text(
            json.dumps(
                {
                    "coverage_example_output": {
                        "path": "data/local/coverage_example_output",
                        "coverage_file": "coverage_summary.json",
                    },
                    "missing_report": {
                        "path": "data/local/missing_report",
                        "coverage_file": "coverage_summary.json",
                    },
                }
            )
        )
        (report_dir / "coverage_details.json").write_text(
            json.dumps(
                {
                    "data": [
                        {
                            "functions": [
                                {
                                    "name": "_ZN13CoverageClass15functionCoveredEv",
                                    "demangled_name": "CoverageClass::functionCovered()",
                                    "count": 1,
                                },
                                {"name": "main", "demangled_name": "main", "count": 1},
                            ]
                        }
                    ]
                }
            )
        )

        asyncio.run(generate_function_manifest(website_data))

        manifest = json.loads((website_data / "functions.json").read_text())
        self.assertEqual(
            manifest["."],
            {
                "functions": {"main": "main"},
                "scopes": {
                    "CoverageClass": {
                        "functions": {
                            "functionCovered()": "CoverageClass::functionCovered()"
                        },
                        "scopes": {},
                    },
                }
            },
        )

    def test_writes_empty_manifest_without_reports(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        website_data = Path(directory.name) / "website" / "data"

        asyncio.run(generate_function_manifest(website_data))

        manifest = json.loads((website_data / "functions.json").read_text())
        self.assertEqual(manifest["."], {"functions": {}, "scopes": {}})


class CopyLocalDataTests(unittest.TestCase):
    def test_copies_report_directory_and_updates_manifest(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        report_dir = root / "coverage_example_output"
        report_dir.mkdir()
        (report_dir / "coverage_summary.json").write_text("{}")
        website_data = root / "website" / "data"
        website_data.mkdir(parents=True)

        context = StubContext(report_dir)
        asyncio.run(copy_local_data(context, website_data))

        copied = website_data / "local" / "coverage_example_output"
        self.assertTrue((copied / "coverage_summary.json").exists())
        manifest = json.loads((website_data / "manifest.json").read_text())
        self.assertEqual(
            manifest["coverage_example_output"],
            {
                "path": "data/local/coverage_example_output",
                "coverage_file": "coverage_summary.json",
            },
        )


if __name__ == "__main__":
    unittest.main()
