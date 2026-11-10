"""Check that a new model version can drop in for an old one.

The code that uses a step expects the same input features and the same output
labels. If either changes, the code must change too, so a plain version swap
is not enough.

Usage:  python check_contract.py <model_key> <old_version> <new_version> [--db path]
"""

import argparse
import json
import sys

import registry


def load(conn, key, number):
    version = registry.get_version(conn, key, number)
    location = json.loads(version["artifacts"])["model"]
    with open(registry.ROOT / location, encoding="utf-8") as f:
        return json.load(f)


def compare(old, new):
    problems = []
    if old["features"] != new["features"]:
        problems.append(f"features differ: {old['features']} vs {new['features']}")
    if old["labels"] != new["labels"]:
        problems.append(f"labels differ: {old['labels']} vs {new['labels']}")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    parser.add_argument("old", type=int)
    parser.add_argument("new", type=int)
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    args = parser.parse_args()

    conn = registry.connect(args.db)
    problems = compare(load(conn, args.key, args.old), load(conn, args.key, args.new))
    if problems:
        print(f"{args.key} v{args.old} -> v{args.new}: NOT a drop-in replacement")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"{args.key} v{args.old} -> v{args.new}: same features and labels, safe to swap")


if __name__ == "__main__":
    main()
