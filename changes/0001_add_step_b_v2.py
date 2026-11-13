"""Change 0001: add step_b version 2 and a draft pipeline that uses it.

What this should change:
  * add step_b v2 (status: draft), files in storage/models/step_b/v2/
  * add pipeline 2 (status: draft), a copy of pipeline 1 with step_b -> v2

What this must NOT change:
  * the active pipeline (pipeline 1 stays active)
  * step_b v1 or its files
  * any prediction history

Going live is a separate, reviewed step:  python switch_pipeline.py 2 --db <path>
Rollback:                                 python switch_pipeline.py 1 --db <path>

Usage:  python changes/0001_add_step_b_v2.py [--db path]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import registry  # noqa: E402

KEY = "step_b"
OLD_VERSION = 1
NEW_VERSION = 2
OLD_PIPELINE = 1
NEW_PIPELINE = 2


def apply(conn):
    existing = [p["version_number"] for p in registry.list_pipelines(conn)]
    if NEW_PIPELINE in existing:
        print(f"Pipeline {NEW_PIPELINE} already exists, nothing to do.")
        return

    # TODO 1: register step_b version 2 as a DRAFT.
    #   Function: registry.add_version(conn, key, number, artifacts, status=..., notes=...)
    #   artifacts: {"model": f"storage/models/{KEY}/v{NEW_VERSION}/model.json"}
    registry.add_version(conn, KEY, NEW_VERSION, {"model": f"storage/models/{KEY}/v{NEW_VERSION}/model.json"}, status="draft")

    # TODO 2: create pipeline 2 as a draft copy of pipeline 1, with only step_b
    #   changed to version 2.
    #   Function: registry.copy_pipeline(conn, from_number, to_number, name, replace={...})
    #   Name it "practice-pipeline-v2".
    registry.copy_pipeline(conn, OLD_PIPELINE, NEW_PIPELINE, "practice-pipeline-v2", replace={"step_b": NEW_VERSION})


    print(f"Added {KEY} v{NEW_VERSION} (draft) and pipeline {NEW_PIPELINE} (draft).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    args = parser.parse_args()
    conn = registry.connect(args.db)
    apply(conn)
    registry.print_state(conn)


if __name__ == "__main__":
    main()
