
import json

import metabuild.public as mb

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
        mb.log.debug(
            f"WARNING: Exact match not found for device name. Using device {first_key} ({first_value})."
        )
        return first_value

    message = (" matching '%s'" % (device_name)) if device_name else ""
    raise RuntimeError("No available iOS simulators found%s" % (message))
