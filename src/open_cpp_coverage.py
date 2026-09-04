from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def coverage_file_path():
    coverage_file = Path(os.environ.get("COVERAGE_FILE"))
    return coverage_file


async def profile_open_cpp_coverage_data(ctx, build_info):
    logger.info("Generating OpenCppCoverage profile data")
    coverage_file = coverage_file_path()
    logger.debug("coverage_file: %s", coverage_file)
    test_output_path = coverage_file.parent
    export_xml_path = Path(test_output_path, "coverage_details.xml")
    open_cpp_cov_export_cmd = [
        "OpenCppCoverage",
        "--quiet",
        f"--input_coverage={coverage_file}",
        f"--export_type=cobertura:{export_xml_path}",
    ]

    await ctx.execute(open_cpp_cov_export_cmd)
    return export_xml_path


async def run_with_open_cpp_coverage(ctx, src_path, test_binary_path):
    coverage_file = coverage_file_path()
    stdoutput = await ctx.execute(
        [
            "OpenCppCoverage.exe",
            "--quiet",
            f"--export_type=binary:{coverage_file}",
            f"--sources={src_path}",
            "--",
            test_binary_path,
        ]
    )
    return stdoutput
