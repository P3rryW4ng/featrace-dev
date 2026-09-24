# FeatraceDev

[简体中文](README.md) | **English**

**Feature · Trace · Delivery**

**Turn evolving requirements into verifiable delivery.**

FeatraceDev helps coding agents understand requirements, investigate impact, implement changes, repair defects, and verify delivery in existing codebases. It connects original sources, confirmed requirements, tasks, historical fixes, and test evidence so future changes can build on recorded facts and completion claims have a clear verification scope.

Works with Claude Code and Codex. Includes a generic workflow and an Android adapter. Current version: **0.5.22**. Check the installed version separately on each machine.

> This is a developer-assisted delivery tool. It surfaces missing decisions and evidence, but cannot guarantee complete PRD understanding, discover every dependency, or replace device testing and subjective acceptance.

## Name and principles

- **Feature**: understand requirements and changes, and define implementation boundaries.
- **Trace**: connect requirements, decisions, code, and verification evidence while protecting confirmed behavior.
- **Delivery**: work toward results that can be accepted and continued by the next developer or agent.

FeatraceDev is the brand name, with Dev referring to development. Feature · Trace · Delivery expresses the product principles: features are the starting point, traceability provides assurance, and delivery is the outcome.

## Install

Requires Python 3.9+, Git, and Claude Code or Codex. Android projects also need their required JDK and Android SDK.

```bash
git clone https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py
```

By default, the installer installs for both Claude Code and Codex under the current user. Use `--agent claude` or `--agent codex` to install for just one. Open a **new session** after installation to load the updated skill.

## Start here

Open Claude Code in your application project and enter `/dev` once to start delivery mode for the current session. Then describe what you need without repeating `/dev next`:

```text
/dev
scan
prd ./requirements.md --feature OGFR-1234
Continue developing the current feature
I have new designs; please review their impact
status
```

Use the product or work-item ID already assigned by your team; the skill does not invent one. Run `scan` when first adopting the workflow in a project to investigate its build setup and module candidates. A newly created feature becomes the selected feature for the current session and project.

In Codex, invoke `$dev`, for example `$dev scan` or `$dev prd ./requirements.md --feature OGFR-1234`. In a Claude Code session, use `dev off` to leave delivery mode. Enter the mode again after starting a new session or switching projects. It does not write a permanent switch into the project or guarantee persistence across sessions.

### Everyday inputs

| Input | When to use it |
|---|---|
| `prd <file> --feature <work-item-ID>` | Create a feature and register its original sources |
| Describe the work, or use `next <description>` | Let the agent choose the next step from the current feature state |
| `status` | Read recorded progress, blockers, and next steps without rebuilding |
| `list` / `use <work-item-ID>` | Find and switch between features |
| `check` | Run selected checks and identify remaining manual acceptance work |
| `help` / `help <command>` | View precise commands and when to use them |
| `dev off` | Leave delivery mode in the current Claude Code session |

If unsure which command to use, describe the situation: “The back button does not follow the confirmed behavior,” “This PRD changes the flag rules,” or “I have a new interactive prototype.” The agent should investigate the defect, handle the requirement revision, or register the new source. Choices affecting product meaning still require your confirmation.

## How it supports delivery

1. **Understand change**: retain original PRDs, designs, API specifications, or HTML prototypes; distinguish clarifications, revisions, and confirmed requirements. Start with one source or several.
2. **Investigate impact**: locate relevant modules, relationships, and behavior to preserve, and identify historical fixes that may need retesting. Android Gradle relationships are review candidates, not a complete call graph.
3. **Implement and verify**: connect requirements to tasks and code, run selected checks, and distinguish automated tests, visual inspection, and device evidence. Failed or stale evidence does not automatically become a pass.
4. **Continue and revisit**: the application's `.agent-workflow/` stores requirements, decisions, fixes, and delivery records so a new session or developer can continue from records rather than chat memory.

A feature may span modules: payment rules can belong to a wallet module while chat hosts their presentation. The skill proposes roles and evidence rather than assigning a single owner from the feature name alone.

The internal workflow has six stages loaded as needed: Requirement, Scope, Build, Verify, Repair, and Deliver. **They currently run within one agent.** These are responsibility boundaries, not six new commands or a claim of independent multi-agent delivery.

## Add sources and handle fixes

Provide a document and prototype together when creating a feature:

```text
prd ./requirements.md --feature OGFR-1234 --source ./prototype.html
```

Add API or design material later without recreating the feature:

```text
api ./api.yaml
figma ./design-export.md
```

For explicit control, use `clarify` to investigate uncertainty, `revise` to update confirmed requirements, or `fix` to record and investigate observed discrepancies. A newer source does not automatically override confirmed requirements, and a code defect is not automatically treated as a PRD change. See the [usage guide (Chinese)](docs/usage.md) for complete parameters and additional commands.

## Project records and sharing

The skill repository and your application's `.agent-workflow/` are separate locations. Current requirements, tasks, decisions, traceability, and reviewed module descriptions can usually be shared according to team policy. Original PRDs, logs, scan drafts, and local quality commands may contain sensitive or environment-specific information; review them individually. Initialization does not automatically commit, push, or upload application materials. See the [Git sharing rules](skills/dev/core/references/git-sharing.md).

## Update and uninstall

From your cloned skill repository:

```bash
git pull --ff-only
python3 scripts/install.py --agent both --update
```

Open a new session afterward. Replace `both` with `claude` or `codex` to update one tool. To uninstall, run `python3 scripts/install.py --agent both --uninstall`. Old copies are moved to `~/.feature-delivery/backups/`. The installer refuses to overwrite an unrelated or locally modified installation.

### Migrate from the old repository

Existing `feature-delivery-skill` users can update the remote in their current clone:

```bash
git remote set-url origin https://github.com/P3rryW4ng/featrace-dev.git
git pull --ff-only
python3 scripts/install.py --agent both --update
```

You may rename the local clone directory to `featrace-dev`. The installer recognizes the legacy package identity and backs it up before updating. `/dev`, `$dev`, `skills/dev`, and the application's `.agent-workflow/` remain compatible. The existing installation marker filename and backup directory are retained to avoid moving existing records.

If Claude Code reports `Unknown skill: dev`, check that the skill exists at `~/.claude/skills/dev/` and open a new session. In Codex, use `$dev`.

## More information

- [Complete usage guide (Chinese)](docs/usage.md)
- [Changelog (Chinese)](CHANGELOG.md)
- [Maintainer documentation (Chinese)](MAINTAINER.md)

An open-source license has not yet been selected. The repository owner must define the permission terms before redistribution.

---

Created by [Perry Wang](https://github.com/P3rryW4ng).
