#!/usr/bin/env python3
import json
import os
from pprint import pprint


def main():
    commits = []
    for commit in json.loads(os.environ.get('GITHUB_EVENT', '{}')).get("commits", list()):
        commits.append(commit["id"])
    print("commits=" + ' '.join(commits))


if __name__ == "__main__":
    main()
