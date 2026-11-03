# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import asyncio
from pathlib import Path
import unittest

from coverage_analytics.bundle import build_info_dict, get_git_commit


class StubContext:
    async def execute(self, command):
        assert command == ["git", "rev-parse", "HEAD"]
        return "abc123\n"


class BundleTests(unittest.TestCase):
    def test_build_info_dict_contents(self):
        info = asyncio.run(
            build_info_dict("main", 42, Path("/repo"), "abc123")
        )
        self.assertEqual(info["branch_name"], "main")
        self.assertEqual(info["build_number"], 42)
        self.assertEqual(info["project_root"], str(Path("/repo")))
        self.assertEqual(info["git_commit"], "abc123")
        self.assertIn("hostname", info)

    def test_get_git_commit_strips_newline(self):
        commit = asyncio.run(get_git_commit(StubContext()))
        self.assertEqual(commit, "abc123")


if __name__ == "__main__":
    unittest.main()
