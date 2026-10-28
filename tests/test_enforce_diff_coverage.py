# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from enforce_diff_coverage import main


class EnforceDiffCoverageTests(unittest.TestCase):
    def run_report(self, gate):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        report_path = root / "report.json"
        report_path.write_text(json.dumps({"gate": gate}), encoding="utf-8")
        summary_path = root / "summary.md"
        summary_path.touch()
        output = io.StringIO()
        errors = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main([str(report_path)])
        return status, output.getvalue(), errors.getvalue(), summary_path.read_text(encoding="utf-8")

    def test_passes_clean_gate_and_writes_summary(self):
        status, output, errors, summary = self.run_report({
            "lines": [], "uncovered": 0, "errors": 0,
        })
        self.assertEqual(status, 0)
        self.assertEqual(output, "")
        self.assertEqual(errors, "")
        self.assertIn("Failing changed lines: 0", summary)
        self.assertIn("Validation errors: 0", summary)

    def test_fails_gate_and_emits_escaped_annotations(self):
        status, output, errors, summary = self.run_report({
            "lines": [{
                "file": "a,b:c.cpp",
                "line": 12,
                "reasons": ["uncovered\nbranch"],
            }],
            "uncovered": 1,
            "errors": 0,
        })
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            "::error file=a%2Cb%3Ac.cpp,line=12::uncovered%0Abranch\n",
        )
        self.assertIn("PR coverage requirements not met", errors)
        self.assertIn("Failing changed lines: 1", summary)


if __name__ == "__main__":
    unittest.main()
