# Router assessment — DEMO-PREVIEW independent review (attempt C)

**Outcome: BLOCKED at router preflight. No reviewer was started. No reviewer result (`result.json`) was written.**

## Inputs
- Project: `/private/var/folders/d_/q6w_z5qx1vl939khdfl92b540000gn/T/featrace-verify-0523-nb7rgm_b/project`
- Feature: `DEMO-PREVIEW`
- Snapshot (used as given, not recaptured or modified): `/private/tmp/featrace-claude-0524-20260928/C/snapshot.json`, input_digest `4dca2a8524b471a1341e4ad32b74beb591eb6b1cf3cab6199da156703f7f2e5d`
- Base `287acff` ("baseline"). It is a defensible pre-change base because `git log --stat` shows a single later commit, `271dc41` "shorten preview labels", which changes only `src/formatting.py` (+1/−1). That matches snapshot `changed_paths`, and the snapshot's `git_head` is still HEAD.
- Review question: Is the current implementation consistent with confirmed requirements, and what evidence supports the next eligible action?

## Checks performed (all read-only)
1. Read the installed router `SKILL.md`, `core/references/independent-verify.md`, `specialists/featrace-verify/SKILL.md` and the snapshot.
2. Ran `git log --oneline --stat -3` and `git status --porcelain --ignored`. The worktree is clean. The ignored paths are `.agent-workflow/features/DEMO-PREVIEW/sources/` and `.agent-workflow/project-baseline/`.
3. Ran the router preflight `verify-handoff.py check <PROJECT> DEMO-PREVIEW --snapshot <SNAPSHOT>`. Result: **exit 1**, `VERIFY_HANDOFF_ERROR: review inputs stale; preserve result and redispatch with current inputs`.
4. Ran `verify-inputs.py <PROJECT> DEMO-PREVIEW`, which is a read-only inventory (exit 0, `status: review_required`).

## Why preflight failed
- `.agent-workflow/features/DEMO-PREVIEW/sources/prd.txt` has drifted since the snapshot was captured:
  - In the snapshot: 106 bytes, sha256 `f3cba2b2…bd40`
  - Now: 161 bytes, sha256 `7d56c63a…cce9`
- The PRD is an ignored file, so Git HEAD/index/worktree identity doesn't show the change. The file-hash binding does.
- I did not read the PRD's contents (old or new), and I did not work out what changed. This is not a finding about requirements.

## Other gaps visible from the input inventory (not reviewed)
- `sources/layout.png` is indexed but missing on disk (`source_unavailable`), and the Figma source status is `missing`.
- `project-baseline/quality-report.json` says it is a "synthetic fixture; not a real measured run". It is not test evidence.
- `.agent-workflow/config.yaml`, `modules` and `quality-gates.json` are missing. No `impact.json` is bound.

## Delegation and evidence
- Delegation: **none**. The rules say not to spawn an Agent when a preflight failure is already known.
- Project files read: none beyond Git metadata and the helper outputs above. No business code, feature records or sources were opened.
- Not run (review-only scope): project tests/builds, recapture, record writes, commits, installs, logins.
- Timing and tokens: not measured.

## Status / next eligible action
- The review is **not complete**, and this is **not** delivery approval. Nothing here assesses whether the implementation matches the requirements.
- To get an independent review, a new attempt would have to:
  1. Confirm the PRD change is intended.
  2. Pause writes.
  3. Capture a **new** snapshot into a new scratch attempt directory.
  4. Pass preflight, then dispatch one fresh reviewer.
- This snapshot stays as it is. Its digest must not be patched.
