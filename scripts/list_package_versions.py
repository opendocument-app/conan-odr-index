#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from functools import cmp_to_key

import yaml
import semver


script_path = Path(__file__).resolve().parent
root_path = script_path.parent
recipes_path = root_path / "recipes"
default_packages_path = root_path / "default-packages-list.txt"
TIER_COUNT = 5


def get_default_packages():
    with open(default_packages_path) as f:
        list = f.read().splitlines()

    result = {}

    for package_version in list:
        package, version = package_version.split("/")
        if package not in result:
            result[package] = set()
        result[package].add(version)

    return result


def get_package_infos():
    package_infos = {}

    for package_path in recipes_path.iterdir():
        if not package_path.is_dir():
            continue

        config_file = package_path / "config.yml"
        if not config_file.is_file():
            continue

        with open(config_file) as f:
            config = yaml.safe_load(f)

        infos = []
        package_name = package_path.name
        for version, details in config["versions"].items():
            infos.append(
                {
                    "package": package_name,
                    "version": version,
                    "package_reference": "{}/{}".format(package_name, version),
                    "conanfile": str(
                        (package_path / details["folder"] / "conanfile.py").relative_to(
                            root_path
                        )
                    ),
                    "test_conanfile": str(
                        (
                            package_path
                            / details["folder"]
                            / "test_package"
                            / "conanfile.py"
                        ).relative_to(root_path)
                    ),
                }
            )

        package_infos[package_name] = sorted(
            infos, key=cmp_to_key(lambda a, b: semver.compare(a["version"], b["version"]))
        )

    return package_infos


def get_package_info(package_infos, package, version):
    versions = package_infos[package]
    for package_versioned in versions:
        if package_versioned["version"] == version:
            return package_versioned


def get_files_in_commit(commit_id):
    files_in_commit = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
        capture_output=True,
        text=True,
        cwd=root_path,
    )
    return filter(None, files_in_commit.stdout.split("\n"))


def get_packages_in_commit(commit_id):
    packages = []
    for file_in_commit in get_files_in_commit(commit_id):
        file_components = file_in_commit.split(os.sep)
        if len(file_components) >= 3 and file_components[0] == "recipes":
            package_name = file_components[1]
            packages.append(package_name)
    return packages


def get_modified_packages_in_commits(commit_id_list):
    packages = []
    for commit_id in commit_id_list:
        print(f"Commit {commit_id} requested as an argument")
        packages += get_packages_in_commit(commit_id)
    return packages


def get_downstream_dependents(dependency_graph_files, package_infos):
    # downstream_packages dictionary key is package name,
    # value is a set of packages, which use this package
    downstream_packages = {}
    for conan_dependency_graph_file in dependency_graph_files:
        print("Parsing dependencies in " + conan_dependency_graph_file)
        with open(conan_dependency_graph_file, "r") as dep_json:
            nodes = json.load(dep_json)["graph"]["nodes"]
            for node in nodes:
                node_name = nodes[node]["name"]
                if node_name not in package_infos:
                    continue

                for dependency in nodes[node]["dependencies"]:
                    dependency_ref = nodes[node]["dependencies"][dependency]["ref"]
                    dep_name = dependency_ref.split("/")[0]

                    # Not tracking external dependencies
                    if dep_name not in package_infos:
                        continue

                    if dep_name not in downstream_packages:
                        downstream_packages[dep_name] = set()

                    downstream_packages[dep_name].add(node_name)
    return downstream_packages


def get_latest_package_version(package_infos, package_name):
    return package_infos[package_name][0]["version"]


def add_dependents_to_requested_packages(
    requested_packages, downstream_dependents, package_infos
):
    dependents = set()
    for package in requested_packages.keys():
        for dependant in downstream_dependents.get(package, []):
            dependents.add(dependant)
    for dependant in dependents:
        if dependant not in requested_packages.keys():
            requested_packages[dependant] = set()
        requested_packages[dependant].add(
            get_latest_package_version(package_infos, dependant)
        )


def get_tiered_packages(requested_packages, downstream_dependents, package_infos):
    tiered_packages = [requested_packages]
    dependency_tier = 0
    while dependency_tier < len(tiered_packages):
        packages_from_this_tier = dict(tiered_packages[dependency_tier])
        packages_to_add_in_next_tier = {}
        for package in packages_from_this_tier.keys():
            for dependant in downstream_dependents.get(package, []):
                if dependant in packages_from_this_tier.keys():
                    packages_to_add_in_next_tier[dependant] = packages_from_this_tier[
                        dependant
                    ]
                    if dependant in tiered_packages[dependency_tier].keys():
                        del tiered_packages[dependency_tier][dependant]
        if len(packages_to_add_in_next_tier):
            tiered_packages.append(packages_to_add_in_next_tier)
        dependency_tier += 1

    if dependency_tier > TIER_COUNT:
        this_file = Path(__file__).resolve().relative_to(root_path)
        print(
            f"Dependency tier overflow. Increase TIER_COUNT in {this_file} and in .github/workflows/build.yml",
            file=sys.stderr,
        )
        sys.exit(1)

    result = [[] for _ in range(TIER_COUNT)]
    for tier, packages in enumerate(tiered_packages):
        package_infos_in_this_tier = []
        for package in packages.keys():
            for version in packages[package]:
                package_infos_in_this_tier.append(
                    get_package_info(package_infos, package, version)
                )
        result[tier] = package_infos_in_this_tier

    return result


def get_cli_args():
    parser = argparse.ArgumentParser(description="List package versions")
    parser.add_argument(
        "--commit-id",
        nargs="*",
        help="Find packages modified by supplied commits. Commit ids will also be obtained from $ENV[GITHUB_EVENT][commits]",
    )
    parser.add_argument(
        "--request-package",
        help="Requested package will also be obtained from $ENV[GITHUB_EVENT][inputs][package_name]",
    )
    parser.add_argument(
        "--request-package-version",
        help="Used together with --request-package, ignored when building default packages. Requested package version will also be obtained from $ENV[GITHUB_EVENT][inputs][package_version]. Specify 'latest' or leave empty to request the latest version. Specify 'all' to request all versions.",
    )
    parser.add_argument(
        "--dependency-graph",
        nargs="*",
        help="Used to calculate downstream dependents of requested packages",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Output file for GitHub action",
    )
    args = parser.parse_args()

    return args


def get_github_args():
    event = json.loads(os.environ.get("GITHUB_EVENT", "{}"))
    inputs = event.get("inputs", {})

    commit_obj_list = event.get("commits", [])
    commit_ids = [
        commit["id"]
        for commit in commit_obj_list
        if "[skipci]" not in commit["message"].lower()
    ]

    request_package = inputs.get("package_name")
    request_package_version = inputs.get("package_version", "latest")
    dependency_graph = inputs.get("dependency_graph", [])
    github_output = Path(os.environ.get("GITHUB_OUTPUT"))

    if event.get("schedule", False):
        print("Scheduled job, requesting default package rebuild")
        request_package = "default"

    return argparse.Namespace(
        commit_id=commit_ids,
        request_package=request_package,
        request_package_version=request_package_version,
        dependency_graph=dependency_graph,
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

    package_infos = get_package_infos()
    default_packages = get_default_packages()
    requested_packages = {}

    for package in get_modified_packages_in_commits(args.commit_id):
        if package not in requested_packages.keys():
            requested_packages[package] = set()
        requested_packages[package].add(
            get_latest_package_version(package_infos, package)
        )

    # Check if any packages were asked to be rebuilt
    input_requested_package = args.request_package
    input_requested_version = args.request_package_version
    if (
        input_requested_package is not None
        and input_requested_package != "default"
        and input_requested_package not in package_infos.keys()
    ):
        print(
            f"Requested package {input_requested_package} not found in recipes",
            file=sys.stderr,
        )
        return 1
    if input_requested_package == "default":
        for package, versions in default_packages.items():
            if package not in requested_packages.keys():
                requested_packages[package] = set()
            requested_packages[package].update(versions)
    elif input_requested_package is not None:
        print(f"Requested package: {input_requested_package}/{input_requested_version}")
        if input_requested_package not in requested_packages.keys():
            requested_packages[input_requested_package] = set()
        if input_requested_version == "latest":
            requested_packages[input_requested_package].add(
                get_latest_package_version(package_infos, input_requested_package)
            )
        elif input_requested_version == "all":
            for version in list(
                map(lambda v: v["version"], package_infos[input_requested_package])
            ):
                requested_packages[input_requested_package].add(version)
        else:
            requested_packages[input_requested_package].add(input_requested_version)

    dependency_graph_files = args.dependency_graph or []
    downstream_dependents = get_downstream_dependents(
        dependency_graph_files, package_infos
    )

    add_dependents_to_requested_packages(
        requested_packages, downstream_dependents, package_infos
    )

    tiered_packages = get_tiered_packages(
        requested_packages, downstream_dependents, package_infos
    )

    for tier_index, packages_in_tier in enumerate(tiered_packages):
        print(
            f"packages_{tier_index}="
            + " ".join(map(lambda x: x["package_reference"], packages_in_tier))
        )

    if is_github:
        with open(args.github_output, "w") as out:
            for tier_index, packages_in_tier in enumerate(tiered_packages):
                print(f"packages_{tier_index}={json.dumps(packages_in_tier)}", file=out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
