# FeatraceDev

[简体中文](README.md) | **English**

A development skill for **Claude Code and Codex**. Implement features and fixes in existing projects, trace their impact through the code, and retain the evidence needed to verify or resume the work.

[Install](#install) · [Examples](#examples) · [Updates and docs](#updates-and-docs)

## Install

Release package: **0.34.2**. Requires Python 3.9+, Git and the chosen Agent; use your project's existing build environment.

```bash
git clone --branch release/0.34.2 --single-branch https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py --agent claude
```

For Codex, replace `claude` with `codex`; use `both` to install for both hosts. Open a new session in your target project afterward.

## Examples

Open a new session in your target project. Enter `/dev` in Claude Code or `$dev` in Codex, then describe the work in plain language.

**Fix a bug**

> A failed sign-in leaves the page blank. Find the cause, fix the message, and verify successful sign-in and the failure message.

**Add a small feature**

> Add an “Open orders only” filter to the order list. Keep all orders visible by default. Check filtering and pagination, and report what you verified.

**Resume a task**

> Resume the order filter task. Read the current plan and existing evidence first, then run the checks that are still needed.

Share the original request, design, or reproduction steps as needed. An empty invocation activates the mode and displays the installed version. Use `dev off` to exit. On completion, the skill reports what changed, what was verified, and any remaining limits.

## Updates and docs

Preserve local changes, fetch and switch to the pinned `release/0.34.2` ref, then run `python3 scripts/install.py --agent claude --update`. Pulling an older release branch does not upgrade versions. The installer backs up the previous copy and refuses to overwrite modified installations.

- [Usage and recovery](docs/usage.md) · [Modules and workflow](docs/module-guide.md)
- [Changelog](CHANGELOG.md) · [Maintenance status](MAINTAINER.md)
- [Validation and limits](docs/validation.md) · [Product direction](PRODUCT.md)

Version 0.34.2 uses contract 10. Resume contract 9 tasks with pinned version 0.33.3. See the [usage guide](docs/usage.md) for older contracts.

**Feature · Trace · Delivery** · Created by [Perry Wang](https://github.com/P3rryW4ng). No open-source license has been selected.
