# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import os
import json
from pathlib import Path
import logging

from artifactory import download_zip, extract_zip

logger = logging.getLogger(__name__)

ROOT_PATH = Path(__file__).resolve().parent.parent
website_data_path = Path(ROOT_PATH, "website", "data")

def update_file_manifest(files_manifest: dict, root_path: Path, parent_path, file: str):
    if file == ".DS_Store":
        return
    file_path = Path(parent_path, file)
    file_relative_path = file_path.relative_to(root_path)
    subfolder = files_manifest["."]
    for part in file_relative_path.parent.parts:
        if part not in subfolder:
            subfolder[part] = {"files": {}}
        subfolder = subfolder[part]
    file_path_str = f"./{file_relative_path}".replace("\\", "/")
    subfolder["files"].update({file_relative_path.name: file_path_str})


async def generate_website(ctx, src_list, root_path: Path):
    files_manifest = {
        ".": {},
        "files": {},
    }

    for src in src_list:
        for parent_path, dirs, files in os.walk(root_path / src):
            # ignore dirs b/c os.walk will walk through all dirs
            for file in files:
                update_file_manifest(files_manifest, root_path, parent_path, file)

    files_json_path = website_data_path / "files.json"
    files_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(files_json_path, "w") as files_json_file:
        json.dump(files_manifest, files_json_file)


async def copy_local_data(ctx):
    logger.debug("Copying local data")
    src = Path(ctx.args["test_output_directory"])
    dst = Path(website_data_path, "local", src.name)
    manifest = {}
    manifest_json_path = Path(website_data_path, "manifest.json")
    
    logger.debug("Copying %s to %s", src, dst)
    await ctx.copy(src, dst)

    if manifest_json_path.exists():
        with open(manifest_json_path, "r") as manifest_json_file:
            manifest = json.load(manifest_json_file)

    unzipped_dir_path = dst.relative_to(website_data_path.parent)
    coverage_file = "coverage_summary.json"
    entry = {
        src.name: {
            "path": unzipped_dir_path.__str__().replace("\\", "/"),
            "coverage_file": coverage_file,
        }
    }
    manifest.update(entry)

    with open(manifest_json_path, "w") as manifest_json_file:
        json.dump(manifest, manifest_json_file)


async def download_remote_data(
    ctx,
    artifactory_api_key: str,
    urls: list[str],
    appendage_bug: Path = None,
):
    logger.debug("Downloading remote data")
    zip_dir_path = website_data_path / "zipped_files"
    unzip_path = website_data_path / "unzipped_files"

    zip_dir_path.mkdir(parents=True, exist_ok=True)
    unzip_path.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for url in urls:
        coverage_file = "coverage_summary.json"
        zip_file_path = await download_zip(artifactory_api_key, url, zip_dir_path)
        unzipped_path = await extract_zip(zip_file_path, unzip_path)
        manifest_name = unzipped_path.stem
        if appendage_bug:
            # bug fix for metabuild.archive_artifact
            unzipped_path = unzipped_path / appendage_bug
        rel_unzipped_path = unzipped_path.relative_to(website_data_path.parent)

        manifest[manifest_name] = {
            "path": rel_unzipped_path.__str__(),
            "coverage_file": coverage_file,
        }

    manifest_json_path = Path(website_data_path, "manifest.json")
    with open(manifest_json_path, "w") as manifest_json_file:
        json.dump(manifest, manifest_json_file)
