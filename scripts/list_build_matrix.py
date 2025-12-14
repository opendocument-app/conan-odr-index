#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path
import fnmatch

import yaml

from list_package_references import item_to_list


script_path = Path(__file__).resolve().parent
root_path = script_path.parent


def get_build_matrix(
    package_reference,
    selection_config_path=None,
    include_platforms=[],
    exclude_platforms=[],
):
    include_platforms = list(include_platforms)
    exclude_platforms = list(exclude_platforms)
    include_profiles = []
    exclude_profiles = []
    rules = []

    if selection_config_path is not None:
        with open(selection_config_path) as f:
            selection_config = yaml.safe_load(f)

        if not include_platforms and not exclude_platforms:
            include_platforms = item_to_list(
                selection_config["platforms"].get("include", [])
            )
            exclude_platforms = item_to_list(
                selection_config["platforms"].get("exclude", [])
            )

        if not include_profiles and not exclude_profiles:
            include_profiles = item_to_list(
                selection_config["profiles"].get("include", [])
            )
            exclude_profiles = item_to_list(
                selection_config["profiles"].get("exclude", [])
            )

        if not rules:
            rules = selection_config["rules"]

    if not include_platforms:
        include_platforms = ["*"]
    if not include_profiles:
        include_profiles = ["*"]

    build_matrix = []

    def check_and_append(platform, config):
        if all(not fnmatch.fnmatch(platform, pattern) for pattern in include_platforms):
            return
        if any(fnmatch.fnmatch(platform, pattern) for pattern in exclude_platforms):
            return

        profile = config["host_profile"]
        if all(not fnmatch.fnmatch(profile, pattern) for pattern in include_profiles):
            return
        if any(fnmatch.fnmatch(profile, pattern) for pattern in exclude_profiles):
            return

        rule_excluded = False
        for rule in rules:
            if all(
                not fnmatch.fnmatch(package_reference, pattern)
                for pattern in item_to_list(rule.get("packages", "*"))
            ):
                continue
            if all(
                not fnmatch.fnmatch(platform, pattern)
                for pattern in item_to_list(rule.get("platforms", "*"))
            ):
                continue
            if all(
                not fnmatch.fnmatch(profile, pattern)
                for pattern in item_to_list(rule.get("profiles", "*"))
            ):
                continue

            if rule["type"] == "include":
                rule_excluded = False
            elif rule["type"] == "exclude":
                rule_excluded = True
        if rule_excluded:
            return

        build_matrix.append(config)

    # android
    for platform in [
        # using 35 because of the 16k page size requirement
        "android-35-armv8",
        "android-35-armv7",
        "android-35-x86",
        "android-35-x86_64",
        # TODO why do we use 23?
        "android-23-armv8",
        "android-23-armv7",
        "android-23-x86",
        "android-23-x86_64",
        # TODO why do we use 21?
        "android-21-armv8",
        "android-21-armv7",
        "android-21-x86",
        "android-21-x86_64",
    ]:
        check_and_append(
            platform,
            {
                "build_machine": "ubuntu-24.04",
                "build_profile": "ubuntu-24.04-x86_64-clang-18",
                "host_profile": platform,
                "ndk_version": "28.1.13356709",
            },
        )

    # macos
    check_and_append(
        "macos-15",
        {
            "build_machine": "macos-15",
            "build_profile": "macos-15-x86_64-apple-clang-14",
            "host_profile": "macos-15-x86_64-apple-clang-14",
        },
    )
    check_and_append(
        "macos-26",
        {
            "build_machine": "macos-26",
            "build_profile": "macos-26-armv8-apple-clang-14",
            "host_profile": "macos-26-armv8-apple-clang-14",
        },
    )

    # ubuntu
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "build_profile": "ubuntu-24.04-x86_64-gcc-13",
            "host_profile": "ubuntu-24.04-x86_64-gcc-13",
        },
    )
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "build_profile": "ubuntu-24.04-x86_64-gcc-14",
            "host_profile": "ubuntu-24.04-x86_64-gcc-14",
        },
    )
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "build_profile": "ubuntu-24.04-x86_64-clang-18",
            "host_profile": "ubuntu-24.04-x86_64-clang-18",
        },
    )

    # windows
    check_and_append(
        "windows-2022",
        {
            "build_machine": "windows-2022",
            "build_profile": "windows-2022-x86_64-msvc-1940",
            "host_profile": "windows-2022-x86_64-msvc-1940",
        },
    )

    return build_matrix


def get_cli_args():
    parser = argparse.ArgumentParser(description="List build matrix")
    parser.add_argument(
        "directory",
        type=Path,
        help="Path to package directory containing conanfile.py",
    )
    parser.add_argument(
        "version",
        type=str,
        help="Version of the package",
    )
    parser.add_argument(
        "--include-platforms",
        nargs="*",
        default=[],
        help="Include patterns for platform selection",
    )
    parser.add_argument(
        "--exclude-platforms",
        nargs="*",
        default=[],
        help="Exclude patterns for platform selection",
    )
    parser.add_argument(
        "--selection-config",
        type=Path,
        help="Path to selection config file",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Output file for GitHub action",
    )
    args = parser.parse_args()

    return args


def get_github_args():
    github = json.loads(os.environ.get("GITHUB_CONTEXT", "{}"))
    inputs = json.loads(os.environ.get("GITHUB_INPUT", "{}"))

    directory = Path(inputs.get("directory"))
    version = inputs.get("package_version")

    include_platforms = (
        inputs.get("platform_include_patterns").split(",")
        if inputs.get("platform_include_patterns", "")
        else []
    )
    exclude_platforms = (
        inputs.get("platform_exclude_patterns").split(",")
        if inputs.get("platform_exclude_patterns", "")
        else []
    )

    selection_config = root_path / "defaults.yaml"

    github_output = Path(os.environ.get("GITHUB_OUTPUT"))

    return argparse.Namespace(
        directory=directory,
        version=version,
        include_platforms=include_platforms,
        exclude_platforms=exclude_platforms,
        selection_config=selection_config,
        github_output=github_output,
    )


def get_is_github():
    return bool(os.environ.get("GITHUB_ACTIONS", False))


def main():
    is_github = get_is_github()

    if is_github:
        args = get_github_args()
    else:
        args = get_cli_args()

    args = get_github_args()

    # TODO that does not look great
    package_name = args.directory.parent.name
    package_reference = f"{package_name}/{args.version}"

    build_matrix = get_build_matrix(
        package_reference,
        args.selection_config,
        args.include_platforms,
        args.exclude_platforms,
    )

    print(json.dumps(build_matrix, indent=4))

    if is_github:
        with open(args.github_output, "w") as out:
            print(f"configs={json.dumps(build_matrix)}", file=out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
