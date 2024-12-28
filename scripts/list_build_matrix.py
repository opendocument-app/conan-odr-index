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


def get_build_matrix(package_reference, selection_config_path):
    if selection_config_path is None:
        selection_config = None
    else:
        with open(selection_config_path) as f:
            selection_config = yaml.safe_load(f)

    build_matrix = []

    def check_and_append(platform, config):
        if selection_config is None:
            build_matrix.append(config)
            return

        if all(
            not fnmatch.fnmatch(platform, pattern)
            for pattern in item_to_list(
                selection_config["platforms"].get("include", "*")
            )
        ):
            return
        if any(
            fnmatch.fnmatch(platform, pattern)
            for pattern in item_to_list(
                selection_config["platforms"].get("exclude", [])
            )
        ):
            return

        profile = config["host_profile"]
        if all(
            not fnmatch.fnmatch(profile, pattern)
            for pattern in item_to_list(
                selection_config["profiles"].get("include", "*")
            )
        ):
            return
        if any(
            fnmatch.fnmatch(profile, pattern)
            for pattern in item_to_list(selection_config["profiles"].get("exclude", []))
        ):
            return

        rule_excluded = False
        for rule in selection_config["rules"]:
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
        "android-23-armv8",
        "android-23-armv7",
        "android-23-x86",
        "android-23-x86_64",
        "android-21-armv8",
        "android-21-armv7",
        "android-21-x86",
        "android-21-x86_64",
    ]:
        check_and_append(
            platform,
            {
                "build_machine": "ubuntu-22.04",
                "host_profile": platform,
                "ndk_version": "26.3.11579264",
            },
        )

    # macos
    check_and_append(
        "macos-13",
        {
            "build_machine": "macos-13",
            "host_profile": "apple-clang-14",
        },
    )
    check_and_append(
        "macos-14",
        {
            "build_machine": "macos-14",
            "host_profile": "apple-armv8-clang-14",
        },
    )

    # ubuntu
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "host_profile": "gcc-13",
        },
    )
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "host_profile": "gcc-14",
        },
    )
    check_and_append(
        "ubuntu-24.04",
        {
            "build_machine": "ubuntu-24.04",
            "host_profile": "clang-18",
        },
    )

    # windows
    check_and_append(
        "windows-2022",
        {
            "build_machine": "windows-2022",
            "host_profile": "msvc-1940",
        },
    )

    return build_matrix


def get_cli_args():
    parser = argparse.ArgumentParser(description="List build matrix")
    parser.add_argument(
        "conanfile",
        type=Path,
        help="Path to conanfile.py",
    )
    parser.add_argument(
        "version",
        type=str,
        help="Version of the package",
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

    conanfile = Path(inputs.get("conanfile"))
    version = inputs.get("package_version")

    selection_config = root_path / "defaults.yaml"

    github_output = Path(os.environ.get("GITHUB_OUTPUT"))

    return argparse.Namespace(
        conanfile=conanfile,
        version=version,
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

    # TODO that does not look great
    package_name = args.conanfile.parent.parent.name
    package_reference = f"{package_name}/{args.version}"

    build_matrix = get_build_matrix(package_reference, args.selection_config)

    print(json.dumps(build_matrix, indent=4))

    if is_github:
        with open(args.github_output, "w") as out:
            print(f"configs={json.dumps(build_matrix)}", file=out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
