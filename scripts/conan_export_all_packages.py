#!/usr/bin/env python3

import argparse
import sys
import subprocess
from pathlib import Path

from list_package_references import get_package_infos


def get_cli_args():
    parser = argparse.ArgumentParser(description="Export all packages")
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

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent

    package_infos = get_package_infos()
    for package_name in package_infos:
        for package_info in package_infos[package_name]:
            print(
                f"Export package {package_name} version {package_info["version"]} ..."
            )

            command = [
                "conan",
                "export",
                str(Path(package_info["directory"]) / package_info["conanfile"]),
                "--version",
                package_info["version"],
            ]
            if args.dry_run:
                print("Dry run, not executing command: " + " ".join(command))
                proc = subprocess.CompletedProcess(
                    args=command, returncode=0, stdout="Dry run", stderr=""
                )
            else:
                print("Running command: " + " ".join(command))
                proc = subprocess.run(
                    command,
                    cwd=root_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            if proc.returncode != 0:
                print("... failed to export")
                print(proc.stdout)
                returncode = proc.returncode

    return returncode


if __name__ == "__main__":
    sys.exit(main())
