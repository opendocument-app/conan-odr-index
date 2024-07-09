#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
from pathlib import Path
from pprint import pprint

import yaml

script_path = Path(__file__).resolve().parent
root_path = script_path.parent
recipes_path = root_path / "recipes"


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
    parser.add_argument("--request-package", action='store',
                        help="Requested package will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_name]")
    parser.add_argument("--request-package-version", action='store',
                        help="Used together with --request-package, ignored when building all packages. "
                             "Requested package version will also be obtained from "
                             "$ENV[GITHUB_EVENT][inputs][package_version]."
                             "Specify 'newest' or leave empty to request the newest version. "
                             "Specify 'all' to request all versions.")
    parser.add_argument("--dependency-graph", nargs='+', dest="CONAN_DEPENDENCY_GRAPH.json",
                        help="Used to calculate downstream dependents of requested packages")

    args = parser.parse_args()

    github_event = json.loads(os.environ.get('GITHUB_EVENT', '{}'))
    inputs = github_event.get("inputs", dict())

    requested_packages = set()

    # Check if any packages were modified in git commits
    for commit_id in args.COMMIT_ID or list():
        print("commit {} requested as argument". format(commit_id))
        requested_packages.update(get_packages_in_commit(commit_id))

    for commit in github_event.get("commits", list()):
        if -1 == str.lower(commit["message"]).find('[skipci]'):
            print("Found commit without [skipci]: {} - {}".format(commit["id"], commit["message"]))
            requested_packages.update(get_packages_in_commit(commit["id"]))

    # Check if any packages were asked to be rebuilt
    if args.request_package:
        if args.request_package == "all":
            requested_packages.add("all")
        else:
            requested = "{}/{}".format(args.request_package, args.request_package_version or "newest")
            print("Requested package: " + requested)
            requested_packages.add(requested)
    elif inputs.get('package_name'):
        if inputs.get('package_name') == "all":
            requested_packages.add("all")
        else:
            requested = "{}/{}".format(inputs.get('package_name'), inputs.get('package_version', "newest"))
            print("Requested package: " + requested)
            requested_packages.add(requested)

    package_infos = get_package_infos()
    filtered_packages = {}

    if 'all' in requested_packages:
        for package in package_infos:
            filtered_packages[package] = package_infos[package]
            # Request only the newest version, first in the array
            filtered_packages[package] = filtered_packages[package][:1]
    else:
        dependency_graph_files = getattr(args, 'CONAN_DEPENDENCY_GRAPH.json') or list()
        downstream_deps = get_downstream_dependencies(dependency_graph_files, package_infos)
        for package in requested_packages:
            if -1 == package.find('/'):
                package += "/newest"

            pkg_name, pkg_version = package.split('/')

            if pkg_version == "newest" or pkg_version == "":
                filtered_packages[pkg_name] = package_infos[pkg_name][:1]
            elif pkg_version == "all":
                filtered_packages[pkg_name] = package_infos[pkg_name]
            else:
                filtered_packages[pkg_name] = filter(lambda x: x["version"] == pkg_version, package_infos[pkg_name])

            for dependency in downstream_deps.get(pkg_name, list()):
                filtered_packages[dependency] = package_infos[dependency][:1]

    result = [
        infos
        for package in sorted(filtered_packages.keys())
        for infos in filtered_packages[package]
    ]
    print("packages=" + ' '.join(map(lambda x: x['package_reference'], result)))

    gh_output = os.environ.get('GITHUB_OUTPUT')
    if gh_output:
        with open(gh_output, 'w') as out:
            print("packages=" + json.dumps(result), file=out)


if __name__ == "__main__":
    main()
