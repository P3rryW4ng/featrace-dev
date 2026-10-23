# FeatraceDev

[简体中文](README.md) | **English**

**Feature · Trace · Delivery** — Turn changing requirements into verifiable delivery.

Help Claude Code and Codex investigate impact, implement changes, repair failures and verify relevant behavior in existing projects. Use code, configuration, tests and actual product intent, without turning every local change into full business reacceptance.

| Object | Current state |
|---|---|
| Release version | **0.25.0**, current-task workflow,11 runtime files |
| Validation scope | 190 current kernel tests; program safeguards and Agent competence evaluated separately, with natural trials still pending |
| Real-world outcome | Phase two remains open: natural classification, resumption and net cost need new-project evidence |

0.25.0 adds bounded correction retaining original receipts and safe policy diagnostics, alongside scoped review/constraints and temporal applicability; it does not read/migrate legacy ledgers. Use pinned0.22.0 for old-record continuation. See [maintenance status](MAINTAINER.md) for release/actual installation identities.


Current main also contains a tested contract3 source replacement, not yet published or installed. Official0.25.0 uses the pinned release ref above; the new source does not read/write or migrate contract1/2 tasks. See maintenance status.

## Replacement capabilities

- Combine presentation, interaction, state, interface, shared and device checks from causal impact, rather than reaccept the entire parent requirement.
- Separate behavioral impact, product authority and execution inputs. Reuse valid checks; distinguish runtime observations, static analysis, failures and unknowns.
- Keep one project policy and one bounded active task. Preserve lasting intent/constraints in tests, adjacent comments or existing concise project records.
- For Figma-based tasks, read selected nodes, reuse project components and compare scoped rendered UI; actual connector access belongs to the host.
- Clean owned task outputs under the confirmed calendar-day policy; query and page necessary content instead of preserving every feature's complete process forever.
- Reuse genuine same-scope authorization; ask only for actual conflicts, missing sources/accounts or host restrictions. Use the host's actual native task/plan tools and presentation; otherwise ordinary concise progress prose, without drawn checkbox/status lists or fixed phases.

Explicitly correct selected claims in retained completed tasks while preserving the original receipt. Corrected format2 records require supporting readers; compacted sources cannot be reconstructed and business records are not automatically migrated.

Commit each completed working subtask locally after necessary checks, before feature closure; actual commit restrictions still apply and push is separate. Current-state claims use the real environment and original observation time; as-of screenshots do not expire uniformly.

These are0.25.0 capability boundaries. Installing old0.22.0 does not enable this workflow. It does not guarantee full dynamic dependencies, objective visual judgment or genuine host independence. Code and structural validity do not establish product correctness.

## Install and update an official release

Requires Python3.9+,Git and the chosen host; Android also needs the project's JDK/SDK. Install from the pinned0.25.0 release branch:

```bash
git clone --branch release/0.25.0 --single-branch https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py --agent both
```

Preserve existing local changes and verify the official checkout before updating. Pulling an old release branch does not upgrade versions: explicitly fetch and switch to release/0.25.0. Use `--update` only from that release tree; select `--agent claude` or `--agent codex` as needed. Open a new session afterward. The installer refuses unrelated or locally modified copies, backs up updates and moves uninstalled copies to backups with `--uninstall`. The installer requires a matching committed release.json, local release ref and runtime/installer content. Development trials require explicit --development with a separate identity; this is not signed remote-origin authentication.

Find legacy commands, acceptance contracts and records in the [fixed0.22.0 guide](https://github.com/P3rryW4ng/featrace-dev/blob/54c5260fd6688a0bca9c83f29bad240321a67b52/README.en.md). The replacement does not migrate or delete old application .agent-workflow data; use a pinned old version for explicit old-record continuation.

## Use and documentation

Claude invokes `/dev`,Codex invokes `$dev`. An empty invocation activates this conversation's mode without starting work. For development, provide the target project, original request and any necessary design reference. Mode is not inherited by a new session/project; `dev off` exits. Help, status and historical questions do not initialize tasks or run tests.

- [Current source workflow](docs/usage.md): daily development, files, resumption and cleanup.
- [Product direction](PRODUCT.md): developer assistance and longer-term vision.
- [Current queue and phase two](ROADMAP.md): unresolved issues and next actions.
- [Capability standards and baseline](docs/capabilities.md): separate ability, evidence and cost, retaining unknowns.
- [Validation and fixed historical entrypoints](docs/validation.md): measured facts and unproven outcomes.
- [Changelog](CHANGELOG.md): published history, not active development instructions.

Commits, pushes, PRs, installation and publication follow actual authorization; materials are not uploaded automatically. No open-source license has been selected; public readability does not grant redistribution rights.

Created by [Perry Wang](https://github.com/P3rryW4ng).
