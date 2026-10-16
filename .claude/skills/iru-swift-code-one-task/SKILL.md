---
name: iru-swift-code-one-task
description: Implement a single task from a Swift `implementation_plan.md`-style task list — just the implementation and its tests. Detects whether the task belongs to a Swift Package (`Package.swift` — including a swift-argument-parser command-line tool, an `.executableTarget` depending on `ArgumentParser`, whose logic lives in a `<Bin>Kit` library behind thin commands, tested in-process and through the built binary, per `reference/cli.md` and the shared `reference/cli-contract.md`) or an Apple app project (a generator manifest — `project.yml` for XcodeGen, `Project.swift` for Tuist, or a bare hand-maintained `*.xcodeproj` with neither) and which target the task belongs to (`Sources/<Target>` in a plain package, `Packages/Core` for an app's shared/testable logic package, or the per-platform app target itself), then loads only the matching guidance from this skill's own `reference/` directory (this catalog's general Swift 6 code agreements: strict concurrency — `Sendable`, actors, `@MainActor`, structured concurrency, `nonisolated`, avoiding `@unchecked Sendable`; value types first; `guard` early exits; access control (`public`/`package`/`internal`); typed throws with `enum: Error` error types; naming per the Swift API Design Guidelines; member ordering; `// MARK:` sections; plus DocC documentation comments, Swift Testing/XCTest conventions, SwiftUI view composition, semver-stable package API conventions, per-platform app structure conventions, macOS desktop app conventions (SwiftUI scenes — `WindowGroup`/`Window`/`UtilityWindow`/`Settings`/`MenuBarExtra` —, menus/commands and keyboard shortcuts, App Sandbox + security-scoped bookmarks, hardened runtime, Apple silicon only), AppKit conventions (programmatic `NSWindowController`/`NSViewController` MVC, Auto Layout and `NSMenu` in code, Observation-tracking MVVM, `NSHostingView`/`NSViewRepresentable` interop), iOS/iPadOS app conventions (`scenePhase` and the suspension model, `BGTaskScheduler`/background `URLSession`, notification authorization, permission prompts and `Info.plist` usage-description keys, the `PrivacyInfo.xcprivacy` privacy manifest and required-reason APIs, widget/App Intents pointers, iPad multiple windows/menu bar/pointer/keyboard shortcuts, size classes, Dynamic Type/accessibility, Keychain secrets), UIKit conventions (programmatic scene-based `UIApplicationDelegate` + `UIWindowSceneDelegate`, view-controller lifecycle, Auto Layout in code, `UINavigationController`/`UITabBarController`, diffable data sources with compositional layout and cell registrations, `UIAction`/target-action, the trait system, `UIHostingController`/`UIHostingConfiguration`/`UIViewRepresentable` interop, MVC over a UI-free Core controller and MVVM via UIKit Observation tracking — `updateProperties()` on iOS 26+, `UIObservationTrackingEnabled` on iOS 18), visionOS conventions (SwiftUI-only windows, volumes, `ImmersiveSpace`/`openImmersiveSpace`, ornaments, hover effects, `RealityView` basics), and the MVVM vs MVC architecture rules — for an app it also detects the touched target's platform (macOS / iOS-iPadOS / visionOS, from the `iru-setup-macos-app` `App/` layout or the `iru-setup-apple-app` `Targets/<Platform>/` layout confirmed against the manifest), its UI framework (`swiftui`/`uikit`/`appkit`), and the architecture from the `Packages/Core/Sources/Core/ViewModels/` vs `…/Controllers/` layout), re-checks the current code state, implements exactly what the task specifies, writes/updates tests (Swift Testing for unit tests, XCTest for XCUITest and `measure`), compile-checks the touched target (`swift build --build-tests` for a package, or `xcodebuild build-for-testing -scheme <AppName>-<Platform>` with `-destination 'generic/platform=<P> Simulator'` (no simulator runtime needed) or `'platform=macOS'` for an app target — regenerating the project via `xcodegen generate`/`tuist generate` first when the manifest changed), then — if the task didn't stop on a blocker — immediately checks off this task's own checkbox (and its sub-tasks') in `implementation_plan.md` with a "group validation pending" note, so an interrupted run doesn't re-attempt work that already landed, before handing back a short summary (package/app and target detected, files touched, tests added/updated, compile-check result, any deliberate deviation from `reference/`, and any blocker) for the caller to record. Does not capture a quality baseline, add license headers, update DocC comments, run the full test suite/coverage/lint checks, or replace the pending note with the final validation outcome — those still happen once per task group in `iru-swift-code-one-task-group`, which is what invokes this skill once per task in a bucket (in parallel when the bucket allows it, through the `iru-isolated-skill-executor` agent) and finalizes each checkbox's note once group validation passes. Invoke as `/iru-swift-code-one-task <task description>`, passing the task's own text — including its exact `implementation_plan.md` checkbox line(s), so this skill can find and flip them — as the argument. Equivalent to `iru-java-code-one-task`/`iru-android-code-one-task`/`iru-typescript-code-one-task` for Swift Package Manager / Apple app projects.
model: sonnet
allowed-tools: Read Edit Write Bash(swift *) Bash(xcodebuild *) Bash(xcrun *) Bash(xcodegen *) Bash(tuist *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(find *) Bash(grep *) Bash(ls *)
---

# Implement one plan task

Carry out a single task's implementation, tests, and checkbox update against the real codebase — nothing else.
This is the narrowest execution unit in the `iru-code` pipeline: `iru-swift-code-one-task-group` calls it once per
task in a bucket (potentially many at once, in parallel agents via `iru-isolated-skill-executor`), then handles
license headers, DocC, and all test/coverage/quality validation itself, once for the whole bucket, instead of
repeating that validation here for every single task. It uses a medium model on purpose — the plan already carries
the hard reasoning; this skill just executes one task's implementation, against code agreements that live in
`reference/` rather than being re-derived per task.

## Step 1 — Detect the project shape, the target, then read only the reference material this task needs

A Swift repository this catalog scaffolds (`iru-setup-swift-library`, `iru-setup-apple-app`, `iru-setup-macos-app`,
`iru-setup-swift-cli`) is one of two shapes.
Work out which before reading anything:

1. **A plain Swift Package** — a `Package.swift` at (or near) the repository root with no `.xcodeproj`/generator
   manifest alongside it. Everything lives under `Sources/<Target>/` and `Tests/<Target>Tests/`, one pair per
   `Package.swift` target. **A command-line tool** is a plain package whose `Package.swift` declares an
   `.executableTarget` depending on `.product(name: "ArgumentParser", …)` (with an `.executable(...)` product):
   `iru-explore` reports it as `Project type: cli-tool (swift)`. In the `iru-setup-swift-cli` layout the logic lives in
   the `Sources/<Bin>Kit/` library, `Sources/<Bin>/` holds thin swift-argument-parser commands, and the tests are
   `Tests/<Bin>KitTests/` (in-process) plus `Tests/<Bin>CLITests/` (runs the built binary) — see `reference/cli.md`.
2. **An Apple app project** — an `.xcodeproj` exists (or is generated), plus one of:
   - **`project.yml`** at the repository root → the project is generated by **XcodeGen**
     (`xcodegen generate`). Targets are declared under its `targets:` key.
   - **`Project.swift`** (usually alongside a `Workspace.swift`/`Tuist.swift`) → the project is generated by
     **Tuist** (`tuist generate`). Targets are declared as `Target(...)` values inside `Project.swift`.
   - **Neither manifest, just a committed `*.xcodeproj`** → the project is **hand-maintained**; there is no
     generator to re-run, and the `.xcodeproj`'s own `project.pbxproj` is the source of truth for targets. Don't
     invent a `project.yml`/`Project.swift` for a project that doesn't have one.

   An app project frequently also has a local `Packages/Core` Swift package (declared as a local package
   dependency in the manifest) holding the testable logic behind the app's thin, per-platform UI targets — see
   `reference/app-structure.md`.

Then work out which **target** the task's file paths or description name:

- A path under `Sources/<Target>/` (package) or `Packages/Core/Sources/<Target>/` (app) names that target
  directly.
- A path under a per-platform app target directory (as the generator manifest names it — commonly
  `Targets/iOS/`, `Targets/macOS/`, `Targets/watchOS/`, `Targets/visionOS/` (`iru-setup-apple-app`) or `App/`
  (`iru-setup-macos-app`), or similar; read the manifest's `targets:`/`Target(...)` list rather than
  guessing the layout) names that target.
- Otherwise infer from what the task describes: reusable, testable logic with no UI import → the package's main
  target or `Packages/Core`; a `View`, `App` entry point, or anything importing SwiftUI/UIKit/AppKit for one
  specific platform → that platform's app target.
- In a command-line tool, logic, output and errors go to `<Bin>Kit`; a new subcommand's thin struct (flags +
  `DescribedCommand` metadata + one call into the Kit) goes to `Sources/<Bin>/` and is registered in the root's
  `subcommands:`.
- If genuinely ambiguous, default to the package's main target (or `Packages/Core` in an app project) — most
  tasks add or change logic, not UI — and say so in Step 8's report.

This module/target choice decides Step 5's compile-check scheme/target and, together with the task's own
file paths, where new files are created.

For an app project, also detect — once, from the repository, never assumed:

- **The layout and the touched target's platform** (full table in `reference/architecture.md`):
  - `App/Sources/` (+ `App/Tests/`, `App/UITests/`) with a single macOS app target → the `iru-setup-macos-app`
    layout (macOS-only, below).
  - `Targets/<Platform>/Sources/` (+ `Tests/`, `UITests/`) → the `iru-setup-apple-app` multiplatform layout: the
    folder names the target — `Targets/iOS/` (iPhone **and** iPad, one target), `Targets/macOS/`, `Targets/watchOS/`,
    `Targets/visionOS/`. Confirm the platform against the manifest (XcodeGen `platform:`/`supportedDestinations:`,
    Tuist `destinations:`), or the target's `SDKROOT` (`iphoneos`/`macosx`/`xros`/`watchos`) for a hand-maintained
    `.xcodeproj`.
  - **iPadOS** is an iOS target whose destinations include iPad (`supportedDestinations: [iOS, iPadOS]`, Tuist
    `.iPad`, or `TARGETED_DEVICE_FAMILY` containing `2`); a visionOS destination on an iOS target
    (`supportedDestinations: […, visionOS]`, Tuist `.appleVision`) or a standalone `xros` target is **visionOS**.
- **A macOS-only desktop app**: the generator manifest declares a single app target whose platform is macOS
  (XcodeGen `platform: macOS` / `supportedDestinations: [macOS]`, Tuist `destinations: .macOS`, or only
  `SDKROOT = macosx` in a hand-maintained `project.pbxproj`) and no iOS/watchOS/visionOS app target. Such an app
  (`iru-explore` reports it as `Project type: macos-app (…)`) compile-checks with `-destination 'platform=macOS'`
  and needs no simulator. A multiplatform app with a macOS target is not one — its Mac code just sits behind
  `#if os(macOS)`.
- **The UI framework** of the touched app target: `swiftui` (a `@main struct …: App` with `some Scene` — a
  `@UIApplicationDelegateAdaptor`/`@NSApplicationDelegateAdaptor` inside it doesn't change this), `uikit` (a `@main`
  `UIApplicationDelegate`/`main.swift` calling `UIApplicationMain`, a `UIWindowSceneDelegate`, `UIViewController`
  subclasses, no SwiftUI `App`; hosted `UIHostingController`/`UIHostingConfiguration` content doesn't change this) or
  `appkit` (a `@main` `NSApplicationDelegate`/`main.swift` running `NSApplication`, `NSWindowController`/
  `NSViewController` subclasses, no SwiftUI `App`; hosted SwiftUI views don't change this). visionOS and watchOS
  targets are SwiftUI.
- **The architecture**, from the layout contract (the same for both layouts): `Packages/Core/Sources/Core/ViewModels/`
  → **MVVM**; `Packages/Core/Sources/Core/Controllers/` (UI-free controllers + passive-view protocols) → **MVC**;
  neither → MV for SwiftUI / MVC for UIKit and AppKit (`reference/architecture.md` has the full table, including what
  to do when both exist). SwiftUI → MVVM or MV; UIKit/AppKit → MVC or MVVM. A task never switches it.

Logic an app task adds goes to `Packages/Core` (Foundation + Observation only — no SwiftUI/UIKit/AppKit import) in
the detected architecture's folder; only views, view controllers, window/scene controllers, menus/commands, the
composition root (`App`, `AppDelegate`, `SceneDelegate`), background-task/notification registration, and protocol
implementations that must touch a UI or platform framework belong in the app target.

This skill ships a `reference/` directory next to this file, holding this catalog's general Swift 6 code
agreements. Read `reference/README.md` first — it is short and routes you to the rest — then read only what it
points at for this task. The routing, restated:

| Read | When |
|---|---|
| `reference/code-style.md` | **Always** — Swift 6 strict concurrency, value types, access control, error handling, naming, member ordering. |
| `reference/docc.md` | The task adds or changes a type, or any `public`/`package`/`internal` member. |
| `reference/testing.md` | The task writes or updates tests — nearly every task, since Step 4 is part of implementing it. |
| `reference/swiftui.md` | The task adds or changes a SwiftUI `View` or view model. |
| `reference/package-api.md` | The task changes a `public` declaration in a library package's target — semver-stable API, availability, `Package.swift` hygiene. |
| `reference/app-structure.md` | The task adds a new app target, touches the generator manifest, or wires shared logic between `Packages/Core` and a platform target. |
| `reference/architecture.md` | The task adds or changes a view model, an MVC controller or its view protocol, a service protocol/test double, or decides whether logic goes in `Packages/Core` or the app target — every app task (macOS, iOS/iPadOS, visionOS) that isn't confined to one existing function. |
| `reference/macos.md` | The task touches a macOS app target: scenes/windows, menus/commands/shortcuts, Settings, `MenuBarExtra`, file access (panels, sandbox, security-scoped bookmarks), entitlements/hardened runtime, or anything that runs on the Mac's main thread. |
| `reference/appkit.md` | The task adds or changes AppKit code: `NSWindowController`/`NSViewController`/`NSView`, target-action, delegates/data sources, `NSMenu`, Auto Layout in code, AppKit MVVM via Observation tracking, or `NSHostingView`/`NSHostingController`/`NSViewRepresentable` interop. |
| `reference/ios.md` | The task touches an iOS/iPadOS app target: `scenePhase`/lifecycle, background tasks, notifications, permission prompts and usage-description keys, the privacy manifest, widgets/App Intents, iPad windows/menu bar/pointer/keyboard, size classes, Dynamic Type/accessibility, Keychain secrets, or main-thread work. |
| `reference/uikit.md` | The task adds or changes UIKit code: app/scene delegates, `UIViewController`/`UIView`, Auto Layout in code, navigation/tab/split containers, diffable collection views, `UIAction`/target-action, traits, UIKit MVVM via Observation tracking, or `UIHostingController`/`UIHostingConfiguration`/`UIViewRepresentable` interop. |
| `reference/cli.md` | The package is a command-line tool and the task adds or changes a command, flag, output, error/exit code, prompt, signal/cleanup, child process or the CLI tests. |
| `reference/cli-contract.md` | With `cli.md`, whenever a CLI task changes what a caller observes: stdout/stderr, exit codes, `--format`/JSON, colour, prompts, `--dry-run`/`--yes`, `schema`/help. |
| `reference/visionos.md` | The task touches a visionOS target or destination: windows, volumes, immersive spaces, ornaments, hover effects, `RealityView`/`Model3D`. |

Read only the file(s) that actually apply — a task inside a package's pure logic reads `package-api.md` only if
it changes `public` surface; a task inside an app's SwiftUI screen reads `swiftui.md` and not `package-api.md`.
Don't read the optional files speculatively — for a change confined to the body of one existing internal function
with no signature change, `code-style.md` plus `testing.md` is the whole list. A new screen in a SwiftUI macOS app
reads `architecture.md` + `macos.md` + `swiftui.md`; one in an AppKit app reads `architecture.md` + `macos.md` +
`appkit.md` (plus `swiftui.md` only when it hosts SwiftUI content). A new screen in a SwiftUI iOS app reads
`architecture.md` + `ios.md` + `swiftui.md`; in a UIKit iOS app `architecture.md` + `ios.md` + `uikit.md` (plus
`swiftui.md` only when it hosts SwiftUI); a visionOS scene reads `architecture.md` + `visionos.md` + `swiftui.md`. A new
command in a command-line tool reads `cli.md` + `cli-contract.md` + `testing.md` (and `docc.md` for its Kit types).

If `reference/` is missing (e.g. the skill directory was copied without it), proceed using this repository's own
`CLAUDE.md` conventions and the surrounding code's existing style, and say so in Step 8's report — don't guess at
what the reference would have said.

## Step 2 — Re-check the current code state

Read the actual current content of the file(s) the task touches before editing — don't assume any "current code
state" notes passed in with the task are still accurate; other tasks in the same bucket may be landing
concurrently, or the file may have changed for unrelated reasons.

Also note what the surrounding file and target already do about the things `reference/` has opinions on: whether
`Sendable`/actor isolation is already applied consistently, whether access control is deliberate or accidental,
how members are ordered, how errors are reported (typed throws vs. plain `Error`). The reference's rules are the
default for new code; a file that consistently does something else wins, and the divergence goes in Step 8's
report rather than becoming an unrequested restyle.

## Step 3 — Implement exactly what the task specifies

The named file(s), the described type/function/property, the behavior, the protocol it conforms to. Apply
`reference/code-style.md` and whichever files Step 1 selected, plus this repository's own `CLAUDE.md` conventions
where they are more specific (Swift language mode, minimum deployment target, license header expectations,
banned dependencies).

Non-negotiable, because a later gate enforces them:

- **Full DocC documentation** on every `public` and `package` type and member, with `- Parameters:`/`- Returns:`/
  `- Throws:` where applicable. The `- Throws:` list is what Step 4's tests are written against.
- **Declaration order** within any type you create or add to — see `reference/code-style.md`'s member-ordering
  section: `// MARK:`-grouped, public → package → internal → fileprivate/private, with overloads kept contiguous.
  Insert new members in their correct group; never reorder an existing file wholesale for an unrelated task.
- **Strict concurrency, clean.** Swift 6 language mode data-race safety is a compile error, not a warning — a new
  or changed declaration must build cleanly under it (Step 5). `Sendable` conformance, actor isolation, and
  `@MainActor` placement are part of "implementing the task," not a follow-up.
- **Value types first**, access control as narrow as it can be (`internal` is the default, `public` only for a
  package's actual API, `package` for cross-module-but-not-published sharing), and typed throws / an `enum: Error`
  for the errors a caller needs to distinguish — see `reference/code-style.md` for all three.
- **No new runtime dependency** unless the task explicitly calls for it. If one seems unavoidable, that's a
  blocker to report (Step 6), not a decision to make quietly.

Don't add anything the task didn't ask for — no speculative abstractions, no unrelated cleanup, no restyling of
code the task doesn't touch.

## Step 4 — Write or update the tests

Follow `reference/testing.md` and the existing test style in the same target (Swift Testing by default; XCTest
only where the project already uses it, or where Swift Testing genuinely can't — XCUITest, `measure`
performance tests). Cover the new/changed behavior, including the edge cases implied by the DocC `- Throws:`
contracts (e.g. invalid-argument or nil-handling cases) and, for an actor or `@MainActor` type, the isolation
itself. Do not run the test suite yourself — `iru-swift-code-one-task-group` runs it once for the whole bucket in
its own consolidated validation pass; this skill only compile-checks (Step 5).

## Step 5 — Compile-check the touched target

Swift 6 strict concurrency errors, an ambiguous overload, or a missed `Sendable` conformance often surface only at
build time, and a broken compile in one task blocks every other task in the same parallel bucket from validating.
Run, for what Step 1 detected:

- **A Swift Package target** (including `Packages/Core` inside an app project):

  ```bash
  swift build --build-tests
  ```

  This alone compiles the target and its test target under the package's declared `swiftLanguageModes`. Nothing
  more: no `swift test`, no coverage, no lint. Those belong to `iru-swift-code-one-task-group`'s consolidated
  validation.

- **An app target** (SwiftUI screen, `App` entry point, anything under a per-platform target directory):

  ```bash
  # Regenerate the project first only when the task edited the generator manifest itself
  # (project.yml / Project.swift) — a change confined to Swift source files doesn't need this.
  xcodegen generate            # if project.yml exists
  tuist generate --no-open      # if Project.swift exists

  # iOS/iPadOS, watchOS, visionOS target — a *generic* simulator destination: compiling needs only the platform SDK,
  # never an installed simulator runtime or a booted device.
  xcodebuild build-for-testing -scheme <AppName>-<Platform> -destination 'generic/platform=<P> Simulator'
  # macOS target (an iru-setup-macos-app project's single scheme is plain <AppName>):
  xcodebuild build-for-testing -scheme <AppName>-macOS -destination 'platform=macOS'
  ```

  `<AppName>-<Platform>` is the scheme `iru-setup-apple-app` generates per platform target (`<AppName>-iOS`,
  `-watchOS`, `-visionOS`, `-macOS`) and `<P>` its destination platform (`iOS`, `watchOS`, `visionOS`); for a
  hand-maintained `.xcodeproj`, use the scheme that builds the target Step 1 detected. Because the generic
  destination needs no runtime, a missing visionOS (or any other) simulator runtime is **not** a reason to report
  "compile-check unavailable" — only running tests needs one, and that belongs to the group validation.

- **Compile failure in code this task wrote or edited**: fix it — it's the task's own code, not a validation
  finding to defer.
- **Compile failure caused by something outside the task's scope** (a sibling task's in-flight edit in the same
  parallel bucket, a pre-existing error in a file the task didn't touch): don't fix unrelated code; note it in
  Step 8's report so the caller can tell a real regression from bucket-mate noise, and re-run the compile check
  once more before reporting if it looks like a transient race with a concurrently-writing sibling task.
- If the compile-check cannot run at all here (no Xcode / the platform's SDK isn't installed, `xcodegen`/`tuist`
  not installed for a manifest that just changed, no network for the first dependency resolution), say so in Step 8 as "compile-check
  unavailable" rather than blocking the task on it — the group-level validation in `iru-swift-code-one-task-group`
  will still catch a real compile error when it runs the full suite.

## Step 6 — When to interrupt the user

Keep interruptions rare — most tasks should complete unattended. Stop and use `AskUserQuestion` (or plain text if
no real choice is being offered) only when:

- Implementing the task reveals it's ambiguous in a way that changes correctness or scope and can't be safely
  inferred — conflicting instructions, a choice only the user can make (e.g. which of two APIs to break), or a
  missing decision. Don't ask about things with an obvious best-practice answer.
- The task's described approach appears infeasible against the real code as it stands (e.g. it names a type or
  member that doesn't exist and isn't a trivial typo) — not something you can resolve by writing the code
  slightly differently.
- The project shape or target detected in Step 1 is genuinely ambiguous in a way that changes which reference
  file and conventions apply (rare — most tasks name their own file path).

Do not stop merely because the task is nontrivial — implement it. Do not report the task done to work around a
blocker; report it as blocked instead (Step 8), with enough detail — what was tried, what failed, why — for the
caller to surface it. A conflict between `reference/` and the surrounding code is *not* a reason to stop: follow
the surrounding code and report the divergence.

## Step 7 — Check off this task's checkbox now

If this task did not stop on a blocker (Step 6), update `implementation_plan.md` at the repository root before
reporting back — don't leave this for the caller. Re-read the file fresh (not any earlier cached view — other
tasks in the same bucket may be landing concurrently) and locate this task's own checkbox line by the exact text
passed in with the task. Flip its `[ ]` to `[x]`, and do the same for every sub-task checkbox that was part of
the work just completed, adding a short note naming the files touched, e.g. `- [x] Task 4. **Implement
`RouteValidator`** — implemented, tests added; group validation pending.` — the same "pending" wording
`iru-swift-code-one-task-group` uses, since the coverage/quality outcome isn't known until it validates the whole
bucket in its own steps. Edit only this task's own line(s) — never rewrite surrounding lines or other tasks'
checkboxes, since sibling tasks in a parallel bucket may be editing this same file at nearly the same moment.
This is what lets an interrupted run resume without re-attempting a task whose implementation and tests already
landed, even if the interruption happened before `iru-swift-code-one-task-group` got to run its own group-wide
validation.

If this task stopped on a blocker instead, leave its checkbox untouched — there's nothing finished to mark done.

## Step 8 — Report the outcome

Hand control back to the caller with a short summary:

- **The project shape and target Step 1 detected** (package/app, generator if any — plus, for an app, the layout
  (`App/` or `Targets/<Platform>/`), the target's platform (macOS / iOS-iPadOS / visionOS), its UI framework and the
  architecture) and the reference file(s) actually read.
- **The file(s) touched** and **the tests added/updated** (not run — see Step 4).
- **The compile-check result** from Step 5 (passed / failed on this task's own code and was fixed / failed for a
  reason outside this task's scope / unavailable on this machine — say which command was used and why).
- **Whether this task stopped on a blocker** per Step 6, with enough detail for the caller to surface it.
- **Any deliberate deviation from `reference/`** — e.g. matching a file that still uses `@unchecked Sendable`,
  keeping a declaration `public` because it's genuinely part of the package's consumer-facing API, or adding a
  member to a file whose existing order is already inconsistent — so the caller can see it was a decision rather
  than an oversight. Say so here too if `reference/` was missing entirely (Step 1).

This is what `iru-swift-code-one-task-group` records for this task before running its own consolidated
license/DocC/test/coverage/quality validation across the whole bucket; this skill has already checked off this
task's own checkbox with a pending-validation note (Step 7) — the caller only needs to replace that note with the
final validation outcome once the whole bucket passes, not create the checkbox entry itself. This skill itself
never captures a quality baseline and never runs the full test suite, coverage, or lint/`swift format` checks.
