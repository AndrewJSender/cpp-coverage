# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import os
import json
from pathlib import Path
import logging

from coverage_analytics.archived.artifactory import download_zip, extract_zip

logger = logging.getLogger(__name__)


def default_website_data_path() -> Path:
    """Default location of the website data directory, relative to the working directory."""
    return Path.cwd() / "website" / "data"

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


def split_function_scope(name: str) -> list[str]:
    """Split a demangled function name on ``::`` outside template/argument nesting.

    For example, ``CoverageClass::functionCovered()`` becomes
    ``["CoverageClass", "functionCovered()"]``.
    """
    parts = []
    depth = 0
    start = 0
    index = 0
    while index < len(name) - 1:
        character = name[index]
        if character in "<([{":
            depth += 1
        elif character in ">)]}":
            depth = max(depth - 1, 0)
        elif depth == 0 and name.startswith("::", index):
            parts.append(name[start:index])
            index += 2
            start = index
            continue
        index += 1
    parts.append(name[start:])
    return [part for part in parts if part] or [name]


def update_function_manifest(functions_manifest: dict, function_name: str):
    """Insert a demangled function name into the namespace/class scope tree."""
    parts = split_function_scope(function_name)
    scope = functions_manifest["."]
    for part in parts[:-1]:
        if part not in scope:
            scope[part] = {"functions": {}}
        scope = scope[part]
    scope.setdefault("functions", {})[parts[-1]] = function_name


async def generate_function_manifest(website_data_path: Path | None = None):
    """Write functions.json from the coverage_details.json of each manifest report."""
    website_data_path = website_data_path or default_website_data_path()
    functions_manifest = {
        ".": {"functions": {}},
        "functions": {},
    }

    manifest_json_path = website_data_path / "manifest.json"
    manifest = {}
    if manifest_json_path.exists():
        with open(manifest_json_path, "r") as manifest_json_file:
            manifest = json.load(manifest_json_file)

    for report_name, report in manifest.items():
        details_path = website_data_path.parent / report["path"] / "coverage_details.json"
        if not details_path.exists():
            logger.warning("No coverage_details.json for report %s", report_name)
            continue
        with open(details_path, "r", encoding="utf-8") as details_file:
            details = json.load(details_file)
        for export in details.get("data", []):
            for function in export.get("functions", []):
                name = function.get("demangled_name") or function.get("name")
                if name:
                    update_function_manifest(functions_manifest, name)

    functions_json_path = website_data_path / "functions.json"
    functions_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(functions_json_path, "w") as functions_json_file:
        json.dump(functions_manifest, functions_json_file)


async def generate_website(ctx, src_list, root_path: Path, website_data_path: Path | None = None):
    website_data_path = website_data_path or default_website_data_path()
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


async def copy_local_data(ctx, website_data_path: Path | None = None):
    logger.debug("Copying local data")
    website_data_path = website_data_path or default_website_data_path()
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
    website_data_path: Path | None = None,
):
    logger.debug("Downloading remote data")
    website_data_path = website_data_path or default_website_data_path()
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
