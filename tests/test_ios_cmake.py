# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(
    sys.platform == "darwin" and shutil.which("cmake") and shutil.which("xcrun"),
    "iOS simulator configuration requires Xcode and CMake",
)
class IosCmakeTests(unittest.TestCase):
    def test_ctest_uses_resolved_simulator_binary_path(self):
        project = Path(__file__).resolve().parents[1] / "example"
        with tempfile.TemporaryDirectory() as build:
            subprocess.run(
                [
                    "cmake", "-G", "Xcode", "-S", str(project), "-B", build,
                    "-DCMAKE_SYSTEM_NAME=iOS",
                    "-DCMAKE_OSX_SYSROOT=iphonesimulator",
                    "-DCMAKE_OSX_ARCHITECTURES=arm64",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                ["ctest", "-C", "Debug", "--show-only=json-v1"],
                cwd=build,
                check=True,
                capture_output=True,
                text=True,
            )
            tests = json.loads(result.stdout)["tests"]
            command = next(test["command"] for test in tests if test["name"] == "coverage_example")
            self.assertEqual(
                command[-1],
                str(Path(build) / "Debug" / "coverage_example.app" / "coverage_example"),
            )


if __name__ == "__main__":
    unittest.main()
