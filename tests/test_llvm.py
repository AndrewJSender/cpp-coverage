# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coverage_analytics.llvm import demangle_function_names, simplify_microsoft_name


class SimplifyMicrosoftNameTests(unittest.TestCase):
    def test_strips_signature_decorations(self):
        cases = {
            "public: void __cdecl CoverageClass::functionCovered(void)": "CoverageClass::functionCovered()",
            "private: static int __stdcall CoverageClass::helper(int)": "CoverageClass::helper(int)",
            "public: virtual void __thiscall CoverageClass::update(void) const": "CoverageClass::update() const",
            "public: __cdecl CoverageClass::CoverageClass(void)": "CoverageClass::CoverageClass()",
            "int __cdecl main(void)": "main()",
            "main": "main",
        }
        for decorated, expected in cases.items():
            with self.subTest(decorated=decorated):
                self.assertEqual(simplify_microsoft_name(decorated), expected)


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
        with patch("coverage_analytics.llvm.subprocess.run", return_value=result) as run:
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

    def test_demangles_microsoft_symbols_with_undname(self):
        details = {
            "data": [
                {
                    "functions": [
                        {"name": "?functionCovered@CoverageClass@@QEAAXXZ", "count": 1},
                        {"name": "main", "count": 0},
                    ]
                },
            ],
        }
        self.write_details(details)

        def run_demanglers(command, **kwargs):
            if command == ["llvm-undname"]:
                self.assertEqual(kwargs["input"], "?functionCovered@CoverageClass@@QEAAXXZ\n")
                # llvm-undname echoes each redirected input line before its result.
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="?functionCovered@CoverageClass@@QEAAXXZ\n"
                    "\n"
                    "public: void __cdecl CoverageClass::functionCovered(void)\n",
                )
            self.assertEqual(command, ["llvm-cxxfilt"])
            self.assertEqual(kwargs["input"], "main\n")
            return subprocess.CompletedProcess(command, 0, stdout="main\n")

        with patch("coverage_analytics.llvm.subprocess.run", side_effect=run_demanglers) as run:
            demangle_function_names(self.details_path, "llvm-cxxfilt", "llvm-undname")

        self.assertEqual(run.call_count, 2)
        details["data"][0]["functions"][0]["demangled_name"] = "CoverageClass::functionCovered()"
        details["data"][0]["functions"][1]["demangled_name"] = "main"
        self.assertEqual(json.loads(self.details_path.read_text(encoding="utf-8")), details)

    def test_microsoft_symbols_fall_back_to_cxxfilt_without_undname(self):
        details = {"data": [{"functions": [{"name": "?functionCovered@CoverageClass@@QEAAXXZ"}]}]}
        self.write_details(details)
        result = subprocess.CompletedProcess(
            ["c++filt"], 0, stdout="?functionCovered@CoverageClass@@QEAAXXZ\n"
        )
        with patch("coverage_analytics.llvm.subprocess.run", return_value=result) as run:
            demangle_function_names(self.details_path, "c++filt")

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["c++filt"])
        updated = json.loads(self.details_path.read_text(encoding="utf-8"))
        self.assertEqual(
            updated["data"][0]["functions"][0]["demangled_name"],
            "?functionCovered@CoverageClass@@QEAAXXZ",
        )

    def test_skips_demangler_when_no_functions_exist(self):
        for export in ({}, {"functions": []}):
            with self.subTest(export=export):
                self.write_details({"data": [export]})
                with patch("coverage_analytics.llvm.subprocess.run") as run:
                    demangle_function_names(self.details_path, "c++filt")
                run.assert_not_called()

    def test_process_failure_preserves_report(self):
        details = {"data": [{"functions": [{"name": "main"}]}]}
        self.write_details(details)
        with patch(
            "coverage_analytics.llvm.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["c++filt"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                demangle_function_names(self.details_path, "c++filt")
        self.assertEqual(json.loads(self.details_path.read_text(encoding="utf-8")), details)

    def test_missing_executable_leaves_function_names_unchanged(self):
        details = {"data": [{"functions": [{"name": "main"}]}]}
        self.write_details(details)
        with patch("coverage_analytics.llvm.subprocess.run", side_effect=FileNotFoundError("c++filt")):
            demangle_function_names(self.details_path, "c++filt")
        self.assertEqual(json.loads(self.details_path.read_text(encoding="utf-8")), details)

    def test_missing_msvc_demangler_leaves_symbols_unchanged(self):
        details = {
            "data": [
                {
                    "functions": [
                        {"name": "?functionCovered@CoverageClass@@QEAAXXZ"},
                        {"name": "main"},
                    ]
                }
            ]
        }
        self.write_details(details)

        def run_demanglers(command, **kwargs):
            if command == ["llvm-undname"]:
                raise FileNotFoundError("llvm-undname")
            return subprocess.CompletedProcess(command, 0, stdout="main\n")

        with patch("coverage_analytics.llvm.subprocess.run", side_effect=run_demanglers):
            demangle_function_names(self.details_path, "llvm-cxxfilt", "llvm-undname")

        updated = json.loads(self.details_path.read_text(encoding="utf-8"))
        self.assertNotIn("demangled_name", updated["data"][0]["functions"][0])
        self.assertEqual(updated["data"][0]["functions"][1]["demangled_name"], "main")

    def test_invalid_output_preserves_report(self):
        details = {"data": [{"functions": [{"name": "main"}]}]}
        for output in ("", "\n", "main\nunexpected\n"):
            with self.subTest(output=output):
                self.write_details(details)
                result = subprocess.CompletedProcess(["c++filt"], 0, stdout=output)
                with patch("coverage_analytics.llvm.subprocess.run", return_value=result):
                    with self.assertRaises(ValueError):
                        demangle_function_names(self.details_path, "c++filt")
                self.assertEqual(
                    json.loads(self.details_path.read_text(encoding="utf-8")), details
                )


if __name__ == "__main__":
    unittest.main()
