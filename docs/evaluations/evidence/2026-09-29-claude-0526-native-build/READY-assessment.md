# FEAT-001 `develop --parallel` — native /dev rehearsal assessment

Result: **external candidate checks passed (`candidate_checks_passed`).** This is not delivery. Nothing was adopted into the primary project, no state was set to complete, and no final Verify was run.

## Native entry and version
- Claude Code loaded the Skill from `/Users/mac/.claude/skills/dev` (personal install, not a project-local copy).
- Install marker `.feature-delivery-install.json`: package `featrace-dev`, version `0.5.26`.
- All 73 files listed in the marker match their recorded SHA-256 hashes (0 mismatches).
- No Skill, settings or plugin files were edited.

## References loaded
- SKILL.md router
- `orchestration.md`
- `workflow.md`
- `parallel-build.md`
- `impact-review.md`
- `task-semantic-review.md`
- `historical-regression.md`
- `profiles/generic/PROFILE.md`
- `specialists/featrace-build/SKILL.md`

`module-context.md` was not loaded. There is no module catalog, the feature is `unclassified`, and the validator did not require module scope. No scan was run.

## Scope exit (read-only; nothing synced, reviewed or refreshed)
- **Requirement:** R-1 is `confirmed` and sourced from `sources/prd-original.txt`. Its acceptance criteria are "upper abc gives ABC" and "lower ABC gives abc". PRD is present; API and Figma are `not_applicable`, with a reason given. There are no decisions and no fixes.
- **Tasks:** T-UP and T-LOW are both `planned`, both link to R-1, and neither depends on the other.
- **Task review:** `task-review.json` has current digest = reviewed digest (`8e46deb2…`), with 1 superseded history entry. Status reports `TASK_SEMANTICS: current`.
- **Historical regression:** `regression-review.json` covers paths `lower.py` and `upper.py`, matching `traceability.json`. It has 0 candidates and 0 pending. This is a valid zero-candidate record; it was not re-synced, because sync writes.
- **Impact:** `impact.json` has base_revision `d7e071f` (= HEAD). Allowed paths are exactly `upper.py` and `lower.py`. All six mechanisms are reviewed, and there is one change behavior and one preserve behavior. `impact.py` reported no changed paths.
- **Validator:** `validate-feature.py --stage develop` returned `FEATURE_VALID`. This checks structure only, not truth.
- **Primary tree:** clean, with no submodules or ignored business paths.
- **Independence:** each file contains only a two-line pure `convert` function (`upper.py:1-2`, `lower.py:1-2`), with no imports and no shared state. Each unit test imports only its own module. The cross-task check is `tests/test_integration.py`, which covers composition and empty strings.
- **Verdict:** Scope ready. The plan (`plan.json`, sha256 `9cbd3404…`) was used unchanged; its hash was the same before and after prepare.

## Prepare / dispatch / returns / integration
- **Prepare** created a new attempt at `READY/attempt`, which did not exist beforehand. Status `PARALLEL_BUILD_PREPARED`, run_digest `2b48e8e7…`.
- **Preflight** reported `PARALLEL_BUILD_INPUTS_CURRENT`.
- **Dispatch:** two native Claude Code Agents (general-purpose type), each told to load the bundled Build specialist. They ran concurrently in separate contexts and separate detached worktrees. No implementation hint was given to either. The split between workers is enforced only by instructions and the helper's post-run checks, not by permissions.
- **Returns:** both workers ran preflight and then `finish` once.
  - T-UP returned `ready`. It changed only `upper.py`. The patch hash matches its record (`20cc9013…`), and the selected check `test_upper.py` passed.
  - T-LOW returned `ready`. It changed only `lower.py`. The patch hash matches its record (`5d29991a…`), and the selected check `test_lower.py` passed.
  - The router inspected the actual `patch.diff` files and check logs; each is a one-line change inside its assigned function.
  - The T-UP worker said it sent its edit and its `finish` call in the same batch. The recorded worker state still shows the edited `upper.py`, and the check ran against it.
- **Integrate** ran only after both Agents had stopped. The candidate is at `attempt/integration`.
  - Status `candidate_checks_passed`, base `d7e071f`, candidate tree `fb2809f2…`.
  - The integration check (`unittest discover -s tests`) ran 4 tests and passed.
  - The changes are staged in the candidate worktree's own index.

## Primary and shared-record preservation
- SHA-256 of every primary non-.git file, plus HEAD and `.git/index`, were recorded before any helper ran and again after integration. The two snapshots are identical.
- Primary HEAD is still `d7e071f` on `main`, the tree is clean, and no branches were added.
- The only primary Git metadata change is three registered worktrees: `workers/T-UP`, `workers/T-LOW` and `integration`.
- No canonical record, source, business or test file was written.
- No commits, pushes, network, MCP, installs or cleanup.

## Metrics (observed)
- Router wall clock from start to integration check: about 130 s.
- Prepare took about 1 s; integrate took about 1 s.
- T-UP worker: 35.0 s, 32,439 tokens, 7 tool uses.
- T-LOW worker: 38.8 s, 31,009 tokens, 6 tool uses.
- Router token count is not exposed. There is no serial baseline, so this run does not show whether parallel is faster.

## Limits
- Worktrees share Git metadata and are not a security sandbox. Hashes detect drift after the fact; they do not prove the workers behaved correctly while running.
- Review records were reused as they were, not re-derived. Structural validity does not prove semantic correctness.
- The tests cover only the stated acceptance criteria, composition and empty strings.
- Not done: adoption into the primary project, task/traceability/verification updates, ordinary check/audit against a primary snapshot, and cleanup. All worktrees and scratch files remain in place.
