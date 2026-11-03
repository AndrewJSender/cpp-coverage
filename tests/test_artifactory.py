# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

from coverage_analytics.artifactory import (
    download_zip,
    extract_zip,
    gen_aql,
    get_directory_contents,
    request_attempt,
)

import asyncio


def mock_urlopen_response(payload: bytes) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = io.BytesIO(payload)
    response.__exit__.return_value = False
    return response


class GenAqlTests(unittest.TestCase):
    def test_generates_items_find_query(self):
        aql = gen_aql(["a/b", "c/d"], "repo-name", "*.zip")
        self.assertTrue(aql.startswith("items.find("))
        self.assertTrue(aql.endswith('.sort({"$desc": ["created"]})'))
        find_str = aql[len("items.find("):aql.index(").sort(")]
        find_dict = json.loads(find_str)
        self.assertEqual(find_dict["repo"], "repo-name")
        self.assertEqual(find_dict["$or"], [{"path": "a/b"}, {"path": "c/d"}])
        self.assertEqual(find_dict["name"], {"$match": "*.zip"})


class RequestAttemptTests(unittest.TestCase):
    def test_returns_parsed_json_on_success(self):
        payload = json.dumps({"results": [1, 2]}).encode("utf-8")
        with patch(
            "coverage_analytics.artifactory.urlopen",
            return_value=mock_urlopen_response(payload),
        ) as urlopen:
            result = request_attempt(MagicMock())
        self.assertEqual(result, {"results": [1, 2]})
        self.assertEqual(urlopen.call_count, 1)

    def test_retries_then_succeeds(self):
        payload = json.dumps({"results": []}).encode("utf-8")
        with patch(
            "coverage_analytics.artifactory.urlopen",
            side_effect=[OSError("boom"), mock_urlopen_response(payload)],
        ) as urlopen:
            result = request_attempt(MagicMock())
        self.assertEqual(result, {"results": []})
        self.assertEqual(urlopen.call_count, 2)

    def test_returns_errors_after_exhausting_retries(self):
        with patch(
            "coverage_analytics.artifactory.urlopen",
            side_effect=OSError("boom"),
        ) as urlopen:
            result = request_attempt(MagicMock())
        self.assertEqual(result, {"errors": [{"status": "boom"}]})
        self.assertEqual(urlopen.call_count, 3)

    def test_does_not_disable_certificate_verification(self):
        payload = json.dumps({}).encode("utf-8")
        with patch(
            "coverage_analytics.artifactory.urlopen",
            return_value=mock_urlopen_response(payload),
        ) as urlopen:
            request_attempt(MagicMock())
        self.assertNotIn("context", urlopen.call_args.kwargs)


class GetDirectoryContentsTests(unittest.TestCase):
    def test_returns_results_list(self):
        payload = json.dumps({"results": [{"name": "a.zip"}]}).encode("utf-8")
        with patch(
            "coverage_analytics.artifactory.urlopen",
            return_value=mock_urlopen_response(payload),
        ):
            results = get_directory_contents("key", "aql", "https://example.invalid")
        self.assertEqual(results, [{"name": "a.zip"}])

    def test_returns_empty_on_errors(self):
        with patch(
            "coverage_analytics.artifactory.urlopen",
            side_effect=OSError("boom"),
        ):
            results = get_directory_contents("key", "aql", "https://example.invalid")
        self.assertEqual(results, {})


class DownloadZipTests(unittest.TestCase):
    def test_streams_response_to_file_with_auth_header(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        zip_dir = Path(directory.name)
        with patch(
            "coverage_analytics.artifactory.urlopen",
            return_value=mock_urlopen_response(b"zip-bytes"),
        ) as urlopen:
            result = asyncio.run(
                download_zip("api-key", "https://example.invalid/path/results.zip", zip_dir)
            )
        self.assertEqual(result, zip_dir / "results.zip")
        self.assertEqual(result.read_bytes(), b"zip-bytes")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("X-jfrog-art-api"), "api-key")


class ExtractZipTests(unittest.TestCase):
    def test_extracts_into_directory_named_after_zip(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        zip_path = root / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("inner/data.txt", "hello")
        unzip_path = root / "out"
        result = asyncio.run(extract_zip(zip_path, unzip_path))
        self.assertEqual(result, unzip_path / "bundle")
        self.assertEqual((result / "inner" / "data.txt").read_text(), "hello")


if __name__ == "__main__":
    unittest.main()
