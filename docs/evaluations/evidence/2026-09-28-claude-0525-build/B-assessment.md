# FEAT-001 `develop --parallel` — attempt assessment

**Outcome: honest failure at integration (`checks_failed`), not `candidate_checks_passed`.**
Both workers returned `ready`. The integration candidate passed the full unit suite (4 tests). The second approved integration command, `python3 -c "raise SystemExit(4)"`, exited 4. That is the controlled failure injection, and it is kept as it is. There was no retry, the check was not weakened and no result was overwritten. This is not final Verify, feature completion or a speed claim.

## Skill and route
- Loaded Skill: personally installed `/Users/mac/.claude/skills/dev`. `.feature-delivery-install.json` reports `featrace-dev` **0.5.25**, and `parallel-build.md` is headed "(0.5.25)".
- `/dev` was not registered as a host Skill: the Skill tool returned "Unknown skill: dev". So I read `SKILL.md`, `core/references/parallel-build.md` and `specialists/featrace-build/SKILL.md` from the installed directory and followed them by hand.
- Route: `develop` → Scope prerequisites (review of the existing records) → explicit `--parallel` pilot. The steps were prepare → preflight → two native Agent workers → inspect returns → integrate. All helper calls used the installed `core/scripts/parallel-build.py`.

## Scope review (read-only)
- `requirements.json`: R-1 is confirmed, with acceptance criteria for upper, lower, empty input and composition. `tasks.json` has T-UP and T-LOW, both `planned` and both linked to R-1. `impact.json` is reviewed, with `allowed_paths` [upper.py, lower.py] and base 8017a0c.
- Code: `upper.py:1-2` and `lower.py:1-2` are separate identity `convert` stubs with no shared state. Only `tests/test_composition.py` couples them, and only through each one's public output. This confirms the plan's independence rationale.
- `validate-feature.py --stage develop` gave `FEATURE_VALID` with two warnings: "historical regression review missing" and "task semantic review missing". These are **gaps** (see below). They were not resolved because canonical record writes were outside the authorization.

## Helper statuses
| Step | Result |
|---|---|
| `prepare <project> FEAT-001 --plan B/plan.json --out B/attempt` | `PARALLEL_BUILD_PREPARED`, run_digest `bbfcb3dc…2114` |
| router `preflight` | `PARALLEL_BUILD_INPUTS_CURRENT` |
| T-UP worker preflight / `finish --status ready` | current / **ready**. Check `test_upper.py` passed (rc 0) |
| T-LOW worker preflight / `finish --status ready` | current / **ready**. Check `test_lower.py` passed (rc 0) |
| router `integrate` | **`checks_failed`** (exit 1), candidate tree `f3f707297ce94aa31f44cd6733f213699c596421` |

The plan was used exactly as supplied, with the same tasks, ownership, checks and 30 s timeout.

## Native Agent calls
There were two host-native `Agent` calls (general-purpose type), launched concurrently in one message and in the background. Each was a fresh context and received only:
- its task ID, RUN, worktree and frozen inputs path;
- the Skill root and the Build specialist path;
- the side-effect restrictions.

No implementation hint was given. I waited for both to stop before inspecting or integrating. Host-reported usage:
- T-UP: 21,623 tokens, 7 tool uses, 37.5 s.
- T-LOW: 21,339 tokens, 7 tool uses, 36.6 s.

The split between workers was **instruction plus post-run helper checks**, not enforced by permissions. T-UP reported one small deviation: it read `run.json` just before running preflight. Preflight then passed with the same digest, and no edits had been made before it.

## Task / changed paths (inspected actual artifacts)
- T-UP, `returns/T-UP/patch.diff` (sha256 `20cc9013…fd8`, which matches result.json): `upper.py` only, `return value` → `return value.upper()`.
- T-LOW, `returns/T-LOW/patch.diff` (sha256 `5d29991a…708`, which matches): `lower.py` only, `return value` → `return value.lower()`.
- The check logs show "Ran 1 test … OK" for each. The patches are disjoint and semantically compatible: both are pure `str` methods that return new strings, so empty input stays empty and they compose. The worktrees show only the assigned file modified.

## Integration evidence (`attempt/integration`, `integration-report.json`)
- Check 0, `python3 -m unittest discover -s tests`: **passed**, rc 0, "Ran 4 tests … OK". This covers upper, lower, composition and empty input.
- Check 1, `python3 -c "raise SystemExit(4)"`: **failed**, rc 4, empty log.
- The candidate worktree has `upper.py` and `lower.py` modified (staged by the helper). The candidate is retained, and it is not accepted.

## Unchanged-primary check
Compared before and after the attempt:
- HEAD is `8017a0c0ab5c…` and the write-tree is `c1f61fbc…`. Both are unchanged.
- The `.git/index` sha256 is `73c342e3…` and unchanged.
- Every project file matches its baseline sha256, including all `.agent-workflow` records (`PRIMARY_FILES_UNCHANGED`).
- The status is still clean, apart from the pre-existing ignored `.agent-workflow/`.
- The branch is still `main` only, and there are no stashes.

The only Git metadata changes are three detached worktree registrations: `attempt/workers/T-UP`, `attempt/workers/T-LOW` and `attempt/integration`. There were no commits, pushes, record/status updates or cleanup.

## Gaps / not done
- Integration did not reach `candidate_checks_passed`, because the approved injected command failed. Nothing was adopted into the primary, and ordinary Verify was not run.
- Historical-regression and task-semantic review records are missing, as warned by the validator. The task meaning was reviewed read-only against R-1, but no review record was written.
- Worktree isolation is not a security sandbox. Scope was held by instructions and final hash checks.
- The worktrees and scratch are retained. Cleanup would be an explicit `git worktree remove` of clean trees only.
- Timings: prepare/preflight took about 1 s and integrate under 1 s (epoch seconds). The workers ran concurrently for about 37 s each. No speed-up is claimed.
