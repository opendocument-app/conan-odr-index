#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

script_path = Path(__file__).resolve().parent
root_path = script_path.parent
recipes_path = root_path / "recipes"
TIER_COUNT = 5


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
                    "conanfile": str((package_path / details["folder"] / "conanfile.py").relative_to(root_path)),
                    "test_conanfile": str((package_path / details["folder"] / "test_package" / "conanfile.py").relative_to(root_path)),
                }
            )

        package_infos[package_name] = sorted(infos, key=lambda x: x["version"], reverse=True)

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
    packages = list()
    for file_in_commit in get_files_in_commit(commit_id):
        file_components = file_in_commit.split(os.sep)
        if len(file_components) >= 3 and file_components[0] == 'recipes':
            package_name = file_components[1]
            packages.append(package_name)
    return packages


def get_modified_packages_in_commits(commit_id_list, commit_obj_list):
    packages = list()
    for commit_id in commit_id_list:
        print(f"Commit {commit_id} requested as an argument")
        packages += get_packages_in_commit(commit_id)

    for commit in commit_obj_list:
        if -1 == str.lower(commit["message"]).find('[skipci]'):
            print(f"Found commit without [skipci]: {commit["id"]} - {commit["message"]}")
            packages += get_packages_in_commit(commit["id"])
    return packages


def get_downstream_dependents(dependency_graph_files, package_infos):
    # downstream_packages dictionary key is package name,
    # value is a set of packages, which use this package
    downstream_packages = dict()
    for conan_dependency_graph_file in dependency_graph_files:
        print("Parsing dependencies in " + conan_dependency_graph_file)
        with open(conan_dependency_graph_file, 'r') as dep_json:
            nodes = json.load(dep_json)['graph']['nodes']
            for node in nodes:
                node_name = nodes[node]['name']
                if node_name not in package_infos:
                    continue

                for dependency in nodes[node]['dependencies']:
                    dependency_ref = nodes[node]['dependencies'][dependency]['ref']
                    dep_name = dependency_ref.split('/')[0]

                    # Not tracking external dependencies
                    if dep_name not in package_infos:
                        continue

                    if dep_name not in downstream_packages:
                        downstream_packages[dep_name] = set()

                    downstream_packages[dep_name].add(node_name)
    return downstream_packages


def get_latest_package_version(package_infos, package_name):
    return package_infos[package_name][0]['version']


def main():
    parser = argparse.ArgumentParser(description="List package versions")
    parser.add_argument("--commit-ids", nargs='*', dest="COMMIT_ID",
                        help="Find packages modified by supplied commits. Commit ids will also be obtained from "
                             "$ENV[GITHUB_EVENT][commits]")
    parser.add_argument("--request-package", action='store',
                        help="Requested package will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_name]")
    parser.add_argument("--request-package-version", action='store',
                        help="Used together with --request-package, ignored when building all packages. "
                             "Requested package version will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_version]."
                             "Specify 'newest' or leave empty to request the newest version. "
                             "Specify 'all' to request all versions.")
    parser.add_argument("--dependency-graph", nargs='*', dest="CONAN_DEPENDENCY_GRAPH.json",
                        help="Used to calculate downstream dependents of requested packages")

    args = parser.parse_args()
    del parser

    github_event = json.loads(os.environ.get('GITHUB_EVENT', '{}'))
    inputs = github_event.get("inputs", dict())

    package_infos = get_package_infos()
    requested_packages = dict()

    commit_ids = args.COMMIT_ID or list()
    commit_obj_list = github_event.get("commits", list())
    for package in get_modified_packages_in_commits(commit_ids, commit_obj_list):
        if package not in requested_packages.keys():
            requested_packages[package] = set()
        requested_packages[package].add(get_latest_package_version(package_infos, package))
    del commit_ids, commit_obj_list

    # Check if any packages were asked to be rebuilt
    input_requested_package = args.request_package if args.request_package else inputs.get('package_name')
    input_requested_version = args.request_package_version or inputs.get('package_version', 'newest')
    if github_event.get("schedule", False):
        print("Scheduled job, requesting all package rebuild")
        input_requested_package = 'all'
    if input_requested_package == 'all':
        for package in package_infos:
            if package not in requested_packages.keys():
                requested_packages[package] = set()
            requested_packages[package].add(get_latest_package_version(package_infos, package))
    elif input_requested_package:
        print(f"Requested package: {input_requested_package}/{input_requested_version}")
        if input_requested_package not in requested_packages.keys():
            requested_packages[input_requested_package] = set()
        if input_requested_version == 'newest':
            requested_packages[input_requested_package].add(get_latest_package_version(package_infos, input_requested_package))
        elif input_requested_version == 'all':
            for version in list(map(lambda v: v['version'], package_infos[input_requested_package])):
                requested_packages[input_requested_package].add(version)
        else:
            requested_packages[input_requested_package].add(input_requested_version)
    del input_requested_package, input_requested_version

    dependency_graph_files = getattr(args, 'CONAN_DEPENDENCY_GRAPH.json') or list()
    downstream_dependents = get_downstream_dependents(dependency_graph_files, package_infos)
    del dependency_graph_files

    dependents = set()
    for package in requested_packages.keys():
        for dependant in downstream_dependents.get(package, list()):
            dependents.add(dependant)
    for dependant in dependents:
        if dependant not in requested_packages.keys():
            requested_packages[dependant] = set()
        requested_packages[dependant].add(get_latest_package_version(package_infos, dependant))
    del dependents

    tiered_packages = [requested_packages]
    del requested_packages
    dependency_tier = 0
    while dependency_tier < len(tiered_packages):
        packages_from_this_tier = dict(tiered_packages[dependency_tier])
        packages_to_add_in_next_tier = dict()
        for package in packages_from_this_tier.keys():
            for dependant in downstream_dependents.get(package, list()):
                if dependant in packages_from_this_tier.keys():
                    packages_to_add_in_next_tier[dependant] = packages_from_this_tier[dependant]
                    if dependant in tiered_packages[dependency_tier].keys():
                        del tiered_packages[dependency_tier][dependant]
        if len(packages_to_add_in_next_tier):
            tiered_packages.append(packages_to_add_in_next_tier)
        dependency_tier += 1

    if dependency_tier > TIER_COUNT:
        this_file = Path(__file__).resolve().relative_to(root_path)
        build_workflow = ".github/workflows/build.yml"
        print(f"Dependency tier overflow. Increase TIER_COUNT in {this_file} and in {build_workflow}", file=sys.stderr)
        sys.exit(1)

    result = []
    for tier in tiered_packages:
        package_infos_in_this_tier = []
        for package in tier.keys():
            for version in tier[package]:
                package_infos_in_this_tier.append(get_package_info(package_infos, package, version))
        result.append(package_infos_in_this_tier)

    for tier_index in range(TIER_COUNT):
        packages_in_tier = result[tier_index] if len(result) > tier_index else list()
        print(f"packages_{tier_index}=" + ' '.join(map(lambda x: x['package_reference'], packages_in_tier)))

    gh_output = os.environ.get('GITHUB_OUTPUT')
    if gh_output:
        with open(gh_output, 'w') as out:
            for tier_index in range(TIER_COUNT):
                packages_in_tier = result[tier_index] if len(result) > tier_index else list()
                print(f"packages_{tier_index}={json.dumps(packages_in_tier)}", file=out)


if __name__ == "__main__":
    main()
