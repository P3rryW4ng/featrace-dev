---
name: featrace-verify
description: Independently review one FeatraceDev feature against a bound Git and evidence snapshot. Used by the dev router for an explicitly requested read-only second review; does not implement, execute project tests, or approve delivery.
---

# Independent Verify reviewer

This is a bundled specialist loaded explicitly by the dev router in a fresh context. It is not a second user workflow or separately installed command. Read only the request, snapshot and relevant project evidence; do not inherit the implementer's conversation or accept its verdict as truth.

## Required request

The router supplies the exact project, feature ID, absolute snapshot path, absolute Skill root, external output path and review question. The snapshot binds the pre-change base, current Git revision/worktree, feature sources/records, quality evidence, additional ignored files and Skill content. A base is an investigation start point, not proof that all feature changes are included. Confirm it against tasks/impact/traceability. If that cannot be established, report the uncertainty.

Before reading project evidence, run the read-only helper:

```text
python3 <SKILL>/core/scripts/verify-handoff.py check <PROJECT> <ID> --snapshot <SNAPSHOT>
```

If it fails, stop and return blocked with the error; do not repair the snapshot. Run `verify-inputs.py <PROJECT> <ID>` to identify actual readable sources and quality claims. Missing sources, build evidence or acceptance artifacts stay missing. A historical recorded observation is evidence of that observation, not an independent rerun or screenshot.

## Investigation

Compare original sources, confirmed requirements/decisions, tasks, implementation diff and actual tests. Check relevant callers and all consumers of changed shared constants/resources, preserved behavior and conditional paths. Start with changed/traceability paths, but search for consumers beyond them: the input list is not a claim of complete impact coverage. Do not read the entire project without a concrete dependency reason.

Track every project file actually read. For historical files read with Git at the bound base (including deleted files), use `base:relative/path` in read_paths and evidence.path; only regular files in snapshot.inputs.base_paths qualify, and the locator must distinguish old from current behavior. Files tracked by Git or marked `file` in snapshot.inputs.files are bound. For an additional ignored file, ask the router to recapture with `--path` and restart before relying on it. Do not read an unavailable/symlink path, external checkout or live remote source as bound evidence. Do not run builds, tests, migrations, project hooks or commands that write records. Recommend necessary checks in the output; the router owns authorized execution.

Identify contradictions, uncovered behavior and evidence limits. Support each finding with a relative file path, locator and observation; distinguish a confirmed mismatch from a possible risk. Put unproven suspicions and missing material in gaps. Do not invent expected behavior or turn an old failed observation into a known root cause. No findings does not mean delivery passed.

## Authority and test evidence

- Feature delivery status and individual requirement status describe different facts. A provisional feature may have confirmed requirements and unfinished implementation/acceptance. Assess the actual requirement status, sources and approved decisions; provisional alone is not evidence of unsettled product intent.
- Distinguish restoring confirmed behavior from changing it. When code violates an explicit preservation requirement, report an implementation defect. Technical ways to restore it do not require a new product choice merely because decisions.json is empty. Changing the requirement or resolving genuinely conflicting sources does require authority; do not offer accepting a regression as an equally authorized repair.
- Test IDs are logical references, not mandatory test function names or literals in source. Look for a mapping to executable cases/commands and inspect their assertions. Missing mapping is an evidence gap, not proof that a test does not exist. A short-input assertion provides partial coverage but does not prove a changed length boundary or another consumer's behavior.
- Cite only records actually read. If impact.json is missing, report a missing impact record; do not claim its contents omit a consumer based only on traceability.json. State what each cited artifact establishes and keep unproved scope assumptions in gaps.

## Return

Follow `../../core/references/write-scope.md` for the router-assigned external output. Write only that result path; do not create extra temporary scripts, copies or summaries in system temp or the project. Missing/unwritable output is a blocker, not permission to choose a new location.

Write only the external result requested by the router; no business code, project records or generated views. Use this JSON shape (replace examples with actual evidence):

```json
{
  "input_digest": "exact snapshot input_digest",
  "status": "reviewed",
  "summary": "What was reviewed and what remains uncertain",
  "read_paths": [],
  "findings": [],
  "gaps": [],
  "checks_not_run": []
}
```

`read_paths`, `gaps` and `checks_not_run` are arrays of strings (not objects); `findings` is an array of evidence-bearing objects. Keep evidence for a gap in its text, or put a supported claim into findings.

A finding is `{"claim":"specific mismatch or risk","evidence":[{"path":"relative/file","locator":"line or JSON pointer","observation":"what this source actually shows"}]}`. `status` is reviewed, blocked or failed, never passed/complete. Reviewed means the read-only investigation finished, even if it found defects. Blocked/failed must explain gaps. Include commands not executed and their purpose in checks_not_run; do not manufacture test results. Add measured elapsed time/token usage if available, otherwise say unmeasured in the summary.

Recheck with the helper and `--result <OUTPUT>` before returning. If inputs changed, retain the result but report stale; do not replace its digest. On timeout, cancellation, inaccessible tools or incomplete output, return the available evidence as blocked/failed when possible. A second reviewer never updates feature complete, fixes verified, decisions, or approval records.
