# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import contextlib
import io
import unittest
from unittest.mock import patch

from coverage_analytics import __version__
from coverage_analytics.cli import main


class CliTests(unittest.TestCase):
    def test_no_arguments_prints_usage_and_fails(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main([]), 2)
        self.assertIn("usage: coverage-analytics", stderr.getvalue())

    def test_help_prints_usage(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["--help"]), 0)
        self.assertIn("profile", stdout.getvalue())
        self.assertIn("diff", stdout.getvalue())
        self.assertIn("gate", stdout.getvalue())

    def test_version_prints_package_version(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["--version"]), 0)
        self.assertEqual(stdout.getvalue().strip(), f"coverage-analytics {__version__}")

    def test_unknown_command_fails(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["frobnicate"]), 2)
        self.assertIn("unknown command 'frobnicate'", stderr.getvalue())

    def test_dispatches_diff_arguments(self):
        with patch("coverage_analytics.git.main", return_value=0) as diff_main:
            self.assertEqual(main(["diff", "main", "--coverage", "reports"]), 0)
        diff_main.assert_called_once_with(["main", "--coverage", "reports"])

    def test_dispatches_gate_arguments(self):
        with patch(
            "coverage_analytics.enforce_diff_coverage.main", return_value=1
        ) as gate_main:
            self.assertEqual(main(["gate", "report.json"]), 1)
        gate_main.assert_called_once_with(["report.json"])

    def test_dispatches_profile_arguments(self):
        with patch(
            "coverage_analytics.generate_profile.main", return_value=0
        ) as profile_main:
            self.assertEqual(main(["profile", "--help"]), 0)
        profile_main.assert_called_once_with(["--help"])


if __name__ == "__main__":
    unittest.main()
