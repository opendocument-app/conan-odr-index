#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

from .list_package_references import get_package_infos


def main():
    returncode = 0

    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent

    package_infos = get_package_infos()
    for package in package_infos:
        for version in package_infos[package]:
            proc = subprocess.run(
                [
                    "conan",
                    "export",
                    version["conanfile"],
                    "--version",
                    version["version"],
                ],
                cwd=root_path,
            )
            if proc.returncode != 0:
                print(f"Failed to export {package} {version['version']}")
                returncode = proc.returncode

    return returncode


if __name__ == "__main__":
    sys.exit(main())
