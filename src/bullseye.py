import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def covfile_path():
    cov_file = Path(os.environ.get("COVFILE"))
    return cov_file


def create_covfile():
    cov_file = covfile_path()
    cov_file.parent.mkdir(parents=True, exist_ok=True)
    cov_file.touch(exist_ok=True)


async def cov01(ctx):
    args = ctx.args["args"]
    cmd = f"cov01 {args}"
    logger.debug("cmd = %s", cmd)
    await ctx.execute(cmd.split(" "))

    if args == "--on":
        create_covfile()


async def export_to_xml(ctx):
    cov_file = covfile_path()
    xml_file = Path(cov_file.parent, f"{cov_file.stem}.xml")
    cmd = f"covxml --cobertura --output {xml_file}"
    logger.debug("cmd = %s", cmd)
    await ctx.execute(cmd.split(" "))
    return xml_file
