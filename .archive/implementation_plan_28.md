# Implementation plan — Optional accessibility and assistive-technology support

## Task summary

Source: GitHub issue #28
Base branch: main

Make accessibility / assistive-technology (AT) support a first-class, **optional** part of the catalog: web ARIA and
semantic-HTML rules; native AT support (Android TalkBack / `contentDescription`, Apple VoiceOver /
`accessibilityLabel`, Windows Narrator / `AutomationProperties`); readable and user-adjustable font sizes; contrast;
and, preferably, reduced-motion, light/dark and high-contrast modes. Projects may opt out at repository setup (e.g. a
mandated non-compliant design); the default stays "supported". For a repository that already contains code, setup must
first **detect whether the existing code already supports accessibility** before considering it enabled, to avoid a
half-compliant app (old non-compliant code + new compliant code).

Decisions made on the user's behalf (challenge in review):

- **Reuse `.ui-quality.yml`'s `accessibility:` key** instead of adding a second key. Today `enforce|report|off`
  controls only the automated UI-test checks, and §8's coding defaults "always apply". New semantics:
  `enforce` / `report` / `off` are unchanged (rules apply, automated checks fail / are listed / not run) and a **new
  value `none` means "opted out entirely"**: no accessibility coding rules, no automated checks, no a11y docs section.
  Backwards compatible — no existing file changes meaning. A missing file still means `enforce` for a *new* UI
  project, but for an existing repository with no detected a11y support setup writes `none` (or asks, see Group 2).
- **One shared detection reference**, `reference/accessibility-detection.md`, byte-identical in `iru-explore` and
  `iru-setup-repository` (same duplication convention as `ui-contract.md`), plus `iru-explore` gains an
  `Accessibility:` report line that the front door reads, like it reads `Project type:`.
- **Detection result is three-state**: `present` (a11y attributes/tests/config found consistently), `partial`
  (some evidence, but coverage is low or only in some modules), `absent` (none). Pre-selection: `present` → recommend
  `enforce`; `partial` → ask, recommend `report` and warn about mixed compliance; `absent` → recommend `none`
  with the warning that enabling it makes only new code compliant. New (empty) repositories keep `enforce` as
  the recommended default.
- **Platform rules live in the shared `ui-contract.md` §8** (12 byte-identical copies, updated together) plus a short
  per-stack section in each `ui-implementation.md`; nothing is restated per setup skill beyond naming the key.
- No language tag on tasks: the work is Markdown/AsciiDoc authoring, implemented directly by `iru-code-one-task-group`.

## Current code state

- `.claude/skills/*/reference/ui-contract.md` — 12 byte-identical copies (md5 `43628cb5…`) in the coding skills
  `android, swift, kmp, typescript, nextjs, react-native, php, django, windows, dotnet, rust, go`
  (`iru-<key>-code-one-task/reference/`). §8 "Accessibility" lists coding defaults (always) + automated checks and the
  `.ui-quality.yml` shape (`accessibility: enforce|report|off`, `directions`, `themes`). Matrix themes already include
  an optional `high-contrast`.
- `.claude/skills/iru-<key>-code-one-task/reference/ui-implementation.md` — per-stack UI guidance (no explicit AT-API
  rules yet: no `contentDescription`/`accessibilityLabel`/`AutomationProperties`/ARIA specifics).
- Setup skills that write `.ui-quality.yml` and take `accessibility` in Step 0: `iru-setup-react-web`,
  `-angular-web`, `-nextjs-web`, `-react-native-app`, `-ionic-app`, `-android-library`, `-android-app`,
  `-apple-app`, `-macos-app`, `-kmp-app`, `-windows-app`, `-php-laravel`, `-php-wordpress`, `-php-prestashop`,
  `-python-django`, `-java-springboot-hilla`, and the TUI-capable `-rust-cli`, `-go-cli`, `-swift-cli`, `-dotnet-cli`.
- Orchestrators forwarding the key: `iru-setup-repository` (front door, Step 9 asks "Run automated accessibility
  checks in the UI tests?" with Enforce/Report/Off), the `*-repository` orchestrators, and `iru-setup-java-springboot`
  (manifest key `accessibility`).
- Readers of the level: `iru-<key>-code-one-task-group` (android, swift, go, react-native, windows, …),
  `iru-typescript-test`, `iru-go-test`, `iru-swift-test`, `iru-typescript-generate-all-tests`,
  `iru-swift-generate-all-tests`, `iru-android-generate-all-tests`, `iru-dotnet-generate-all-tests`,
  the `-github-workflows` skills (a11y report artifacts), `iru-gate-runner` agent (description mentions UI test runs
  with accessibility checks), `iru-update-docs` / `iru-update-java-springboot-documentation` `reference/ui-docs.md`
  (an *Accessibility* section per screen/component).
- `iru-explore` (Step 5/7) reports `User interface:` incl. `.ui-quality.yml accessibility: …`; has no scan of existing
  code. `iru-plan` Step 5 names the automated check "at the repository's `.ui-quality.yml` level".
- Docs: `docs/modules/ROOT/pages/skills/*.adoc`, `agents/*.adoc`, `index.adoc` are generated by
  `iru-generate-skill-docs`; `guides/building-user-interfaces.adoc` and `CLAUDE.md` are hand-maintained.
- Precedent: `.archive/implementation_plan_6.md` (group-per-area, byte-identical shared files, final generated-docs run).

## Implementation steps

### Group 1 — Shared contract and detection reference (Parallelizable: yes)

- [x] Task 1. Extend the shared UI contract §8 (author once, then copy verbatim to the 12 copies in Group 2)
  - [x] Task 1.1. Edit `.claude/skills/iru-swift-code-one-task/reference/ui-contract.md` §8: add the `none` value to the
    `.ui-quality.yml` block (`none: opted out entirely — none of the rules below apply, no checks, no a11y docs`),
    state that "Coding defaults, always" becomes "Coding defaults, unless `accessibility: none`", and keep
    `off` = "rules apply, checks not run".
  - [x] Task 1.2. Add a **Platform assistive-technology rules** subsection: Web (native semantic elements first — `h1`…, `article`,
    `section`, `button`; every interactive control keyboard-operable; never hide focusable elements with
    `display:none`/`aria-hidden`; accessible names via `aria-label`/`alt`/associated `<label>`), Android (TalkBack:
    `contentDescription` / Compose `semantics { contentDescription }`, `importantForAccessibility`, 48dp targets),
    Apple (VoiceOver: `accessibilityLabel`/`Value`/`Hint`/traits, SwiftUI `.accessibilityLabel`, Dynamic Type),
    Windows (Narrator: `AutomationProperties.Name`/`HelpText`, UI Automation peers, tab order), plus terminal UIs
    (unchanged: colour-independence, `NO_COLOR`, keyboard-only).
  - [x] Task 1.3. Add a **Visual comfort** subsection: adjustable/legible font sizes, contrast ratios (already stated),
    and the *preferred* extras — reduced-motion modes (`prefers-reduced-motion`, Android animator scale,
    `accessibilityReduceMotion`, `SystemParameters.ClientAreaAnimation`), light/dark themes, high-contrast modes
    (`forced-colors`, Windows High Contrast, iOS Increase Contrast); flag these as "preferred, not gated".
  - [x] Task 1.4. Add an **Opting out and existing code** paragraph: `none` is chosen at setup; an existing repository
    is scanned first (pointer to `iru-explore`'s `Accessibility:` line); never mix — when `none`, generated code and
    docs omit the AT-specific additions and say so once in the UI docs index.
- [x] Task 2. Write the shared detection reference `reference/accessibility-detection.md`
  - [x] Task 2.1. Create `.claude/skills/iru-explore/reference/accessibility-detection.md`: per-stack grep signals
    (web: `aria-`, `role=`, `alt=`, `<label for`, `@axe-core/*`, `eslint-plugin-jsx-a11y`/`@angular-eslint` a11y rules,
    `jest-axe`; Android: `contentDescription`, `semantics {`, `importantForAccessibility`, Espresso
    `AccessibilityChecks`; Apple: `accessibilityLabel`, `.accessibilityLabel(`, `performAccessibilityAudit`,
    `UIAccessibility`; Windows: `AutomationProperties.`, `Axe.Windows`; React Native: `accessibilityLabel`,
    `accessibilityRole`, `eslint-plugin-react-native-a11y`; PHP/Python templates: `aria-`, `alt=`; any existing
    `.ui-quality.yml`), a **coverage heuristic** (accessibility-attribute count vs. count of interactive elements /
    image usages, sampled), and the `present | partial | absent` thresholds with the evidence list to print.
  - [x] Task 2.2. State the pre-selection table (present → enforce, partial → report + warning, absent → none + warning)
    and that detection never edits code; it only informs the question.
- [x] Task 3. Update `iru-explore` to report accessibility status
  - [x] Task 3.1. In `.claude/skills/iru-explore/SKILL.md` Step 4 add an "Accessibility scan" bullet (UI projects only)
    pointing at `reference/accessibility-detection.md`; in Step 7's Tech-stack block add the line
    `Accessibility: <present|partial|absent|not applicable (no UI)> — <evidence summary>; .ui-quality.yml: <value|missing>`.
  - [x] Task 3.2. Update the `description` frontmatter and the `User interface:` sentence in Step 7 accordingly.

### Group 2 — Contract propagation and per-stack guidance (Parallelizable: yes)

- [x] Task 4. Copy the finished §8 verbatim into the other 11 `ui-contract.md` files (android, kmp, typescript, nextjs,
  react-native, php, django, windows, dotnet, rust, go) and verify all 12 are byte-identical (`md5` check).
- [x] Task 5. Add AT-specific sections to each `ui-implementation.md` (one sub-task per stack, short, link to §8):
  - [x] Task 5.1. `iru-typescript-code-one-task` (React/Angular/Ionic/Hilla ARIA + semantic elements, Angular CDK a11y,
    React Native `accessibilityRole`/`Label`), `iru-nextjs-code-one-task`, `iru-react-native-code-one-task`
  - [x] Task 5.2. `iru-android-code-one-task`, `iru-kmp-code-one-task` (TalkBack, `contentDescription`, Compose
    semantics, font scale `sp`, animator-duration scale; iOS host: VoiceOver)
  - [x] Task 5.3. `iru-swift-code-one-task` (VoiceOver, Dynamic Type, Reduce Motion, Increase Contrast; iOS/iPadOS/macOS/
    watchOS/visionOS), `iru-windows-code-one-task` (Narrator, `AutomationProperties`, High Contrast themes)
  - [x] Task 5.4. `iru-php-code-one-task`, `iru-django-code-one-task` (templates: semantic HTML, `aria-*`, WordPress/
    PrestaShop theme notes), `iru-dotnet-code-one-task`, `iru-rust-code-one-task`, `iru-go-code-one-task` (TUI only)
- [x] Task 6. Make the coding/test skills honour `none`
  - [x] Task 6.1. In every `iru-<key>-code-one-task-group` that reads `.ui-quality.yml` (android, swift, kmp, go,
    react-native, windows, typescript, nextjs, php, django, rust, dotnet — grep `ui-quality`), document: `none` ⇒ skip
    AT rules and checks, report them "opted out", never "unverified".
  - [x] Task 6.2. Same for the test/generate skills that parse the key: `iru-typescript-test`, `iru-go-test`,
    `iru-swift-test`, `iru-typescript-generate-all-tests`, `iru-swift-generate-all-tests`,
    `iru-android-generate-all-tests`, `iru-dotnet-generate-all-tests`, and `.claude/agents/iru-gate-runner.md`
    (treat `none` and `off` as "accessibility checks not applicable").
  - [x] Task 6.3. `iru-plan` Step 5 UI bullet: mention that accessibility tasks/checks are omitted when
    `.ui-quality.yml` says `none`.

### Group 3 — Setup flow: ask and detect (Parallelizable: no — Task 8 consumes the contract of Task 7)

- [x] Task 7. Front door `iru-setup-repository`
  - [x] Task 7.1. Copy `accessibility-detection.md` (byte-identical) to `.claude/skills/iru-setup-repository/reference/`.
  - [x] Task 7.2. Rework Step 9: reword to "Support accessibility and assistive technologies?" with options
    **Enforce (Recommended for new projects)**, **Report only**, **Off** (rules apply, no automated checks),
    **None — opt out entirely** (e.g. a mandated non-compliant design); in `mode: existing` run/reuse the
    `iru-explore` `Accessibility:` result first, show the evidence, and apply the pre-selection table with the
    mixed-compliance warning. Update the `args` vocabulary (`accessibility: enforce|report|off|none`) in the
    description, Step 0 notes, forwarding section (~lines 29, 98, 555, 699) and the final-report line.
- [x] Task 8. Orchestrators and scaffolds accept `none`
  - [x] Task 8.1. Update the `accessibility` Step 0 parsing/validation + the forwarded-keys sentence in the 11
    `*-repository` orchestrators and `iru-setup-java-springboot` (manifest comment), listing `none`.
  - [x] Task 8.2. In each UI scaffold (the 16 UI + 4 TUI setup skills listed under "Current code state") add: with
    `none`, write `accessibility: none` to `.ui-quality.yml`, skip a11y test tooling (axe, ATF audit, Axe.Windows,
    jsx-a11y/react-native-a11y lint) and skip a11y-specific template attributes; with `enforce|report|off`
    include the AT attributes from §8 in the generated templates (accessible names on icon buttons, semantic landmarks,
    `alt`, font-scale-safe units, `prefers-reduced-motion` guards). For `mode: existing` runs, a scaffold that finds
    a prior `.ui-quality.yml` follows the existing Update/Keep/Replace prompt and never silently flips the level.
  - [x] Task 8.3. `-github-workflows` skills (typescript, android, swift, macos, windows, kmp, php, python,
    java-springboot): skip the a11y report artifact/step when `none`.
  - Notes: Task 7 — `iru-setup-repository` (byte-identical `reference/accessibility-detection.md`, md5 690d42a4…; Step 9 reworked with Enforce/Report/Off/None + detection pre-selection; args/forwarding/report lines). Task 8 — 10 orchestrators and 20 UI/TUI scaffolds accept `none` (question rewording, None option, `.ui-quality.yml` template comment, AT-template/tooling opt-out paragraph), 9 `-github-workflows` skills carry an accessibility opt-out paragraph. Markdown only: no tests/coverage; no new YAML-frontmatter parse failures; license headers n/a.

### Group 4 — Docs and catalog documentation (Parallelizable: yes)

- [x] Task 9. Update `iru-update-docs/reference/ui-docs.md` and the byte-identical copy in
  `iru-update-java-springboot-documentation/reference/`: the *Accessibility* subsection is written only when the level
  is not `none`; with `none`, add one sentence on the UI index page stating accessibility support is opted out.
- [x] Task 10. Hand-maintained docs: extend `docs/modules/ROOT/pages/guides/building-user-interfaces.adoc` with an
  "Accessibility and assistive technologies" section (the four levels, platform rules, visual comfort extras, the
  existing-code detection) and update `common-workflows.adoc` / `creating-skills-and-agents.adoc` if they list the
  setup questions or the `accessibility` args.
- [x] Task 11. Update `CLAUDE.md` ("Shared bootstrap inputs", "UI contract", `iru-explore` bullets): `accessibility:
  enforce|report|off|none`, the new `Accessibility:` explore line, and the second shared byte-identical file.

### Group 5 — Verification and generated docs (Parallelizable: no — must run after Groups 1–4)

- [x] Task 12. Consistency checks (run via `iru-gate-runner`/Bash, no build tool here): all 12 `ui-contract.md`
  identical; both `accessibility-detection.md` identical; both `ui-docs.md` identical; `grep -rn "enforce|report|off"`
  finds no remaining three-value-only mention in `.claude/`; every skill frontmatter still valid YAML.
- [x] Task 13. Dry-run the detection heuristics from `accessibility-detection.md` against 2–3 real repositories in a
  throwaway dir outside this repo (`$TMPDIR/iru-verify/accessibility/`): one with a11y attributes, one without;
  record results and any heuristic fix in the reference.
- [x] Task 14. Run `/iru-generate-skill-docs` to regenerate `index.adoc`, `skills/*.adoc`, `agents/*.adoc`, `nav.adoc`,
  then `cd docs && npx antora antora-playbook.yml` to confirm the site builds; report anything unverifiable.
