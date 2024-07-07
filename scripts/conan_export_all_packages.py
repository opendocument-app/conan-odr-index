#!/usr/bin/env python3
import subprocess
from pathlib import Path

from list_package_versions import get_package_infos


def main():
    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent

    package_infos = get_package_infos()
    for package in package_infos:
        for version in package_infos[package]:
            subprocess.run(
                ["conan", "export", version["conanfile"], "--version", version["version"]],
                cwd=root_path
            )


if __name__ == "__main__":
    main()
