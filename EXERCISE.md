# Exercise: Replace step_b version 1 with version 2, then plan its retirement

Time: about 30 minutes. Commands are written for PowerShell on Windows, run from the
project folder.

The goal is to propose the change in a branch and a pull request, prove it with tests and a
trial run on a copy of the database, and leave the main database untouched.

Starter files with marked gaps (`TODO 1` to `TODO 5`) are already in place:

- `changes/0001_add_step_b_v2.py`
- `changes/0002_retire_step_b_v1.py`
- `tests/test_change_0001.py`
- `PR_DESCRIPTION.md`

## Part 1. Starting point (5 minutes)

1. Create the registry and make two predictions so there is some history.

   ```
   python seed.py
   python predict.py
   python predict.py --score_b 4
   python show_state.py
   ```

2. Run the registry tests. All 6 should pass.

   ```
   python -m unittest discover -s tests -p "test_registry.py" -v
   ```

## Part 2. Find the dependencies (5 minutes)

3. Create a branch for the change.

   ```
   git switch -c replace-step-b-v2
   ```

4. List everything that depends on step_b version 1 and save it.

   ```
   New-Item -ItemType Directory -Force reports
   python find_dependencies.py step_b 1 | Out-File -Encoding utf8 reports/dependencies_step_b_v1.txt
   Get-Content reports/dependencies_step_b_v1.txt
   ```

   Note which pipelines use it, how many history rows point at it, where its files are, and
   which code lines name it.

## Part 3. Make the change (10 minutes)

5. Add the new model file in a new folder. Do not edit the v1 file.

   ```
   New-Item -ItemType Directory -Force storage/models/step_b/v2
   Copy-Item storage/models/step_b/v1/model.json storage/models/step_b/v2/model.json
   ```

   Open `storage/models/step_b/v2/model.json` and change `threshold` from 5 to 6 and
   `trained_on` to "practice data, second run with more examples".

6. Fill in TODO 1 and TODO 2 in `changes/0001_add_step_b_v2.py`, and TODO 3 in
   `changes/0002_retire_step_b_v1.py`. Delete each `raise NotImplementedError` line once
   its gap is filled.

7. Fill in TODO 4 and TODO 5 in `tests/test_change_0001.py`. Delete each `self.fail` line.

8. Run all the tests. All 12 should pass.

   ```
   python -m unittest discover -s tests -v
   ```

9. Run the change on the main database and check v2 can drop in for v1.

   ```
   python changes/0001_add_step_b_v2.py
   python check_contract.py step_b 1 2
   ```

   Pipeline 1 must still say `[active]` and pipeline 2 `[draft]`.

## Part 4. Trial run on a copy (5 minutes)

10. Copy the database and try the live switch on the copy only. Save the output.

    ```
    New-Item -ItemType Directory -Force practice_copy
    Copy-Item registry.db practice_copy/registry_copy.db
    python switch_pipeline.py 2 --db practice_copy/registry_copy.db
    python predict.py --db practice_copy/registry_copy.db
    python changes/0002_retire_step_b_v1.py --db practice_copy/registry_copy.db
    python -c "import registry; c=registry.connect('practice_copy/registry_copy.db'); registry.delete_version(c,'step_b',1)"
    python switch_pipeline.py 1 --db practice_copy/registry_copy.db
    python show_state.py
    ```

    What each line shows:
    - the switch makes pipeline 2 active and retires pipeline 1
    - the prediction now uses step_b v2
    - the retirement marks step_b v1 deprecated
    - the delete attempt is refused (`FOREIGN KEY constraint failed`)
    - the rollback makes pipeline 1 active again
    - the last line shows the main database: pipeline 1 is still active

    Copy this output into `reports/trial_run_on_copy.txt`.

## Part 5. Open the pull request (5 minutes)

11. Fill in `PR_DESCRIPTION.md` using the dependency report, the test result and the trial
    run.

12. Commit, push and open a pull request into `main`. Do not merge it. The pull request is
    the walkthrough for review.

    ```
    git add .
    git commit -m "Propose replacing step_b v1 with v2"
    git push -u origin replace-step-b-v2
    gh pr create --base main --head replace-step-b-v2 --title "Replace step_b v1 with v2 (proposal)" --body-file PR_DESCRIPTION.md
    ```

    The pull request can also be opened from the repository page on GitHub using the
    "Compare & pull request" button.
