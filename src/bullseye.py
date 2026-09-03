import os
from pathlib import Path
import metabuild.public as mb

mb.load("//bundle", "build_info_dict", "get_git_commit")


def covfile_path():
    cov_file = Path(os.environ.get("COVFILE"))
    return cov_file


def create_covfile():
    cov_file = covfile_path()
    cov_file.parent.mkdir(parents=True, exist_ok=True)
    cov_file.touch(exist_ok=True)


async def cov01(ctx: mb.GenRulePyContext):
    args = ctx.args["args"]
    cmd = f"cov01 {args}"
    mb.log.debug(f"cmd = {cmd}")
    await ctx.execute(cmd.split(" "))

    if args == "--on":
        create_covfile()


async def export_to_xml(ctx: mb.GenRulePyContext):
    cov_file = covfile_path()
    xml_file = Path(cov_file.parent, f"{cov_file.stem}.xml")
    cmd = f"covxml --cobertura --output {xml_file}"
    mb.log.debug(f"cmd = {cmd}")
    await ctx.execute(cmd.split(" "))
    return xml_file


mb.genrule(
    name="on",
    py=cov01,
    args={
        "args": "--on",
    },
)

mb.genrule(
    name="off",
    py=cov01,
    args={
        "args": "--off",
    },
)

mb.genrule(
    name="generate_profile_data",
    py=export_to_xml,
)
