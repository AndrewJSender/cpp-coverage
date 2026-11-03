# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

"""Command line entry point for coverage-analytics."""

import sys

from coverage_analytics import __version__

USAGE = """\
usage: coverage-analytics [-h] [-V] <command> [args...]

commands:
  profile   Generate coverage reports and website data from test outputs
  diff      Analyze coverage of changed lines between Git revisions
  gate      Enforce the changed-coverage gate from a diff coverage report

Run `coverage-analytics <command> --help` for command-specific options.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE, file=sys.stderr)
        return 2
    if args[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if args[0] in ("-V", "--version"):
        print(f"coverage-analytics {__version__}")
        return 0

    command, rest = args[0], args[1:]
    if command == "profile":
        from coverage_analytics.generate_profile import main as profile_main

        return profile_main(rest)
    if command == "diff":
        from coverage_analytics.git import main as diff_main

        return diff_main(rest)
    if command == "gate":
        from coverage_analytics.enforce_diff_coverage import main as gate_main

        return gate_main(rest)

    print(f"coverage-analytics: unknown command '{command}'\n\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
