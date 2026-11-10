# Exercise: Replace step_b version 1 with version 2, then plan its retirement

Time: about 30 minutes. Commands are written for PowerShell on Windows.

The goal is to propose the change in a branch and a pull request, prove it with tests and a
trial run on a copy of the database, and leave the main database untouched.

## Part 1. Starting point (5 minutes)

1. Create the registry and make two predictions so there is some history.

   ```
   python seed.py
   python predict.py
   python predict.py --score_b 4
   python show_state.py
   ```

2. Run the tests. All should pass.

   ```
   python -m unittest discover -s tests -v
   ```

## Part 2. Find the dependencies (5 minutes)

3. Create a branch for the change.

   ```
   git switch -c replace-step-b-v2
   ```

4. List everything that depends on step_b version 1 and save it.

   ```
   New-Item -ItemType Directory -Force reports
   python find_dependencies.py step_b 1 | Tee-Object -FilePath reports/dependencies_step_b_v1.txt
   ```

   Note which pipelines use it, how many history rows point at it, where its files are, and
   which code lines name it.

## Part 3. Propose the change (10 minutes)

5. Add the new model files in a new folder: `storage/models/step_b/v2/model.json`.
   Do not edit the v1 file.

6. Write a change script, `changes/0001_add_step_b_v2.py`, that:
   - registers step_b version 2 as **draft**,
   - creates pipeline 2 as a **draft** copy of pipeline 1 with only step_b changed to version 2,
   - does **not** change which pipeline is active.

7. Add a test, `tests/test_change_0001.py`, that proves pipeline 1 is still active after the
   script runs, pipeline 2 differs from pipeline 1 only in step_b, and history is unchanged.

8. Check that version 2 is a drop-in replacement (same inputs and labels).

   ```
   python changes/0001_add_step_b_v2.py
   python check_contract.py step_b 1 2
   ```

## Part 4. Trial run on a copy (5 minutes)

9. Copy the database and try the live switch on the copy only.

   ```
   New-Item -ItemType Directory -Force practice_copy
   Copy-Item registry.db practice_copy/registry_copy.db
   python switch_pipeline.py 2 --db practice_copy/registry_copy.db
   python predict.py --db practice_copy/registry_copy.db
   python switch_pipeline.py 1 --db practice_copy/registry_copy.db
   python show_state.py
   ```

   The last command shows the main database: pipeline 1 is still active.

10. Show that the old version is protected: on the copy, try to delete step_b v1 and see it refused.

    ```
    python -c "import registry; c=registry.connect('practice_copy/registry_copy.db'); registry.delete_version(c,'step_b',1)"
    ```

## Part 5. Open the pull request (5 minutes)

11. Write a follow-up script, `changes/0002_retire_step_b_v1.py`, that marks v1 as
    deprecated. It is part of the proposal but is only run after pipeline 2 has been live and
    stable.

12. Fill in `PR_DESCRIPTION.md`, commit, push the branch and open a pull request.
    Do not merge it. The pull request is the walkthrough for review.

    ```
    git add .
    git commit -m "Propose replacing step_b v1 with v2"
    git push -u origin replace-step-b-v2
    ```
