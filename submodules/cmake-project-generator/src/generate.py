# Copyright (c) 2026 Andrew J. Sender AndrewJ.Sender@gmail.com
# SPDX-License-Identifier: MIT

import argparse
import os
import subprocess
import sys
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()

logging.basicConfig(level=logging.INFO)

def run_cmake_command(build_dir, source_dir, generator, architecture=None):
    logging.info(f"Generating {generator}...")
    os.makedirs(build_dir, exist_ok=True)
    cmd = [
        "cmake",
        "-G", generator,
        "-S", source_dir,
        "-B", build_dir
    ]
    if architecture:
        cmd.extend(["-A", architecture])
    subprocess.run(cmd, check=True)


gen_properties = {
    "vs": {
        "build_dir": "build_vs",
        "generator": "Visual Studio 17 2022",
        "architecture": "x64"
    },
    "xcode": {
        "build_dir": "build_xcode",
        "generator": "Xcode",
        "architecture": None,
    }
}
def generate_projects(args):
    if args.generator:
        generator = args.generator
    else:
        if sys.platform == "win32":
            generator = "vs"
        elif sys.platform == "darwin":
            generator = "xcode"
        else:
            logging.error("Unsupported platform. Please specify a generator using --generator.")
            sys.exit(1)
    source_dir = args.source_dir if args.source_dir else ROOT_DIR
    build_dir = source_dir / gen_properties[generator]["build_dir"]

    run_cmake_command(build_dir, source_dir, gen_properties[generator]["generator"], gen_properties[generator]["architecture"])

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate CMake projects for different IDEs.")
    parser.add_argument("--generator", choices=["vs", "xcode"], help="Specify the generator to use")
    parser.add_argument("--build-dir", required=True, type=Path, help="Specify a custom build directory")
    parser.add_argument("--source-dir", required=True, type=Path, help="Specify a custom source directory")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    generate_projects(args)
