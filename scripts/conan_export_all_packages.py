#!/usr/bin/env python3
import subprocess
from pathlib import Path

from list_package_versions import get_package_infos


def main():
    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    recipes_path = root_path / "recipes"
    package_infos = get_package_infos()
    for package in package_infos:
        for version in package_infos[package]:
            conanfile = recipes_path / package / version["folder"] / "conanfile.py"
            subprocess.run(["conan", "export", conanfile, "--version", version["version"]])


if __name__ == "__main__":
    main()
