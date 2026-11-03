# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import ssl
from urllib.request import Request, urlopen
import json
import zipfile
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def request_attempt(request: Request) -> dict:
    """attempt to make the request"""
    context = ssl._create_unverified_context()
    maxTries = 3
    for attempt in range(1, maxTries):
        try:
            with urlopen(request, timeout=90, context=context) as response:
                response_json = json.loads(response.read())
            break  # success
        except Exception as e:
            print(f"Attempt {attempt} failed with error: {e}")
            if attempt >= maxTries:
                return {"errors": [{"status": e}]}

    return response_json

def request_aql(api_key: str, remote_url: str, aql_unencoded: str) -> dict:
    """run the AQL query

    Args:
        api_key (str): artifactory api key
        remote_url (str): artifactory url
        aql_unencoded (str): aql query

    Returns:
        dict: aql query response
    """
    request = Request(remote_url, aql_unencoded.encode("utf-8"))
    request.add_header("X-JFrog-Art-Api", api_key)
    request.add_header("Content-Type", "text/plain")
    return request_attempt(request)


def gen_aql(remote_dir_paths: list, repo_name: str, name_match: str) -> str:
    """generate the AQL query

    Args:
        remote_dir_paths (list): remote directory paths
        repo_name (str): artifactory repo name
        name_match (str): file extension to match (e.g. *.zip)

    Returns:
        str: AQL query
    """
    path_dicts = [{"path": remote_dir_path} for remote_dir_path in remote_dir_paths]
    find_dict = {
        "repo": repo_name,
        "$or": path_dicts,
        "name": {"$match": name_match},
    }
    sort_dict = {"$desc": ["created"]}
    find_str = json.dumps(find_dict)
    sort_str = json.dumps(sort_dict)
    return f"items.find({find_str}).sort({sort_str})"


def get_directory_contents(api_key: str, aql: str, artifactory_root) -> list:
    """get the directory contents from artifactory

    Args:
        api_key (str): artifactory api key
        aql (str): aql query

    Returns:
        list: list of files found
    """
    remote_url = "/".join([artifactory_root, "api/search/aql/"])
    response_json = request_aql(api_key, remote_url, aql)
    if "errors" in response_json:
        return {}
    return response_json["results"]

async def download_zip(artifactory_api_key, url, zip_dir_path: Path):
    zip_file_name = url.split("/")[-1]
    logger.debug("Downloading %s to %s", zip_file_name, zip_dir_path)
    curl_cmd = f'curl -H "X-JFrog-Art-Api: {artifactory_api_key}" -O {url}'
    os.chdir(zip_dir_path)
    os.system(curl_cmd)
    return zip_dir_path / zip_file_name

async def extract_zip(zip_file_path: Path, unzip_path: Path):
    logger.debug("Unzipping %s to %s", zip_file_path, unzip_path)
    zip_filename = zip_file_path.stem
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        unzip_result_path = Path(unzip_path, zip_filename)
        zip_ref.extractall(unzip_result_path)

    return unzip_result_path
