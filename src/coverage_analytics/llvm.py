# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import subprocess
import os
import json
import re
from pathlib import Path
import logging

from coverage_analytics.lcov_cobertura import LcovCobertura

logger = logging.getLogger(__name__)

def llvm_profile_path():
    llvm_profile_file = os.environ.get("LLVM_PROFILE_FILE")
    if llvm_profile_file is None:
        raise ValueError("LLVM_PROFILE_FILE environment variable is not set")
    return Path(llvm_profile_file)


def run_subprocess(cmd_parts, out_path):
    with open(out_path, "w") as outfile:
        logger.debug("Running: %s", " ".join(cmd_parts))
        subprocess.run(cmd_parts, stdout=outfile, check=True)


MSVC_SIGNATURE_PREFIXES = ("public: ", "protected: ", "private: ", "static ", "virtual ")
MSVC_CALLING_CONVENTIONS = re.compile(
    r"\b(?:__cdecl|__stdcall|__thiscall|__fastcall|__vectorcall|__clrcall)\s+"
)


def simplify_microsoft_name(demangled: str) -> str:
    """Reduce an MSVC-style signature to the Itanium-style qualified name.

    For example, ``public: void __cdecl CoverageClass::functionCovered(void)``
    becomes ``CoverageClass::functionCovered()``.
    """
    name = demangled
    while name.startswith(MSVC_SIGNATURE_PREFIXES):
        for prefix in MSVC_SIGNATURE_PREFIXES:
            name = name.removeprefix(prefix)
    # The return type precedes the outermost calling convention.
    match = MSVC_CALLING_CONVENTIONS.search(name)
    if match:
        name = name[match.end():]
    return name.replace("(void)", "()")


def run_demangler(demangler: str, names: list[str], echoes_input: bool = False) -> list[str]:
    result = subprocess.run(
        [demangler],
        input="".join(f"{name}\n" for name in names),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    lines = result.stdout.splitlines()
    # llvm-undname echoes each redirected input line before its demangled name.
    if echoes_input and len(lines) == 2 * len(names) and lines[::2] == names:
        lines = lines[1::2]
    if len(lines) != len(names) or any(not line for line in lines):
        raise ValueError("C++ demangler returned an unexpected number of function names or an empty name")
    return lines


def demangle_function_names(
    details_json_path: Path, llvm_cxxfilt: str, llvm_undname: str | None = None
) -> None:
    with open(details_json_path, encoding="utf-8") as details_file:
        details = json.load(details_file)

    functions = [
        function
        for export in details["data"]
        for function in export.get("functions", [])
    ]
    if not functions:
        return

    # llvm-cxxfilt only reads Itanium symbols from stdin, so MSVC-mangled
    # names (leading "?") go through llvm-undname when it is available.
    def uses_msvc_mangling(function) -> bool:
        return llvm_undname is not None and function["name"].startswith("?")

    msvc_functions = [function for function in functions if uses_msvc_mangling(function)]
    itanium_functions = [function for function in functions if not uses_msvc_mangling(function)]

    if itanium_functions:
        names = run_demangler(llvm_cxxfilt, [function["name"] for function in itanium_functions])
        for function, name in zip(itanium_functions, names):
            function["demangled_name"] = name

    if msvc_functions:
        names = run_demangler(
            llvm_undname,
            [function["name"] for function in msvc_functions],
            echoes_input=True,
        )
        for function, name in zip(msvc_functions, names):
            function["demangled_name"] = simplify_microsoft_name(name)

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
    ignore_filename_regex = re.escape(str(Path(output_directory).resolve()))
    coverage_file_path = llvm_profile_path()
    profile_stem = "coverage"
    test_output_path = coverage_file_path.parent
    profiles = sorted(test_output_path.glob("coverage*.profraw"))
    if coverage_file_path.is_file() and coverage_file_path not in profiles:
        profiles.append(coverage_file_path)
    if not profiles:
        raise FileNotFoundError(f"No raw coverage profiles found in {test_output_path}")

    llvm_undname = None
    if platform in ["macos", "ios"]:
        llvm_profdata = await ctx.eval_async("$(xcode_tool llvm-profdata)")
        llvm_cov = await ctx.eval_async("$(xcode_tool llvm-cov)")
        llvm_cxxfilt = await ctx.eval_async("$(xcode_tool c++filt)")
    elif platform in ["win32"]:
        llvm_bin_path = await ctx.eval_async("$(which llvm-profdata)")
        llvm_profdata = await ctx.eval_async(f"{llvm_bin_path}/llvm-profdata.exe")
        llvm_cov = await ctx.eval_async(f"{llvm_bin_path}/llvm-cov.exe")
        llvm_cxxfilt = await ctx.eval_async(f"{llvm_bin_path}/llvm-cxxfilt.exe")
        llvm_undname = await ctx.eval_async(f"{llvm_bin_path}/llvm-undname.exe")
    elif platform in ["linux"]:
        llvm_bin_path = await ctx.eval_async("$(which llvm-profdata)")
        llvm_profdata = await ctx.eval_async(f"{llvm_bin_path}/llvm-profdata")
        llvm_cov = await ctx.eval_async(f"{llvm_bin_path}/llvm-cov")
        llvm_cxxfilt = await ctx.eval_async(f"{llvm_bin_path}/llvm-cxxfilt")
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
        *(str(path) for path in profiles),
        "-o",
        f"{test_output_path}/{profile_stem}.profdata",
    ]

    await ctx.execute(llvm_profdata_merge_cmd)

    details_json_path = Path(f"{test_output_path}", "coverage_details.json")
    details_cmd = [llvm_cov, "export", "--format=text"] + llvm_cov_common_args
    run_subprocess(details_cmd, details_json_path)
    demangle_function_names(details_json_path, llvm_cxxfilt, llvm_undname)

    lcov_path = Path(f"{test_output_path}", "coverage.lcov")
    if gen_lcov or gen_lcov_to_cobertura:
        logger.info("Generating lcov data")
        export_lcov_cmd = [llvm_cov, "export", "--format=lcov"] + llvm_cov_common_args
        run_subprocess(export_lcov_cmd, lcov_path)

    if gen_lcov_to_cobertura:
        logger.info("Generating lcov to cobertura data")
        xml_path = Path(f"{test_output_path}", "coverage.xml")
        demangle = True
        base_dir = str(build_info["project_root"])
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
