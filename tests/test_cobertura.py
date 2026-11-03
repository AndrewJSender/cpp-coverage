# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from coverage_analytics.cobertura import adjust_xml_file, split_xml_data_to_json

COBERTURA_XML = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package name="example">
      <classes>
        <class filename="my_lib.cpp" name="my_lib">
          <lines>
            <line number="1" hits="2"/>
            <line number="2" hits="0"/>
            <line number="3" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


class AdjustXmlFileTests(unittest.TestCase):
    def test_strips_whitespace_and_returns_root(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        xml_path = Path(directory.name) / "coverage.xml"
        xml_path.write_text(COBERTURA_XML)

        root = asyncio.run(adjust_xml_file(xml_path))

        self.assertEqual(root.tag, "coverage")
        self.assertNotIn("\n", xml_path.read_text())


class SplitXmlDataToJsonTests(unittest.TestCase):
    def test_writes_per_file_details_and_summary(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output_path = Path(directory.name)
        xml_path = output_path / "coverage.xml"
        xml_path.write_text(COBERTURA_XML)
        root = asyncio.run(adjust_xml_file(xml_path))
        build_info = {"branch_name": "main", "build_number": 7}

        asyncio.run(split_xml_data_to_json(root, output_path, build_info))

        details = json.loads(
            (output_path / "code_coverage_details" / "my_lib.cpp.json").read_text()
        )
        self.assertEqual(details["filename"], "my_lib.cpp")
        self.assertEqual(details["summary"]["lines"], {"count": 3, "covered": 2})
        self.assertEqual(
            details["segments"],
            [
                [1, 0, 2, True, False, False],
                [2, 0, 0, True, False, False],
                [3, 0, 1, True, False, False],
            ],
        )

        summary = json.loads((output_path / "coverage_summary.json").read_text())
        self.assertEqual(summary["build_info"], build_info)
        files = summary["data"][0]["files"]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["filename"], "my_lib.cpp")
        self.assertNotIn("segments", files[0])


if __name__ == "__main__":
    unittest.main()
