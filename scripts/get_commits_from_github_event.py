#!/usr/bin/env python3
import json
import os


def main():
    commits = []
    for commit in json.loads(os.environ.get('GITHUB_EVENT', '{}')).get("commits", list()):
        commits.append(commit["id"])
    print("commits=" + json.dumps(commits))


if __name__ == "__main__":
    main()
