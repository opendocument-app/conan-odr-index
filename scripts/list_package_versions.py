#!/usr/bin/env python3

import argparse
from pathlib import Path
import yaml
import json


def get_package_infos():
    script_path = Path(__file__).resolve().parent
    root_path = script_path.parent
    recipes_path = root_path / "recipes"

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
    package_infos = get_package_infos()
    parser = argparse.ArgumentParser(description="List package versions")
    parser.add_argument(
        "--github", help="Format output for GitHub Actions", action="store_true"
    )
    args = parser.parse_args()
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
