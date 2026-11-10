# Replace step_b v1 with v2 (proposal, not live)

## Summary

<!-- Two or three sentences: what changes, and that the active pipeline is NOT changed. -->

## Dependencies found

Report: `reports/dependencies_step_b_v1.txt`

| Dependency | Finding | Effect on the plan |
|------------|---------|--------------------|
| Pipelines | | |
| History | | |
| Model files | | |
| Code | | |
| Contract (`check_contract.py`) | | |

## Changes in this pull request

- `storage/models/step_b/v2/model.json`:
- `changes/0001_add_step_b_v2.py`:
- `changes/0002_retire_step_b_v1.py`:
- `tests/test_change_0001.py`:
- `reports/`:

## Testing

<!-- Number of tests and the result. What the trial run on the copy showed. -->

## Live configuration steps (not run in this pull request)

1. After approval, merge and run `python changes/0001_add_step_b_v2.py --db <live db>`.
2. Mark step_b v2 validated once its review is signed off.
3. Optional: set pipeline 2 to shadow and compare its outputs with pipeline 1.
4. In a planned window: `python switch_pipeline.py 2 --db <live db>`, then restart workers so cached model files reload.
5. Check that the next predictions record pipeline 2 and step_b v2.
6. After a stable period: `python changes/0002_retire_step_b_v1.py --db <live db>`.

## Rollback

<!-- The command, and why no file or data restore is needed. -->

## Risks

| Risk | Safeguard |
|------|-----------|
| | |
