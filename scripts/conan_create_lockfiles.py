#!/usr/bin/env python3

import sys
import argparse
import subprocess
from pathlib import Path

from list_package_references import get_package_infos
from list_build_matrix import get_build_matrix


def main():
    parser = argparse.ArgumentParser(description="Create Conan lockfiles for all packages.")
    parser.add_argument(
        "--recreate",
        action="store_true",
    )
    args = parser.parse_args()

    returncode = 0

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    lockfile_root_path = root_path / "lockfiles"

    package_infos = get_package_infos()
    for package_name in package_infos:
        for package_info in package_infos[package_name]:
            package_version = package_info["version"]
            package_reference = f"{package_name}/{package_version}"

            build_matrix = get_build_matrix(package_reference)

            for build_info in build_matrix:
                build_machine = build_info["build_machine"]
                host_profile = build_info["host_profile"]
                profile_build_file = (
                    root_path
                    / ".github"
                    / "config"
                    / build_machine
                    / "conan"
                    / "profiles"
                    / "default"
                )
                profile_host_file = (
                    root_path
                    / ".github"
                    / "config"
                    / build_machine
                    / "conan"
                    / "profiles"
                    / host_profile
                )

                lockfile_path = (
                    lockfile_root_path
                    / package_name
                    / package_version
                    / host_profile
                    / "conan.lock"
                )
                lockfile_path.parent.mkdir(parents=True, exist_ok=True)

                print(
                    f"Create lockfile for package {package_name} version {package_version} profile {host_profile} ..."
                )

                if not args.recreate and lockfile_path.exists():
                    print(f"... already exists, skipping.")
                    continue

                proc = subprocess.run(
                    [
                        "conan",
                        "lock",
                        "create",
                        package_info["conanfile"],
                        "--version",
                        package_version,
                        "--profile:build",
                        str(profile_build_file),
                        "--profile:host",
                        str(profile_host_file),
                        "--lockfile-out",
                        str(lockfile_path),
                    ],
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
