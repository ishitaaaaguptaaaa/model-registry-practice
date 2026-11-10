"""
Small model registry used for practice.

It keeps the same structure as a typical Django ML registry:

    ml_model            one row per pipeline step (the step's permanent name)
    model_version       numbered, frozen sets of files for one step
    pipeline_version    a bundle of versions that run together
    pipeline_component  "in pipeline N, step X uses version V"
    prediction_run      history of every prediction made
    prediction_run_step which version each step of a run used

Rules copied from the real design:
  * only one pipeline can be 'active' at a time
  * a version that is part of any pipeline cannot be deleted (RESTRICT)
  * a pipeline that has prediction history cannot be deleted (RESTRICT)
  * if a version is deleted, history rows lose their link (SET NULL),
    which is why old versions are retired and never deleted
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "registry.db"

VERSION_STATUSES = ("draft", "validated", "deprecated")
PIPELINE_STATUSES = ("draft", "shadow", "canary", "active", "retired")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ml_model (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    framework TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_version (
    id INTEGER PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_model(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL,
    artifacts TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'validated', 'deprecated')),
    notes TEXT NOT NULL DEFAULT '',
    UNIQUE (model_id, version_number)
);

CREATE TABLE IF NOT EXISTS pipeline_version (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    version_number INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'shadow', 'canary', 'active', 'retired')),
    notes TEXT NOT NULL DEFAULT ''
);

-- at most one active pipeline
CREATE UNIQUE INDEX IF NOT EXISTS one_active_pipeline
    ON pipeline_version (status) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS pipeline_component (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER NOT NULL REFERENCES pipeline_version(id) ON DELETE CASCADE,
    ml_model_id INTEGER NOT NULL REFERENCES ml_model(id) ON DELETE RESTRICT,
    model_version_id INTEGER NOT NULL REFERENCES model_version(id) ON DELETE RESTRICT,
    UNIQUE (pipeline_id, ml_model_id)
);

CREATE TABLE IF NOT EXISTS prediction_run (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER NOT NULL REFERENCES pipeline_version(id) ON DELETE RESTRICT,
    input_payload TEXT NOT NULL,
    output_payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prediction_run_step (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES prediction_run(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    ml_model_id INTEGER REFERENCES ml_model(id) ON DELETE SET NULL,
    model_version_id INTEGER REFERENCES model_version(id) ON DELETE SET NULL,
    output_value TEXT NOT NULL DEFAULT ''
);
"""


class RegistryError(Exception):
    pass


def connect(db_path=DEFAULT_DB):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn):
    conn.executescript(SCHEMA)
    conn.commit()


# ---------- models and versions ----------

def add_model(conn, key, name, framework="xgboost"):
    conn.execute(
        "INSERT OR IGNORE INTO ml_model (key, name, framework) VALUES (?, ?, ?)",
        (key, name, framework),
    )
    conn.commit()


def _model_id(conn, key):
    row = conn.execute("SELECT id FROM ml_model WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise RegistryError(f"No model with key '{key}'")
    return row["id"]


def get_version(conn, key, number):
    row = conn.execute(
        """SELECT mv.* FROM model_version mv
           JOIN ml_model m ON m.id = mv.model_id
           WHERE m.key = ? AND mv.version_number = ?""",
        (key, number),
    ).fetchone()
    if row is None:
        raise RegistryError(f"No version {number} for model '{key}'")
    return row


def add_version(conn, key, number, artifacts, status="draft", notes=""):
    if status not in VERSION_STATUSES:
        raise RegistryError(f"Unknown version status '{status}'")
    conn.execute(
        """INSERT INTO model_version (model_id, version_number, artifacts, status, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (_model_id(conn, key), number, json.dumps(artifacts), status, notes),
    )
    conn.commit()


def set_version_status(conn, key, number, status):
    if status not in VERSION_STATUSES:
        raise RegistryError(f"Unknown version status '{status}'")
    version = get_version(conn, key, number)
    conn.execute("UPDATE model_version SET status = ? WHERE id = ?", (status, version["id"]))
    conn.commit()


def delete_version(conn, key, number):
    """Will fail with sqlite3.IntegrityError if any pipeline still uses the version."""
    version = get_version(conn, key, number)
    conn.execute("DELETE FROM model_version WHERE id = ?", (version["id"],))
    conn.commit()


# ---------- pipelines ----------

def _pipeline_id(conn, number):
    row = conn.execute(
        "SELECT id FROM pipeline_version WHERE version_number = ?", (number,)
    ).fetchone()
    if row is None:
        raise RegistryError(f"No pipeline version {number}")
    return row["id"]


def create_pipeline(conn, number, name, status="draft", notes=""):
    if status == "active":
        raise RegistryError("Create the pipeline as draft, then use set_pipeline_status")
    conn.execute(
        "INSERT INTO pipeline_version (name, version_number, status, notes) VALUES (?, ?, ?, ?)",
        (name, number, status, notes),
    )
    conn.commit()


def add_component(conn, pipeline_number, key, version_number):
    version = get_version(conn, key, version_number)
    if version["status"] == "deprecated":
        raise RegistryError(f"{key} v{version_number} is deprecated and cannot be added")
    conn.execute(
        """INSERT INTO pipeline_component (pipeline_id, ml_model_id, model_version_id)
           VALUES (?, ?, ?)""",
        (_pipeline_id(conn, pipeline_number), version["model_id"], version["id"]),
    )
    conn.commit()


def copy_pipeline(conn, from_number, to_number, name, replace=None):
    """Make a new draft pipeline with the same components, optionally swapping some.

    replace = {"step_b": 2} means: use version 2 of step_b, keep everything else.
    """
    replace = replace or {}
    create_pipeline(conn, to_number, name, status="draft",
                    notes=f"Copy of pipeline {from_number} with changes: {replace}")
    for key, version_number in get_components(conn, from_number).items():
        add_component(conn, to_number, key, replace.get(key, version_number))


def set_pipeline_status(conn, number, status):
    """Same behaviour as PipelineVersion.save(): making one active retires the old one."""
    if status not in PIPELINE_STATUSES:
        raise RegistryError(f"Unknown pipeline status '{status}'")
    pid = _pipeline_id(conn, number)
    with conn:
        if status == "active":
            conn.execute(
                "UPDATE pipeline_version SET status = 'retired' WHERE status = 'active' AND id != ?",
                (pid,),
            )
        conn.execute("UPDATE pipeline_version SET status = ? WHERE id = ?", (status, pid))


def get_components(conn, pipeline_number):
    rows = conn.execute(
        """SELECT m.key, mv.version_number FROM pipeline_component pc
           JOIN ml_model m ON m.id = pc.ml_model_id
           JOIN model_version mv ON mv.id = pc.model_version_id
           WHERE pc.pipeline_id = ? ORDER BY m.key""",
        (_pipeline_id(conn, pipeline_number),),
    ).fetchall()
    return {row["key"]: row["version_number"] for row in rows}


def get_active_pipeline(conn):
    """Same idea as get_active_pipeline() in the real app: one active pipeline and its steps."""
    pipeline = conn.execute(
        "SELECT * FROM pipeline_version WHERE status = 'active'"
    ).fetchone()
    if pipeline is None:
        raise RegistryError("No active pipeline found")
    rows = conn.execute(
        """SELECT m.id AS model_id, m.key, mv.id AS version_id, mv.version_number, mv.artifacts
           FROM pipeline_component pc
           JOIN ml_model m ON m.id = pc.ml_model_id
           JOIN model_version mv ON mv.id = pc.model_version_id
           WHERE pc.pipeline_id = ?""",
        (pipeline["id"],),
    ).fetchall()
    steps = {
        row["key"]: {
            "model_id": row["model_id"],
            "version_id": row["version_id"],
            "version_number": row["version_number"],
            "artifacts": json.loads(row["artifacts"]),
        }
        for row in rows
    }
    return pipeline, steps


def list_pipelines(conn):
    return conn.execute(
        "SELECT version_number, name, status FROM pipeline_version ORDER BY version_number"
    ).fetchall()


def print_state(conn):
    print("Pipelines:")
    for p in list_pipelines(conn):
        comps = ", ".join(f"{k} v{v}" for k, v in get_components(conn, p["version_number"]).items())
        print(f"  pipeline {p['version_number']} ({p['name']}) [{p['status']}]: {comps}")
    print("Model versions:")
    for row in conn.execute(
        """SELECT m.key, mv.version_number, mv.status FROM model_version mv
           JOIN ml_model m ON m.id = mv.model_id ORDER BY m.key, mv.version_number"""
    ):
        print(f"  {row['key']} v{row['version_number']} [{row['status']}]")
