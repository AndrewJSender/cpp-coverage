#!/usr/bin/env python3
# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

"""Generate LLVM coverage reports and the static coverage website data."""

import argparse
import asyncio
import logging
import platform
import shutil
import subprocess
from pathlib import Path

from profile import profile_data, OPEN_CPP_COVERAGE_STR, BULLSEYE_STR, CLANG_STR
from website import copy_local_data, generate_website


logger = logging.getLogger(__name__)
ROOT_PATH = Path(__file__).resolve().parent.parent


class CoverageContext:
    """Minimal context adapter used by the reusable coverage modules."""

    def __init__(self, output_directory: Path):
        self.args = {"test_output_directory": str(output_directory)}

    async def execute(self, command: list[str]) -> str:
        logger.debug("Running: %s", " ".join(str(part) for part in command))
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    async def eval_async(self, expression: str) -> str:
        if expression == "$(xcode_tool llvm-profdata)":
            return shutil.which("llvm-profdata") or _xcrun_path("llvm-profdata")
        if expression == "$(xcode_tool llvm-cov)":
            return shutil.which("llvm-cov") or _xcrun_path("llvm-cov")
        if expression == "$(xcode_tool c++filt)":
            return shutil.which("c++filt") or _xcrun_path("c++filt")
        if expression == "/usr/lib/llvm-18/bin":
            return "/usr/lib/llvm-18/bin"
        raise ValueError(f"Unsupported context expression: {expression}")

    async def copy(self, source: Path, destination: Path) -> None:
        if destination.exists():
            shutil.rmtree(destination)
        await asyncio.to_thread(shutil.copytree, source, destination)


def _xcrun_path(tool: str) -> str:
    result = subprocess.run(
        ["xcrun", "--find", tool],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT_PATH,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def generate(args: argparse.Namespace) -> None:
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    profile_path = output_directory / "coverage.profraw"
    if not profile_path.exists():
        raise FileNotFoundError(f"LLVM profile data was not found: {profile_path}")

    build_info = {
        "branch_name": args.branch_name,
        "build_number": args.build_number,
        "hostname": platform.node(),
        "project_root": str(ROOT_PATH),
        "git_commit": _git_commit(),
    }
    context = CoverageContext(output_directory)
    platform_name = {
        "Darwin": "macos",
        "Windows": "win32",
        "Linux": "linux",
    }.get(platform.system())
    if platform_name is None:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")

    import os

    os.environ["LLVM_PROFILE_FILE"] = str(profile_path)
    await profile_data(
        context,
        args.ccov_tool,
        platform_name,
        args.test_binary.resolve(),
        build_info,
        output_directory,
        gen_html=True,
        gen_lcov=True,
        gen_lcov_to_cobertura=True,
    )

    await generate_website(
        context,
        [args.source_directory],
        ROOT_PATH,
    )
    await copy_local_data(context)

    logger.info("Coverage reports written to %s", output_directory)
    logger.info("Website data written to %s", ROOT_PATH / "website" / "data")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate LLVM coverage reports and website data."
    )
    parser.add_argument(
        "--source-directory",
        type=Path,
        default="example/submodules/googletest/googletest/samples",
        help="Directory containing the source code to analyze.  This is relative to the project root.",
    )

    parser.add_argument(
        "--test-binary",
        type=Path,
        required=True,
        help="Instrumented test executable used by llvm-cov.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT_PATH / "build" / "coverage",
        help="Directory containing coverage.profraw and receiving reports.",
    )
    parser.add_argument("--branch-name", default="local")
    parser.add_argument("--build-number", type=int, default=0)
    parser.add_argument(
        "--ccov-tool",
        choices=[OPEN_CPP_COVERAGE_STR, BULLSEYE_STR, CLANG_STR],
        default=CLANG_STR,
        help="Coverage tool to use.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    asyncio.run(generate(parse_args()))
