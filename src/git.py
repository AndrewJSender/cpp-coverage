# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

"""Compare changed destination lines with one or more project coverage reports."""

import argparse
from collections import Counter
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from source_hash import source_hash


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def run_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout


def diff_revisions(repo: Path, revisions: list[str]) -> list[str]:
    if len(revisions) == 1 and ".." in revisions[0]:
        value = revisions[0]
        separator = "..." if "..." in value else ".."
        parts = value.split(separator)
        if len(parts) != 2:
            raise ValueError(f"Invalid Git range: {value}")
        refs = [part or "HEAD" for part in parts]
    else:
        separator = None
        refs = revisions
    commits = [
        run_git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip()
        for ref in refs
    ]
    if separator == "...":
        commits[0] = run_git(repo, "merge-base", *commits).strip()
    return commits


def added_lines(patch: str) -> dict[int, str]:
    lines = {}
    destination = None
    for text in patch.split("\n"):
        match = HUNK.match(text)
        if match:
            destination = int(match[1])
        elif destination is not None:
            if text.startswith("+"):
                lines[destination] = text[1:]
                destination += 1
            elif text.startswith(" "):
                destination += 1
    return lines


def changed_lines(repo: Path, revisions: list[str]) -> dict[str, dict[int, str]]:
    args = [
        "diff", "--no-ext-diff", "--no-textconv", "--no-color", "--no-renames",
        "--ignore-submodules=all", *diff_revisions(repo, revisions),
    ]
    paths = run_git(repo, *args, "--name-only", "-z", "--diff-filter=AMT", "--").split("\0")
    result = {}
    for path in filter(None, paths):
        patch = run_git(repo, *args, "--unified=0", "--", f":(literal){path}")
        lines = added_lines(patch)
        if lines:
            result[path] = lines
    return result


def line_counts(segments: list[list]) -> dict[int, int | None]:
    if not isinstance(segments, list):
        raise ValueError("Coverage segments must be an array")
    previous = (0, 0)
    for segment in segments:
        if (
            not isinstance(segment, list) or len(segment) != 6
            or any(type(segment[index]) is not int for index in (0, 1, 2))
            or any(type(segment[index]) is not bool for index in (3, 4, 5))
            or segment[0] < 1 or segment[1] < 0 or segment[2] < 0
            or (segment[0], segment[1]) < previous
        ):
            raise ValueError(f"Invalid or unsorted coverage segment: {segment!r}")
        previous = (segment[0], segment[1])
    if not segments:
        return {}
    if all(segment[1] == 0 for segment in segments):
        return {segment[0]: segment[2] for segment in segments if segment[3]}
    if any(segment[1] == 0 for segment in segments):
        raise ValueError("Cannot mix line-only and LLVM column-based segments")

    counts = {}
    wrapped = None
    index = 0
    for line in range(1, segments[-1][0] + 1):
        current = []
        while index < len(segments) and segments[index][0] == line:
            current.append(segments[index])
            index += 1
        entries = [segment for segment in current if segment[3] and segment[4] and not segment[5]]
        skipped = bool(current and not current[0][3] and current[0][4])
        mapped = (
            not skipped and (bool(wrapped and wrapped[3]) or bool(entries))
        ) or any(segment[3] and segment[4] for segment in current)
        counts[line] = max(
            [wrapped[2] if wrapped else 0, *(segment[2] for segment in entries)]
        ) if mapped else None
        if current:
            wrapped = current[-1]
    return counts


def report_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"Coverage report does not exist: {path}")
    details = path / "coverage_details.json"
    if details.is_file():
        return [details]
    split = path / "code_coverage_details"
    files = sorted((split if split.is_dir() else path).rglob("*.json"))
    if files:
        return files
    files = sorted(
        candidate
        for pattern in ("*.xml", "*.lcov", "*.info")
        for candidate in path.rglob(pattern)
    )
    if not files:
        raise ValueError(f"No supported coverage reports found in {path}")
    return files


def normalize_filename(filename: str, roots: list[str]) -> str:
    name = posixpath.normpath(filename.replace("\\", "/"))
    for root in sorted(roots, key=len, reverse=True):
        prefix = posixpath.normpath(root.replace("\\", "/")).rstrip("/") + "/"
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def load_cobertura(path: Path, repo: Path) -> dict[str, dict[int, int]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise ValueError(f"{path}: invalid XML: {error}") from error
    if root.tag.rsplit("}", 1)[-1] != "coverage":
        raise ValueError(f"{path}: expected a Cobertura coverage XML document")

    repo_root = posixpath.normpath(str(repo).replace("\\", "/"))
    sources = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "source" and element.text:
            source = posixpath.normpath(element.text.strip().replace("\\", "/"))
            if not posixpath.isabs(source):
                source = posixpath.normpath(posixpath.join(repo_root, source))
            sources.append(source)

    files: dict[str, dict[int, int]] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "class":
            continue
        filename = element.get("filename")
        if not filename:
            raise ValueError(f"{path}: Cobertura class is missing its filename")
        filename = filename.replace("\\", "/")
        candidates = (
            [filename] if posixpath.isabs(filename)
            else [posixpath.join(source, filename) for source in sources] + [filename]
        )
        name = None
        for candidate in candidates:
            relative = normalize_filename(candidate, [repo_root])
            if not posixpath.isabs(relative):
                name = relative
                break
        if name is None:
            name = normalize_filename(candidates[0], sources)
        lines = files.setdefault(name, {})
        for line in element.iter():
            if line.tag.rsplit("}", 1)[-1] != "line":
                continue
            number = line.get("number")
            hits = line.get("hits")
            try:
                line_number = int(number) if number is not None else 0
                count = int(hits) if hits is not None else -1
            except ValueError as error:
                raise ValueError(f"{path}: invalid Cobertura line in {filename}") from error
            if line_number < 1 or count < 0:
                raise ValueError(f"{path}: invalid Cobertura line in {filename}")
            lines[line_number] = max(lines.get(line_number, 0), count)
    if not files:
        raise ValueError(f"{path}: no file-level Cobertura coverage data")
    return files


def load_lcov(path: Path, repo: Path) -> dict[str, dict[int, int]]:
    files: dict[str, dict[int, int]] = {}
    filename = None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        raise
    for text in content.splitlines():
        if text == "end_of_record":
            filename = None
            continue
        if text.startswith("SF:"):
            filename = text[3:]
            if not filename:
                raise ValueError(f"{path}: LCOV source record has an empty filename")
            files.setdefault(normalize_filename(filename, [str(repo)]), {})
        elif text.startswith("DA:"):
            if filename is None:
                raise ValueError(f"{path}: LCOV line record appears before a source record")
            parts = text[3:].split(",")
            if len(parts) < 2:
                raise ValueError(f"{path}: invalid LCOV line record: {text}")
            try:
                number, count = int(parts[0]), int(parts[1])
            except ValueError as error:
                raise ValueError(f"{path}: invalid LCOV line record: {text}") from error
            if number < 1 or count < 0:
                raise ValueError(f"{path}: invalid LCOV line record: {text}")
            name = normalize_filename(filename, [str(repo)])
            lines = files[name]
            lines[number] = max(lines.get(number, 0), count)
    if not files or not any(files.values()):
        raise ValueError(f"{path}: no line coverage data in LCOV report")
    return files


def load_coverage(
    paths: list[Path], repo: Path, evidence: list[dict] | None = None,
) -> dict[str, list[dict[int, int | None]]]:
    coverage: dict[str, list[dict[int, int | None]]] = {}
    seen = set()
    for path in paths:
        for report_path in report_files(path):
            resolved = report_path.resolve()
            if resolved in seen:
                raise ValueError(f"Duplicate coverage input: {report_path}")
            seen.add(resolved)
            if report_path.suffix.lower() == ".xml":
                files = load_cobertura(report_path, repo)
                for name, counts in files.items():
                    coverage.setdefault(name, []).append(counts)
                if evidence is not None:
                    evidence.append({
                        "path": str(report_path),
                        "files": {name: {} for name in files},
                        "line_only": True,
                    })
                continue
            if report_path.suffix.lower() in (".lcov", ".info"):
                files = load_lcov(report_path, repo)
                for name, counts in files.items():
                    coverage.setdefault(name, []).append(counts)
                if evidence is not None:
                    evidence.append({
                        "path": str(report_path),
                        "files": {name: {} for name in files},
                        "line_only": True,
                    })
                continue
            with report_path.open(encoding="utf-8") as report_file:
                report = json.load(report_file)
            if not isinstance(report, dict):
                raise ValueError(f"{report_path}: expected a coverage JSON object")
            roots = [str(repo)]
            build_info = report.get("build_info", {})
            if not isinstance(build_info, dict):
                raise ValueError(f"{report_path}: build_info must be an object")
            project_root = build_info.get("project_root")
            if project_root:
                if not isinstance(project_root, str):
                    raise ValueError(f"{report_path}: project_root must be a string")
                roots.append(project_root)
            if "data" in report:
                exports = report["data"]
                if not isinstance(exports, list) or any(
                    not isinstance(export, dict) or not isinstance(export.get("files"), list)
                    for export in exports
                ):
                    raise ValueError(f"{report_path}: expected data entries containing files arrays")
                files = [file for export in exports for file in export["files"]]
            else:
                files = [report]
            if not files:
                raise ValueError(f"{report_path}: no file-level coverage data")
            for file in files:
                if (
                    not isinstance(file, dict)
                    or not isinstance(file.get("filename"), str)
                    or not file["filename"]
                    or "segments" not in file
                ):
                    raise ValueError(
                        f"{report_path}: line coverage requires details with filename and segments; "
                        "summary-only reports are not supported"
                    )
                name = normalize_filename(file["filename"], roots)
                coverage.setdefault(name, []).append(line_counts(file["segments"]))
            if evidence is not None:
                exports = report["data"] if "data" in report else [report]
                for export in exports:
                    functions = export.get("functions", [])
                    if not isinstance(functions, list):
                        raise ValueError(f"{report_path}: functions must be an array")
                    evidence.append({
                        "path": str(report_path),
                        "build_info": build_info,
                        "type": report.get("type"),
                        "version": report.get("version"),
                        "files": {
                            normalize_filename(file["filename"], roots): file
                            for file in (export["files"] if "data" in report else [report])
                        },
                        "functions": functions,
                        "has_functions": "functions" in export,
                        "roots": roots,
                    })
    return coverage


def compare_coverage(
    changes: dict[str, dict[int, str]],
    coverage: dict[str, list[dict[int, int | None]]],
) -> dict:
    output = []
    for filename, lines in changes.items():
        reports = coverage.get(filename)
        for number, source in sorted(lines.items()):
            counts = [report.get(number) for report in reports] if reports else []
            mapped = [count for count in counts if count is not None]
            count = sum(mapped) if mapped else None
            if not reports:
                status = "missing"
            elif not mapped:
                status = "not_instrumented"
            else:
                status = "covered" if any(mapped) else "uncovered"
            output.append({
                "file": filename, "line": number, "status": status,
                "count": count, "source": source,
            })
    totals = Counter(line["status"] for line in output)
    return {
        "summary": {status: totals[status] for status in (
            "covered", "uncovered", "not_instrumented", "missing"
        )},
        "lines": output,
    }


def source_digest(repo: Path, filename: str, target: str | None) -> str:
    if target is None:
        return source_hash(repo, filename, (repo / filename).read_bytes())
    data = subprocess.run(
        ["git", "-C", str(repo), "show", f"{target}:{filename}"],
        check=True, capture_output=True,
    ).stdout
    return hashlib.sha256(data).hexdigest()


def intersects(start: int, end: int, end_column: int, lines: dict[int, str]) -> list[int]:
    last = end - (end_column == 1 and end > start)
    return [line for line in lines if start <= line <= last]


def validate_range(region: list, size: int) -> None:
    if (
        not isinstance(region, list) or len(region) != size
        or any(type(value) is not int or value < 0 for value in region)
        or region[0] < 1 or region[1] < 1
        or (region[2], region[3]) < (region[0], region[1])
    ):
        raise ValueError(f"Invalid coverage region: {region!r}")


def analyze_details(
    repo: Path, revisions: list[str], changes: dict[str, dict[int, str]],
    evidence: list[dict], result: dict, metrics: list[str], scope: str,
) -> None:
    commits = diff_revisions(repo, revisions)
    target = commits[-1] if len(commits) == 2 else None
    expected_commit = target or run_git(repo, "rev-parse", "HEAD").strip()
    failures: dict[tuple[str, int], set[str]] = {}
    errors = []
    regions: dict[tuple, dict] = {}
    branches: dict[tuple, dict] = {}
    functions: dict[tuple, dict] = {}

    def fail(filename: str, lines: list[int], reason: str) -> None:
        for line in lines:
            failures.setdefault((filename, line), set()).add(reason)

    def invalid(filename: str, report: str, message: str) -> None:
        errors.append({"file": filename, "report": report, "message": message})
        fail(filename, list(changes[filename]), message)

    for item in result["lines"]:
        if item["status"] == "missing" or ("lines" in metrics and item["status"] == "uncovered"):
            fail(item["file"], [item["line"]], item["status"])

    for filename, lines in changes.items():
        matching = [report for report in evidence if filename in report["files"]]
        expected_hash = source_digest(repo, filename, target) if matching else None
        for report in matching:
            if report.get("line_only"):
                unsupported = []
                if "regions" in metrics:
                    unsupported.append("region")
                if "branches" in metrics:
                    unsupported.append("branch")
                if scope == "functions":
                    unsupported.append("function")
                if unsupported:
                    invalid(
                        filename, report["path"],
                        f"{', '.join(unsupported)} coverage unavailable in line-only report",
                    )
                continue
            info = report["build_info"]
            if info.get("git_commit") != expected_commit:
                invalid(filename, report["path"], "missing or mismatched report revision")
            hashes = info.get("source_hashes", {})
            if not isinstance(hashes, dict) or hashes.get(filename) != expected_hash:
                invalid(filename, report["path"], "missing or mismatched source hash")
            if report["type"] == "llvm.coverage.json.export" and report["version"] not in ("2.0.1", "3.0.1"):
                invalid(filename, report["path"], "unsupported LLVM export version")
            file = report["files"][filename]
            if ("regions" in metrics or scope == "functions") and not report["has_functions"]:
                invalid(filename, report["path"], "function region data unavailable")
            if "branches" in metrics and not isinstance(file.get("branches"), list):
                invalid(filename, report["path"], "branch data unavailable")
            if (
                report["type"] == "llvm.coverage.json.export"
                and ("regions" in metrics or "branches" in metrics)
                and not isinstance(file.get("expansions"), list)
            ):
                invalid(filename, report["path"], "macro expansion data unavailable")

            spans = []
            for function in report["functions"]:
                if not isinstance(function, dict):
                    raise ValueError(f"{report['path']}: expected function objects")
                filenames = function.get("filenames")
                if (
                    not isinstance(filenames, list) or any(not isinstance(name, str) for name in filenames)
                    or not isinstance(function.get("regions"), list)
                    or not isinstance(function.get("name"), str)
                ):
                    raise ValueError(f"{report['path']}: invalid function coverage data")
                code_regions = []
                for region in function["regions"]:
                    validate_range(region, 8)
                    if region[5] >= len(filenames):
                        raise ValueError("Function region file index is out of bounds")
                    name = normalize_filename(filenames[region[5]], report["roots"])
                    if name == filename and region[7] == 0:
                        code_regions.append(region)
                if not code_regions:
                    continue
                start = min(region[0] for region in code_regions)
                end_line, end_column = max((region[2], region[3]) for region in code_regions)
                end = end_line - (end_column == 1 and end_line > start)
                anchors = intersects(start, end, 2, lines)
                if not anchors:
                    continue
                spans.append((start, end, anchors))
                function_key = (filename, function["name"], start, end)
                entry = functions.setdefault(function_key, {
                    "file": filename, "name": function.get("demangled_name", function["name"]),
                    "start_line": start, "end_line": end, "count": 0, "changed_lines": anchors,
                })
                count = function.get("count")
                if type(count) is not int or count < 0:
                    raise ValueError("Invalid function execution count")
                entry["count"] += count
                for region in code_regions:
                    affected = anchors if scope == "functions" else intersects(region[0], region[2], region[3], lines)
                    if not affected or "regions" not in metrics:
                        continue
                    key = (filename, *region[:4])
                    entry = regions.setdefault(key, {
                        "file": filename, "start_line": region[0], "start_column": region[1],
                        "end_line": region[2], "end_column": region[3], "count": 0,
                        "changed_lines": affected,
                    })
                    entry["count"] += region[4]

            if scope == "functions" and "lines" in metrics:
                counts = line_counts(file["segments"])
                for start, end, anchors in spans:
                    for number in range(start, end + 1):
                        if counts.get(number) is not None:
                            key = (filename, number, 0, number, 0)
                            entry = regions.setdefault(key, {
                                "file": filename, "start_line": number, "start_column": 0,
                                "end_line": number, "end_column": 0, "count": 0,
                                "changed_lines": anchors, "metric": "lines",
                            })
                            entry["count"] += counts[number]
            for expansion in file.get("expansions", []):
                source = expansion["source_region"]
                validate_range(source, 8)
                affected = intersects(source[0], source[2], source[3], lines)
                if scope == "functions":
                    affected = sorted({
                        line for start, end, anchors in spans
                        if start <= source[0] <= end for line in anchors
                    })
                if not affected:
                    continue
                names = expansion["filenames"]
                targets = expansion["target_regions"]
                expanded_ids = {source[6]}
                for region in targets:
                    validate_range(region, 8)
                while True:
                    nested = {
                        region[6] for region in targets
                        if region[7] == 1 and region[5] in expanded_ids
                    }
                    if nested <= expanded_ids:
                        break
                    expanded_ids.update(nested)
                candidates = []
                if "regions" in metrics:
                    candidates.extend(("regions", region) for region in targets
                                      if region[5] in expanded_ids and region[7] == 0)
                if "branches" in metrics:
                    if not isinstance(expansion.get("branches"), list):
                        invalid(filename, report["path"], "expanded branch data unavailable")
                    else:
                        candidates.extend(("branches", branch) for branch in expansion["branches"])
                for metric, region in candidates:
                    validate_range(region, 8 if metric == "regions" else 9)
                    file_id = region[5] if metric == "regions" else region[6]
                    if file_id >= len(names) or not isinstance(names[file_id], str):
                        raise ValueError("Expansion file index is out of bounds")
                    definition = normalize_filename(names[file_id], report["roots"])
                    key = (filename, "expansion", *source[:4], definition, *region[:4])
                    collection = regions if metric == "regions" else branches
                    entry = collection.setdefault(key, {
                        "file": filename, "start_line": region[0], "start_column": region[1],
                        "end_line": region[2], "end_column": region[3],
                        "definition_file": definition, "expansion_line": source[0],
                        "changed_lines": affected,
                        **({"count": 0} if metric == "regions" else {"true_count": 0, "false_count": 0}),
                    })
                    if metric == "regions":
                        entry["count"] += region[4]
                    else:
                        entry["true_count"] += region[4]
                        entry["false_count"] += region[5]
            if "branches" in metrics:
                for branch in file.get("branches", []):
                    validate_range(branch, 9)
                    affected = intersects(branch[0], branch[2], branch[3], lines)
                    if scope == "functions":
                        affected = sorted({
                            line for start, end, anchors in spans
                            if start <= branch[0] <= end for line in anchors
                        })
                    if not affected:
                        continue
                    key = (filename, *branch[:4])
                    entry = branches.setdefault(key, {
                        "file": filename, "start_line": branch[0], "start_column": branch[1],
                        "end_line": branch[2], "end_column": branch[3],
                        "true_count": 0, "false_count": 0, "changed_lines": affected,
                    })
                    entry["true_count"] += branch[4]
                    entry["false_count"] += branch[5]

    region_items = []
    function_line_items = []
    for item in regions.values():
        item["status"] = "covered" if item["count"] else "uncovered"
        metric = item.pop("metric", "regions")
        (region_items if metric == "regions" else function_line_items).append(item)
        if not item["count"]:
            fail(item["file"], item["changed_lines"], f"uncovered {metric} at line {item['start_line']}")
    for item in branches.values():
        item["status"] = "covered" if item["true_count"] and item["false_count"] else "uncovered"
        if item["status"] == "uncovered":
            fail(item["file"], item["changed_lines"], f"uncovered branch outcome at line {item['start_line']}")
    for item in functions.values():
        item["status"] = "covered" if item["count"] else "uncovered"

    def metric_summary(items: list[dict]) -> dict:
        return {status: sum(item["status"] == status for item in items) for status in ("covered", "uncovered")}

    result.update({
        "schema_version": 1,
        "comparison": {"revisions": revisions, "destination_commit": expected_commit, "working_tree": target is None},
        "policy": {"metrics": metrics, "scope": scope},
        "regions": region_items,
        "branches": list(branches.values()),
        "functions": list(functions.values()),
        "function_lines": function_line_items,
        "metrics": {
            "lines": result["summary"], "regions": metric_summary(region_items),
            "branches": metric_summary(list(branches.values())),
        },
        "validation": {"errors": errors},
        "gate": {
            "uncovered": len(failures), "errors": len(errors),
            "lines": [
                {"file": file, "line": line, "reasons": sorted(reasons)}
                for (file, line), reasons in sorted(failures.items())
            ],
        },
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "revisions", nargs="+",
        help="Base ref (compared to working tree), two refs, or A..B / A...B",
    )
    parser.add_argument(
        "--coverage", nargs="+", required=True, type=Path,
        help="One or more coverage details JSON files or report directories",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Git repository directory")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--include", action="append", default=[], help="Repository-relative glob to include (repeatable)")
    parser.add_argument("--exclude", action="append", default=[], help="Repository-relative glob to exclude (repeatable)")
    parser.add_argument("--metrics", nargs="+", choices=["lines", "regions", "branches"], default=["lines", "regions", "branches"])
    parser.add_argument("--scope", choices=["diff", "functions"], default="diff")
    args = parser.parse_args(argv)
    if len(args.revisions) > 2:
        parser.error("Specify one base ref, two refs, or one Git range")
    try:
        repo = Path(run_git(args.repo, "rev-parse", "--show-toplevel").strip())
        changes = {
            name: lines for name, lines in changed_lines(repo, args.revisions).items()
            if (not args.include or any(fnmatchcase(name, pattern) for pattern in args.include))
            and not any(fnmatchcase(name, pattern) for pattern in args.exclude)
        }
        evidence: list[dict] = []
        result = compare_coverage(changes, load_coverage(args.coverage, repo, evidence))
        analyze_details(repo, args.revisions, changes, evidence, result, args.metrics, args.scope)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        message = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        parser.exit(2, f"error: {message}\n")
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        for line in result["lines"]:
            count = "-" if line["count"] is None else str(line["count"])
            print(f"{line['status']:16} {line['file']}:{line['line']} ({count}) {line['source']}")
        print("Summary: " + ", ".join(f"{key}={value}" for key, value in result["summary"].items()))
        for item in result["gate"]["lines"]:
            print(f"GATE {item['file']}:{item['line']}: {', '.join(item['reasons'])}")
        print(f"Gate: uncovered={result['gate']['uncovered']}, errors={result['gate']['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())