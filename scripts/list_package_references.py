#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
import fnmatch

import yaml


def item_to_list(item_or_list):
    if isinstance(item_or_list, list):
        return item_or_list
    return [item_or_list]


def get_package_infos(root_path, recipes_path):
    package_infos = []

    for package_path in recipes_path.iterdir():
        if not package_path.is_dir():
            continue

        config_file = package_path / "config.yml"
        if not config_file.is_file():
            continue

        with open(config_file) as f:
            config = yaml.safe_load(f)

        package_name = package_path.name
        for version, details in config["versions"].items():
            package_directory = (package_path / str(details["folder"])).relative_to(
                root_path
            )

            package_infos.append(
                {
                    "package": package_name,
                    "version": version,
                    "package_reference": "{}/{}".format(package_name, version),
                    "directory": str(package_directory),
                    "conanfile": "conanfile.py",
                    "test_conanfile": "test_package/conanfile.py",
                }
            )

    package_infos = sorted(package_infos, key=lambda x: x["version"])
    package_infos = sorted(package_infos, key=lambda x: x["package"])

    return package_infos


def get_selected_packages(
    package_references, config, include_packages, exclude_packages
):
    include_packages = list(include_packages)
    exclude_packages = list(exclude_packages)

    if config is not None:
        with open(config) as f:
            selection = yaml.safe_load(f)
        package_selection = selection["packages"]

        if not include_packages and not exclude_packages:
            include_packages = item_to_list(package_selection.get("include", []))
            exclude_packages = item_to_list(package_selection.get("exclude", []))

    if not include_packages:
        include_packages = ["*"]

    result = []

    for package_reference in package_references:
        if all(
            not fnmatch.fnmatch(package_reference, pattern)
            for pattern in include_packages
        ):
            continue
        if any(
            fnmatch.fnmatch(package_reference, pattern) for pattern in exclude_packages
        ):
            continue
        result.append(package_reference)

    return result


def get_files_in_commit(root_path, commit_id):
    files_in_commit = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
        capture_output=True,
        text=True,
        cwd=root_path,
    )
    return filter(None, files_in_commit.stdout.split("\n"))


def get_packages_in_commit(root_path, commit_id):
    packages = []
    for file_in_commit in get_files_in_commit(root_path, commit_id):
        file_components = Path(file_in_commit).parts
        if len(file_components) >= 3 and file_components[0] == "recipes":
            package_name = file_components[1]
            packages.append(package_name)
    return packages


def get_modified_packages_in_commits(root_path, commit_id_list):
    packages = []
    for commit_id in commit_id_list:
        print(f"Commit {commit_id} requested as an argument")
        packages += get_packages_in_commit(root_path, commit_id)
    return packages


def get_cli_args():
    parser = argparse.ArgumentParser(description="List package versions")
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
        "--commit-id",
        nargs="*",
        help="Find packages modified by supplied commits. Commit ids will also be obtained from $ENV[GITHUB_CONTEXT][commits]",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Output file for GitHub action",
    )
    args = parser.parse_args()

    return args


def get_github_args(root_path):
    github = json.loads(os.environ.get("GITHUB_CONTEXT", "{}"))
    inputs = json.loads(os.environ.get("GITHUB_INPUT", "{}"))

    event = github.get("event", {})

    include_packages = (
        inputs.get("package_include_patterns").split(",")
        if inputs.get("package_include_patterns", "")
        else []
    )
    exclude_packages = (
        inputs.get("package_exclude_patterns").split(",")
        if inputs.get("package_exclude_patterns", "")
        else []
    )

    selection_config = root_path / "defaults.yaml"

    if github.get("event_name") in ["push", "pull_request"]:
        commit_obj_list = event.get("commits", [])
        commit_ids = [commit["id"] for commit in commit_obj_list]
    else:
        commit_ids = []

    github_output = Path(os.environ.get("GITHUB_OUTPUT"))

    return argparse.Namespace(
        include_packages=include_packages,
        exclude_packages=exclude_packages,
        selection_config=selection_config,
        commit_id=commit_ids,
        github_output=github_output,
    )


def get_is_github():
    return bool(os.environ.get("GITHUB_ACTIONS", False))


def main():
    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    recipes_path = root_path / "recipes"

    is_github = get_is_github()

    if is_github:
        args = get_github_args(root_path)
    else:
        args = get_cli_args()

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

    if args.commit_id:
        modified_selected_packages = []
        modified_packages = get_modified_packages_in_commits(root_path, args.commit_id)
        for package_references in selected_packages:
            if package_references.split("/")[0] in modified_packages:
                modified_selected_packages.append(package_references)
        selected_packages = modified_selected_packages

    for package_reference in selected_packages:
        print(package_reference)

    if is_github:
        with open(args.github_output, "w") as out:
            selected_package_infos = [
                package_info
                for package_info in package_infos
                if package_info["package_reference"] in selected_packages
            ]
            print(f"packages={json.dumps(selected_package_infos)}", file=out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
