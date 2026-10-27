# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from llvm import demangle_function_names


class DemangleFunctionNamesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.details_path = Path(self.directory.name) / "coverage_details.json"

    def write_details(self, data):
        self.details_path.write_text(json.dumps(data), encoding="utf-8")

    def test_adds_readable_names_and_preserves_symbols_across_exports(self):
        details = {
            "data": [
                {"functions": [{"name": "_ZN13CoverageClass9functionCoveredEv", "count": 1}]},
                {"functions": [{"name": "main", "count": 0}]},
            ],
            "version": "3.0.1",
        }
        self.write_details(details)
        result = subprocess.CompletedProcess(
            ["c++filt"], 0, stdout="CoverageClass::functionCovered()\nmain\n"
        )
        with patch("llvm.subprocess.run", return_value=result) as run:
            demangle_function_names(self.details_path, "c++filt")

        run.assert_called_once_with(
            ["c++filt"],
            input="_ZN13CoverageClass9functionCoveredEv\nmain\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        details["data"][0]["functions"][0]["demangled_name"] = "CoverageClass::functionCovered()"
        details["data"][1]["functions"][0]["demangled_name"] = "main"
        self.assertEqual(json.loads(self.details_path.read_text(encoding="utf-8")), details)

    def test_skips_demangler_when_no_functions_exist(self):
        for export in ({}, {"functions": []}):
            with self.subTest(export=export):
                self.write_details({"data": [export]})
                with patch("llvm.subprocess.run") as run:
                    demangle_function_names(self.details_path, "c++filt")
                run.assert_not_called()

    def test_process_failure_preserves_report(self):
        details = {"data": [{"functions": [{"name": "main"}]}]}
        self.write_details(details)
        with patch(
            "llvm.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["c++filt"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                demangle_function_names(self.details_path, "c++filt")
        self.assertEqual(json.loads(self.details_path.read_text(encoding="utf-8")), details)

    def test_missing_executable_is_reported(self):
        self.write_details({"data": [{"functions": [{"name": "main"}]}]})
        with patch("llvm.subprocess.run", side_effect=FileNotFoundError("c++filt")):
            with self.assertRaises(FileNotFoundError):
                demangle_function_names(self.details_path, "c++filt")

    def test_invalid_output_preserves_report(self):
        details = {"data": [{"functions": [{"name": "main"}]}]}
        for output in ("", "\n", "main\nunexpected\n"):
            with self.subTest(output=output):
                self.write_details(details)
                result = subprocess.CompletedProcess(["c++filt"], 0, stdout=output)
                with patch("llvm.subprocess.run", return_value=result):
                    with self.assertRaises(ValueError):
                        demangle_function_names(self.details_path, "c++filt")
                self.assertEqual(
                    json.loads(self.details_path.read_text(encoding="utf-8")), details
                )


if __name__ == "__main__":
    unittest.main()
