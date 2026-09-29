T-UP is ready for your review: `upper.convert` now returns the uppercase of its input, and its one assigned check passed.

**Change (`upper.py:2`):** `return value` became `return value.upper()`. I read the diff before finishing: `upper.py` is the only changed file, and it's left uncommitted in the T-UP worktree.

**Finish output:** the helper recorded `status: ready`, `changed_paths: ["upper.py"]` and `patch_sha256 20cc9013…`. The assigned check (`python3 -m unittest discover -s tests -p test_upper.py`) passed with return code 0, logged in `check-0.log`.

**Scope:** `lower.py`, the tests, `.agent-workflow` records, the frozen inputs, the primary project and the T-LOW worktree were not touched. There was no commit, install or network use, and I have not marked the task complete.

**Limitations:**
- `ready` means only that this one check passed; the feature is not done or verified.
- I did not run the integration check (`tests/test_integration.py`, which tests the two functions together and empty strings). It depends on T-LOW's change and is the router's job at integration.
- Non-string inputs are not handled or checked, because the requirements only cover `str -> str`.
- The host didn't show me elapsed time or token counts, so I can't report them.
