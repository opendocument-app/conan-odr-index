#!/usr/bin/env python3

import argparse
import json
import sys
import subprocess
from datetime import datetime, timezone


def create_package_index(dry_run=False):
    command = [
        "conan",
        "list",
        "-f",
        "json",
        "*:*",
    ]
    if dry_run:
        print("Dry run, not executing command: " + " ".join(command))
        proc = subprocess.CompletedProcess(
            args=command, returncode=0, stdout="Dry run", stderr=""
        )
        return {}

    print("Running command: " + " ".join(command))
    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        print(f"Command failed with return code {proc.returncode}")
        print(f"stderr: {proc.stderr}")
        raise subprocess.CalledProcessError(
            proc.returncode, command, output=proc.stdout, stderr=proc.stderr
        )
    output = proc.stdout
    parsed = json.loads(output)

    result = {}

    package_version_infos = parsed["Local Cache"]

    for package_version, package_info in package_version_infos.items():
        package, version = package_version.split("/")
        for revision, revision_info in package_info["revisions"].items():
            timestamp = revision_info["timestamp"]
            utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%MZ"
            )

            result.setdefault(package, {}).setdefault(version, {}).setdefault(
                "revisions", {}
            )[revision] = {
                "timestamp": utc_time,
            }
            result[package][version].setdefault("latest", revision)
            if (
                utc_time
                > result[package][version]["revisions"][
                    result[package][version]["latest"]
                ]["timestamp"]
            ):
                result[package][version]["latest"] = revision

    return result


def get_cli_args():
    parser = argparse.ArgumentParser(description="Create package index")
    parser.add_argument(
        "output_file",
        nargs="?",
        default="package_index.json",
        help="Output file for the package index (default: package_index.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without executing commands",
    )
    args = parser.parse_args()

    return args


def main():
    returncode = 0

    args = get_cli_args()

    index = create_package_index(dry_run=args.dry_run)
    if not args.dry_run:
        with open(args.output_file, "w") as f:
            json.dump(index, f, indent=2)
        print(f"Package index written to {args.output_file}")

    return returncode


if __name__ == "__main__":
    sys.exit(main())
