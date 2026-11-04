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
    generate_website,
    update_file_manifest,
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
