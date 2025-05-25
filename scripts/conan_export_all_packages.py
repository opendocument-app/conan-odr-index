#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

from list_package_references import get_package_infos


def main():
    returncode = 0

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent

    package_infos = get_package_infos()
    for package_name in package_infos:
        for package_info in package_infos[package_name]:
            print(f"Export package {package_name} version {package_info["version"]} ...")

            proc = subprocess.run(
                [
                    "conan",
                    "export",
                    package_info["conanfile"],
                    "--version",
                    package_info["version"],
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
