# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "release.py"


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote = root / "remote.git"
        self.repo = root / "checkout"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", str(self.remote))
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "example"\nversion = "0.1.0"\n'
            '\n[tool.example]\nversion = "unchanged"\n',
            encoding="utf-8",
        )
        self.git("add", "pyproject.toml")
        self.git("commit", "-m", "Initial")
        self.git("push", "-u", "origin", "main")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, text=True, capture_output=True
        ).stdout.strip()

    def release(self, version):
        return subprocess.run(
            [sys.executable, str(SCRIPT), version],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )

    def test_release_updates_project_version_and_pushes_commit_and_tag(self):
        result = self.release("0.2.0rc1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.repo / "pyproject.toml").read_text(encoding="utf-8"),
            '[project]\nname = "example"\nversion = "0.2.0rc1"\n'
            '\n[tool.example]\nversion = "unchanged"\n',
        )
        commit = self.git("rev-parse", "HEAD")
        self.assertEqual(self.git("rev-parse", "v0.2.0rc1"), commit)
        remote_refs = self.git("ls-remote", "origin", "refs/heads/main", "refs/tags/v0.2.0rc1")
        self.assertEqual(
            set(remote_refs.splitlines()),
            {f"{commit}\trefs/heads/main", f"{commit}\trefs/tags/v0.2.0rc1"},
        )

    def test_refuses_invalid_version_dirty_tree_and_existing_tag(self):
        result = self.release("0.2.0rc")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version must be", result.stderr)

        (self.repo / "untracked").touch()
        result = self.release("0.2.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("working tree is not clean", result.stderr)
        (self.repo / "untracked").unlink()

        self.git("tag", "v0.2.0")
        result = self.release("0.2.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertIn('version = "0.1.0"', (self.repo / "pyproject.toml").read_text())

    def test_refuses_wrong_branch_and_missing_project_version(self):
        self.git("checkout", "-b", "other")
        result = self.release("0.2.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("releases must be made from main", result.stderr)

        self.git("checkout", "main")
        path = self.repo / "pyproject.toml"
        path.write_text('[project]\nname = "example"\n', encoding="utf-8")
        self.git("add", "pyproject.toml")
        self.git("commit", "-m", "Remove version")
        self.git("push", "origin", "main")
        result = self.release("0.2.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not find exactly one project version", result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
