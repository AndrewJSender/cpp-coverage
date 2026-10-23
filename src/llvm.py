# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import subprocess
import os
import json
from pathlib import Path
import logging

from lcov_cobertura import LcovCobertura

logger = logging.getLogger(__name__)

def llvm_profile_path():
    llvm_profile_file = os.environ.get("LLVM_PROFILE_FILE")
    if llvm_profile_file is None:
        raise ValueError("LLVM_PROFILE_FILE environment variable is not set")
    return Path(llvm_profile_file)


def run_subprocess(cmd_parts, out_path):
    with open(out_path, "w") as outfile:
        logger.debug("Running: %s", " ".join(cmd_parts))
        subprocess.run(cmd_parts, stdout=outfile)


def demangle_function_names(details_json_path: Path, llvm_cxxfilt: str) -> None:
    with open(details_json_path, encoding="utf-8") as details_file:
        details = json.load(details_file)

    functions = [
        function
        for export in details["data"]
        for function in export.get("functions", [])
    ]
    if not functions:
        return

    result = subprocess.run(
        [llvm_cxxfilt],
        input="".join(f"{function['name']}\n" for function in functions),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    names = result.stdout.splitlines()
    if len(names) != len(functions) or any(not name for name in names):
        raise ValueError("C++ demangler returned an unexpected number of function names or an empty name")

    for function, name in zip(functions, names):
        function["demangled_name"] = name

    with open(details_json_path, "w", encoding="utf-8") as details_file:
        json.dump(details, details_file)


async def profile_llvm_data(
    ctx,
    platform,
    test_path,
    build_info,
    output_directory,
    gen_html=False,
    gen_lcov=False,
    gen_lcov_to_cobertura=False,
):
    project_root = Path(build_info["project_root"])
    ignore_filename_regex = f"{project_root}/{output_directory}"
    coverage_file_path = llvm_profile_path()
    profile_stem = coverage_file_path.stem
    test_output_path = coverage_file_path.parent

    if platform in ["macos", "ios"]:
        llvm_profdata = await ctx.eval_async("$(xcode_tool llvm-profdata)")
        llvm_cov = await ctx.eval_async("$(xcode_tool llvm-cov)")
        llvm_cxxfilt = await ctx.eval_async("$(xcode_tool c++filt)")
    elif platform in ["win32"]:
        msvs_path = await ctx.eval_async("$(msvs_install_dir)")
        ignore_filename_regex = f"{project_root}\\{output_directory}"
        ignore_filename_regex = ignore_filename_regex.replace("\\", "\\\\")
        llvm_profdata = await ctx.eval_async(
            f"{msvs_path}/VC/Tools/Llvm/x64/bin/llvm-profdata.exe"
        )
        llvm_cov = await ctx.eval_async(
            f"{msvs_path}/VC/Tools/Llvm/x64/bin/llvm-cov.exe"
        )
        llvm_cxxfilt = await ctx.eval_async(
            f"{msvs_path}/VC/Tools/Llvm/x64/bin/llvm-cxxfilt.exe"
        )

    elif platform in ["linux"]:
        llvm_bin_path = await ctx.eval_async("/usr/lib/llvm-18/bin")
        llvm_profdata = await ctx.eval_async(f"{llvm_bin_path}/llvm-profdata")
        llvm_cov = await ctx.eval_async(f"{llvm_bin_path}/llvm-cov")
        llvm_cxxfilt = await ctx.eval_async(f"{llvm_bin_path}/c++filt")
    else:
        logger.warning("platform %s not supported", platform)
        return

    llvm_cov_common_args = [
        f"--instr-profile={test_output_path}/{profile_stem}.profdata",
        f"--ignore-filename-regex={ignore_filename_regex}",
        f"{test_path}",
    ]

    llvm_profdata_merge_cmd = [
        llvm_profdata,
        "merge",
        "-sparse",
        f"{test_output_path}/{profile_stem}.profraw",
        "-o",
        f"{test_output_path}/{profile_stem}.profdata",
    ]

    await ctx.execute(llvm_profdata_merge_cmd)

    details_json_path = Path(f"{test_output_path}", "coverage_details.json")
    details_cmd = [llvm_cov, "export", "--format=text"] + llvm_cov_common_args
    run_subprocess(details_cmd, details_json_path)
    demangle_function_names(details_json_path, llvm_cxxfilt)

    lcov_path = Path(f"{test_output_path}", "coverage.lcov")
    if gen_lcov or gen_lcov_to_cobertura:
        logger.info("Generating lcov data")
        export_lcov_cmd = [llvm_cov, "export", "--format=lcov"] + llvm_cov_common_args
        run_subprocess(export_lcov_cmd, lcov_path)

    if gen_lcov_to_cobertura:
        logger.info("Generating lcov to cobertura data")
        xml_path = Path(f"{test_output_path}", "coverage.xml")
        demangle = True
        base_dir = project_root.__str__()
        excludes = []
        with open(lcov_path, 'r') as lcov_file:
            lcov_data = lcov_file.read()
            lcov_cobertura = LcovCobertura(lcov_data, base_dir, excludes, demangle, llvm_cxxfilt)
            cobertura_xml = lcov_cobertura.convert()
        with open(xml_path, mode='wt') as output_file:
            output_file.write(cobertura_xml)


    llvm_cov_common_args.append("--summary-only")
    summary_json_path = Path(f"{test_output_path}", "coverage_summary.json")
    summary_cmd = [llvm_cov, "export", "--format=text"] + llvm_cov_common_args
    run_subprocess(summary_cmd, summary_json_path)

    if gen_html:
        await ctx.execute(
            [
                llvm_cov,
                "show",
                f"--output-dir={test_output_path}/coverage_html",
                "--format=html",
            ]
            + llvm_cov_common_args
        )

    return (details_json_path, summary_json_path)
