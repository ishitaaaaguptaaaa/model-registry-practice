"""Print all pipelines and model versions.

Usage:  python show_state.py [--db path]
"""

import argparse

import registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    args = parser.parse_args()
    registry.print_state(registry.connect(args.db))


if __name__ == "__main__":
    main()
