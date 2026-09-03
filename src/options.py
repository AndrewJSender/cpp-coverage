import metabuild.public as mb

COVERAGE_OPTION_NAME = "code_coverage//options:tool"
COVERAGE_CONFIG_NAME = "code_coverage.tool"

CLANG_STR = "clang"
OPEN_CPP_COVERAGE_STR = "open_cpp_coverage"
BULLSEYE_STR = "bullseye"
VSCCOV_STR = "vsccov"
GCOV_STR = "gcov"
LCOV_STR = "lcov"

mb.option(
    name="tool",
    type="string",
    default_value=None,
    choices=[
        CLANG_STR,
        OPEN_CPP_COVERAGE_STR,
        BULLSEYE_STR,
        # VSCCOV_STR,
        # GCOV_STR,
        # LCOV_STR,
    ],
    config=COVERAGE_CONFIG_NAME,
)

mb.option(
    name="branch_name",
    type="string",
    default_value="none",
    config="code_coverage.branch_name",
)

mb.option(
    name="build_number",
    type="int",
    config="code_coverage.build_number",
)
