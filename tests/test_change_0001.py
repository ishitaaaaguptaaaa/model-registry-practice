"""Checks for changes/0001 and changes/0002.

Run with:  python -m unittest discover -s tests -v
"""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import predict  # noqa: E402
import registry  # noqa: E402
from test_registry import make_seeded_db  # noqa: E402


def load_change(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "changes" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


change_0001 = load_change("0001_add_step_b_v2.py")
change_0002 = load_change("0002_retire_step_b_v1.py")


def history(conn):
    rows = conn.execute("SELECT run_id, model_version_id FROM prediction_run_step ORDER BY id")
    return [tuple(row) for row in rows]


class Change0001(unittest.TestCase):
    def setUp(self):
        self.conn = make_seeded_db()
        predict.run_prediction(self.conn, {"score_a": 6, "score_b": 5.5, "score_c": 3})
        self.history_before = history(self.conn)
        change_0001.apply(self.conn)

    def test_pipeline_1_is_still_active(self):
        pipeline, steps = registry.get_active_pipeline(self.conn)
        self.assertEqual(pipeline["version_number"], 1)
        self.assertEqual(steps["step_b"]["version_number"], 1)

    def test_pipeline_2_only_changes_step_b(self):
        old = registry.get_components(self.conn, 1)
        new = registry.get_components(self.conn, 2)
        changed = {key for key in old if old[key] != new[key]}
        # TODO 4: check that `changed` is exactly {"step_b"}
        #   and that new["step_b"] is 2. Use self.assertEqual(a, b).
        self.fail("Fill in TODO 4, then delete this line")

    def test_history_is_unchanged(self):
        # TODO 5: check that history(self.conn) equals self.history_before.
        self.fail("Fill in TODO 5, then delete this line")

    def test_switch_and_rollback(self):
        registry.set_pipeline_status(self.conn, 2, "active")
        _, steps = registry.get_active_pipeline(self.conn)
        self.assertEqual(steps["step_b"]["version_number"], 2)
        registry.set_pipeline_status(self.conn, 1, "active")
        _, steps = registry.get_active_pipeline(self.conn)
        self.assertEqual(steps["step_b"]["version_number"], 1)


class Change0002(unittest.TestCase):
    def setUp(self):
        self.conn = make_seeded_db()
        change_0001.apply(self.conn)

    def test_refused_while_pipeline_1_is_active(self):
        with self.assertRaises(registry.RegistryError):
            change_0002.apply(self.conn)

    def test_allowed_after_pipeline_2_is_live(self):
        registry.set_pipeline_status(self.conn, 2, "active")
        change_0002.apply(self.conn)
        self.assertEqual(registry.get_version(self.conn, "step_b", 1)["status"], "deprecated")


if __name__ == "__main__":
    unittest.main()
