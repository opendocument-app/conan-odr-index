#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

from list_package_references import get_package_infos


def create_lock_file(package_info, root_path, build_profile, host_profile):
    conanfile_path = Path(package_info["directory"]) / package_info["conanfile"]
    proc = subprocess.run(
        [
            "conan",
            "lock",
            "create",
            str(conanfile_path),
            "--version",
            package_info["version"],
            "--profile:build",
            str(build_profile),
            "--profile:host",
            str(host_profile),
        ],
        cwd=root_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def main():
    returncode = 0

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent

    package_infos = get_package_infos()
    for package_name in package_infos:
        for package_info in package_infos[package_name]:
            for host_profile in [
                "android-21-armv8",
                "ubuntu-24.04-x86_64-clang-18",
                "macos-15-armv8-apple-clang-14",
                "windows-2022-x86_64-msvc-1940",
            ]:
                print(
                    f"Lock package {package_name} version {package_info["version"]} for {host_profile} ..."
                )

                proc = create_lock_file(
                    package_info,
                    root_path,
                    Path(f".github/config/conan/profiles/{host_profile}"),
                    Path(f".github/config/conan/profiles/{host_profile}"),
                )
                if proc.returncode != 0:
                    print("... failed to lock")
                    print(proc.stdout)
                returncode = proc.returncode

    return returncode


if __name__ == "__main__":
    sys.exit(main())
