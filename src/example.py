from pathlib import Path
import os
import logging

from profile import profile_data
from bundle import build_info_dict, get_git_commit
from website import generate_website, copy_local_data, download_remote_data
from test import get_ios_device
from artifactory import get_directory_contents, gen_aql
from open_cpp_coverage import run_with_open_cpp_coverage
from options import COVERAGE_OPTION_NAME, BULLSEYE_STR, OPEN_CPP_COVERAGE_STR

logger = logging.getLogger(__name__)

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
    logger.debug("url = %s", url)
    return url


async def download_all(ctx):
    # artifactory_user = os.environ.get("ARTIFACTORY_USER")
    artifactory_api_key = os.environ.get("ARTIFACTORY_API_KEY")
    branch_name = await ctx.eval_async("$(option //options:branch_name)")
    build_number = await ctx.eval_async("$(option //options:build_number)")
    remote_dir_path = _remote_dir_path(branch_name, build_number)
    url_path = f"{ARTIFACTORY_ROOT}/{ARTIFACTORY_REPO}/{remote_dir_path}"
    logger.debug("AQL .zip files in %s", url_path)
    aql = gen_aql([remote_dir_path], ARTIFACTORY_REPO, "*.zip")
    zip_files = get_directory_contents(artifactory_api_key, aql, ARTIFACTORY_ROOT)
    urls = []
    for zip_file in zip_files:
        zip_file_name = zip_file["name"]
        test_result_url = (
            f"{ARTIFACTORY_ROOT}/{ARTIFACTORY_REPO}/{remote_dir_path}/{zip_file_name}"
        )
        urls.append(test_result_url)
    logger.debug("Download URLs: %s", urls)
    appendage_bug = Path("out")
    await download_remote_data(ctx, artifactory_api_key, urls, appendage_bug)
    return urls


async def _gen_profile_data(ctx):
    logger.info("Generating profile data")
    platform = await ctx.eval_async("$(config.platform)")
    branch_name = await ctx.eval_async("$(option code_coverage//options:branch_name)")
    build_number = await ctx.eval_async("$(option code_coverage//options:build_number)")
    test_path = await ctx.eval_async(f"$(exe :test_binary)")
    git_commit = await get_git_commit(ctx)
    project_root = Path(await ctx.eval_async("$(project_root)/..")).resolve()
    logger.info("project_root: %s", project_root)
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


async def gen_website(ctx):
    logger.info("Generating website")
    logger.info("ROOT_PATH %s", ROOT_PATH)
    src_list = [
        "example/src",
        "example/include",
        "example/test/src",
    ]
    await generate_website(ctx, src_list, ROOT_PATH)
