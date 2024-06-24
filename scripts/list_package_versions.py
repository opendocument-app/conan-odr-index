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
    parser.add_argument("--git-modified", help="Filter packages to include only modified packages, pass ${{ toJson("
                                               "github.event.commits) }} as argument here", action="store")
    parser.add_argument("--git-modified-tree", help="Filter packages to include only modified packages or packages "
                                                    "with modified dependencies, pass ${{ toJson("
                                                    "github.event.commits) }} as argument here", action="store")
    args = parser.parse_args()
    package_infos = get_package_infos()

    if args.git_modified_tree:
        # @TODO:
        raise Exception("Not implemented yet")

    if args.git_modified:
        updated_recipes = set()
        global_update = False
        for commit in json.loads(args.git_modified):
            files_in_commit = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit['id']],
                capture_output=True,
                text=True,
                cwd=root_path
            )
            for updated_file in filter(None, files_in_commit.stdout.split("\n")):
                update_file_full_path = PurePath(root_path / updated_file)
                if update_file_full_path.relative_to(recipes_path):
                    updated_recipe_name = update_file_full_path.parts[len(recipes_path.parts)]
                    updated_recipes.add(updated_recipe_name)
                else:
                    global_update = True

        if not global_update:
            filtered_packages = {}
            for package in package_infos:
                if package in updated_recipes:
                    filtered_packages[package] = package_infos[package]
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
