# Repository maintenance

Read MAINTAINER.md and ROADMAP.md before modifying the Skill. Keep runtime resources self-contained under skills/dev. Use synthetic inputs in tests; never commit project .agent-workflow or personal configuration. Run python3 -m unittest discover -s tests -v after script changes. Update VERSION and CHANGELOG for releases. Do not claim planned capabilities are implemented.
