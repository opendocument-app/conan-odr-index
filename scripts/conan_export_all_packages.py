#!/usr/bin/env python3
import os
import subprocess

from list_package_versions import get_package_infos


def main():
    package_infos = get_package_infos()
    for package in package_infos:
        for version in package_infos[package]:
            conanfile = os.path.join("recipes", package, version["folder"], "conanfile.py")
            subprocess.run(["conan", "export", conanfile, "--version", version["version"]])


if __name__ == "__main__":
    main()
