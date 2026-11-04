# FeatraceDev

[简体中文](README.md) | **English**

A development Skill for **Claude Code and Codex**: understand impact, implement changes, and verify relevant behavior without unnecessary full-feature reacceptance.

## Install

Current release: **0.30.4**. Requires Python 3.9+, Git and the chosen Agent; use your project's existing build environment.

```bash
git clone --branch release/0.30.4 --single-branch https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py --agent claude
```

For Codex, replace `claude` with `codex`; use `both` to install for both hosts. Open a new session in your target project afterward.

## Use

Enter `/dev` in Claude Code or `$dev` in Codex, then describe the work. For example:

> Fix the login error message. Investigate the impact, implement the change, and verify the affected behavior.

Provide the original request and relevant design or bug details. No internal workflow commands are required. An empty invocation only activates the mode; `dev off` exits. Entry shows the installed version; successful closure explicitly reports the completed scope.

The Skill selects checks by actual impact, reuses applicable results, retains necessary evidence and commits completed subtasks within actual authorization. It does not replace product decisions, project gates or publication approval.

## Update and docs

Preserve local changes, fetch and switch to the pinned `release/0.30.4` ref, then run `python3 scripts/install.py --agent claude --update`. Pulling an older release branch does not upgrade versions. The installer backs up the previous copy and refuses to overwrite modified installations.

- [Usage and recovery](docs/usage.md) · [Modules and workflow](docs/module-guide.md)
- [Changelog](CHANGELOG.md) · [Maintenance status](MAINTAINER.md)
- [Validation and limits](docs/validation.md) · [Product direction](PRODUCT.md)

Use the appropriate pinned version for old tasks; business records are not automatically migrated or deleted. Long-term reliability and net savings still need real-world evidence.

**Feature · Trace · Delivery** · Created by [Perry Wang](https://github.com/P3rryW4ng). No open-source license has been selected.
