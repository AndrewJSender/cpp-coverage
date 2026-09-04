# Integrate with metabulid.cxx_library

Add the clang compiler flags to the `//:universe_flags` target.

```python
mb.load("code_coverage//build_spec", "coverage_flags", "msvs_coverage_flags")
mb.load("code_coverage//options", "COVERAGE_OPTION_NAME", "BULLSEYE_STR")
COVERAGE_OPTION_NAME: str
BULLSEYE_STR: str

mb.cxx_library(
    name="universe_flags",
    exported_compiler_flags=[
        coverage_flags,
    ],
    exported_linker_flags=[
        coverage_flags,
    ],
    exported_msvs_flags=[
        msvs_coverage_flags,
    ],
    deps=[
        (mb.target.option(COVERAGE_OPTION_NAME, BULLSEYE_STR), "code_coverage//bullseye:on"),
    ]
)
```

# Set `LLVM_PROFILE_FILE` environment variable

When running the `cxx_binary`, set the `LLVM_PROFILE_FILE` environment variable for where the code coverage (raw) profile data will be written to.

```zsh
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./example_test ...
```

# Create Code Coverage Profile target

Create a metabuild [build_group](https://git.corp.adobe.com/pages/meta-build/meta-build/docs/api/nodes/build_group/) that depends on a [genrule](https://git.corp.adobe.com/pages/meta-build/meta-build/docs/api/nodes/genrule/). Then have the genrule run a python function that calls the [code_coverage//profile:profile_data](../META/profile.meta.py) function.

```python
mb.load("code_coverage//profile", "profile_data")
async def _gen_profile_data(ctx):
    mb.log.info("Generating profile data")
    platform = await ctx.eval_async("$(config.platform)")
    test_path = await ctx.eval_async(f"$(exe :test_binary)")
    project_root = Path(await ctx.eval_async("$(project_root)/..")).resolve()
    build_info = await build_info_dict(branch_name="branch_name", build_number="build_number", project_root=project_root, git_commit="git_commit")
    await profile_data(ctx, platform, test_path, build_info, "dist")


mb.genrule(
    name="_gen_profile_data",
    py=_gen_profile_data,
)

mb.build_group(
    name="generate_profile_data",
    deps=[":_gen_profile_data"],
)
```

# Create Code Coverage Website target

Create a metabuild [build_group](https://git.corp.adobe.com/pages/meta-build/meta-build/docs/api/nodes/build_group/) that depends on a [genrule](https://git.corp.adobe.com/pages/meta-build/meta-build/docs/api/nodes/genrule/). Then have the genrule run a python function that calls the [code_coverage//website:generate_website](../META/website.meta.py) function.

```python
mb.load("code_coverage//website", "generate_website")
ROOT_PATH = Path(__file__).parents[1]
async def gen_website(ctx):
    mb.log.info(f"Generating website")
    src_list = [
        "example/src",
        "example/include",
        "example/test/src",
    ]
    await generate_website(ctx, src_list, ROOT_PATH)

mb.genrule(
    name="gen_website",
    py=gen_website,
)


mb.build_group(
    name="generate_website",
    deps=[
        ":gen_website",
        # ":copy_data",
        # ":download_data",
    ],
)
```

## Import code coverage profile data

There are 2 ways to import the code coverage profile data: copy locally or download remotely.

### Copy data locally

Create a [genrule](https://git.corp.adobe.com/pages/meta-build/meta-build/docs/api/nodes/genrule) which calls the [code_coverage//website:copy_local_data](../META/website.meta.py) function and inputs the `test_output_directory` argument.

```python
mb.load("code_coverage//website", "copy_local_data")
mb.genrule(
    name="copy_data",
    py=copy_local_data,
    args={
        "test_output_directory": test_output_directory,
    },
)
```

### Download remote data

Because Clang Code Coverage is supported on multiple platforms, this library implements a way to download multiple profiles.
There are helper functions in [code_coverage//artifactory](../META/artifactory.meta.py) to query what test result zip files are available in Artifactory. Once that list of URLs is generated, call the `code_coverage//website:download_remote_data` to download the zip files and configure the Code Coverage website.

```python
mb.load(
    "code_coverage//artifactory",
    "get_directory_contents",
    "gen_aql",
)
mb.load("code_coverage//website", "download_remote_data")

async def download_data(ctx):
    # artifactory_user = os.environ.get("ARTIFACTORY_USER")
    artifactory_api_key = os.environ.get("ARTIFACTORY_API_KEY")
    ARTIFACTORY_ROOT = "https://artifactory.corp.adobe.com/artifactory"
    ARTIFACTORY_REPO = "generic-code-coverage-release-local"
    remote_dir_path = "chosen/path/to/test/results/*.zip"
    url_path = f"{ARTIFACTORY_ROOT}/{VM_REPO}/{remote_dir_path}"
    mb.log.debug(f"AQL .zip files in {url_path}")
    aql = gen_aql([remote_dir_path], VM_REPO, "*.zip")
    zip_files = get_directory_contents(artifactory_api_key, aql, ARTIFACTORY_ROOT)
    urls = []
    for zip_file in zip_files:
        zip_file_name = zip_file["name"]
        test_result_url = (
            f"{ARTIFACTORY_ROOT}/{VM_REPO}/{remote_dir_path}/{zip_file_name}"
        )
        urls.append(test_result_url)
    mb.log.debug(f"Download URLs: {urls}")
    appendage_bug = Path("out")
    await download_remote_data(ctx, artifactory_api_key, urls, appendage_bug)

mb.genrule(
    name="download_data",
    py=download_data,
)
```
