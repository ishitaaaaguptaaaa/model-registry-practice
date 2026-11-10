# Model Registry Practice

A small practice project for learning how to replace or retire a model version safely.

It copies the structure of a typical Django machine learning registry, but uses only the
Python standard library (SQLite and unittest), so it runs anywhere with Python 3.10 or newer
and needs nothing installed.

## What is in it

| File | What it does |
|------|--------------|
| `registry.py` | The registry tables and the rules that protect them |
| `seed.py` | Creates a fresh registry: pipeline 1 active, three steps at version 1 |
| `predict.py` | Runs one prediction with the active pipeline and saves it to history |
| `find_dependencies.py` | Lists everything that depends on one model version |
| `check_contract.py` | Checks a new version has the same inputs and outputs as the old one |
| `switch_pipeline.py` | Makes a pipeline active (the "live" change); needs an explicit database path |
| `show_state.py` | Prints all pipelines and versions |
| `storage/models/` | The model files, one folder per step and version |
| `tests/` | Checks for the registry rules |
| `EXERCISE.md` | The 30 minute exercise |

## The tables

```
ml_model ──< model_version ──< pipeline_component >── pipeline_version
                  │                                         │
                  └──────< prediction_run_step >── prediction_run
```

- **ml_model**: the permanent name of a step, for example `step_b`.
- **model_version**: version 1, 2, 3 of that step. Each points to its own files. Status is draft, validated or deprecated.
- **pipeline_version**: a set of versions that run together. Status is draft, shadow, canary, active or retired. Only one can be active.
- **pipeline_component**: one row per step per pipeline, saying which version that pipeline uses.
- **prediction_run / prediction_run_step**: history. Each saved prediction remembers which pipeline and which versions produced it.

## Rules

1. Only one pipeline can be active. Activating a new one retires the old one.
2. A version that is part of any pipeline cannot be deleted.
3. A deprecated version cannot be added to a new pipeline.
4. Old versions are retired, not deleted, so history stays readable.
5. New model files go in a new folder. Old files are never overwritten.

## Quick start

```
python seed.py
python predict.py
python find_dependencies.py step_b 1
python -m unittest discover -s tests -v
```
