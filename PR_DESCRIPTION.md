# Replace step_b v1 with v2 (proposal, not live)

## Summary

Adds step_b version 2, a new version with the decision threshold changed from 5 to 6 and the
same inputs and labels as version 1. It also adds a draft pipeline 2 that uses it, and a
follow-up script that retires version 1 later. The active pipeline is NOT changed: version 2
and pipeline 2 are added as drafts only.

## Dependencies found

Report: `reports/dependencies_step_b_v1.txt`

| Dependency | Finding | Effect on the plan |
|------------|---------|--------------------|
| Pipelines | step_b v1 is used by pipeline 1, which is active | v1 cannot be edited in place; a new version and a new pipeline are added instead |
| History | 2 prediction history rows point at v1 | v1 is retired (deprecated), never deleted, so history stays readable |
| Model files | `storage/models/step_b/v1/model.json` found | v1 file is left as it is; v2 goes in a new folder |
| Code | 29 source lines mention step_b: seed, tests, change scripts and one comment in `registry.py` | None are live code paths, so no code change is needed |
| Contract (`check_contract.py`) | step_b v1 -> v2: same features and labels, safe to swap | v2 can replace v1 without code changes |

## Changes in this pull request

- `storage/models/step_b/v2/model.json`: the new model file, with the threshold changed from 5 to 6.
- `changes/0001_add_step_b_v2.py`: registers v2 as a draft and creates pipeline 2 as a draft copy of pipeline 1 with only step_b changed. Safe to run twice.
- `changes/0002_retire_step_b_v1.py`: marks v1 as deprecated. Refuses to run while any pipeline that is not retired still uses v1.
- `tests/test_change_0001.py`: tests for both change scripts.
- `reports/`: the dependency report and the trial run on a copy of the database.

## Testing

All 12 tests pass (6 registry rule tests and 6 tests for this change).

Trial run on a copy of the database (`reports/trial_run_on_copy.txt`), with the main database untouched:

- Switching to pipeline 2 made it active and retired pipeline 1.
- A prediction with the default input (score_b 5.5) used step_b v2 and gave "Calm". With v1 the same input gives "Alert". This is the behaviour change caused by the threshold moving from 5 to 6.
- The retirement script marked v1 as deprecated.
- Deleting v1 was refused with `FOREIGN KEY constraint failed`, because history still points at it.
- Switching back to pipeline 1 restored the original live pipeline.

## Live configuration steps (not run in this pull request)

1. After approval, merge and run `python changes/0001_add_step_b_v2.py --db <live db>`.
2. Mark step_b v2 validated once its review is signed off.
3. Optional: set pipeline 2 to shadow and compare its outputs with pipeline 1.
4. In a planned window: `python switch_pipeline.py 2 --db <live db>`, then restart workers so cached model files reload.
5. Check that the next predictions record pipeline 2 and step_b v2.
6. After a stable period: `python changes/0002_retire_step_b_v1.py --db <live db>`.

## Rollback

Run `python switch_pipeline.py 1 --db <live db>`, then restart workers. Pipeline 1 becomes
active again and pipeline 2 is retired. No file or data restore is needed, because nothing is
deleted: pipeline 1, step_b v1 and its model file all still exist.

## Risks

| Risk | Safeguard |
|------|-----------|
| The wrong database is switched | `switch_pipeline.py` has no default database; the path must be given |
| The old model file is overwritten | v2 uses a new folder; the v1 file is not edited |
| History loses its links | Versions are deprecated, never deleted; the database refuses to delete a version in use |
| Workers keep the old model after the switch | Restarting workers is part of the go-live step |
| v2 gives different answers (for example "Calm" instead of "Alert" near the threshold) | Optional shadow comparison before go-live, and a one-command rollback |
| v1 is retired too early | The retirement script refuses to run while any non-retired pipeline still uses v1 |
