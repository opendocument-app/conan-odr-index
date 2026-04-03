#!/usr/bin/env python3

import argparse
import json
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def create_package_index():
    command = [
        "conan",
        "list",
        "-f",
        "json",
        "*:*",
    ]

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

    return result


def get_cli_args():
    parser = argparse.ArgumentParser(description="Create package index")
    parser.add_argument(
        "--output-path",
        help="Output path for the package index",
        type=Path,
        default=Path("packages"),
    )
    args = parser.parse_args()

    return args


def main():
    returncode = 0

    args = get_cli_args()

    index = create_package_index()

    args.output_path.mkdir(parents=True, exist_ok=True)

    for package, package_info in index.items():
        result = {
            "releases": []
        }

        for version, version_info in package_info.items():
            for revision, revision_info in version_info["revisions"].items():
                result["releases"].append({
                    "version": version,
                    "digest": revision,
                    "releaseTimestamp": revision_info["timestamp"],
                })

        with open(args.output_path / f"{package}.json", "w") as f:
            json.dump(result, f, indent=2)

    return returncode


if __name__ == "__main__":
    sys.exit(main())
