# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import json
from pathlib import Path
import re
import xml.etree.ElementTree as XmlET
import logging

logger = logging.getLogger(__name__)


async def split_xml_data_to_json(xml_root, output_path, build_info):
    code_coverage_dir = output_path / "code_coverage_details"
    code_coverage_dir.mkdir(parents=True, exist_ok=True)

    file_summary_data = []
    for file in xml_root.findall(".//class"):
        line_count = 0
        line_covered = 0
        filename = file.get("filename")
        segments = []
        for line in file.find(".//lines"):
            line_num = int(line.get("number"))
            hits = int(line.get("hits"))
            line_count += 1
            if hits > 0:
                line_covered += 1
            # https://github.com/llvm/llvm-project/blob/main/llvm/tools/llvm-cov/CoverageExporterJson.cpp#L83-L86
            segments.append([line_num, 0, hits, True, False, False])
        file_data = {
            "filename": filename,
            "summary": {
                "lines": {"count": line_count, "covered": line_covered},
            },
        }
        file_summary_data.append(file_data.copy())
        file_data["segments"] = segments
        file_path = code_coverage_dir / Path(f"{filename}.json")
        file_dir = file_path.parent
        file_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(file_data, f)

    summary_data = {
        "data": [
            {
                "files": file_summary_data,
            }
        ],
        "build_info": build_info,
    }
    with open(output_path / "coverage_summary.json", "w") as f:
        json.dump(summary_data, f)


async def adjust_xml_file(file_path):
    logger.debug("Adjusting xml file: %s", file_path)
    with open(file_path, "r") as f:
        txt = f.read()
    # remove whitespacing
    txt = txt.replace("\n", "")
    txt = re.sub(r">\s+<", "><", txt)
    root = XmlET.fromstring(txt)
    tree = XmlET.ElementTree(root)
    tree.write(file_path)

    return root
