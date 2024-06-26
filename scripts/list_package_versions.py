#!/usr/bin/env python3
import argparse
import json
import os.path
import subprocess
from pathlib import Path, PurePath
from pprint import pprint

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


def main():
    parser = argparse.ArgumentParser(description="List package versions")
    parser.add_argument("--github", help="Format output for GitHub Actions", action="store_true")
    parser.add_argument("--git-modified", nargs='+', dest="COMMIT_ID",
                        help="Return packages modified by supplied commits")
    parser.add_argument("--modified-tree", nargs='+', dest="CONAN_GRAPH.json",
                        help="Extra parameter for --git-modified to include dependants of modified packages too")
    args = parser.parse_args()

    if getattr(args, 'CONAN_GRAPH.json') and not args.COMMIT_ID:
        raise Exception("--modified-tree can only be used with --git-modified")

    package_infos = get_package_infos()
    pprint(package_infos)

    if args.COMMIT_ID:
        updated_packages = set()
        global_update = False

        for commit_id in args.COMMIT_ID:
            print("commit_id: '{}'".format(commit_id))
            print("git diff-tree --no-commit-id --name-only -r " + commit_id)
            subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id], cwd=root_path)
            files_in_commit = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
                capture_output=True,
                text=True,
                cwd=root_path
            )
            print('stderr: "{}"'.format(files_in_commit.stderr))
            print("Files in commit: {}".format(files_in_commit.stdout))
            for updated_file in filter(None, files_in_commit.stdout.split("\n")):
                print("Updated file: '{}'".format(updated_file))
                update_file_full_path = PurePath(root_path / updated_file)
                if update_file_full_path.is_relative_to(recipes_path):
                    updated_recipe_name = update_file_full_path.parts[len(recipes_path.parts)]
                    updated_packages.add(updated_recipe_name)
                else:
                    global_update = True

        # downstream_packages key is package name,
        # value is a set of packages that use this package
        downstream_packages = dict()
        for conan_dependency_graph_file in getattr(args, 'CONAN_GRAPH.json'):
            with open(conan_dependency_graph_file, 'r') as dep_json:
                nodes = json.load(dep_json)['graph']['nodes']
                for node in nodes:
                    node_name = nodes[node]['name']
                    if node_name not in package_infos:
                        continue

                    for dependency in nodes[node]['dependencies']:
                        dependency_ref = nodes[node]['dependencies'][dependency]['ref']
                        dep_name = dependency_ref.split('/')[0]

                        if dep_name not in package_infos:
                            continue

                        if dep_name not in downstream_packages:
                            downstream_packages[dep_name] = set()

                        downstream_packages[dep_name].add(node_name)

        if not global_update:
            filtered_packages = {}
            for package in package_infos:
                if package in updated_packages:
                    filtered_packages[package] = package_infos[package]
                    for dependency in downstream_packages.get(package, list()):
                        filtered_packages[dependency] = package_infos[dependency]
            package_infos = filtered_packages

    if args.github:
        result = [
            {
                "package_reference": f"{package}/{infos["version"]}",
                "package": package,
                "version": infos["version"],
                "conanfile": str(
                    Path("recipes") / package / infos["folder"] / "conanfile.py"
                ),
            }
            for package in sorted(package_infos.keys())
            for infos in sorted(package_infos[package], key=lambda x: x["version"], reverse=True)
        ]

        print("packages=" + json.dumps(result))
    else:
        for package in sorted(package_infos.keys()):
            infos = package_infos[package]
            print(f"{package}: {", ".join(sorted(info['version'] for info in infos))}")


if __name__ == "__main__":
    main()
