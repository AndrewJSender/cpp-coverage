#!/usr/bin/env python3
"""Commit, tag, and push a package release. See docs/releasing.md."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


def git(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], check=True, text=True, capture_output=capture_output
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="release version, e.g. 0.2.0")
    args = parser.parse_args()
    version = args.version
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?", version):
        parser.error("version must be like 0.2.0 or 0.2.0rc1")

    try:
        root = git("rev-parse", "--show-toplevel", capture_output=True).stdout.strip()
        os.chdir(root)
        branch = git("rev-parse", "--abbrev-ref", "HEAD", capture_output=True).stdout.strip()
        if branch != "main":
            raise ValueError(f"releases must be made from main (currently on {branch!r})")
        if git("status", "--porcelain", capture_output=True).stdout:
            raise ValueError("working tree is not clean; commit or stash changes first")

        git("pull", "--ff-only", "origin", "main")
        tag = f"v{version}"
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"]
        )
        if result.returncode == 0:
            raise ValueError(f"tag {tag} already exists")
        if result.returncode != 1:
            raise subprocess.CalledProcessError(result.returncode, result.args)

        path = Path("pyproject.toml")
        text = path.read_text(encoding="utf-8")
        pattern = (
            r'(?m)(^\[project\][ \t]*\r?\n'
            r'(?:(?!\[)[^\r\n]*\r?\n)*?'
            r'^version[ \t]*=[ \t]*")[^"\r\n]*(")'
        )
        updated, count = re.subn(pattern, lambda match: match[1] + version + match[2], text)
        if count != 1:
            raise ValueError("could not find exactly one project version in pyproject.toml")
        path.write_text(updated, encoding="utf-8")

        git("add", "pyproject.toml")
        git("commit", "-m", f"Release {version}")
        git("tag", tag)
        git("push", "origin", "main", tag)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"\nPushed {tag}. Watch the release workflow with:")
    print("  gh run watch --repo AndrewJSender/coverage-analytics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
