from pathlib import Path
import os

import metabuild.public as mb

mb.set_root_directory("..")
mb.project_link("googletest")

mb.load("//profile", "profile_data")
mb.load("//bundle", "build_info_dict", "get_git_commit")
mb.load("//website", "generate_website", "copy_local_data")
mb.load("//test", "get_ios_device")
mb.load(
    "code_coverage//artifactory",
    "get_directory_contents",
    "gen_aql",
)
mb.load("code_coverage//website", "download_remote_data")
mb.load("//open_cpp_coverage", "run_with_open_cpp_coverage")
mb.load("code_coverage//options", "COVERAGE_OPTION_NAME", "BULLSEYE_STR", "OPEN_CPP_COVERAGE_STR")

ROOT_PATH = Path(__file__).parents[1]
ARTIFACTORY_ROOT = "https://artifactory.corp.adobe.com/artifactory"
ARTIFACTORY_REPO = "generic-code-coverage-release-local"
OPEN_CPP_COVERAGE_STR: str
COVERAGE_OPTION_NAME: str
BULLSEYE_STR: str

# TODO: This should be an option
test_output_directory = "$(output_directory)/tests/out"


async def test_runner(ctx):
    ios_dst = None
    platform = await ctx.eval_async("$(config.platform)")
    tool = await ctx.eval_async(f"$(option {COVERAGE_OPTION_NAME})")

    if platform == "ios":
        ios_dst = await get_ios_device(
            ctx, "iPhone", is_sim=True, exact_match_only=False
        )
    if tool == OPEN_CPP_COVERAGE_STR:
        src_path = ROOT_PATH / "example"
        test_path = await ctx.eval_async(f"$(exe :test_binary)")
        await run_with_open_cpp_coverage(ctx, src_path, test_path)
    else:
        await ctx.invoke(
            ":test_binary",
            xcode_destination=ios_dst,
        )


def zip_filename(tool, platform, config, cpu_arch):
    prepend_folder_name = "coverage_results"
    return f"{prepend_folder_name}_{tool}_{platform}_{config}_{cpu_arch}.zip"


def _remote_dir_path(branch_name, build_number):
    return f"test_results/{branch_name}/{build_number}"


def remote_url_dir_path(branch_name, build_number):
    url_path = f"{ARTIFACTORY_ROOT}/{ARTIFACTORY_REPO}/{_remote_dir_path(branch_name, build_number)}"
    return url_path


def bundle_url():
    filename = zip_filename(
        "$(option //options:tool)",
        "$(config.platform)",
        "$(config.type)",
        "$(config.cpu_arch)",
    )
    url_parts = [
        remote_url_dir_path(
            "$(option //options:branch_name)",
            "$(option //options:build_number)",
        ),
        filename,
    ]
    url = "/".join(url_parts)
    # mb.log.debug(f"url = {url}")
    return url


async def download_all(ctx):
    # artifactory_user = os.environ.get("ARTIFACTORY_USER")
    artifactory_api_key = os.environ.get("ARTIFACTORY_API_KEY")
    branch_name = await ctx.eval_async("$(option //options:branch_name)")
    build_number = await ctx.eval_async("$(option //options:build_number)")
    remote_dir_path = _remote_dir_path(branch_name, build_number)
    url_path = f"{ARTIFACTORY_ROOT}/{ARTIFACTORY_REPO}/{remote_dir_path}"
    mb.log.debug(f"AQL .zip files in {url_path}")
    aql = gen_aql([remote_dir_path], ARTIFACTORY_REPO, "*.zip")
    zip_files = get_directory_contents(artifactory_api_key, aql, ARTIFACTORY_ROOT)
    urls = []
    for zip_file in zip_files:
        zip_file_name = zip_file["name"]
        test_result_url = (
            f"{ARTIFACTORY_ROOT}/{ARTIFACTORY_REPO}/{remote_dir_path}/{zip_file_name}"
        )
        urls.append(test_result_url)
    mb.log.debug(f"Download URLs: {urls}")
    appendage_bug = Path("out")
    await download_remote_data(ctx, artifactory_api_key, urls, appendage_bug)
    return urls


async def _gen_profile_data(ctx):
    mb.log.info("Generating profile data")
    platform = await ctx.eval_async("$(config.platform)")
    branch_name = await ctx.eval_async("$(option code_coverage//options:branch_name)")
    build_number = await ctx.eval_async("$(option code_coverage//options:build_number)")
    test_path = await ctx.eval_async(f"$(exe :test_binary)")
    git_commit = await get_git_commit(ctx)
    project_root = Path(await ctx.eval_async("$(project_root)/..")).resolve()
    mb.log.info(f"project_root: {project_root}")
    build_info = await build_info_dict(
        branch_name=branch_name,
        build_number=build_number,
        project_root=project_root,
        git_commit=git_commit,
    )

    await profile_data(
        ctx,
        platform,
        test_path,
        build_info,
        "dist",
        gen_html=True,
        gen_lcov=True,
        gen_lcov_to_cobertura=True,
    )


mb.cxx_library(
    name="example_library",
    public_include_directories="example/include",
    srcs=[
        mb.cpp_glob(
            ["example/include/**", "example/src/**"],
        ),
    ],
)

mb.cxx_binary(
    name="test_binary",
    srcs=[
        mb.cpp_glob(
            ["example/test/include/**", "example/test/src/**"],
        ),
    ],
    tests=":test_runner",
    xcode_product_type=(mb.target.macos, "tool"),
    xcode_flags={
        "PRODUCT_BUNDLE_IDENTIFIER": "com.adobe.photoshop.code_coverage.example"
    },
    xcode_scheme={
        "LaunchAction": {
            "EnvironmentVariables[]": [
                {
                    "EnvironmentVariable": {
                        "key": "LLVM_PROFILE_FILE",
                        "value": f"{test_output_directory}/coverage.profraw",
                        "isEnabled": True,
                    },
                },
            ],
        },
    },
    deps=[
        ":example_library",
        "googletest//:gtest",
        "googletest//:gmock",
        "googletest//:gmock_main",
    ],
)


mb.test(
    name="test_runner",
    py=test_runner,
    deps = [
        (mb.target.option(COVERAGE_OPTION_NAME, BULLSEYE_STR), "code_coverage//bullseye:off"),
    ]
)

mb.genrule(name="_gen_profile_data", py=_gen_profile_data)

mb.build_group(
    name="generate_profile_data",
    deps=[":_gen_profile_data"],
)


async def gen_website(ctx):
    mb.log.info(f"Generating website")
    mb.log.info("ROOT_PATH", ROOT_PATH)
    src_list = [
        "example/src",
        "example/include",
        "example/test/src",
    ]
    await generate_website(ctx, src_list, ROOT_PATH)


mb.genrule(
    name="copy_data",
    py=copy_local_data,
    args={
        "test_output_directory": test_output_directory,
    },
    deps=[
        ":generate_profile_data",
    ],
)

mb.genrule(
    name="gen_website",
    py=gen_website,
)


mb.build_group(
    name="generate_website",
    deps=[
        ":gen_website",
        ":copy_data",
    ],
)

mb.archive_artifacts(
    name="_archive",
    data=[
        test_output_directory,
    ],
)

mb.build_group(
    name="archive_output",
    deps=[
        ":_archive",
    ],
)

mb.http_upload(
    name="_upload",
    src="$(location :_archive)",
    phase="build",
    sharing="cpu_arch",
    url=bundle_url(),
    deps=[
        ":_archive",
    ],
)

mb.build_group(
    name="upload_output",
    deps=[
        ":_upload",
    ],
)

mb.genrule(
    name="download_data",
    py=download_all,
)

mb.build_group(
    name="generate_website_from_remote",
    deps=[
        ":gen_website",
        ":download_data",
    ],
)
