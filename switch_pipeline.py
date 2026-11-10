"""Make one pipeline the active one. This is the "live configuration" change.

The old active pipeline becomes 'retired' automatically. Rolling back is the
same command with the old pipeline number.

Usage:  python switch_pipeline.py <pipeline_number> --db <path>

The --db argument is required on purpose, so the live database is never
changed by accident. Practise on a copy first.
"""

import argparse

import registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("number", type=int)
    parser.add_argument("--db", required=True)
    args = parser.parse_args()

    conn = registry.connect(args.db)
    registry.set_pipeline_status(conn, args.number, "active")
    print(f"Pipeline {args.number} is now active in {args.db}")
    registry.print_state(conn)


if __name__ == "__main__":
    main()
