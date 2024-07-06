#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path

import yaml

script_path = Path(__file__).resolve().parent
root_path = script_path.parent
recipes_path = root_path / "recipes"


def get_package_infos():
    package_infos = {}

    for recipe_path in recipes_path.iterdir():
        if not recipe_path.is_dir():
            continue

        infos = []

        with open(recipe_path / "config.yml") as f:
            config = yaml.safe_load(f)

        for version, details in config["versions"].items():
            infos.append(
                {
                    "version": version,
                    "folder": Path(details["folder"]),
                }
            )

        package_infos[recipe_path.name] = infos

    return package_infos


def get_files_in_commit(commit_id):
    files_in_commit = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
        capture_output=True,
        text=True,
        cwd=root_path,
    )
    return filter(None, files_in_commit.stdout.split("\n"))


def get_packages_in_commit(commit_id):
    packages = set()
    for file_in_commit in get_files_in_commit(commit_id):
        file_components = file_in_commit.split(os.sep)
        if len(file_components) >= 3 and file_components[0] == 'recipes':
            packages.add(file_components[1])
    return packages


def get_downstream_dependencies(dependency_graph_files, package_infos):
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


def main():
    parser = argparse.ArgumentParser(description="List package versions")
    parser.add_argument("--commit-ids", nargs='*', dest="COMMIT_ID",
                        help="Find packages modified by supplied commits. Commit ids will also be obtained from "
                             "$ENV[GITHUB_EVENT][commits]")
    parser.add_argument("--requested-package", action='store',
                        help="Requested package will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_name]")
    parser.add_argument("--requested-package-version", action='store',
                        help="Used together with --requested-package, ignored when building all packages. "
                             "Requested package version will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_version]")
    parser.add_argument("--dependency-graph", nargs='+', dest="CONAN_DEPENDENCY_GRAPH.json",
                        help="Used to calculate downstream dependents of requested packages")

    args = parser.parse_args()

    github_event = json.loads(os.environ.get('GITHUB_EVENT', '{}'))
    inputs = github_event.get("inputs", dict())

    requested_packages = set()

    # Check if any packages were modified in git commits
    for commit_id in args.COMMIT_ID or list():
        print("commit {} requested as argument". format(commit_id))
        requested_packages.add(get_packages_in_commit(commit_id))

    for commit in github_event.get("commits", list()):
        if not str.lower(commit["message"]).find('[skipci]'):
            print("Found commit without [skipci]: {} - {}".format(commit["id"], commit["message"]))
            requested_packages.add(get_packages_in_commit(commit["id"]))

    # Check if any packages were asked to be rebuilt
    if args.requested_package:
        print("Requested package: " + args.requested_package)
        if args.requested_package_version and args.requested_package != 'all':
            requested_packages.add("{}/{}".format(args.requested_package, args.requested_package_version))
        else:
            requested_packages.add(args.requested_package)
    elif inputs.get('package_name'):
        print("Requested package: " + inputs.get('package_name'))
        if inputs.get('package_version') and inputs.get('package_name') != 'all':
            requested_packages.add("{}/{}".format(inputs.get('package_name'), inputs.get('package_version')))
        else:
            requested_packages.add(inputs.get('package_name'))

    package_infos = get_package_infos()
    filtered_packages = {}

    if 'all' in requested_packages:
        filtered_packages = package_infos
    else:
        dependency_graph_files = getattr(args, 'CONAN_DEPENDENCY_GRAPH.json') or list()
        downstream_deps = get_downstream_dependencies(dependency_graph_files, package_infos)
        for package in requested_packages:
            filtered_packages[package] = package_infos[package]
            for dependency in downstream_deps.get(package, list()):
                filtered_packages[dependency] = package_infos[dependency]

    gh_output = os.environ.get('GITHUB_OUTPUT')
    if gh_output:
        with open(gh_output, 'w') as out:
            print("packages=" + json.dumps(filtered_packages), file=out)

    print("packages=" + ' '.join(filtered_packages))


if __name__ == "__main__":
    main()
