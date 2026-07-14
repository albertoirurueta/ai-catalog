# 🗂️ ai-catalog

AI Catalog is a collection of [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) —
reusable, version-controlled playbooks for common software engineering workflows, invoked on demand with a
slash command such as `/plan` or `/pr-review`.

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

Skills range from small, single-purpose checks (`check-license`, `java-test`) to orchestrators that call
other skills in sequence — `issue`, for example, chains `explore` → `plan` → `code` → `pr-description` →
`pr-review` into one end-to-end, issue-to-PR flow.

To adopt a skill in another repository, copy its directory into that repository's `.claude/skills/`:

```bash
mkdir -p .claude/skills
cp -R ai-catalog/.claude/skills/plan .claude/skills/
cp -R ai-catalog/.claude/skills/pr-review .claude/skills/
```

Claude Code picks up any skill under `.claude/skills/<name>/SKILL.md` automatically — invoke it the same way
it's documented, e.g. `/plan` or `/pr-review`.

The catalog currently includes:

- **🏗️ Repository bootstrap** — `setup-java-library-repository`, `setup-java-library`,
  `setup-java-github-workflows`, `setup-java-gitignore`, `setup-readme`, `setup-changelog`, `antora-setup`.
- **☕ Java quality** — `java-test`, `java-coverage`, `java-code-quality`, `java-javadoc`.
- **🔄 Issue-to-PR workflow** — `issue`, `explore`, `plan`, `code`.
- **🔀 Pull request lifecycle** — `pr-description`, `pr-review`.
- **🛠️ Maintenance** — `release`, `update-docs`, `check-license`.
- **🧰 Catalog tooling** — `generate-skill-docs`, which regenerates this catalog's own
  documentation from the skills and agents actually defined on disk.

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
