# .claude-plugin

`marketplace.json` in this directory is generated: do not edit it by hand. It is the `ai-catalog` plugin marketplace, one
entry per plugin (`iru-core`, `iru-knowledge` and one plugin per stack), built from the membership map in
`tools/plugins.json` over the unchanged `.claude/skills/` and `.claude/agents/` directories. Add the marketplace with
`claude plugin marketplace add albertoirurueta/ai-catalog` and install plugins with `/plugin install iru-core@ai-catalog`.

To regenerate it after adding, removing or renaming a skill or agent (new skills must first be added to a plugin in
`tools/plugins.json`), run `python3 tools/generate-marketplace.py`, then `claude plugin validate .`. CI runs
`python3 tools/generate-marketplace.py --check` and fails when the committed file is stale.
