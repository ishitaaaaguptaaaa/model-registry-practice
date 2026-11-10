"""Run one prediction with the active pipeline and save it to the history tables.

Usage:  python predict.py [--db path] [--score_a N] [--score_b N] [--score_c N]
"""

import argparse
import json
from functools import lru_cache

import registry


@lru_cache(maxsize=32)
def load_model_file(location):
    # Cached like the real artifact loader: a running process keeps the old
    # file in memory until it is restarted.
    with open(registry.ROOT / location, encoding="utf-8") as f:
        return json.load(f)


def predict_step(model, inputs):
    feature = model["features"][0]
    value = float(inputs.get(feature, 0))
    low, high = model["labels"]
    return high if value >= model["threshold"] else low


def run_prediction(conn, inputs):
    pipeline, steps = registry.get_active_pipeline(conn)
    if "step_a" not in steps:
        raise RuntimeError("Missing step_a model in active pipeline")

    outputs = {}
    used = []
    for sequence, key in enumerate(sorted(steps), 1):
        step = steps[key]
        model = load_model_file(step["artifacts"]["model"])
        outputs[key] = predict_step(model, inputs)
        used.append((sequence, step, outputs[key]))

    with conn:
        cur = conn.execute(
            "INSERT INTO prediction_run (pipeline_id, input_payload, output_payload) VALUES (?, ?, ?)",
            (pipeline["id"], json.dumps(inputs), json.dumps(outputs)),
        )
        run_id = cur.lastrowid
        for sequence, step, value in used:
            conn.execute(
                """INSERT INTO prediction_run_step
                   (run_id, sequence, ml_model_id, model_version_id, output_value)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, sequence, step["model_id"], step["version_id"], value),
            )
    return pipeline, steps, outputs, run_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(registry.DEFAULT_DB))
    parser.add_argument("--score_a", type=float, default=6)
    parser.add_argument("--score_b", type=float, default=5.5)
    parser.add_argument("--score_c", type=float, default=3)
    args = parser.parse_args()

    conn = registry.connect(args.db)
    inputs = {"score_a": args.score_a, "score_b": args.score_b, "score_c": args.score_c}
    pipeline, steps, outputs, run_id = run_prediction(conn, inputs)

    print(f"Run {run_id} used pipeline {pipeline['version_number']} ({pipeline['name']})")
    for key in sorted(outputs):
        print(f"  {key} v{steps[key]['version_number']} -> {outputs[key]}")


if __name__ == "__main__":
    main()
