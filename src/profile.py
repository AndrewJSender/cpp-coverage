import json
from pathlib import Path
import re
import xml.etree.ElementTree as XmlET

import metabuild.public as mb

mb.load(
    "code_coverage//options",
    "COVERAGE_OPTION_NAME",
    "CLANG_STR",
    "OPEN_CPP_COVERAGE_STR",
    "BULLSEYE_STR",
)

mb.load("//llvm", "profile_llvm_data")
mb.load("//open_cpp_coverage", "profile_open_cpp_coverage_data")
mb.load("//bullseye", "export_to_xml")
mb.load("//cobertura", "adjust_xml_file", "split_xml_data_to_json")


COVERAGE_OPTION_NAME: str
CLANG_STR: str
OPEN_CPP_COVERAGE_STR: str
BULLSEYE_STR: str


async def adjust_file(file_path, build_info):
    project_root = Path(build_info["project_root"])
    project_root_str = project_root.__str__().replace("\\", "/").replace("//", "/")
    # OpenCppCoveerage truncates the C:\ ... weird
    project_root_str_2 = re.sub(r"^[A-Z]:/", "", project_root_str)
    with open(file_path, "r") as f:
        txt = f.read()
        txt = (
            txt.replace("\\", "/")
            .replace("//", "/")
            .replace(f"{project_root_str}/", "")
            .replace(f"{project_root_str_2}/", "")
        )
    with open(file_path, "w") as f:
        f.write(txt)


async def adjust_json_file(file_path, build_info):
    mb.log.debug(f"Adjusting json file: {file_path}")
    with open(file_path, "r") as f:
        this_json = json.load(f)
    this_json["build_info"] = build_info

    with open(file_path, "w") as f:
        json.dump(this_json, f)


async def split_details(details_json_path):
    with open(details_json_path, "r") as f:
        details_json = json.load(f)

    code_coverage_dir = Path(details_json_path).parent / "code_coverage_details"
    code_coverage_dir.mkdir(parents=True, exist_ok=True)
    for file in details_json["data"][0]["files"]:
        if "filename" not in file:
            continue
        file_path = code_coverage_dir / Path(file["filename"] + ".json")
        file_dir = file_path.parent
        file_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(file, f)


async def profile_data(
    ctx,
    platform,
    test_path,
    build_info,
    output_directory,
    gen_html=False,
    gen_lcov=False,
    gen_lcov_to_cobertura=False,
) -> None:
    tool = await ctx.eval_async(f"$(option {COVERAGE_OPTION_NAME})")
    mb.log.debug("Generating profile data with tool: %s", tool)

    if tool == OPEN_CPP_COVERAGE_STR:
        xml_path = await profile_open_cpp_coverage_data(ctx, build_info)
        await adjust_file(xml_path, build_info)
        xml_root = await adjust_xml_file(xml_path)
        await split_xml_data_to_json(xml_root, xml_path.parent, build_info)
    elif tool == BULLSEYE_STR:
        xml_path = await export_to_xml(ctx)
        await adjust_file(xml_path, build_info)
        xml_root = await adjust_xml_file(xml_path)
        await split_xml_data_to_json(xml_root, xml_path.parent, build_info)
    elif tool == CLANG_STR:
        (details_json_path, summary_json_path) = await profile_llvm_data(
            ctx,
            platform,
            test_path,
            build_info,
            output_directory,
            gen_html=gen_html,
            gen_lcov=gen_lcov,
            gen_lcov_to_cobertura=gen_lcov_to_cobertura,
        )
        await adjust_file(details_json_path, build_info)
        await adjust_file(summary_json_path, build_info)

        await adjust_json_file(details_json_path, build_info)
        await adjust_json_file(summary_json_path, build_info)
        await split_details(details_json_path)
