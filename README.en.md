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

These simulated Claude Code excerpts show the session flow. In Codex, use `$dev` in place of `/dev`.

**Fix a bug**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.2

❯ A failed sign-in leaves the page blank. Fix the message and verify both sign-in outcomes.
FeatraceDev ON · 项目：store-web
Found the error state in the sign-in page. I’ll update the message and run the sign-in tests.

FeatraceDev ON · 项目：store-web
Fixed the failure message. Two sign-in tests passed. Browser behavior was not checked.
```

**Add a small feature**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.2

❯ Add an “Open orders only” filter. Show all orders by default.
FeatraceDev ON · 项目：store-web
The list uses a shared pagination query. Changing the filter will return to page one.

FeatraceDev ON · 项目：store-web
Added the filter. Tests passed for the default view, filter changes, and pagination.
```

**Resume a task**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.2

❯ Resume the order filter task. Review existing evidence and run only the missing checks.
FeatraceDev ON · 项目：store-web
Resumed the order filter task. The filter evidence still applies. Pagination is the only remaining check.

FeatraceDev ON · 项目：store-web
The pagination check passed. The previous filter evidence was reused, and the task is closed.
```

Share the original request, design, or reproduction steps as needed. An empty invocation activates the mode and displays the installed version. Use `dev off` to exit. On completion, the skill reports what changed, what was verified, and any remaining limits.

## Updates and docs

Preserve local changes, fetch and switch to the pinned `release/0.34.2` ref, then run `python3 scripts/install.py --agent claude --update`. Pulling an older release branch does not upgrade versions. The installer backs up the previous copy and refuses to overwrite modified installations.

- [Usage and recovery](docs/usage.md) · [Modules and workflow](docs/module-guide.md)
- [Changelog](CHANGELOG.md) · [Maintenance status](MAINTAINER.md)
- [Validation and limits](docs/validation.md) · [Product direction](PRODUCT.md)

Version 0.34.2 uses contract 10. Resume contract 9 tasks with pinned version 0.33.3. See the [usage guide](docs/usage.md) for older contracts.

**Feature · Trace · Delivery** · Created by [Perry Wang](https://github.com/P3rryW4ng). No open-source license has been selected.
