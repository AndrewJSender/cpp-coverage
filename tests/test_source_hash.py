# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from coverage_analytics.source_hash import source_hash


class SourceHashTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def test_hash_matches_sha256_of_content(self):
        data = b"int main() { return 0; }\n"
        digest = source_hash(self.repo, "main.cpp", data)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_hash_uses_git_cleaned_bytes(self):
        (self.repo / ".gitattributes").write_text("*.cpp text\n")
        crlf = b"int main() { return 0; }\r\n"
        lf = crlf.replace(b"\r\n", b"\n")
        digest = source_hash(self.repo, "main.cpp", crlf)
        self.assertEqual(digest, hashlib.sha256(lf).hexdigest())

    def test_hash_does_not_pollute_repository_objects(self):
        objects = self.repo / ".git" / "objects"
        before = {path for path in objects.rglob("*") if path.is_file()}
        source_hash(self.repo, "main.cpp", b"data\n")
        after = {path for path in objects.rglob("*") if path.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
