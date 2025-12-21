#!/usr/bin/env python3

import argparse
import sys
import subprocess
from pathlib import Path

from list_package_references import (
    get_package_infos,
    get_selected_packages,
)


def export_package(package_info, root_path, dry_run=False):
    conanfile_path = Path(package_info["directory"]) / package_info["conanfile"]
    command = [
        "conan",
        "export",
        str(conanfile_path),
        "--version",
        package_info["version"],
    ]
    if dry_run:
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
    return proc


def get_cli_args():
    parser = argparse.ArgumentParser(description="Export all packages")
    parser.add_argument(
        "--include-packages",
        nargs="*",
        default=[],
        help="Include patterns for package selection",
    )
    parser.add_argument(
        "--exclude-packages",
        nargs="*",
        default=[],
        help="Exclude patterns for package selection",
    )
    parser.add_argument(
        "--selection-config",
        type=Path,
        help="Path to selection config file",
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

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    recipes_path = root_path / "recipes"

    package_infos = get_package_infos(root_path, recipes_path)
    package_references = [
        package_info["package_reference"] for package_info in package_infos
    ]
    selected_packages = get_selected_packages(
        package_references,
        args.selection_config,
        args.include_packages,
        args.exclude_packages,
    )

    for package_info in package_infos:
        if package_info["package_reference"] not in selected_packages:
            continue

        print(
            f"Export package {package_info["package"]} version {package_info["version"]} ..."
        )

        proc = export_package(package_info, root_path, dry_run=args.dry_run)
        if proc.returncode != 0:
            print("... failed to export")
            print(proc.stdout)
            returncode = proc.returncode

    return returncode


if __name__ == "__main__":
    sys.exit(main())
