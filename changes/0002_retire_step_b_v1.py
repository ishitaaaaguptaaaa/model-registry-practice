"""Change 0002: retire step_b version 1.

Run ONLY after pipeline 2 has been active and stable.

The version is marked deprecated, not deleted:
  * prediction history keeps pointing at it
  * it can no longer be added to a new pipeline
  * its files stay in storage/models/step_b/v1/ so old runs can be explained

Usage:  python changes/0002_retire_step_b_v1.py --db <path>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import registry  # noqa: E402

KEY = "step_b"
VERSION = 1
LIVE_STATUSES = ("draft", "shadow", "canary", "active")


def still_used(conn):
    """Pipelines that are not retired and still include step_b v1."""
    version = registry.get_version(conn, KEY, VERSION)
    return conn.execute(
        """SELECT p.version_number, p.status FROM pipeline_component pc
           JOIN pipeline_version p ON p.id = pc.pipeline_id
           WHERE pc.model_version_id = ? AND p.status IN (?, ?, ?, ?)""",
        (version["id"], *LIVE_STATUSES),
    ).fetchall()


def apply(conn):
    blocking = still_used(conn)
    if blocking:
        names = ", ".join(f"pipeline {p['version_number']} [{p['status']}]" for p in blocking)
        raise registry.RegistryError(f"{KEY} v{VERSION} is still used by: {names}. Not retired.")

    # TODO 3: mark step_b v1 as "deprecated".
    #   Function: registry.set_version_status(conn, key, number, status)
    raise NotImplementedError("Fill in TODO 3, then delete this line")

    print(f"{KEY} v{VERSION} marked deprecated.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    conn = registry.connect(args.db)
    apply(conn)
    registry.print_state(conn)


if __name__ == "__main__":
    main()
