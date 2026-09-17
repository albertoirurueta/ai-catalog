# Implementation plan — Extend the catalog to TypeScript, Android, Swift and hybrid mobile stacks

## Task summary

Source: GitHub issue #6
Base branch: main

Extend `ai-catalog` — today a Java / Spring Boot / .NET / database-only catalog of Claude Code skills — so the same
end-to-end support (repository bootstrap, GitHub Actions CI/CD, tests, coverage, SonarCloud, lint/static analysis,
security checks, docs generation, and the `iru-plan` → `iru-code` implementation pipeline) exists for ten more
project types: npm/TypeScript library, React web app, Angular web app, Spring Boot + Vaadin + Hilla, Android
library, Android app, Swift Package Manager library, Apple (iOS/iPadOS/macOS/watchOS) app, React Native app, and
Ionic app. Three cross-cutting changes come with it: every setup skill (existing Java ones included) asks whether
the project is open source before wiring SonarCloud / Maven Central / npm / Swift Package Index; a single
`iru-setup-repository` front door asks the project type and delegates; and an existing-repository mode runs
`iru-explore` first and forces every sub-skill into gap-fill mode.

The deliverable is Markdown (`SKILL.md` files, agent definitions, `reference/` notes) plus AsciiDoc docs — no
application code. The full specification (design decisions 1–10, acceptance criteria A–G, and the September 2026
tooling research with versions) lives in the issue body; this plan turns it into ordered, checkable tasks and
pins every naming/contract decision so tasks can be authored in parallel without re-deriving them.

Decisions made on the user's behalf (no ambiguity worth blocking on; challenge them in review if wrong):

- **No language tag on any task.** The installed `*-code-one-task` keys (`java`, `java-springboot`, `dotnet`,
  `database`) don't apply to Markdown/AsciiDoc authoring; `iru-code-one-task-group` will implement every task
  directly (its catch-all Step 3), in parallel inside groups marked parallelizable since each task creates its
  own distinct files.
- **Groups per stack, orchestrators one group later.** Scaffold, gitignore, workflows and gate skills of a
  stack are independent files and are authored in parallel; the stack's `code-one-task-group` skill and
  `-repository` orchestrator come in the following group so they can read the finished descriptions/`args`
  contracts of the skills they call.
- **Verification is part of authoring, not a trailing phase.** Every scaffold/workflows/gate task carries a
  sub-task that exercises its templates against the real tooling in a throwaway directory *outside* the
  repository (`$TMPDIR/iru-verify/<stack>/`), records tool quirks in the `SKILL.md`, and reports what could not
  be verified on this machine. Locally available: Node 24 (`node`/`npm`/`npx`), Maven, JDK, the Android SDK at
  `~/Library/Android/sdk` (Gradle via the wrapper a scaffold generates), Xcode's `swift`/`xcodebuild`. Not
  installed: `ng` (use `npx @angular/cli`), `swiftlint`/`xcodegen`/`tuist` (try `brew install`; if `brew` is
  unavailable or the install fails, mark that check "unverified locally" in the skill and the report instead of
  blocking). Emulator/simulator runs and anything needing GitHub secrets (Sonar, publishing, signing) are never
  executed locally — only the generated YAML is validated (well-formed, actions/versions resolvable).
- **Shared `args` vocabulary** (design decision 4 of the issue), used identically by every orchestrator, scaffold
  and workflows skill so `iru-setup-repository` can pass answers straight through:
  `open-source: yes|no`, `publish: yes|no` (libraries), `distribution: none|internal|store` (apps),
  `sonar: cloud|self-hosted|none` (+ `sonar-organization`, `sonar-project-key`, `sonar-host-url` when set),
  `mode: new|existing`, `flavor: <per skill>`, `integration-branch`, `stable-branch`, `license`,
  `developer-name`, `developer-email`, `organization-url`. Defaults: `sonar` is `cloud` when `open-source: yes`,
  otherwise asked with `none` recommended and the paid-plan caveat stated; `publish`/`distribution` default to
  `yes`/`store` only when `open-source: yes`.
- **Model tiers** (issue decision 9, same as issue #1): `haiku` for setup, gitignore, workflows, orchestrator,
  test, coverage, code-quality and bump-version skills; `sonnet` for `code-one-task`, `code-one-task-group`,
  doc-comment audit, `generate-all-tests`, and the front door (it reasons over `iru-explore` output).
- **Docs**: generated pages (`index.adoc`, `skills/*.adoc`, `agents/*.adoc`, `nav.adoc` entries) come from one
  `/iru-generate-skill-docs` run at the end (Group 9); hand-maintained guides (`extending-the-catalog.adoc`,
  `common-workflows.adoc`, `CLAUDE.md`) are edited directly in Group 8.

## Current code state

- **Skills** live in `.claude/skills/<name>/SKILL.md` (57 today), agents in `.claude/agents/<name>.md` (3).
  Every name carries the `iru-` prefix. Frontmatter: `name`, `description` (one dense paragraph that states the
  invocation form, accepted `args`, idempotency/existing-file behaviour and a "Use whenever…" clause — it is the
  routing contract), `model`, and for implementation skills `allowed-tools` (e.g. `iru-java-code-one-task`:
  `Read Edit Write Bash(mvn *) Bash(git status *) … Skill Agent`). Body: `# Title`, then `## Step N — <verb
  phrase>` sections ending with a `## Step N — Report` that lists what to summarize and a "Warn explicitly"
  block. Bounded choices use `AskUserQuestion` (max four options per question), free text is plain
  conversation. Sub-skills are invoked through `iru-isolated-skill-executor` (`Agent({subagent_type:
  "iru-isolated-skill-executor", prompt: "Invoke Skill({skill: \"<name>\", args: \"key: value\\n…\"})…"})`),
  gates through `iru-gate-runner`, codebase surveys through the built-in `Explore` agent.
- **Java library bootstrap** — `iru-setup-java-library-repository/SKILL.md` (183 lines) collects identity
  (Step 1) and six pipeline parameters (Step 2 table: integration branch `develop`, Java `21`, publishing
  server id `central`, extras profile `build-extras`, sign profile `sign`, settings file `mvnsettings.xml`),
  then runs `iru-setup-java-library` (Step 3) → `iru-setup-antora` (4) → `iru-setup-java-gitignore` (5) →
  `iru-setup-java-github-workflows` (6) → `iru-setup-changelog` (7) → `iru-setup-readme` (8) → report (9).
  `iru-setup-java-library/SKILL.md` (546 lines) parses `args` in Step 0, asks identity in Step 2 (license via
  `AskUserQuestion`, then a Sonar question: SonarCloud / self-hosted / No — lines 86–97), embeds the reference
  `pom.xml` in Step 4 (sonar properties lines 191–195, `central-publishing-maven-plugin` lines 390–395,
  `sonar-maven-plugin` lines 399–403, `sign`/`build-extras` profiles). `iru-setup-java-github-workflows/SKILL.md`
  (646 lines) parses eight `args` keys (Step 1), stops-or-updates on existing files (Step 2), embeds
  `develop.yml`/`main.yml`/`sync.yml` templates (Step 3: `Run SonarCloud analysis` step at ~line 181, `Deploy to
  maven central` at ~218), writes `mvnsettings.xml` (Step 6), lists secrets `SONAR_TOKEN`, `OSSRH_USERNAME`,
  `OSSRH_PASSWORD`, `SIGNING_KEY`, `SIGNING_PASSWORD` (table ~line 619). None of the three asks whether the
  project is open source; Maven Central deploy and `mvnsettings.xml` are unconditional; no Dependabot/CodeQL/
  dependency-review/OSV/gitleaks steps exist.
- **Spring Boot bootstrap** — `iru-setup-java-springboot/SKILL.md` (660 lines) interviews once, writes
  `springboot-stack.yml`, and chains `-pom` → `-modules` → `-apis` → `-testcontainers` → `-platform` →
  `-github-workflows` → `iru-update-java-springboot-documentation`, then gitignore/readme/changelog (Step 9). It
  never asks about open source or Sonar. `iru-setup-java-springboot-pom/SKILL.md` (883 lines) hard-codes
  `sonar.host.url=https://sonarcloud.io` and has "omit if the stack opted out" branches (~lines 448, 529) that
  are unreachable because the manifest has no such field. `iru-setup-java-springboot-github-workflows/SKILL.md`
  (545 lines) writes `build.yml`/`deploy.yml`/`undeploy.yml`, runs `mvn sonar:sonar` (line ~113) and offers to
  add/omit the Sonar step only reactively (line ~40); no frontend/Node steps, no security block.
- **Language-backend registry** — `iru-plan` Step 5 derives keys from `find .claude/skills -maxdepth 1 -type d
  -name "*-code-one-task"`; `iru-code-one-task-group` Step 1 does the same for `*-code-one-task-group` and
  dispatches per bucket (Step 2), implementing untagged tasks itself (Step 3); `iru-code` Step 3/7 looks up
  `iru-<key>-code-quality` by name for baselines. Java backend shape to mirror: `iru-java-code-one-task`
  (`sonnet`, 129 lines, `reference/{README,code-style,class-member-ordering,javadoc,testing}.md` with a
  read-this-much routing table), `iru-java-code-one-task-group` (`sonnet`, 135 lines: baseline via
  `iru-java-code-quality` → parallel one-task runs via `iru-isolated-skill-executor` → one validation pass:
  `check-license`, `java-javadoc`, scoped `java-test`, `java-coverage` ≥ 80 % lines, full suite, quality diff vs
  baseline → finalize checkboxes → report), gate skills `iru-java-test` (67 lines), `iru-java-coverage` (106),
  `iru-java-code-quality` (99), `iru-java-javadoc` (153), `iru-java-generate-all-tests` (152) — all `haiku`
  except javadoc/generate-all-tests (`sonnet`), all report-only through `iru-gate-runner`'s compact contract.
- **Cross-cutting skills to touch** — `iru-explore/SKILL.md` Step 5 (manifest heuristics: `package.json` deps
  `react|vue|angular|next|express|nestjs`; AGP plugin ids; `Package.swift`/`*.xcodeproj`; no RN/Expo/Ionic/
  Capacitor/Hilla/XcodeGen/Tuist signals; no normalized project-type line in the Step 7 `## Tech stack` block).
  `iru-setup-readme/SKILL.md` (179 lines; Step 2 detects `pom.xml`/`build.gradle`/`package.json`; Step 5 links a
  Maven site report; Step 6 install snippets for Maven/Gradle/npm). `iru-pr-review/SKILL.md` Step 5 lists
  Checkstyle/PMD/SpotBugs and ESLint/Prettier as example configs. `iru-release/SKILL.md` (193 lines) reads
  `<version>` under a literal `<artifactId>hermes</artifactId>` (Step 2), requires `-SNAPSHOT`, edits only
  `pom.xml`, assumes `sync.yml`/`sync_versions.py`, uses `gh` only (Step 13). `iru-check-license/SKILL.md`
  illustrates source roots as `src/main`/`src/test` vs `src/`, `lib/`, `test/`. `.claude/agents/iru-gate-runner.md`
  enumerates the Java/.NET gate skill names in its description.
- **Docs** — `docs/modules/ROOT/pages/{index.adoc,skills/*.adoc,agents/*.adoc}` are generated by
  `iru-generate-skill-docs` (sonnet; one sub-agent per skill; also maintains `nav.adoc`); `guides/*.adoc` are
  hand-maintained (`extending-the-catalog.adoc` already documents the "parallel orchestrator" and "front door
  that asks first" shapes and the `iru-<key>-bump-version` idea for `iru-release`). `CLAUDE.md` Architecture
  section lists the pipelines and the three agents.
- **Android reference repositories** (issue "Reference repositories" section) — the templates for every
  `iru-*android*` skill are genericized from https://github.com/albertoirurueta/irurueta-android-glutils
  (`lib/` + Compose `app/`, `gradle/libs.versions.toml`, `gradle.properties` with
  `android.builtInKotlin=false`/`android.newDsl=false`, `val libraryVersion`, JUnit 4 + MockK + Robolectric +
  AndroidX test + Espresso, AGP JaCoCo + vendored `jacoco-0.8.13/lib/jacococli.jar`, inline `sonar {
  properties {…} }` run as `./gradlew :lib:sonar`, `main.yml` with KVM step + `reactivecircus/android-emulator-
  runner@v2` + `EnricoMi/publish-unit-test-result-action@v2` + Dokka to gh-pages, `publish.yml` with
  `publishAndReleaseToMavenCentral --no-configuration-cache` and secrets `MAVEN_CENTRAL_USERNAME`,
  `MAVEN_CENTRAL_PASSWORD`, `SIGNING_MEMORY_KEY`, `SIGNING_MEMORY_KEY_ID`, `SIGNING_IN_MEMORY_KEY_PASSWORD`).
  Decided departures: Antora site + Dokka under `api/`; `develop`/`main` branching with `-SNAPSHOT` on
  `develop` and a `sync.yml`, `main`-only offered as the alternative.

## Conventions every new skill in this plan must follow

Referenced from the tasks below as "(conventions)"; do not repeat them per task.

1. Directory `.claude/skills/<name>/SKILL.md`, `name:` equal to the directory, `iru-` prefix everywhere
   (including every cross-reference in other skills/docs). `description:` names the exact invocation form
   (`/iru-<name>` or `/iru-<name> <args>`), the `args` keys accepted, the existing-file behaviour, and ends with a
   "Use whenever…" sentence. `model:` per the tier decision above.
2. `## Step 0 — Resolve inputs` parses `args` as `key: value` lines (skip any question already answered);
   `## Step 1 — Survey` inspects the repository before writing; a "stop or update" `AskUserQuestion` whenever a
   file the skill owns already exists (preserve steps/entries it doesn't own, show a diff for hand-maintained
   files like `.gitignore`/`README.md`); last step `## Step N — Report` with a "Warn explicitly" block that
   always includes: review generated files before committing; secrets/SonarCloud project/registry accounts must
   exist before CI passes; which values were inferred.
3. Templates are embedded in the `SKILL.md` (genericized: no real repo/org names, `<placeholder>` markers with a
   resolution table), and versions are **looked up at run time** (npm registry, Maven Central search, GitHub
   releases API, Gradle plugin portal) — the issue's September 2026 versions are the fallback when lookup fails.
4. Sonar is generated only when `sonar` ≠ `none`; publishing/store steps only when `publish: yes` /
   `distribution` ≠ `none`; every workflows skill ends with a required-secrets/environments table listing only
   what its generated steps use.
5. Every workflows skill embeds the same **security block**: `.github/dependabot.yml` (stack ecosystem +
   `github-actions`, grouped weekly updates), a `dependency-review` job on `pull_request`
   (`actions/dependency-review-action@v5`), a CodeQL job (`github/codeql-action@v4` with the stack's language, or
   a documented recommendation to enable default setup on public repos), an OSV-Scanner job
   (`google/osv-scanner-action` reusable workflow), and a gitleaks job (`gitleaks/gitleaks-action@v3`); each step
   omittable by the user in Step 1.
6. Gate skills (`test`, `coverage`, `code-quality`, doc audit) are report-only, run through `iru-gate-runner`,
   verify the tool is actually wired before reporting "zero issues", accept a scope argument, and report pass/fail
   names, percentages and rule-id counts — never raw output.
7. Verification sub-task: create `$TMPDIR/iru-verify/<stack>/<skill>/`, run the skill's own template commands
   (scaffold, install, test, lint, coverage, docs) there, delete nothing inside this repository, and fold every
   quirk discovered (wrong default, missing flag, deprecated option) into the `SKILL.md` before finishing.
   Report what was verified and what wasn't.

## Implementation steps

### Group 1 — Open-source / publishing / Sonar awareness in the existing Java skills

Parallelizable: yes — Task 1 edits the library family, Task 2 the Spring Boot family; no shared files.

- [x] Task 1. Add `open-source` / `publish` / `sonar` inputs and the security block to the Java library family
  - [x] Task 1.1. `iru-setup-java-library-repository/SKILL.md`: extend Step 2 with three questions — `open-source`
        (`AskUserQuestion`: yes/no), `publish` (Maven Central; default yes when open source, otherwise asked with
        "no" recommended since Central is for redistributable artifacts), `sonar` (`cloud` recommended when open
        source; when not, the question states SonarCloud is free only for open-source projects and recommends
        `none`, with `self-hosted` as the second option; collect `sonar-organization`/`sonar-project-key`/
        `sonar-host-url` as `iru-setup-java-library` Step 2 does). Accept all of them plus `mode: new|existing`
        via `args` (Step 0 — add one). Pass them through to Steps 3 and 6. In `mode: existing`, skip Step 3 when
        `pom.xml` exists (report instead of asking to regenerate) and tell Steps 4–8 to take their update paths.
        Update the Step 2 table, the description, and Step 9's report (say which of Sonar/Central were wired).
  - [x] Task 1.2. `iru-setup-java-library/SKILL.md`: accept `open-source`, `publish`, `sonar` (+ the three sonar
        values) in Step 0; when `publish: no` drop `central-publishing-maven-plugin` and the `sign` profile
        requirement from the Step 4 template (keep `build-extras`), and when `sonar: none` drop the four `sonar.*`
        properties and `sonar-maven-plugin` (the existing Step 2 Sonar question becomes the fallback when `args`
        didn't resolve it); ask `open-source` first when invoked stand-alone and derive the defaults from it.
        Update the placeholder table (Step 5) and the report.
  - [x] Task 1.3. `iru-setup-java-github-workflows/SKILL.md`: accept the same keys in Step 1; when `publish: no`
        omit the `Deploy to maven central` step, the `server-id`/`server-username`/`server-password`/
        `gpg-*` inputs of `setup-java`, `mvnsettings.xml` (Step 6) and the `OSSRH_*`/`SIGNING_*` rows of the
        secrets table; when `sonar: none` omit the `Run SonarCloud analysis` step and `SONAR_TOKEN`; keep Pages
        publishing regardless. Add the security block (conventions §5) to the templates as a separate
        `security.yml` workflow plus `.github/dependabot.yml` (`maven` + `github-actions`), each step omittable
        in Step 1, and list the new files in Step 2's existence check and Step 8's report.
  - [x] Task 1.4. Consistency pass: the three descriptions mention the new keys; `iru-setup-java-library-repository`'s
        Step 6 `args` block includes them; no template still hard-codes SonarCloud when `sonar: none`.
- [x] Task 2. Add `openSource` / `sonar` to the Spring Boot interview, manifest, pom and workflows
  - [x] Task 2.1. `iru-setup-java-springboot/SKILL.md`: add an "open source?" question and a `sonar`
        (`cloud`/`self-hosted`/`none`, same wording as Task 1.1) question to the interview, record them as
        `openSource:` and `sonar: {mode, organization, projectKey, hostUrl}` in `springboot-stack.yml`, accept them
        via `args` (with `mode: new|existing`), and add a `frontend: none|hilla` interview item whose `hilla`
        branch is implemented by Task 19 (write the manifest field now; Task 19 wires the sub-skill call).
  - [x] Task 2.2. `iru-setup-java-springboot-pom/SKILL.md`: make the existing "if the stack opted out of Sonar"
        branches real — read `sonar.mode` from the manifest; `none` omits the `sonar.*` properties and
        `sonar-maven-plugin`; `self-hosted` writes the given host URL instead of `https://sonarcloud.io`.
  - [x] Task 2.3. `iru-setup-java-springboot-github-workflows/SKILL.md`: read `sonar.mode` and omit the
        `Run SonarCloud analysis` step and `SONAR_TOKEN` when `none`; add the security block (conventions §5) as
        `security.yml` + `dependabot.yml` (`maven`, `docker`, `github-actions`, and `npm` when a frontend exists),
        omittable per step; update the secrets table and the report.
  - [x] Task 2.4. Consistency pass across the seven Spring Boot skills: every place that assumes SonarCloud is
        present (e.g. README badges via `iru-setup-readme`, `iru-update-java-springboot-documentation` mentions)
        reads the manifest field instead.

### Group 2 — TypeScript stack: scaffold, gitignore, workflows and gate skills

Parallelizable: yes — every task creates its own new skill directory; the `args`/name contracts below are fixed
so no task needs another's output. Framework detection rule shared by Tasks 12–17 (write it into each skill):
inspect `package.json` — `@vaadin/hilla`/`hilla-spring-boot-starter` in `pom.xml` or a `src/main/frontend/`
dir → `hilla-frontend`; `expo` or `react-native` → `react-native`; `@ionic/angular` or `@ionic/react` +
`@capacitor/core` → `ionic`; `@angular/core` → `angular`; `react` + `vite` → `react`; otherwise `library`.
Test runner rule: `vitest` in devDependencies → Vitest; `jest`/`jest-expo` → Jest; `@angular/build` with the
`unit-test` builder → `ng test` (Vitest runner). Package manager from `packageManager`/lockfile
(`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn).

- [x] Task 3. Create `iru-setup-typescript-library` (`haiku`) — `.claude/skills/iru-setup-typescript-library/SKILL.md` (569 lines); verified locally in `$TMPDIR/iru-verify/typescript/library`: `npm install`, build (tsup), `vitest run`, coverage (`coverage/lcov.info` present), `eslint .` (header rule proven to fire), `tsc --noEmit`, typedoc, `prettier --check` all green; quirks folded (TypeScript `latest` 7.x vs typescript-eslint/typedoc peer ranges → resolve from peers, fallback 6.0.3; `ignoreDeprecations` for `baseUrl`; `.prettierignore`; ESLint 10 `ignores`); nothing unverified; quality/coverage gates not applicable (Markdown).
  - [x] Task 3.1. `SKILL.md` per conventions: `/iru-setup-typescript-library`; `args`: `package-name`, `scope`,
        `description`, `license`, `developer-*`, `open-source`, `publish`, `sonar` (+ values), `mode`. Steps:
        resolve inputs → survey (existing `package.json`? stop-or-update) → ask identity → write `package.json`
        (`"type": "module"`, `exports` map with `types`/`import`, `files`, `sideEffects: false`, `engines.node
        >= 22`, `publishConfig: {access: public, provenance: true}` only when `publish: yes`, scripts: `build`
        (`tsup src/index.ts --format esm --dts`), `test` (`vitest run`), `coverage` (`vitest run --coverage`),
        `lint` (`eslint .`), `format` (`prettier --check .`), `typecheck` (`tsc --noEmit`), `docs` (`typedoc`)),
        `tsconfig.json` (strict, `moduleResolution: bundler`, `declaration`), `vitest.config.ts` (coverage provider
        `v8`, reporters `text` + `lcov` → `coverage/lcov.info`, threshold 80 % lines), `eslint.config.js` (ESLint
        10 flat: `@eslint/js` recommended + `typescript-eslint` recommended + `eslint-config-prettier` + a
        license-header rule via `@tony.ganchev/eslint-plugin-header` when a license was chosen), `.prettierrc`,
        `typedoc.json` (`out: docs/api`, `treatWarningsAsErrors`), `sonar-project.properties` when `sonar` ≠ none
        (`sonar.organization`, `sonar.projectKey`, `sonar.sources=src`, `sonar.tests=test`,
        `sonar.javascript.lcov.reportPaths=coverage/lcov.info`, `sonar.exclusions=**/dist/**`), `src/index.ts` +
        `test/index.test.ts` skeleton, optional `.changeset/config.json` when `publish: yes`; `npm install` with
        versions looked up from the registry → report.
  - [x] Task 3.2. Verification (conventions §7): scaffold in `$TMPDIR/iru-verify/typescript/library`, run
        `npm install`, `npm run build`, `npm test`, `npm run coverage` (confirm `coverage/lcov.info` exists),
        `npm run lint`, `npm run typecheck`, `npm run docs`; fold quirks into the skill.
- [x] Task 4. Create `iru-setup-react-web` (`haiku`) — `.claude/skills/iru-setup-react-web/SKILL.md` (637 lines); verified locally in `$TMPDIR/iru-verify/typescript/react`: `npm create vite@latest` (non-interactive, ships Oxlint today), install, `vitest run` + coverage (lcov), ESLint flat, Prettier, Stylelint 17 (needs one `--fix` pass), `tsc -b` (root tsconfig is references-only), build, `npm init playwright@latest -- --quiet --lang ts --no-browsers`, `npx playwright install --with-deps chromium` + `npm run e2e` (1 passed), Storybook init; unverified locally: Linux `--with-deps` sudo path, full pipeline re-run after Storybook; quality/coverage not applicable (Markdown).
  - [x] Task 4.1. `SKILL.md`: `/iru-setup-react-web`; same shared `args` (no `publish`; `distribution` n/a);
        scaffold with `npm create vite@latest <name> -- --template react-ts` (run inside the repository root when
        empty, otherwise ask), then add Vitest + `@vitest/coverage-v8` + `@testing-library/react` + `jsdom`
        (`vitest.config.ts` with `environment: jsdom`, lcov), ESLint flat config replacing the template's Oxlint
        script (or keeping Oxlint alongside — ask once), `eslint-plugin-react-hooks`, Prettier, Stylelint 17 for
        CSS, Playwright (`npm init playwright@latest -- --quiet --lang ts`, `e2e/` dir, one smoke test),
        optional Storybook (`npm create storybook@latest`, asked), `sonar-project.properties` when enabled
        (`sonar.sources=src`, `sonar.tests=src`, `sonar.test.inclusions=**/*.test.tsx,**/*.test.ts`,
        `sonar.exclusions=**/e2e/**,**/dist/**`), scripts `test`/`coverage`/`lint`/`format`/`typecheck`/`e2e`.
  - [x] Task 4.2. Verification: scaffold in `$TMPDIR/iru-verify/typescript/react`, run install/build/test/
        coverage/lint/typecheck and `npx playwright install --with-deps chromium` + `npm run e2e` (skip e2e with a
        note if browser download fails offline).
- [x] Task 5. Create `iru-setup-angular-web` (`haiku`) — `.claude/skills/iru-setup-angular-web/SKILL.md` (472 lines); verified locally in `$TMPDIR/iru-verify/typescript/angular` (Angular CLI 22.1.8): `ng new … --defaults --ssr=false`, `ng test --coverage` → real path `coverage/<project>/lcov.info` (requires `@vitest/coverage-v8` major-matched to the bundled vitest), `ng lint`, `ng build`, `npm run docs` (Compodoc → `docs/api`), `ng add angular-eslint`/`playwright-ng-schematics`, `ng e2e`; unverified locally: optional Storybook init; quality/coverage not applicable (Markdown).
  - [x] Task 5.1. `SKILL.md`: `/iru-setup-angular-web`; scaffold with `npx -p @angular/cli@latest ng new <name>
        --standalone --style=scss --routing --skip-git --package-manager=npm`; confirm `angular.json`'s
        `test` target uses the `@angular/build:unit-test` builder with `runner: vitest` and add
        `coverageReporters: ["text","lcov"]` + `coverageThresholds` (80 % lines); `ng add angular-eslint` (pin the
        major to Angular's), Prettier, Stylelint (SCSS), Playwright via `ng add playwright-ng-schematics`,
        Compodoc (`@compodoc/compodoc`, script `docs` → `docs/api`), optional Storybook (`@storybook/angular-vite`),
        `sonar-project.properties` (`sonar.sources=src`, `sonar.tests=src`, `sonar.test.inclusions=**/*.spec.ts`,
        `sonar.javascript.lcov.reportPaths=coverage/<project>/lcov.info`).
  - [x] Task 5.2. Verification in `$TMPDIR/iru-verify/typescript/angular`: `ng new`, `ng test --coverage`
        (confirm lcov path), `ng lint`, `ng build`, `npm run docs`; record the real coverage output path.
- [x] Task 6. Create `iru-setup-react-native-app` (`haiku`) — `.claude/skills/iru-setup-react-native-app/SKILL.md` (579 lines); verified locally in `$TMPDIR/iru-verify/typescript/react-native`: `create-expo-app --template blank-typescript --no-install --no-agents-md`, jest-expo + RNTL 14 `npm test -- --coverage` (lcov.info; `render()` is async), `npx expo lint` (pre-install eslint + eslint-config-expo), `tsc --noEmit` (needs `types: [jest]`), `npx expo export --platform web` (needs react-dom/react-native-web/@expo/metro-runtime); unverified locally: `eas.json`/EAS builds, Maestro flow, native toolchains; quality/coverage not applicable (Markdown).
  - [x] Task 6.1. `SKILL.md`: `/iru-setup-react-native-app`; `args` add `native-builds: eas|local`,
        `distribution`; scaffold with `npx create-expo-app@latest <name> --template blank-typescript`; add
        `jest-expo` preset + `@testing-library/react-native` (`jest.config.js` with `collectCoverage`,
        `coverageReporters: ["text","lcov"]`), `eslint-config-expo` flat config + Prettier (`npx expo lint`),
        `eas.json` with `development`/`preview`/`production` profiles, a Maestro flow skeleton
        (`.maestro/smoke.yaml`), `sonar-project.properties` excluding `android/**`, `ios/**`, `node_modules/**`,
        `coverage/**`; state the EAS free tier (15 builds/platform/month) vs `eas build --local` /
        `npx expo prebuild` on runners when asking `native-builds`; note Cordova-free, New Architecture only.
  - [x] Task 6.2. Verification in `$TMPDIR/iru-verify/typescript/react-native`: scaffold, `npm test -- --coverage`,
        `npx expo lint`, `npx expo export --platform web` (build sanity without native toolchains).
- [x] Task 7. Create `iru-setup-ionic-app` (`haiku`) — `.claude/skills/iru-setup-ionic-app/SKILL.md` (498 lines); verified locally in `$TMPDIR/iru-verify/typescript/ionic-{angular,react}` (Ionic CLI 7.2.1, Ionic 9.0.4, Capacitor 8.5.2): `ionic start … --no-interactive --confirm`, unit tests + coverage (`coverage/app/lcov.info` Angular, `coverage/lcov.info` React), lint (React starter ships one pre-existing ESLint failure), `npm run build`, `npx cap sync android` (needs JDK 17/21 `JAVA_HOME`), `npx cap add ios` (SPM, no CocoaPods), Playwright web smoke; unverified locally: Maestro flow; quality/coverage not applicable (Markdown).
  - [x] Task 7.1. `SKILL.md`: `/iru-setup-ionic-app`; `args` add `framework: angular|react`, `distribution`;
        scaffold with `npx @ionic/cli start <name> blank --type=angular-standalone|react --no-git --no-deps`
        (then `npm install`), `npm i @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios`,
        `npx cap init`, `npx cap add android`, `npx cap add ios` (each add asked; ios only on macOS), Vitest
        (Angular runner or Vite) with lcov, ESLint + Prettier, Playwright (web build), Maestro skeleton,
        `sonar-project.properties` excluding `android/**`/`ios/**`; state Ionic 9 + Capacitor 8 baseline, no
        Cordova/Appflow, Capgo/Capawesome for OTA.
  - [x] Task 7.2. Verification in `$TMPDIR/iru-verify/typescript/ionic-{angular,react}`: scaffold both flavors,
        run unit tests with coverage, lint, `npm run build`, `npx cap sync android` (Android SDK present).
- [x] Task 8. Create `iru-setup-typescript-gitignore` (`haiku`) — `.claude/skills/iru-setup-typescript-gitignore/SKILL.md` (229 lines); composed template checked with `git check-ignore -v` in a scratch repo under `$TMPDIR/iru-verify/typescript/gitignore` (all entries incl. `.env.example`/`.vscode` negations behave as intended); Hilla block verified against Vaadin's published gitignore template; quality/coverage not applicable (Markdown).
  - [x] Task 8.1. `SKILL.md` mirroring `iru-setup-java-gitignore`'s contract (create if missing, else diff +
        approval): base entries `node_modules/`, `dist/`, `build/`, `out/`, `coverage/`, `*.tsbuildinfo`,
        `.eslintcache`, `.env*` (except `.env.example`), `npm-debug.log*`, `.DS_Store`, `.idea/`, `.vscode/`
        (partial), plus detected additions: `.angular/` (Angular), `.vite/`/`storybook-static/` (React), `.expo/`,
        `web-build/`, `*.jks`, `*.p8`/`*.p12`/`*.mobileprovision`, `android/app/build/`, `ios/Pods/`,
        `ios/build/` (RN/Ionic), `docs/build/` (Antora), `docs/api/` when TypeDoc/Compodoc output is generated,
        `src/main/frontend/generated/` + `node_modules/` at the Maven root (Hilla).
- [x] Task 9. Create `iru-setup-typescript-github-workflows` (`haiku`) — `.claude/skills/iru-setup-typescript-github-workflows/SKILL.md` (1390 lines); verified locally in `$TMPDIR/iru-verify/typescript/workflows`: all flavor variants of build/release/sync/security/dependabot parse as YAML, every `uses:` major confirmed via `gh api` (`download-artifact` corrected to v8; codeql/sonar resolved via tags), `build.yml` shell steps run green against the Task 3 and Task 4 scaffolds, `sync_versions.py` bump proven on scratch files; unverified locally: Sonar scan, npm trusted publishing, EAS, Android/iOS signing + store uploads, Firebase, Pages deploy, Playwright in CI; quality/coverage not applicable (Markdown).
  - [x] Task 9.1. `SKILL.md`: `/iru-setup-typescript-github-workflows`; `args`: `flavor:
        library|react|angular|react-native|ionic`, `integration-branch` (default `develop`), `stable-branch`
        (`main`), `node-version` (`24`), `package-manager`, `open-source`, `publish`/`distribution`, `sonar`
        (+ values), `native-builds` (RN), `framework` (Ionic), `docs-tool: typedoc|compodoc|storybook|none`.
        Templates: **`build.yml`** (push to integration + stable branches, `pull_request`, `workflow_dispatch`;
        `actions/checkout@v7` `fetch-depth: 0`, `actions/setup-node@v7` with `cache`, install (`npm ci`), lint,
        format check, typecheck, unit tests with coverage, `SonarSource/sonarqube-scan-action@v8` when enabled
        (skipped on fork PRs), Playwright e2e (web flavors, artifact on failure), docs build (TypeDoc/Compodoc/
        Storybook into `docs/api` or `storybook-static`) + Antora build, merge under `docs/build/site/api/`,
        `actions/upload-pages-artifact` + `actions/deploy-pages` from the stable branch only); **`release.yml`**
        per flavor — library: on `release: [published]`, `permissions: id-token: write, contents: read`,
        `setup-node` with `registry-url: https://registry.npmjs.org`, `npm ci && npm run build && npm publish`
        (trusted publishing, provenance automatic; note npm ≥ 11.5.1 and the trusted-publisher configuration on
        npmjs.com naming this workflow file), plus an optional `changesets/action@v2` version-PR job on push to
        the stable branch; react/angular: build artifact upload and Pages deploy of `dist/`; react-native: either
        `expo/expo-github-action@9` + `eas build --platform all --non-interactive --profile production` and
        `eas submit` (needs `EXPO_TOKEN`) or local jobs (`ubuntu-latest` Gradle `bundleRelease` after `npx expo
        prebuild`, `macos-latest` `xcodebuild archive`), per `native-builds`; ionic: `npm run build && npx cap
        sync`, Android job (`./gradlew bundleRelease` in `android/`, keystore secret), iOS job on `macos-latest`
        (`xcodebuild -workspace ios/App/App.xcworkspace -scheme App archive`/`-exportArchive` with App Store
        Connect API key secrets, or fastlane when present), uploads per `distribution`; **`sync.yml`** +
        `.github/scripts/sync_versions.py` for library/web flavors (merge stable back into integration and bump
        `package.json` version to the next prerelease `x.y.z-dev.0`, README and Antora docs — same shape as the
        Java skill's), and the security block (`npm` ecosystem, CodeQL `javascript-typescript` with `build-mode:
        none`). Secrets table: `SONAR_TOKEN`, `EXPO_TOKEN`, `ANDROID_KEYSTORE_BASE64`/`ANDROID_KEYSTORE_PASSWORD`/
        `ANDROID_KEY_ALIAS`/`ANDROID_KEY_PASSWORD`, `APP_STORE_CONNECT_API_KEY_ID`/`_ISSUER_ID`/`_KEY_BASE64`,
        `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`, `FIREBASE_*` — each listed only when used.
  - [x] Task 9.2. Verification: generate the five flavor variants into `$TMPDIR/iru-verify/typescript/workflows/`
        and validate YAML (`python3 -c 'import yaml…'` or `npx yaml-lint`), confirm every `uses:` action/major
        exists via `gh api repos/<owner>/<action>/releases/latest`, and run `build.yml`'s shell steps by hand
        against the Task 3 and Task 4 scaffolds.
- [x] Task 10. Create `iru-typescript-test` (`haiku`) — `.claude/skills/iru-typescript-test/SKILL.md` (150 lines); verified locally in `$TMPDIR/iru-verify/typescript/test`: JSON reporter flags/shapes for Vitest (`--reporter=json --outputFile`), Jest (`--json --outputFile`), `ng test --reporters=json --output-file`; exit codes (all three exit 1 on an unmatched file selector — plain Jest too, unless `passWithNoTests`; an unmatched `-t` name filter exits 0 with everything skipped); unverified locally: pnpm/yarn invocation forms; quality/coverage not applicable (Markdown).
  - [x] Task 10.1. `SKILL.md`: `/iru-typescript-test [selector]`; detect runner/package manager (rule above);
        run `vitest run [pattern]` / `jest [pattern]` / `ng test --watch=false --include=<glob>`; note that an
        unmatched Vitest filter exits non-zero ("No test files found") while Jest passes with zero tests — call
        both out; parse the runner's JSON reporter (`--reporter=json`, `--json`) for pass/fail names; report
        counts + failing test names + first assertion message only.
- [x] Task 11. Create `iru-typescript-coverage` (`haiku`) — `.claude/skills/iru-typescript-coverage/SKILL.md` (217 lines); verified locally in `$TMPDIR/iru-verify/typescript/coverage`: Vitest/Jest coverage flags, `coverage-summary.json` + `lcov.info` shapes, `--coverage.include`/`collectCoverageFrom` necessity, tested `awk` totals/per-file/uncovered-range snippets, Angular nested `coverage/<project>/` path and the version-matched `@vitest/coverage-v8` requirement; unverified locally: Karma layout, pnpm/yarn, framework-preset quirks; quality/coverage not applicable (Markdown).
  - [x] Task 11.1. `SKILL.md`: `/iru-typescript-coverage [scope]`; run the runner with coverage (`vitest run
        --coverage --coverage.reporter=lcov --coverage.reporter=json-summary`, `jest --coverage
        --coverageReporters=lcov --coverageReporters=json-summary`, `ng test --coverage`); parse
        `coverage/coverage-summary.json` (or `lcov.info` via `LF`/`LH` records with `awk`) for line/branch %,
        per-file percentages for the scope, and uncovered line ranges (`DA:<line>,0`); report only those.
- [x] Task 12. Create `iru-typescript-code-quality` (`haiku`) — `.claude/skills/iru-typescript-code-quality/SKILL.md` (172 lines); verified locally in `$TMPDIR/iru-verify/typescript/code-quality`: ESLint 10 `--format json` shape/exit codes, `tsc --pretty false` output, solution-style tsconfig silently reporting zero (use `tsc -b`), Prettier `--check` on stderr (prefer `--list-different`), Stylelint JSON on stderr (`-o`), Oxlint JSON object shape; unverified locally: `ng lint --format json` wrapping; quality/coverage not applicable (Markdown).
  - [x] Task 12.1. `SKILL.md`: `/iru-typescript-code-quality [scope]`; Step 1 verifies `eslint.config.*` (or
        `angular.json` lint target), `tsconfig.json`, `.prettierrc`/`prettier` key, `stylelint` config exist
        before trusting a zero; run `eslint --format json [scope]`, `tsc --noEmit -p tsconfig.json` (filter to
        scope), `prettier --check [scope]`, `stylelint "**/*.{css,scss}"` when configured; classify by rule id
        (`@typescript-eslint/*`, `react-hooks/*`, `@angular-eslint/*`, `TS<n>`, formatting); report counts per
        rule id and the new-vs-baseline diff when a baseline is given in the prompt.
- [x] Task 13. Create `iru-typescript-tsdoc` (`sonnet`) — `.claude/skills/iru-typescript-tsdoc/SKILL.md` (240 lines); verified locally in `$TMPDIR/iru-verify/typescript/tsdoc`: `typedoc --emit none --treatWarningsAsErrors` needs `--validation.notDocumented true` to flag undocumented exports, entry-point discovery from `exports`, `requiredToBeDocumented`, TypeDoc 0.28.20 crash on TS 6.0.3 (pin 5.9.x), Compodoc `--silent --coverageTest`/`--coverageMinimumPerFile` exit codes; nothing unverified; quality/coverage not applicable (Markdown).
  - [x] Task 13.1. `SKILL.md`: `/iru-typescript-tsdoc [scope]`; discover the documentation bar (`typedoc.json`
        `treatWarningsAsErrors`/`requiredToBeDocumented`, `eslint-plugin-jsdoc`/`eslint-plugin-tsdoc` rules,
        observed practice — stricter wins); audit exported functions/classes/interfaces/types/enums for TSDoc
        (`/** … */` with `@param`/`@returns`/`@throws` where applicable, `@example` on public entry points);
        verify with `typedoc --emit none --treatWarningsAsErrors` (library/react) or `compodoc -p tsconfig.json
        --silent --coverageTest 80` (angular); report undocumented symbols and the doc-build result only.
- [x] Task 14. Create `iru-typescript-generate-all-tests` (`sonnet`) — `.claude/skills/iru-typescript-generate-all-tests/SKILL.md` (200 lines), mirrors `iru-java-generate-all-tests` step for step (coverage via `iru-gate-runner` → `iru-typescript-coverage`, 80 % lines); no verification sub-task applies; quality/coverage not applicable (Markdown).
  - [x] Task 14.1. `SKILL.md` mirroring `iru-java-generate-all-tests`: enumerate source files lacking a
        sibling/mirrored test, generate Vitest/Jest tests with the framework's testing library (RTL, RNTL,
        Angular TestBed), run `iru-typescript-coverage` via `iru-gate-runner` until 80 % lines, same interruption
        rules.
- [x] Task 15. Create `iru-typescript-code-one-task` (`sonnet`) — `.claude/skills/iru-typescript-code-one-task/SKILL.md` (161 lines) + `reference/{README,code-style,tsdoc,testing,react,angular,react-native,ionic,hilla-frontend}.md`; no verification sub-task applies; quality/coverage not applicable (Markdown).
  - [x] Task 15.1. `SKILL.md` mirroring `iru-java-code-one-task` (implement one task + its tests, never run
        tests, flip its checkbox with "group validation pending", report files touched); `allowed-tools`: `Read
        Edit Write Bash(npm *) Bash(npx *) Bash(pnpm *) Bash(yarn *) Bash(git status *) Bash(git diff *)
        Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *)`; Step 1 runs the framework-detection rule and reads
        only the matching reference files.
  - [x] Task 15.2. `reference/README.md` routing table + `reference/code-style.md` (strict TS, `readonly`,
        discriminated unions, no `any`, named exports, ESM, error handling, async), `reference/tsdoc.md`,
        `reference/testing.md` (Vitest/Jest conventions, RTL query priority, `userEvent`, no snapshot-only tests,
        mocking with `vi.mock`/`jest.mock`), `reference/react.md` (function components, hooks rules, state
        colocation, Suspense/error boundaries, file layout `src/features/<name>/`), `reference/angular.md`
        (standalone components, signals, `inject()`, OnPush, `provideHttpClient`, TestBed + `HttpTestingController`),
        `reference/react-native.md` (Expo Router, platform files, RNTL, no direct native modules without config
        plugins), `reference/ionic.md` (Ionic components, Capacitor plugin usage, platform checks),
        `reference/hilla-frontend.md` (`src/main/frontend/views/*.tsx` file routing, generated endpoint clients
        under `generated/` are read-only, `@vaadin/react-components`, Vitest browser-mode config from Vaadin docs).
- [x] Task 16. Create `iru-typescript-bump-version` (`haiku`) — `.claude/skills/iru-typescript-bump-version/SKILL.md` (157 lines); verified locally in `$TMPDIR/iru-verify/typescript/bump-version`: `npm version <v> --no-git-tag-version` updates package.json + lockfile and validates semver, `npm version prerelease --preid=dev` yields `x.y.(z+1)-dev.0`, `npm pkg set` needs `npm install --package-lock-only`, pnpm 12 `version --no-git-tag-version` supported; unverified locally: Yarn Classic/Berry; quality/coverage not applicable (Markdown).
  - [x] Task 16.1. `SKILL.md`: `/iru-typescript-bump-version <new-version>` — updates `package.json` `version`
        and the lockfile (`npm version <v> --no-git-tag-version` / `pnpm version` / `yarn version`), reports the
        old/new value; defines the ecosystem's "pre-release" convention for `iru-release` (Task 50): current
        `x.y.z-dev.N` → release `x.y.z` → next `x.y.(z+1)-dev.0`.
- [x] Task 17. Create `iru-typescript-code-one-task-group` (`sonnet`) — `.claude/skills/iru-typescript-code-one-task-group/SKILL.md` (157 lines), mirrors `iru-java-code-one-task-group` step for step with gate invocations matched to the finished `iru-typescript-test`/`-coverage`/`-code-quality`/`-tsdoc`/`-code-one-task` contracts; no verification sub-task applies; quality/coverage not applicable (Markdown).
  - [x] Task 17.1. `SKILL.md` mirroring `iru-java-code-one-task-group` exactly (baseline via
        `iru-typescript-code-quality` → parallel `iru-typescript-code-one-task` runs through
        `iru-isolated-skill-executor` when `Parallelizable: yes` → one validation pass: `check-license` scoped,
        `iru-typescript-tsdoc`, scoped `iru-typescript-test`, `iru-typescript-coverage` ≥ 80 % lines, full suite
        (`npm test`), quality diff vs baseline → finalize checkboxes → report); `allowed-tools` as Task 15 plus
        `Skill Agent`. (Placed in this group because its contract only depends on names fixed by this plan; it
        must still read Tasks 10–13's finished descriptions before writing its gate invocations.)

### Group 3 — TypeScript orchestrator and the Hilla frontend

Parallelizable: yes — Task 18 creates a new skill; Task 19 creates one skill and edits three Spring Boot skills
that no other task in this group touches.

- [x] Task 18. Create `iru-setup-typescript-repository` (`haiku`) — `.claude/skills/iru-setup-typescript-repository/SKILL.md` (351 lines, `haiku`), mirrors `iru-setup-java-library-repository` step for step: two-round `AskUserQuestion` flavor pick, identity collected once, flavor→scaffold map (`library`→`iru-setup-typescript-library`, `react`→`iru-setup-react-web`, `angular`→`iru-setup-angular-web`, `react-native`→`iru-setup-react-native-app`, `ionic`→`iru-setup-ionic-app`), `docs-tool` derived from flavor/Storybook answer, only args each sub-skill actually accepts are passed; no tests/coverage/quality gates apply (Markdown); license headers not applicable.
  - [x] Task 18.1. `SKILL.md` mirroring `iru-setup-java-library-repository`: `/iru-setup-typescript-repository`;
        `args`: `flavor: library|react|angular|react-native|ionic` (asked via `AskUserQuestion` when absent —
        five options, so two rounds), the shared inputs, `mode`; collects identity once, then runs via
        `iru-isolated-skill-executor`: the flavor's scaffold skill (Tasks 3–7) → `iru-setup-antora` →
        `iru-setup-typescript-gitignore` → `iru-setup-typescript-github-workflows` (passing `flavor` and every
        shared input) → `iru-setup-changelog` → `iru-setup-readme`; in `mode: existing` skip the scaffold when
        `package.json` exists and run the rest in update mode; report per sub-skill + the consolidated secrets
        table.
- [x] Task 19. Create `iru-setup-java-springboot-hilla` and wire it into the Spring Boot family — new `.claude/skills/iru-setup-java-springboot-hilla/SKILL.md` (468 lines, `haiku`) plus edits to `iru-setup-java-springboot`, `-github-workflows`, `-pom` (Group 1's `sonar.mode`/`frontend` edits kept); web module = `boot`; 19.5 verified locally in `$TMPDIR/iru-verify/hilla/verify/` with Spring Boot 4.1.1 + Vaadin/Hilla 25.2.8 under Maven 3.9.16 on JDK 21 and JDK 26 (`mvn package -DskipTests`, `mvn -Pproduction package -DskipTests`, `vaadin:prepare-frontend`/`build-frontend`, `-Dvaadin.skip=true`, `npm ci`, `npx vitest run --coverage` → `<module>/coverage/lcov.info`, eslint, prettier); a real GitHub Actions run of the generated `build.yml` is marked unverified locally. Quirks folded in: both `hilla-` and `vaadin-spring-boot-starter` are required, `routes.tsx`/`file-routes.ts` are generated (never hand-written), `package.json`/`vite.config.ts`/`tsconfig.json`/`types.d.ts` live at the module root, `vaadin:prepare-frontend` must precede `vitest`, Vite root is `src/main/frontend`, helper is `overrideVaadinConfig`. No tests/coverage/quality gates apply (Markdown).
  - [x] Task 19.1. `iru-setup-java-springboot-hilla/SKILL.md` (`haiku`): `/iru-setup-java-springboot-hilla`,
        `args: stack-file`, standalone or invoked by `iru-setup-java-springboot` when `frontend: hilla`; adds the
        Vaadin BOM (`com.vaadin:vaadin-bom`, version looked up) and `com.vaadin:hilla-spring-boot-starter` (+
        `vaadin-spring-boot-starter` only if Flow views are wanted — ask) to the API/web module's pom, the
        `vaadin-maven-plugin` with `prepare-frontend`/`build-frontend` goals and a `production` profile,
        `src/main/frontend/` with `views/@index.tsx`, `views/@layout.tsx`, `routes.tsx` (file-based routing),
        `vitest.config.ts` extending Vaadin's Vite config with `@vitest/coverage-v8` lcov, `package.json` scripts
        (`test`, `coverage`, `lint`, `format`), ESLint flat + typescript-eslint + react-hooks + Prettier,
        `.gitignore` entries (`src/main/frontend/generated/`, `node_modules/`, `frontend/index.html` generated),
        `sonar.*` additions to the root pom when `sonar` ≠ none (`sonar.sources=src/main/java,src/main/frontend`,
        `sonar.tests=src/test/java,src/main/frontend`, `sonar.test.inclusions=**/*.test.ts,**/*.test.tsx`,
        `sonar.javascript.lcov.reportPaths=<module>/coverage/lcov.info`, `sonar.exclusions=**/frontend/generated/**`);
        verifies with `mvn -q -pl <module> vaadin:prepare-frontend` and `npx vitest run` through `iru-gate-runner`.
  - [x] Task 19.2. `iru-setup-java-springboot/SKILL.md`: the `frontend: hilla` manifest field (Task 2.1) now
        invokes `iru-setup-java-springboot-hilla` right after `-apis` in the chain; description updated.
  - [x] Task 19.3. `iru-setup-java-springboot-github-workflows/SKILL.md`: when the manifest has `frontend: hilla`,
        add `actions/setup-node@v7` (cache npm on `src/main/frontend/package-lock.json`) before Maven, a
        `npx vitest run --coverage` step in the module dir, `-Pproduction -Dvaadin.ci.build=true` on the package
        step, and the `npm` Dependabot ecosystem.
  - [x] Task 19.4. `iru-setup-java-springboot-pom/SKILL.md`: version management for `vaadin-bom`/
        `vaadin-maven-plugin`, the `production` profile, and a `vaadin.skip`-style property, only when
        `frontend: hilla`.
  - [x] Task 19.5. Verification in `$TMPDIR/iru-verify/hilla/`: generate a Spring Boot 4 + Hilla project from
        start.vaadin.com's Maven archetype or Initializr per the skill's Step 1, run `mvn -q package -Pproduction
        -DskipTests` and `npx vitest run --coverage` in the frontend; record generated-folder names and the real
        lcov path in the skill.

### Group 4 — Android stack: scaffold, gitignore, workflows and gate skills

Parallelizable: yes — independent new skill directories. Every template is genericized from the reference
repositories in "Current code state"; the skill text must say so and link them.

- [x] Task 20. Create `iru-setup-android-library` (`haiku`)
  - [x] Task 20.1. `SKILL.md`: `/iru-setup-android-library`; `args`: `group-id`, `artifact-id`, `namespace`,
        `description`, `min-sdk` (26), `compile-sdk` (current), `license`, `developer-*`, `open-source`,
        `publish`, `sonar` (+ values), `built-in-kotlin: no|yes`, `junit: 4|5`, `coverage-tool: jacoco|kover`,
        `static-analysis: lint|lint+detekt+ktlint`, `mode`. Embedded, genericized templates: Gradle wrapper
        (`gradle-wrapper.properties` with the current version + `distributionSha256Sum`), root `build.gradle.kts`,
        `settings.gradle.kts` (pluginManagement content filters, `FAIL_ON_PROJECT_REPOS`, `google()` +
        `mavenCentral()`), `gradle.properties` (reference set incl. `android.builtInKotlin=false`/`android.newDsl=
        false` unless opted in, configuration cache, Dokka V2), `gradle/libs.versions.toml` (aliases exactly as
        the reference: `android-application`, `android-library`, `kotlin-android`, `kotlin-compose`, `dokka`,
        `sonarqube`, `publish`; libraries `junit`, `androidx-junit`, `androidx-espresso-core`,
        `androidx-compose-bom`, `androidx-material3`, `androidx-test-core-ktx`, `androidx-test-ext-junit-ktx`,
        `material`, `mockk-android`, `robolectric`, `kotlin-reflect`, `irurueta-test-utils`; versions looked up),
        `lib/build.gradle.kts` (the reference file with `<placeholders>`: `libraryVersion = "1.0.0-SNAPSHOT"`,
        `namespace`, `enableUnitTestCoverage`/`enableAndroidTestCoverage`, `packaging` excludes, `kotlin {
        compilerOptions { jvmTarget } }`, the inline `sonar { properties {…} }` block — omitted when `sonar:
        none`, host URL replaced when self-hosted — and the `mavenPublishing { configure(AndroidSingleVariantLibrary
        ("release", sourcesJar = true, publishJavadocJar = true)); publishToMavenCentral(); signAllPublications();
        coordinates(…); pom {…} }` block — omitted when `publish: no`), `lib/proguard-rules.pro`,
        `lib/src/main/AndroidManifest.xml`, `lib/src/androidTest/AndroidManifest.xml`,
        `lib/src/test/resources/<package>/robolectric.properties`, `lib/.gitignore` (`/build`), one placeholder
        source + unit test + instrumented test, and the `app/` Compose sample (`app/build.gradle.kts` from the
        reference with `applicationId`, `versionCode`/`versionName` mirrored from `libraryVersion`, build-config
        fields `BUILD_NUMBER`/`BUILD_TIMESTAMP`/`GIT_COMMIT`/`GIT_BRANCH`, `implementation(project(":lib"))`).
        Opt-ins add Detekt (`detekt.yml`, SARIF), Spotless (`ktlint` + `licenseHeader`), Kover
        (`koverXmlReportDebug`), `de.mannodermaus.android-junit`. Verifies with `./gradlew --offline help` then
        `./gradlew :lib:assembleDebug` via `iru-gate-runner` (warn that first run downloads the SDK components).
  - [x] Task 20.2. Verification in `$TMPDIR/iru-verify/android/library`: generate, run `./gradlew :lib:testDebugUnitTest
        :lib:lint :lib:dokkaGenerate` with `ANDROID_HOME=~/Library/Android/sdk`, confirm
        `lib/build/reports/coverage/…` and `lint-results-debug.xml` paths, and whether AGP's
        `createDebugUnitTestCoverageReport` emits `report.xml` (if not, keep the vendored `jacoco-<ver>/lib/
        jacococli.jar` step exactly as the reference and document why).
- [x] Task 21. Create `iru-setup-android-app` (`haiku`) — SKILL.md created (1335 lines); verified in $TMPDIR/iru-verify/android/app: assembleDebug/testDebugUnitTest/lint pass, assembleRelease unsigned-path confirmed, createDebugUnitTestCoverageReport emits report.xml (no vendored jacococli.jar needed for app module); found+fixed missing activity-compose/ui-tooling-preview deps, dropped dead manifest package attr, Gradle bumped to 9.7.1; JDK 21 required (26 unsupported); distribution/Firebase/GPP plugins config-checked only (no credentials).
  - [x] Task 21.1. `SKILL.md`: `/iru-setup-android-app`; same toolchain templates with a single `app/`
        `com.android.application` module (Compose by default, Views on request), `versionCode`/`versionName`,
        `signingConfigs.release` reading `SIGNING_STORE_FILE`/`SIGNING_STORE_PASSWORD`/`SIGNING_KEY_ALIAS`/
        `SIGNING_KEY_PASSWORD` from env (unsigned when absent), `bundleRelease`/`assembleRelease`, optional
        `com.google.firebase.appdistribution` plugin (`distribution: internal`) or Gradle Play Publisher
        (`distribution: store`, alternative to the workflow-level upload action — ask), inline `sonar` block,
        no publishing block, `google-services.json` gitignored.
  - [x] Task 21.2. Verification in `$TMPDIR/iru-verify/android/app`: `./gradlew :app:assembleDebug
        :app:testDebugUnitTest :app:lint`.
- [x] Task 22. Create `iru-setup-android-gitignore` (`haiku`) — SKILL.md created (196 lines); genericized from irurueta-android-glutils root/lib/app .gitignore; verified in $TMPDIR/iru-verify/android/gitignore/ with git init + git check-ignore -v: lib/build/x, docs/build/site/index.html, local.properties, app/release.jks, google-services.json, .idea/x all ignored; jacoco-0.8.13/lib/jacococli.jar confirmed NOT ignored (no *.jar pattern in template).
  - [x] Task 22.1. `SKILL.md` with the reference `.gitignore` content (root) + per-module `/build`, same
        diff-and-approve contract as `iru-setup-java-gitignore`, plus Antora `docs/build/` and `jacoco-*/` vendored
        CLI **not** ignored (it is committed in the reference).
- [x] Task 23. Create `iru-setup-android-github-workflows` (`haiku`) — SKILL.md created (1371 lines); templates genericized from irurueta-android-glutils `main.yml`/`publish.yml` (fetched via `gh api`), mirroring the Java/TypeScript workflows siblings (security block, secrets table, stop-or-update preserving foreign jobs); coverage step picks AGP's `createDebugUnitTestCoverageReport` → `lib/build/reports/coverage/test/debug/report.xml` per Task 20.2, vendored-jacococli conversion kept as templated fallback (exercised with org.jacoco.cli-0.8.13-nodeps.jar against the scaffold's real .exec); verified in $TMPDIR/iru-verify/android/workflows/: 4 flavor×branching renders (18 files) YAML-valid, all 17 distinct `uses:` refs resolve via `git ls-remote --tags` (`actions/setup-python` bumped to `@v7`; `actions/dependency-review-action`/`google/osv-scanner-action` have no floating major → pinned `@v5.0.0`/`@v2.6.0`), `sync_versions.py` py_compile-clean and exercised against copied scaffold build files + README/antora.yml, develop.yml Gradle steps run by hand against the Task 20 scaffold (JDK 21) confirming every test-result/SARIF/coverage/Dokka/.exec path; bug fixed during verification: coverage task must target only the flavor's module (`:app:createDebugUnitTestCoverageReport` doesn't exist in the sample app). Emulator run, Sonar, Maven Central publish, Play/Firebase upload, CodeQL, OWASP/mobsfscan opt-ins unverified locally. Quality/coverage gates n/a (Markdown); license headers n/a.
  - [x] Task 23.1. `SKILL.md`: `/iru-setup-android-github-workflows`; `args`: `flavor: library|app`,
        `branching: gitflow|main-only` (default `gitflow`), `integration-branch` (`develop`), `stable-branch`
        (`main`), `java-version` (`17`), `run-instrumented-tests: yes|no`, `api-level` (35), shared inputs.
        Templates for `gitflow`: **`develop.yml`** (push to integration branch + `workflow_dispatch`;
        `permissions: checks: write, pull-requests: write, contents: write`; `actions/checkout@v7` `fetch-depth: 0`;
        "Enable KVM" udev step (only with instrumented tests); `actions/setup-java@v6` Temurin `<java-version>`;
        `gradle/actions/setup-gradle@v6` with `dependency-graph: generate-and-submit`; either
        `reactivecircus/android-emulator-runner@v2` (`api-level`, `google_apis`, `x86_64`, script `./gradlew clean
        test connectedAndroidTest lint lib:dokkaGenerate`) or plain `./gradlew clean test lint lib:dokkaGenerate`;
        `EnricoMi/publish-unit-test-result-action@v2` on `lib/**` and `app/**` result globs; "Convert unit tests
        coverage results" (AGP task first, vendored `jacococli.jar` fallback — both templated, one chosen at
        generation per Task 20.2's finding); `github/codeql-action/upload-sarif` for `lint-results-*.sarif`;
        `./gradlew :lib:sonar` with `SONAR_TOKEN`/`GITHUB_TOKEN` when enabled; Antora install/build, copy
        `lib/build/dokka/html` to `docs/build/site/api/`, `actions/upload-pages-artifact` + `deploy-pages`;
        optional snapshot publish `./gradlew lib:publishToMavenCentral --no-configuration-cache` when `publish:
        yes`); **`main.yml`** (on `release: [released]`: same pipeline + `:lib:assembleRelease` +
        `lib:publishAndReleaseToMavenCentral --no-configuration-cache` with env `ORG_GRADLE_PROJECT_mavenCentralUsername:
        ${{ secrets.MAVEN_CENTRAL_USERNAME }}` etc. — the five reference secret names — when `publish: yes`; for
        `flavor: app` instead decode `ANDROID_KEYSTORE_BASE64` to `app/release.jks`, export the signing env vars,
        `./gradlew :app:bundleRelease`, then `r0adkll/upload-google-play@v1` (`distribution: store`) or
        `wzieba/Firebase-Distribution-Github-Action@v1` (`internal`)); **`sync.yml`** + `.github/scripts/
        sync_versions.py` (merge the released stable branch back into the integration branch and bump
        `libraryVersion` in `lib/build.gradle.kts`, `versionName`/`versionCode` in `app/build.gradle.kts`,
        `README.md` and Antora docs to the next `-SNAPSHOT`); for `main-only`: the reference `main.yml`
        (push/PR to main) + `publish.yml`. Security block: `dependabot.yml` (`gradle` + `github-actions`),
        `security.yml` with CodeQL `java-kotlin` `build-mode: autobuild`, dependency-review, OSV-Scanner,
        gitleaks; OWASP dependency-check (`NVD_API_KEY`) and `MobSF/mobsfscan` (apps) as opt-ins. Stop-or-update
        preserving foreign steps; secrets table.
  - [x] Task 23.2. Verification: render both branching variants for both flavors into
        `$TMPDIR/iru-verify/android/workflows/`, YAML-validate, check every `uses:` resolves, and run the
        `develop.yml` Gradle/coverage-conversion shell steps by hand against the Task 20 scaffold.
- [x] Task 24. Create `iru-android-test` (`haiku`) — SKILL.md created (183 lines); JUnit XML parsing verified against hand-written fixtures in $TMPDIR/iru-verify/android/gates/junit/ (mixed pass/failure/error/skipped); live ./gradlew run unverified locally by this skill's author, exercised by Task 20.2/23.2.
  - [x] Task 24.1. `SKILL.md`: `/iru-android-test [selector]`; runs `./gradlew :<module>:testDebugUnitTest
        --tests '<pattern>'` (module from the selector's path, default `lib`); notes that an unmatched `--tests`
        filter fails the build; `connectedAndroidTest` only when the prompt asks for it and `adb devices` shows a
        device; parses `build/test-results/testDebugUnitTest/*.xml` for pass/fail names and first failure message.
- [x] Task 25. Create `iru-android-coverage` (`haiku`) — SKILL.md created (196 lines); JaCoCo XML parsing verified against hand-written fixture in $TMPDIR/iru-verify/android/gates/jacoco/report.xml (class + sourcefile counters, uncovered lines, scoped filter); Kover/AGP-task/vendored-CLI priority order and AGP report.xml existence unverified locally, exercised by Task 20.2.
  - [x] Task 25.1. `SKILL.md`: `/iru-android-coverage [scope]`; runs the unit-test coverage task
        (`createDebugUnitTestCoverageReport`, or `koverXmlReportDebug` when Kover is applied, or the vendored
        JaCoCo CLI conversion when present in the repo — detect which), parses the JaCoCo XML (`<counter
        type="LINE" missed covered>` at report/package/class level with `python3`/`awk`), reports line/branch %
        and uncovered lines for the scope only.
- [x] Task 26. Create `iru-android-code-quality` (`haiku`) — SKILL.md created (203 lines); Lint + Detekt XML parsing verified against hand-written fixtures in $TMPDIR/iru-verify/android/gates/{lint,detekt}/; live Gradle runs and whether Detekt/Spotless/ktlint are wired in the Task 20 scaffold unverified locally, exercised by Task 20.2/23.2.
  - [x] Task 26.1. `SKILL.md`: `/iru-android-code-quality [scope]`; verifies which tools are wired (Android Lint
        always; Detekt/ktlint/Spotless when plugins present); runs `./gradlew :lib:lintDebug` (+ `detekt`,
        `spotlessCheck`), parses `lint-results-debug.xml` `<issue id= severity=>` (and Detekt XML/SARIF),
        classifies by issue id/severity, reports counts and the new-vs-baseline diff.
- [x] Task 27. Create `iru-android-dokka` (`sonnet`) — SKILL.md created (190 lines); mirrors iru-java-javadoc's audit-then-generate shape for KDoc/Dokka V2 (dokkaGenerate/dokkaGeneratePublicationHtml, module.md/package.md via includes.from), grounded in the reference repo's actual libs.versions.toml (dokka=2.1.0) and gradle.properties (V2Enabled); no detekt.yml exists in the reference repo so the bar-discovery step documents the observed-practice fallback explicitly; Gradle not run by this agent, marked unverified locally, deferred to Task 20.2.
  - [x] Task 27.1. `SKILL.md` mirroring `iru-java-javadoc` for KDoc: bar from `detekt.yml`
        `UndocumentedPublicClass/Function` or observed practice; audit public/internal API (classes, functions,
        properties, constructors, enum entries), `@param`/`@return`/`@throws`/`@sample`; `module.md`/
        `package.md` Dokka includes; verify with `./gradlew :lib:dokkaGenerate` and report warnings.
- [x] Task 28. Create `iru-android-generate-all-tests` (`sonnet`) — SKILL.md created (183 lines); mirrors iru-java-generate-all-tests' coverage-loop shape with JUnit 4 + MockK + Robolectric conventions read from the reference repo's actual test sources (mockk<T>(relaxed=true), @MockK/MockKRule, unmockkAll in @After, irurueta.android.testutils private-member helpers, @RunWith(RobolectricTestRunner::class) only for Android-framework-touching classes, SDK-branch *QTest convention); delegates to iru-android-coverage/iru-android-test (both now present) via iru-gate-runner, 80% bar, capped at two extension attempts; Gradle not run by this agent, marked unverified locally, deferred to Task 20.2.
  - [x] Task 28.1. `SKILL.md` mirroring `iru-java-generate-all-tests` with JUnit 4 + MockK + Robolectric
        conventions from the reference repos (`@RunWith(RobolectricTestRunner::class)` for Android-framework
        code, `@Config(sdk=…)`, `mockk<T>(relaxed=…)`, `irurueta-android-test-utils` helpers), coverage loop to
        80 % via `iru-android-coverage`.
- [x] Task 29. Create `iru-android-code-one-task` (`sonnet`) — SKILL.md (186 lines, sonnet, allowed-tools Read Edit Write Bash(./gradlew *) Bash(gradle *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *)) mirrors iru-java-code-one-task's 8-step shape (module detect -> reference routing -> re-check state -> implement -> tests -> compile-check -> interrupt policy -> checkbox -> report), adding a Step 5 Gradle compile-check (:module:compileDebugKotlin :module:compileDebugUnitTestKotlin) not present in the Java sibling. reference/ (888 lines: README 66, code-style 200, kdoc 81, testing 160, compose 132, views 119, library-api 130) genericized from https://github.com/albertoirurueta/irurueta-android-glutils (GLTextureView, OrientationHelper, GLTextureViewTest, lib/build.gradle.kts, lib/proguard-rules.pro read directly); no real repo/org/person names used except the real com.irurueta:irurueta-android-test-utils dependency. Not run against Gradle per instructions (other agents running heavy builds) - compile verification marked unverified locally; exercised by Task 20.2's scaffold build.
  - [x] Task 29.1. `SKILL.md` mirroring `iru-java-code-one-task` with `allowed-tools`: `Read Edit Write
        Bash(./gradlew *) Bash(gradle *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(find *)
        Bash(grep *) Bash(ls *)`.
  - [x] Task 29.2. `reference/README.md` + `code-style.md` (Kotlin official style, `val` over `var`, data/
        sealed classes, null-safety, coroutines/Flow, visibility `internal` by default in libs, no `!!`),
        `kdoc.md`, `testing.md` (JUnit 4, MockK, Robolectric, Espresso/Compose test rules, `irurueta-android-
        test-utils`), `compose.md` (stateless composables, state hoisting, previews, `Modifier` first
        param), `views.md` (ViewBinding, custom views), `library-api.md` (binary compatibility, `@JvmStatic`,
        ProGuard consumer rules, no leaking of transitive deps via `api`).
- [x] Task 30. Create `iru-android-bump-version` (`haiku`) — SKILL.md created (~230 lines); rewrites lib/build.gradle.kts val libraryVersion and app/build.gradle.kts versionName/versionCode via python3 re.subn (macOS/Linux-safe); versionCode increments only for non-SNAPSHOT release; verified in $TMPDIR/iru-verify/android/bump-version/ against copied reference lib/app build.gradle.kts + README.md: 1.1.11->1.2.0-SNAPSHOT (versionCode unchanged), 1.2.0-SNAPSHOT->1.2.0 (versionCode 10->11); caught and fixed a README regex bug (missing \s* before optional paren) during verification. ./gradlew -q help not run (Gradle runs deferred to another agent per instructions) - marked unverified locally.
  - [x] Task 30.1. `SKILL.md`: `/iru-android-bump-version <new-version>` — rewrites `val libraryVersion =
        "…"` in `lib/build.gradle.kts`, `versionName` (and increments `versionCode`) in `app/build.gradle.kts`,
        verifies with `./gradlew -q help`; pre-release convention `x.y.z-SNAPSHOT` → `x.y.z` → `x.y.(z+1)-SNAPSHOT`.
- [x] Task 31. Create `iru-android-code-one-task-group` (`sonnet`) — SKILL.md created (173 lines); mirrors iru-java-code-one-task-group/iru-typescript-code-one-task-group step-for-step (per-module baseline via iru-android-code-quality → parallel iru-android-code-one-task runs via iru-isolated-skill-executor → one validation pass: check-license, iru-android-dokka, scoped iru-android-test per touched module, iru-android-coverage ≥ 80 % lines on testDebugUnitTest only with instrumented coverage informational, full `./gradlew test`, quality diff → checkbox backfill → report); gate invocations written against the finished descriptions/args of iru-android-test/-coverage/-code-quality/-dokka/-code-one-task; allowed-tools = Task 29's list + `Skill Agent`; verified name matches directory and every referenced skill/agent exists on disk. Gradle commands not run by this task (no verification sub-task; noted in the SKILL.md as unverified locally, exercised by Task 20.2/23.2). Quality/coverage gates n/a (Markdown); license headers n/a.
  - [x] Task 31.1. `SKILL.md` mirroring `iru-java-code-one-task-group` with gates `check-license`,
        `iru-android-dokka`, scoped `iru-android-test`, `iru-android-coverage` ≥ 80 % lines (unit tests only;
        instrumented coverage reported for information when available), full `./gradlew test`, quality diff via
        `iru-android-code-quality`; `allowed-tools` as Task 29 plus `Skill Agent`.

### Group 5 — Android orchestrator

Parallelizable: yes — single task.

- [x] Task 32. Create `iru-setup-android-repository` (`haiku`) — SKILL.md created (440 lines, haiku); mirrors iru-setup-java-library-repository/iru-setup-typescript-repository step-for-step (Step 0 args → flavor/branching/mode → identity once → pipeline-parameter table develop/main/17/26/35/yes + open-source/publish|distribution/sonar → iru-setup-android-library|app → iru-setup-antora → iru-setup-android-gitignore → iru-setup-android-github-workflows → iru-setup-changelog → iru-setup-readme via iru-isolated-skill-executor → report with verbatim consolidated secrets table); every sub-skill invocation written against the finished Step 0 key lists on disk (only accepted keys passed; scaffold toggles, security-* and compile-sdk deliberately left to the sub-skills); mode: existing skips the scaffold when settings.gradle.kts exists. Quality/coverage gates n/a (Markdown); license headers n/a; no throwaway verification required for an orchestrator.
  - [x] Task 32.1. `SKILL.md` mirroring `iru-setup-java-library-repository`: `/iru-setup-android-repository`;
        `args: flavor: library|app`, `branching`, shared inputs, `mode`; collects identity + pipeline parameters
        once (table: integration branch `develop`, stable `main`, Java `17`, min SDK `26`, API level `35`,
        instrumented tests `yes`), then runs `iru-setup-android-library|app` → `iru-setup-antora` →
        `iru-setup-android-gitignore` → `iru-setup-android-github-workflows` → `iru-setup-changelog` →
        `iru-setup-readme` through `iru-isolated-skill-executor`; `mode: existing` skips the scaffold when
        `settings.gradle.kts` exists; report + consolidated secrets table.

### Group 6 — Swift stack: scaffold, gitignore, workflows and gate skills

Parallelizable: yes — independent new skill directories. Local verification uses Xcode's `swift`/`xcodebuild`;
`swiftlint`/`xcodegen`/`tuist` via `brew install` when possible, else marked unverified.

- [x] Task 33. Create `iru-setup-swift-library` (`haiku`)
  - [x] Task 33.1. `SKILL.md`: `/iru-setup-swift-library`; `args`: `package-name`, `platforms` (list from
        `ios|ipados|macos|watchos|tvos|visionos|linux`), `min-deployment-targets`, `license`, `developer-*`,
        shared inputs, `formatter: swift-format|swiftformat`, `mode`. Steps: `swift package init --type library
        --name <name>` (then rewrite `Package.swift`: `// swift-tools-version: 6.0`, `platforms:`, `swiftLanguageModes:
        [.v6]`, `Sources/<Name>/`, `Tests/<Name>Tests/` with a Swift Testing `@Test` and an XCTest example),
        `.swiftlint.yml` (opt-in strict rules, `excluded: .build`), `.swift-format` (or `.swiftformat`),
        `swift-docc-plugin` dependency + `Sources/<Name>/<Name>.docc/<Name>.md`, `.spi.yml`
        (`builder.configs: [{documentation_targets: [<Name>]}]`) when `publish: yes`, `sonar-project.properties`
        when `sonar` ≠ none (`sonar.sources=Sources`, `sonar.tests=Tests`, `sonar.swift.file.suffixes=.swift`,
        `sonar.coverageReportPaths=sonarqube-generic-coverage.xml`, `sonar.swiftlint.reportPaths=swiftlint.json`),
        `Package.resolved` policy note, `.github/CODEOWNERS` no; verify via `iru-gate-runner` with `swift build`
        and `swift test`.
  - [x] Task 33.2. Verification in `$TMPDIR/iru-verify/swift/library`: `swift build`, `swift test
        --enable-code-coverage`, `xcrun llvm-cov export -format=lcov` on the test binary, `swift format lint
        --strict --recursive Sources`, `swift package --allow-writing-to-directory docs generate-documentation
        --target <Name> --transform-for-static-hosting`; SwiftLint if installable.
- [x] Task 34. Create `iru-setup-apple-app` (`haiku`)
  - [x] Task 34.1. `SKILL.md`: `/iru-setup-apple-app`; `args`: `app-name`, `bundle-id-prefix`, `platforms`
        (multi-select `ios|ipados|macos|watchos`; iPadOS = iOS target with `TARGETED_DEVICE_FAMILY = 1,2`),
        `generator: xcodegen|tuist` (asked; recommendation stated: XcodeGen for a single-target app, Tuist for
        modular apps), `distribution`, `signing: fastlane-match|api-key|none`, shared inputs, `mode`. Writes the
        generator manifest (`project.yml` or `Project.swift` + `Tuist.swift`) declaring one app target per
        platform (SwiftUI `App` entry, `Info.plist` keys, `MARKETING_VERSION`/`CURRENT_PROJECT_VERSION`, Swift 6,
        `SWIFT_STRICT_CONCURRENCY = complete`), a shared `Packages/Core` local SwiftPM package for testable
        logic, unit-test targets (Swift Testing) and a UI-test target (XCUITest) per platform, watchOS companion
        wiring when both iOS and watchOS are chosen, `.swiftlint.yml`, `.swift-format`, `fastlane/Fastfile` with
        `match`/`build_app`/`upload_to_testflight`/`notarize` lanes per `signing`/`distribution`, `.xcodeproj`
        gitignored and regenerated by `xcodegen generate`/`tuist generate`; `sonar-project.properties` as Task 33.
  - [x] Task 34.2. Verification in `$TMPDIR/iru-verify/swift/app`: generate with XcodeGen (brew) and build/test
        with `xcodebuild -scheme <App> -destination 'platform=iOS Simulator,name=<first available>' test
        -enableCodeCoverage YES -resultBundlePath TestResults.xcresult` (list simulators with `xcrun simctl list
        devices available`), and macOS `-destination 'platform=macOS'`; Tuist path verified only if installable.
- [x] Task 35. Create `iru-setup-swift-gitignore` (`haiku`)
  - [x] Task 35.1. `SKILL.md`: `.build/`, `DerivedData/`, `*.xcodeproj/` and `*.xcworkspace/` (only when a
        generator manifest exists — keep them otherwise), `*.xcresult`, `xcuserdata/`, `*.xcuserstate`,
        `.swiftpm/xcode/`, `Package.resolved` (asked: commit for apps, ignore for libraries), `fastlane/report.xml`,
        `fastlane/screenshots/`, `fastlane/test_output/`, `*.p8`, `*.p12`, `*.mobileprovision`, `*.cer`,
        `.DS_Store`, `docs/build/`, `docs/api/` (DocC output); same diff-and-approve contract.
- [x] Task 36. Create `iru-setup-swift-github-workflows` (`haiku`)
  - [x] Task 36.1. `SKILL.md`: `/iru-setup-swift-github-workflows`; `args`: `flavor: library|app`, `platforms`,
        `runner: macos-26|xcode-27`, `xcode-version`, `integration-branch`, `stable-branch`, `signing`, shared
        inputs. Templates: **`build.yml`** on `runs-on: <runner>` (`maxim-lobanov/setup-xcode@v1` with
        `xcode-version`, `swiftlint --strict --reporter json > swiftlint.json` (via `brew install swiftlint` or
        the preinstalled binary), `swift format lint --strict --recursive Sources Tests`; library: `swift build`,
        `swift test --enable-code-coverage --parallel`, `xcrun llvm-cov export -format=lcov … > coverage.lcov` and
        `slather coverage --sonarqube-xml` (or SonarSource's `xccov-to-sonarqube-generic.sh` fallback) into
        `sonarqube-generic-coverage.xml`, plus an `ubuntu-latest` matrix leg for pure packages; app: `xcodegen
        generate`/`tuist generate`, one `xcodebuild test` per selected platform destination with
        `-enableCodeCoverage YES -resultBundlePath`, piped through `xcbeautify`, `.xcresult` uploaded with
        `actions/upload-artifact@v7` `if: always()`; `SonarSource/sonarqube-scan-action@v8` when enabled; DocC
        (`swift package generate-documentation --transform-for-static-hosting --hosting-base-path <repo>` into
        `docs/build/site/api/`) + Antora, Pages deploy from the stable branch); **`release.yml`** — library: on
        `release: [published]` verify the tag matches semver and that `swift package dump-package` succeeds, plus
        an optional `googleapis/release-please-action@v5` (`release-type: simple`) job on the stable branch; app:
        `xcodebuild archive` + `-exportArchive -exportOptionsPlist` using either fastlane `match` (`MATCH_GIT_URL`,
        `MATCH_PASSWORD`) or `-allowProvisioningUpdates -authenticationKeyPath` with `APP_STORE_CONNECT_API_KEY_ID`/
        `_ISSUER_ID`/`_KEY_BASE64`, TestFlight upload (`fastlane pilot` or `apple-actions/upload-testflight-build`),
        `xcrun notarytool submit --wait` + `stapler staple` for macOS, watchOS archived with the iOS scheme;
        **`sync.yml`** for gitflow (bump `MARKETING_VERSION` in the generator manifest / `version.txt` for
        libraries). Security block: `dependabot.yml` (`swift` + `github-actions`), CodeQL `swift` on macOS,
        dependency-review, OSV-Scanner, gitleaks. Notes: macOS minutes cost ~10× Linux; CocoaPods not generated.
  - [x] Task 36.2. Verification: render library/app variants, YAML-validate, check `uses:` resolve, run the
        library `build.yml` shell steps locally against Task 33's scaffold (coverage export + slather if
        installable via `gem install slather`).
- [x] Task 37. Create `iru-swift-test` (`haiku`)
  - [x] Task 37.1. `SKILL.md`: `/iru-swift-test [selector]`; packages: `swift test --filter '<regex>'` (works for
        both XCTest and Swift Testing; note unmatched filter runs zero tests and passes); apps: `xcodebuild test
        -scheme … -destination … -only-testing:<Target>/<Suite>/<test>` with `-resultBundlePath`, parse via
        `xcrun xcresulttool get test-results summary --path` (Xcode 16+) or `--format json`; report pass/fail
        names and first failure message.
- [x] Task 38. Create `iru-swift-coverage` (`haiku`)
  - [x] Task 38.1. `SKILL.md`: `/iru-swift-coverage [scope]`; packages: `swift test --enable-code-coverage` then
        `xcrun llvm-cov report <test-binary> -instr-profile .build/debug/codecov/default.profdata
        [files]` (binary path via `swift build --show-bin-path`); apps: `xcrun xccov view --report --json
        <bundle>.xcresult`; report line/function % per file in scope and uncovered line ranges (`llvm-cov export
        -format=lcov` + `DA:` parsing); branch coverage noted as unavailable from xccov.
- [x] Task 39. Create `iru-swift-code-quality` (`haiku`)
  - [x] Task 39.1. `SKILL.md`: `/iru-swift-code-quality [scope]`; verifies `.swiftlint.yml`/`.swift-format`
        exist; runs `swiftlint lint --reporter json [paths]` and `swift format lint --strict --recursive [paths]`
        (Periphery `periphery scan --format json` when a `.periphery.yml` exists); classifies by rule id and
        severity; reports counts + baseline diff; installs nothing without asking.
- [x] Task 40. Create `iru-swift-docc` (`sonnet`)
  - [x] Task 40.1. `SKILL.md` mirroring `iru-java-javadoc`: bar from `.swiftlint.yml`
        (`missing_docs` rule), `.spi.yml` documentation targets, observed practice; audit public API (`///`
        summaries, `- Parameters:`, `- Returns:`, `- Throws:`, `- Note:`), DocC catalog articles for entry points;
        verify with `swift package generate-documentation --warnings-as-errors` (or `xcodebuild docbuild` for
        apps); report undocumented symbols + doc-build result.
- [x] Task 41. Create `iru-swift-generate-all-tests` (`sonnet`)
  - [x] Task 41.1. `SKILL.md` mirroring `iru-java-generate-all-tests` with Swift Testing (`@Suite`, `@Test`,
        `#expect`, `#require`, parameterized tests) as default and XCTest for UI/performance; coverage loop via
        `iru-swift-coverage`.
- [x] Task 42. Create `iru-swift-code-one-task` (`sonnet`)
  - [x] Task 42.1. `SKILL.md` mirroring `iru-java-code-one-task`; `allowed-tools`: `Read Edit Write
        Bash(swift *) Bash(xcodebuild *) Bash(xcrun *) Bash(xcodegen *) Bash(tuist *) Bash(git status *)
        Bash(git diff *) Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *)`; detects package vs app (and
        generator) in Step 1.
  - [x] Task 42.2. `reference/README.md` + `code-style.md` (Swift 6 strict concurrency: `Sendable`, actors,
        `@MainActor` for UI, structured concurrency; value types first; `guard` early exits; access control
        `public` only for API; error types), `docc.md`, `testing.md` (Swift Testing conventions, XCTest for
        XCUITest/`measure`), `swiftui.md` (view composition, `@Observable`, environment, navigation, previews,
        platform conditionals `#if os(watchOS)`), `package-api.md` (semver-stable API, `@available`, availability
        per platform, `Package.swift` products/targets hygiene), `app-structure.md` (per-platform targets,
        shared `Core` package, watch companion, `Info.plist` keys via the generator manifest).
- [x] Task 43. Create `iru-swift-bump-version` (`haiku`)
  - [x] Task 43.1. `SKILL.md`: `/iru-swift-bump-version <new-version>` — libraries: no in-tree version (SwiftPM
        uses the git tag) so it updates `version.txt`/`CHANGELOG.md`/README snippets only and reports that the
        tag is the release; apps: `MARKETING_VERSION` (and `CURRENT_PROJECT_VERSION` increment) in `project.yml`/
        `Project.swift`/`*.xcconfig`; pre-release convention: none in-tree (tags only) — `iru-release` treats the
        release version as the next semver from the last tag.
- [x] Task 44. Create `iru-swift-code-one-task-group` (`sonnet`)
  - [x] Task 44.1. `SKILL.md` mirroring `iru-java-code-one-task-group` with gates `check-license`,
        `iru-swift-docc`, scoped `iru-swift-test`, `iru-swift-coverage` ≥ 80 % lines, full `swift test`/
        `xcodebuild test`, quality diff via `iru-swift-code-quality`; a repository-wide lock (`mkdir
        .simulator-test.lock`, same shape as the Spring Boot integration-test lock) serializes simulator runs when
        parallel tasks both need `xcodebuild test`.

### Group 7 — Swift orchestrator

Parallelizable: yes — single task.

- [x] Task 45. Create `iru-setup-swift-repository` (`haiku`)
  - [x] Task 45.1. `SKILL.md` mirroring `iru-setup-java-library-repository`: `/iru-setup-swift-repository`;
        `args: flavor: library|app`, `platforms`, `generator`, `signing`, shared inputs, `mode`; runs
        `iru-setup-swift-library|iru-setup-apple-app` → `iru-setup-antora` → `iru-setup-swift-gitignore` →
        `iru-setup-swift-github-workflows` → `iru-setup-changelog` → `iru-setup-readme`; `mode: existing` skips the
        scaffold when `Package.swift` or a generator manifest exists; report + secrets table.

### Group 8 — Front door and cross-cutting updates to existing skills, agents and hand-maintained docs

Parallelizable: yes — every task edits a distinct set of files (listed per task); Task 46 only references the
orchestrators created in Groups 3, 5 and 7 plus the existing Java ones.

- [x] Task 46. Create `iru-setup-repository` (`sonnet`)
  - [x] Task 46.1. `SKILL.md`: `/iru-setup-repository`; Step 1 detects a non-empty repository (`git ls-files |
        head`, or any manifest present) and, if so, runs `Skill({skill: "iru-explore"})` with no ticket and reads
        its `Project type:` line (Task 47) to pre-select the recommended option and set `mode: existing`; Step 2
        asks the project type — 12 options over three `AskUserQuestion` rounds ("Backend/JVM": Java library,
        Spring Boot service, Spring Boot + Vaadin + Hilla, Android library; "Mobile/native": Android app, Swift
        library, Apple app (iOS/iPadOS/macOS/watchOS), React Native app; "Web/Node": TypeScript/npm library, React
        web app, Angular web app, Ionic app — each round's last option is "Something in the next group"); Step 3
        asks the three shared inputs once (`open-source`, then `publish` or `distribution` depending on
        library/app, then `sonar` with the wording from Task 1.1) plus Apple platforms / Ionic framework / RN
        native-builds when relevant; Step 4 delegates through `iru-isolated-skill-executor` with `args` to
        `iru-setup-java-library-repository`, `iru-setup-java-springboot` (`frontend: hilla` when chosen),
        `iru-setup-typescript-repository` (`flavor`), `iru-setup-android-repository` (`flavor`),
        `iru-setup-swift-repository` (`flavor`); Step 5 reports what each delegated skill created/updated/skipped
        and one consolidated secrets/environments table. Description states it is the one entry point new users
        should use.
- [x] Task 47. Update `iru-explore` detection and report (`iru-explore/SKILL.md` only)
  - [x] Task 47.1. Step 5 manifests: add Vite (`vite` + `react`), Angular CLI (`@angular/cli`/`angular.json`),
        Hilla (`hilla-spring-boot-starter`/`@vaadin/hilla`, `src/main/frontend/`), Expo/React Native (`expo`,
        `react-native`, `app.json`/`app.config.*`, `metro.config.js`, `eas.json`), Ionic/Capacitor (`@ionic/*`,
        `@capacitor/core`, `capacitor.config.*`, `ionic.config.json`), Android (`com.android.library` vs
        `com.android.application`, `gradle/libs.versions.toml`, Compose BOM), SwiftPM/Xcode/XcodeGen/Tuist
        (`Package.swift` products, `project.yml`, `Project.swift`, `*.xcodeproj`, target platforms from
        `platforms:`/`SUPPORTED_PLATFORMS`/`TARGETED_DEVICE_FAMILY`).
  - [x] Task 47.2. Step 7 `## Tech stack` block gains `- Project type: <one of: java-library, java-springboot,
        java-springboot-hilla, typescript-library, react-web, angular-web, android-library, android-app,
        swift-library, apple-app (ios, ipados, macos, watchos), react-native-app, ionic-app (angular|react),
        dotnet, other, unknown>` — the same vocabulary `iru-setup-repository` uses — with "multiple" listing one per
        module.
- [x] Task 48. Update `iru-setup-readme` (`iru-setup-readme/SKILL.md` only)
  - [x] Task 48.1. Step 2 detection for the new manifests/project types (reuse Task 47's list); Step 4 status
        table rows for platform/min SDK/deployment targets; Step 5 links to TypeDoc/Compodoc/Storybook/Dokka/
        DocC output under the Pages `api/` path when the workflows publish it; Step 6 install snippets for npm
        (`npm install <name>`), Gradle Kotlin DSL (`implementation("<group>:<artifact>:<version>")` +
        version-catalog form), SwiftPM (`.package(url: "…", from: "<version>")` + Xcode "Add Package"), and app
        store/TestFlight/Play links when `distribution: store`; badges: npm version/downloads, Maven Central
        (`maven-badges`), Swift Package Index (platforms + Swift versions), plus the full SonarCloud set the
        reference Android READMEs use — only when the feature is wired.
- [x] Task 49. Update `iru-pr-review`, `iru-check-license`, `iru-gate-runner`, and the three registry skills'
      descriptions
  - [x] Task 49.1. `iru-pr-review/SKILL.md` Step 5 example configs: add ESLint/Prettier/Biome, `tsconfig.json`,
        Detekt/ktlint/Android Lint, SwiftLint/swift-format.
  - [x] Task 49.2. `iru-check-license/SKILL.md`: source-root hints `app/src/main`, `lib/src/main`, `Sources/`,
        `Tests/`, `src/main/frontend`, `ios/`, `android/`; comment syntax examples for `.kt`, `.swift`, `.ts`/
        `.tsx`; inception-year sources `package.json`/`lib/build.gradle.kts` `inceptionYear`/git first commit.
  - [x] Task 49.3. `.claude/agents/iru-gate-runner.md` description: list the new gate skills
        (`iru-typescript-*`, `iru-android-*`, `iru-swift-*`) and report shapes (lcov %, JaCoCo XML %, llvm-cov %).
  - [x] Task 49.4. `iru-plan`, `iru-code`, `iru-code-one-task-group` descriptions/examples: mention `typescript`,
        `android`, `swift` alongside `java`/`dotnet` where keys are exemplified (no logic change).
- [x] Task 50. Generalize `iru-release` and extract `iru-java-bump-version`
  - [x] Task 50.1. Create `iru-java-bump-version` (`haiku`): `/iru-java-bump-version <new-version>` — the
        `pom.xml` `<version>` edit logic lifted from `iru-release` Step 6 (root artifact's version, not a
        dependency's; reactor modules via `mvn versions:set -DnewVersion=… -DgenerateBackupPoms=false` when
        present), pre-release convention `x.y.z-SNAPSHOT`.
  - [x] Task 50.2. `iru-release/SKILL.md`: remove the `hermes` artifactId literal; Step 2 detects the ecosystem
        (via `iru-explore` output if present, else manifests) and calls the installed `iru-<key>-bump-version`
        (`find .claude/skills -maxdepth 1 -type d -name "iru-*-bump-version"`) to read the current version and its
        pre-release convention, falling back to asking the user which file carries the version; Step 6 delegates
        the bump the same way; Step 4/15 make `sync.yml`/`sync_versions.py` optional (skip with a note when
        absent); Step 13 uses the host tooling per `iru-explore` (`gh` for GitHub, REST/MCP for Bitbucket,
        `az repos` for Azure DevOps/TFS) like `iru-pr-description`; keep the changelog/PR-description/label steps
        unchanged; description updated.
- [x] Task 51. Update `CLAUDE.md` and the hand-maintained guides
  - [x] Task 51.1. `CLAUDE.md` Architecture: add the three backends to the issue-to-PR pipeline paragraph, the
        new bootstrap orchestrators and the `iru-setup-repository` front door, the shared `open-source`/`publish`/
        `distribution`/`sonar`/`mode` inputs, the Android reference-repository rule, and the "verify templates in
        a throwaway dir" convention.
  - [x] Task 51.2. `docs/modules/ROOT/pages/guides/extending-the-catalog.adoc`: rewrite "Repository bootstrap for
        other stacks" (front door now exists; how to add a 13th type), "Release generation for other ecosystems"
        (bump-version registry now exists), and add "Adding a project type" checklist; `guides/common-workflows.adoc`:
        add walkthroughs for `iru-setup-repository` on a new and an existing repository, and one per new stack
        family; `nav.adoc` untouched here (Task 52 handles generated entries; guide pages already listed).

### Group 9 — Documentation regeneration and end-to-end verification

Parallelizable: no — Task 52 must see every skill from Groups 1–8 on disk, and Task 53 may feed fixes back
into skills that Task 52 then has to re-document.

- [x] Task 52. Regenerate the Antora skill/agent docs and build the site
  - [x] Task 52.1. Run `Skill({skill: "iru-generate-skill-docs"})` so `index.adoc` (reference table, dependency
        graph, purpose groups — new groups for "TypeScript/Node bootstrap", "Android bootstrap", "Swift/Apple
        bootstrap", and the front door), every new `skills/*.adoc` page, the updated `agents/*.adoc`, and
        `nav.adoc` entries exist; confirm no skill directory lacks a page and no page lacks a skill.
  - [x] Task 52.2. Build: `cd docs && npm ci && npx antora antora-playbook.yml` via `iru-gate-runner`; fix every
        warning/xref error; `docs/build/` stays uncommitted.
- [x] Task 53. End-to-end smoke tests of the pipeline on throwaway projects
  - [x] Task 53.1. For each of `typescript` (Task 3 scaffold), `android` (Task 20 scaffold) and `swift` (Task 33
        scaffold) in `$TMPDIR/iru-verify/<stack>/e2e/`: copy this repository's `.claude/` into the throwaway
        project, write a two-task `implementation_plan.md` (one function + its test, untagged), run
        `/iru-plan`'s key-discovery command to confirm the key is found, then invoke
        `Skill({skill: "iru-code-one-task-group", args: "<group text>"})` and confirm it dispatches to
        `iru-<key>-code-one-task-group`, that the gates run (test, coverage, quality, doc audit) and that the
        checkboxes get checked; record any contract mismatch and fix the skill.
  - [x] Task 53.2. Run `iru-setup-repository` in `mode: existing` against the Task 20 Android throwaway
        (already scaffolded) to confirm it proposes `android-library`, skips the scaffold, and takes update paths
        without overwriting; and in `mode: new` on an empty `$TMPDIR/iru-verify/frontdoor/` for `typescript-library`
        end to end (Sonar `none`, publish `no`) to confirm the six sub-skills chain and the report's secrets table
        is empty apart from `GITHUB_TOKEN`.
  - [x] Task 53.3. Final report: list every skill created/modified (expected: 41 new skill directories, 1 agent
        edited, ~15 existing skills edited, 3 guides + `CLAUDE.md`), what was verified locally vs marked
        unverified (emulator/simulator runs, Sonar/publishing/signing steps, Tuist/SwiftLint if not installable),
        and any research-version drift found at run time.
