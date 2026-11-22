#!/usr/bin/env python3
# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

"""CMAKE_CROSSCOMPILING_EMULATOR launcher for iOS Simulator binaries.

Runs the given executable with `simctl spawn`. The target simulator is taken
from IOS_SIMULATOR_DEVICE (a device name, UDID, or "booted"); otherwise an
available simulator matching IOS_SIMULATOR_DEVICE_NAME (default "iPhone") is
discovered with get_ios_device (copied from
coverage_analytics.archived.test) and booted on demand. simctl only forwards
environment variables prefixed with SIMCTL_CHILD_, so LLVM_PROFILE_FILE is
re-exported under that prefix to reach the instrumented process.

ctest does not expand the ${EFFECTIVE_PLATFORM_NAME} placeholder the Xcode
generator embeds in per-config binary paths, so it is substituted here.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

EFFECTIVE_PLATFORM_NAME = "${EFFECTIVE_PLATFORM_NAME}"


# Copied from coverage_analytics.archived.test.
async def get_ios_device(ctx, device_name, is_sim=False, exact_match_only=False):
    stdout = await ctx.execute(["xcrun", "xcdevice", "list"])
    devices_list_json = json.loads(stdout)

    candidates = {}
    for device_json in devices_list_json:
        if (
            device_name in device_json["name"]
            and device_json["available"]
            and is_sim == device_json["simulator"]
        ):
            if device_name == device_json["name"]:
                return device_json["identifier"]
            elif not exact_match_only:
                candidates[device_json["name"]] = device_json["identifier"]

    if len(candidates) > 0 and not exact_match_only:
        first_key = next(iter(candidates.keys()))
        first_value = candidates[first_key]
        logger.warning(
            "Exact match not found for device name. Using device %s (%s).",
            first_key,
            first_value,
        )
        return first_value

    message = (" matching '%s'" % (device_name)) if device_name else ""
    raise RuntimeError("No available iOS simulators found%s" % (message))


class SimulatorContext:
    """Minimal context adapter used by get_ios_device."""

    async def execute(self, command: list[str]) -> str:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()


def resolve_device() -> str:
    device = os.environ.get("IOS_SIMULATOR_DEVICE")
    if device:
        return device
    device_name = os.environ.get("IOS_SIMULATOR_DEVICE_NAME", "iPhone")
    return asyncio.run(get_ios_device(SimulatorContext(), device_name, is_sim=True))


def ensure_booted(device: str) -> None:
    if device == "booted":
        return
    # Boots the simulator if needed and waits until it is ready.
    subprocess.run(
        ["xcrun", "simctl", "bootstatus", device, "-b"],
        check=True,
        capture_output=True,
        text=True,
    )


def main(argv: list[str]) -> int:
    device = resolve_device()
    ensure_booted(device)
    env = os.environ.copy()
    profile_file = env.get("LLVM_PROFILE_FILE")
    if profile_file:
        env["SIMCTL_CHILD_LLVM_PROFILE_FILE"] = profile_file
    platform_name = env.get("EFFECTIVE_PLATFORM_NAME", "-iphonesimulator")
    argv = [
        argument.replace(EFFECTIVE_PLATFORM_NAME, platform_name)
        for argument in argv
    ]
    command = ["xcrun", "simctl", "spawn", device, *argv]
    return subprocess.run(command, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
