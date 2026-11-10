"""List everything that depends on one model version before it is replaced or retired.

Usage:  python find_dependencies.py <model_key> <version_number> [--db path]

Checks four places:
  1. pipelines that include this version (blocks deletion)
  2. prediction history that points at this version (would lose its link)
  3. model files on disk for this version
  4. code and config files in this folder that mention the model key by name
"""

import argparse
import json

import registry

SKIP_DIRS = {".git", "__pycache__", "reports", "practice_copy"}


def pipelines_using(conn, version_id):
    return conn.execute(
        """SELECT p.version_number, p.name, p.status FROM pipeline_component pc
           JOIN pipeline_version p ON p.id = pc.pipeline_id
           WHERE pc.model_version_id = ? ORDER BY p.version_number""",
        (version_id,),
    ).fetchall()


def history_count(conn, version_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM prediction_run_step WHERE model_version_id = ?",
        (version_id,),
    ).fetchone()["n"]


def code_mentions(key):
    hits = []
    for path in sorted(registry.ROOT.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix not in (".py", ".json"):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if key in line:
                hits.append(f"{path.relative_to(registry.ROOT).as_posix()}:{number}: {line.strip()}")
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    parser.add_argument("version", type=int)
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    args = parser.parse_args()

    conn = registry.connect(args.db)
    version = registry.get_version(conn, args.key, args.version)
    artifacts = json.loads(version["artifacts"])

    print(f"Dependency report for {args.key} v{args.version} (status: {version['status']})")
    print()

    usages = pipelines_using(conn, version["id"])
    print(f"1. Pipelines that use it: {len(usages)}")
    for p in usages:
        print(f"   - pipeline {p['version_number']} ({p['name']}) [{p['status']}]")
    if any(p["status"] == "active" for p in usages):
        print("   WARNING: used by the ACTIVE pipeline. Changing it changes live predictions.")

    count = history_count(conn, version["id"])
    print(f"2. Prediction history rows pointing at it: {count}")
    if count:
        print("   Deleting this version would blank these links. Retire it instead.")

    print("3. Model files:")
    for name, location in artifacts.items():
        exists = (registry.ROOT / location).exists()
        print(f"   - {name}: {location} ({'found' if exists else 'MISSING'})")

    hits = code_mentions(args.key)
    print(f"4. Source lines that mention '{args.key}': {len(hits)}")
    for hit in hits:
        print(f"   - {hit}")


if __name__ == "__main__":
    main()
