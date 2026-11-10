"""Checks for the registry rules. Run with:  python -m unittest discover -s tests -v"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import predict  # noqa: E402
import registry  # noqa: E402

STEPS = ("step_a", "step_b", "step_c")


def make_seeded_db():
    folder = tempfile.mkdtemp()
    conn = registry.connect(Path(folder) / "test.db")
    registry.create_tables(conn)
    for key in STEPS:
        registry.add_model(conn, key, key)
        registry.add_version(conn, key, 1, {"model": f"storage/models/{key}/v1/model.json"}, "validated")
    registry.create_pipeline(conn, 1, "test-v1")
    for key in STEPS:
        registry.add_component(conn, 1, key, 1)
    registry.set_pipeline_status(conn, 1, "active")
    return conn


class RegistryRules(unittest.TestCase):
    def setUp(self):
        self.conn = make_seeded_db()

    def test_active_pipeline_has_all_steps(self):
        pipeline, steps = registry.get_active_pipeline(self.conn)
        self.assertEqual(pipeline["version_number"], 1)
        self.assertEqual(sorted(steps), list(STEPS))

    def test_only_one_active_pipeline(self):
        registry.create_pipeline(self.conn, 2, "test-v2")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE pipeline_version SET status = 'active' WHERE version_number = 2")

    def test_switching_retires_old_pipeline(self):
        registry.copy_pipeline(self.conn, 1, 2, "test-v2")
        registry.set_pipeline_status(self.conn, 2, "active")
        statuses = {p["version_number"]: p["status"] for p in registry.list_pipelines(self.conn)}
        self.assertEqual(statuses, {1: "retired", 2: "active"})

    def test_version_in_a_pipeline_cannot_be_deleted(self):
        with self.assertRaises(sqlite3.IntegrityError):
            registry.delete_version(self.conn, "step_b", 1)

    def test_deprecated_version_cannot_join_new_pipeline(self):
        registry.set_version_status(self.conn, "step_b", 1, "deprecated")
        registry.create_pipeline(self.conn, 2, "test-v2")
        with self.assertRaises(registry.RegistryError):
            registry.add_component(self.conn, 2, "step_b", 1)

    def test_prediction_records_versions_used(self):
        predict.run_prediction(self.conn, {"score_a": 6, "score_b": 5.5, "score_c": 3})
        rows = self.conn.execute("SELECT model_version_id FROM prediction_run_step").fetchall()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["model_version_id"] is not None for row in rows))


if __name__ == "__main__":
    unittest.main()
