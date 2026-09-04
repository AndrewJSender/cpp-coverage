# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

import json
from pathlib import Path
import platform

BUILD_INFO_FILENAME = "build_info.json"

async def get_git_commit(ctx) -> str:
    git_cmd = "git rev-parse HEAD"
    git_commit = await ctx.execute(git_cmd.split(" "))
    git_commit = git_commit.replace("\n", "")
    return git_commit

async def build_info_dict(branch_name: str, build_number: int, project_root: Path, git_commit: str) -> dict:
    return {
        "branch_name": branch_name,
        "build_number": build_number,
        "hostname": platform.node(),
        "project_root": project_root.__str__(),
        "git_commit": git_commit,
    }

async def gen_build_info(ctx):
    output_file = Path(ctx.outputs[0])
    project_root = Path(await ctx.eval_async(ctx.args["project_root"])).resolve()
    git_commit = await get_git_commit(ctx)
    build_info = await build_info_dict(ctx.args["branch_name"], ctx.args["build_number"], project_root, git_commit)

    with open(output_file, "w") as f:
        json.dump(build_info, f)
