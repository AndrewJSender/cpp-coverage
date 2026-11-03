# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile


def source_hash(repo: Path, filename: str, data: bytes) -> str:
    object_path = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-path", "objects"],
        check=True, capture_output=True, encoding="utf-8",
    ).stdout.strip()
    object_path = Path(object_path)
    if not object_path.is_absolute():
        object_path = repo / object_path

    with tempfile.TemporaryDirectory() as directory:
        temporary_objects = Path(directory) / "objects"
        temporary_objects.mkdir()
        env = {
            **os.environ,
            "GIT_OBJECT_DIRECTORY": str(temporary_objects),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(object_path.resolve()),
        }
        object_id = subprocess.run(
            [
                "git", "-C", str(repo), "hash-object", "-w",
                f"--path={filename}", "--stdin",
            ],
            input=data, check=True, capture_output=True, env=env,
        ).stdout.decode("ascii").strip()
        clean_data = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", object_id],
            check=True, capture_output=True, env=env,
        ).stdout
    return hashlib.sha256(clean_data).hexdigest()
