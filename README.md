# 🗂️ ai-catalog

AI Catalog is a collection of [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) —
reusable, version-controlled playbooks for common software engineering workflows, invoked on demand with a
slash command such as `/iru-plan` or `/iru-pr-review`. Every skill and agent in this catalog carries an
`iru-` prefix to avoid colliding with skills installed from other marketplaces.

## 📊 Project Status

| | |
| --- | --- |
| License | Apache License 2.0 |
| CI | GitHub Actions — builds the Antora documentation site and publishes it to GitHub Pages on every push to `main` |

## 📖 Documentation

- [Antora documentation site](https://albertoirurueta.github.io/ai-catalog/) — published to GitHub Pages by the `docs.yml` workflow on every push to `main`

## ⚙️ How It Works

Each skill lives in its own directory under `.claude/skills/` and contains a single `SKILL.md` file with a
short description (used by Claude Code to decide when the skill is relevant) and step-by-step instructions
written for an agent to follow.

Skills range from small, single-purpose checks (`iru-check-license`, `iru-java-test`) to orchestrators that call
other skills in sequence — `iru-issue`, for example, chains `iru-explore` → `iru-plan` → `iru-code` → `iru-pr-description` →
`iru-pr-review` into one end-to-end, issue-to-PR flow.

To adopt a skill in another repository, copy its directory into that repository's `.claude/skills/`:

```bash
mkdir -p .claude/skills
cp -R ai-catalog/.claude/skills/iru-plan .claude/skills/
cp -R ai-catalog/.claude/skills/iru-pr-review .claude/skills/
```

Claude Code picks up any skill under `.claude/skills/<name>/SKILL.md` automatically — invoke it the same way
it's documented, e.g. `/iru-plan` or `/iru-pr-review`.

The catalog currently includes:

- **🏗️ Repository bootstrap** — `iru-setup-java-library-repository`, `iru-setup-java-library`,
  `iru-setup-java-github-workflows`, `iru-setup-java-gitignore`, `iru-setup-readme`, `iru-setup-changelog`, `iru-setup-antora`.
- **☕ Java quality** — `iru-java-test`, `iru-java-coverage`, `iru-java-code-quality`, `iru-java-javadoc`.
- **🔄 Issue-to-PR workflow** — `iru-issue`, `iru-explore`, `iru-plan`, `iru-code`.
- **🔀 Pull request lifecycle** — `iru-pr-description`, `iru-pr-review`.
- **🛠️ Maintenance** — `iru-release`, `iru-update-docs`, `iru-check-license`.
- **🧰 Catalog tooling** — `iru-generate-skill-docs`, which regenerates this catalog's own
  documentation from the skills and agents actually defined on disk.

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
