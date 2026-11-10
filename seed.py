"""Create a fresh registry with pipeline 1 active and every step at version 1.

Usage:  python seed.py [--db path]
"""

import argparse

import registry

STEPS = [
    ("step_a", "Step A classifier"),
    ("step_b", "Step B classifier"),
    ("step_c", "Step C classifier"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    args = parser.parse_args()

    conn = registry.connect(args.db)
    registry.create_tables(conn)

    if registry.list_pipelines(conn):
        print("Registry already has pipelines, nothing seeded.")
        registry.print_state(conn)
        return

    for key, name in STEPS:
        registry.add_model(conn, key, name)
        registry.add_version(
            conn, key, 1,
            {"model": f"storage/models/{key}/v1/model.json"},
            status="validated",
            notes="First version",
        )

    registry.create_pipeline(conn, 1, "practice-pipeline-v1")
    for key, _ in STEPS:
        registry.add_component(conn, 1, key, 1)
    registry.set_pipeline_status(conn, 1, "active")

    print("Seeded registry.")
    registry.print_state(conn)


if __name__ == "__main__":
    main()
