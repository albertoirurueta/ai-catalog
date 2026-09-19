---
name: iru-java-bump-version
description: Set a Maven/Java project's version to an exact value. For a single-module `pom.xml`, rewrites the
  root artifact's own `<version>` element in place (the first `<version>` that is a direct child of `<project>`,
  never the `<parent>`'s version or a dependency/plugin's version). For a Maven reactor (the root `pom.xml`
  declares `<modules>`), instead runs `mvn versions:set -DnewVersion=<new-version> -DgenerateBackupPoms=false` so
  every module and parent reference updates consistently in one step. Gradle-based JVM projects are out of scope
  for this skill — see `iru-android-bump-version` for a Gradle/Kotlin DSL project. Invoke as
  `/iru-java-bump-version <new-version>` where `<new-version>` is the literal target version (e.g. `1.4.0` or
  `1.4.1-SNAPSHOT`) — this skill does not compute bumps itself, it only applies the value it's given (`iru-release`
  computes the release/next-dev values per the pre-release convention documented in this file and passes each one
  through in turn). Also accepts `args`: `sync-files: yes|no` (default: ask) to also update README/Antora version
  mentions, `next-version: <upcoming-version>` so that sync maps "Latest release" markers to `<new-version>` and
  "Latest snapshot"/"Current development version" markers to the upcoming pre-release value instead of rewriting
  every marker to the single value, and `dry-run: yes|no` (default `no`) to print the diff/command without writing
  or running anything.
  Reports the old and new version, whether the project was treated as a reactor or a single module, and every file
  touched. Use whenever the user, or another skill such as `iru-release`, needs a Maven project's version set to a
  specific value instead of hand-editing `pom.xml`.
model: haiku
---

# Java Bump Version

Set a Maven/Java project's version to an exact value across every file that needs to agree with it: `pom.xml` (the
root artifact's own version, or every module's version in a reactor), and — optionally — README/Antora version
mentions. This skill never computes a version itself — it applies exactly the version string it's given, validated
for shape. The "which version to compute next" logic (release vs. pre-release bump) belongs to the caller
(typically `iru-release`) and is defined in Step 5 below so that caller has one place to read it from — the same
contract `iru-typescript-bump-version`, `iru-android-bump-version`, and `iru-swift-bump-version` each define for
their own ecosystems.

## Step 0 — Resolve inputs

Parse the invocation:

- The positional argument is `<new-version>` — the exact target version string (e.g. `1.4.0`, `2.0.0-SNAPSHOT`). If
  it's missing, ask the user for it before doing anything else; don't guess or compute one here.
- `args` (`key: value` lines), if present:
  - `sync-files: yes|no` — whether to also update README/Antora version mentions (Step 7). If omitted, ask once
    with `AskUserQuestion` after Step 2 confirms whether such mentions actually exist; skip asking if none do.
  - `next-version: <upcoming-version>` — the upcoming pre-release version (e.g. `1.5.0-SNAPSHOT`) that README/
    Antora "Latest snapshot"/"Current development version" markers should show after a release, while "Latest
    release" markers show `<new-version>`. Only meaningful with `sync-files: yes`; `iru-release` passes it
    alongside the release version. Validate it the same way Step 1 validates `<new-version>`.
  - `dry-run: yes|no` — default `no`. When `yes`, run every step through composing the new file contents (or the
    `mvn versions:set` command that would run) and showing the diff, then stop — do not write anything or run any
    mutating command, and say so plainly in the report.

Reject, before touching anything, a `<new-version>` that is obviously not attempting a version at all (empty
string, or contains whitespace) with a short message asking for a valid value — Step 1 validates the actual shape.

## Step 1 — Validate the version string

Maven's own CLI doesn't strictly parse `-DnewVersion=` as semver (it accepts any string), so — the same situation
`iru-android-bump-version` is in — there's no build-tool command to lean on for validation the way `npm version
<v> --no-git-tag-version` does for the npm ecosystem. Validate with a regex instead, using this catalog's
Maven-style convention: `X.Y.Z` optionally followed by `-SNAPSHOT`:

```bash
python3 -c 'import re,sys; v=sys.argv[1]; sys.exit(0 if re.fullmatch(r"\d+\.\d+\.\d+(-SNAPSHOT)?", v) else 1)' "<new-version>"
```

If it doesn't match, warn the user the value doesn't follow this catalog's `X.Y.Z`/`X.Y.Z-SNAPSHOT` convention and
ask whether to proceed anyway (some projects intentionally use a different pre-release scheme, e.g. `-rc.1`) —
don't hard-stop on a non-matching but plausible string, only flag it, mirroring `iru-android-bump-version`'s Step 1.

## Step 2 — Survey the project layout

- Confirm `pom.xml` exists at the repository root. If it doesn't, but a `build.gradle`/`build.gradle.kts` does,
  stop and tell the user this skill only covers Maven — point them at `iru-android-bump-version` for a
  Gradle/Kotlin DSL JVM project instead (it already documents the equivalent Gradle rewrite, just under its
  Android-flavored file layout — the `libraryVersion`/`versionName` rewrite mechanics are the same shape a plain
  Gradle-JVM project would need). If neither build file exists, ask the user for the correct path or build tool.
- Determine whether this is a **reactor** (multi-module) build: does the root `pom.xml` declare a `<modules>`
  element as a direct child of `<project>` (not nested inside `<profiles>`)?
  ```bash
  python3 -c '
  import re, sys
  text = open("pom.xml").read()
  parent = re.search(r"<parent>.*?</parent>", text, flags=re.DOTALL)
  search = text
  if parent:
      s, e = parent.span()
      search = text[:s] + " " * (e - s) + text[e:]
  profiles = re.search(r"<profiles>", search)
  scope = search[:profiles.start()] if profiles else search
  sys.exit(0 if re.search(r"<modules>", scope) else 1)
  '
  ```
  Exit `0` → reactor, Step 4 uses `mvn versions:set`. Exit `1` → single module, Step 4 edits `pom.xml` directly.
- Note this finding for Step 8's report — the report must say plainly which path was taken and why.

## Step 3 — Locate and read the current version

Before changing anything, locate and read the current value so the diff is visible even if a later step fails
partway through, and so a caller like `iru-release` can obtain it without guessing.

**Locating the project's own `<version>`** — the rule to follow, without ever hardcoding any artifactId: it is the
first `<version>` element that is a **direct child of `<project>`**, i.e. it is never the `<parent>`'s `<version>`
(a child of `<parent>`, one level deeper) and never a dependency's or plugin's `<version>` (nested inside
`<dependencies>`/`<dependencyManagement>`/`<build>`/`<profiles>`). By Maven convention this element sits right
after `<artifactId>`, near the top of the file, before any of those later sections begin. Locate it by first
blanking out the `<parent>...</parent>` block (if any) so its own `<version>` can never match, then taking the
first `<version>...</version>` that appears before the first `<dependencies>`, `<dependencyManagement>`,
`<build>`, `<profiles>`, `<modules>`, or `<properties>` section:

```bash
python3 - "pom.xml" <<'PY'
import re, sys
path = sys.argv[1] if len(sys.argv) > 1 else "pom.xml"
text = open(path).read()

parent = re.search(r"<parent>.*?</parent>", text, flags=re.DOTALL)
search = text
if parent:
    s, e = parent.span()
    search = text[:s] + " " * (e - s) + text[e:]

boundary = re.search(
    r"<(dependencies|dependencyManagement|build|profiles|modules|properties)>", search
)
scope = search[: boundary.start()] if boundary else search

m = re.search(r"<version>([^<]*)</version>", scope)
if not m:
    sys.exit("Could not locate the project's own <version> element in pom.xml")
print(m.group(1))
PY
```

For a reactor, the root `pom.xml`'s own version located this way is normally what every module inherits from (via
`<parent><version>${revision}</version></parent>` or an explicit matching version) — this is the value to report
and pass through as "current version"; Step 4's `mvn versions:set` updates every module regardless of whether they
currently agree with it exactly.

## Step 4 — Preview (`dry-run: yes`) or apply the new version

**Reactor** (Step 2 found `<modules>`):

```bash
mvn versions:set -DnewVersion=<new-version> -DgenerateBackupPoms=false
```

`-DgenerateBackupPoms=false` writes the change directly instead of leaving `pom.xml.versionsBackup` files behind,
which also means `mvn versions:commit` (whose only job is to delete those backups) is unnecessary here — don't run
it. If `dry-run: yes`, run `mvn versions:set -DnewVersion=<new-version> -DgenerateBackupPoms=false -DdryRun` and
report what it shows to be planning to change (the `versions-maven-plugin` supports its own `-DdryRun` flag), or
if that flag isn't available in the resolved plugin version, at minimum show every `pom.xml` under the reactor
whose `<version>` currently matches the value read in Step 3, since those are exactly the files `versions:set`
would touch, then stop without running the mutating command.

**Single module** (no `<modules>`):

```bash
python3 - "pom.xml" "<new-version>" <<'PY'
import re, sys
path, new_version = sys.argv[1], sys.argv[2]
text = open(path).read()

parent = re.search(r"<parent>.*?</parent>", text, flags=re.DOTALL)
search = text
if parent:
    s, e = parent.span()
    search = text[:s] + " " * (e - s) + text[e:]

boundary = re.search(
    r"<(dependencies|dependencyManagement|build|profiles|modules|properties)>", search
)
scope_end = boundary.start() if boundary else len(search)

m = re.search(r"<version>[^<]*</version>", search[:scope_end])
if not m:
    sys.exit("Could not locate the project's own <version> element in pom.xml")
start, end = m.span()
old = m.group(0)
new_text = text[:start] + f"<version>{new_version}</version>" + text[end:]

if len(sys.argv) > 3 and sys.argv[3] == "--dry-run":
    import difflib
    diff = difflib.unified_diff(
        text.splitlines(keepends=True), new_text.splitlines(keepends=True),
        fromfile=path, tofile=path,
    )
    sys.stdout.writelines(diff)
else:
    open(path, "w").write(new_text)
    print(f"pom.xml: {old} -> <version>{new_version}</version>")
PY
```

Pass a fourth argument `--dry-run` (computing and printing the diff inside the same `python3` process, not via a
shell variable, so a trailing newline isn't lost) when `dry-run: yes`; otherwise omit it so the file is written.

If either path fails (non-zero exit, or the locate step can't find a `<version>` to rewrite), stop, show the
actual error, and do not treat any file as updated — don't partially apply the version by hand as a fallback.

## Step 5 — The Java-catalog pre-release convention (for `iru-release` and other callers)

This is the Maven-ecosystem equivalent of `iru-typescript-bump-version`'s `-dev.N` convention,
`iru-android-bump-version`'s `-SNAPSHOT` convention, and `iru-swift-bump-version`'s tag-based convention — the
contract a caller (typically `iru-release`) is expected to call this skill against (two calls per release, each
passing a computed `new-version` through the positional argument):

- **Current development version**: `x.y.z-SNAPSHOT` (e.g. `1.4.0-SNAPSHOT`) — Maven's own conventional
  pre-release marker, and this catalog's pre-existing convention before this skill was extracted from
  `iru-release`.
- **Cutting a release**: strip the `-SNAPSHOT` suffix entirely — `x.y.z-SNAPSHOT` → `x.y.z`. Call this skill with
  `<new-version>: x.y.z`.
- **Opening the next development cycle**: bump the patch or minor component (caller's choice — this catalog's
  established default is a minor bump, matching the repeatable `1.3.0` → `1.4.0-SNAPSHOT` cadence `iru-release`
  has always used) and reappend `-SNAPSHOT` — `x.y.z` → `x.y.(z+1)-SNAPSHOT` or `x.(y+1).0-SNAPSHOT`. Call this
  skill again, immediately or in a follow-up sync step, with the resulting `<new-version>`. This skill only
  applies whatever exact string it's given — it never guesses which component to bump.

## Step 6 — Sanity check

After Step 4's rewrite (skip entirely when `dry-run: yes`), confirm `pom.xml` is still well-formed and the new
version actually took effect, with a cheap, side-effect-free Maven command rather than a full build:

```bash
mvn -q help:evaluate -Dexpression=project.version -DforceStdout
```

This should print exactly `<new-version>`. A non-zero exit, an XML-parsing error, or a mismatched printed value
means the rewrite broke the file or targeted the wrong element — stop, show the actual error/output, and do not
report success. For a reactor, also spot-check one non-root module's POM
(`mvn -q -pl <module> help:evaluate -Dexpression=project.version -DforceStdout`) to confirm `versions:set`
actually propagated there too.

## Step 7 — Optionally sync other files that mirror the version

Ask (or honor `args: sync-files`) whether to also update other places that name the current version, the same way
`iru-typescript-bump-version`'s Step 6, `iru-android-bump-version`'s Step 8, and `iru-swift-bump-version`'s Step 8
do for their ecosystems:

- **`README.md`** — a Maven/Gradle dependency snippet naming the current version, if any:
  ```bash
  grep -n "<version>\|Latest release\|Latest snapshot\|Current development version" README.md
  ```
  Update each matched `<version>...</version>` inside an install/dependency code block the same way Step 4
  rewrote `pom.xml` — a targeted, scoped substitution, not a blind repository-wide replace — mapping each marker
  by what it names rather than rewriting them all to one value:
  - "Latest release" markers (and a Project Status row such as `Latest release`) → `<new-version>` when
    `<new-version>` is a release (no `-SNAPSHOT`); when `<new-version>` is itself a `-SNAPSHOT` (a next-dev bump
    on `develop`), leave them untouched — they still name the last real release.
  - "Latest snapshot"/"Current development version" markers → `next-version` when it was given; otherwise
    `<new-version>` only if it is a `-SNAPSHOT` value, and untouched (with a warning in Step 8 that the caller
    should pass `next-version`) when `<new-version>` is a release — never regress a development marker to a
    release value.
  - A snippet naming a single version with no such marker → `<new-version>`.
- **`docs/antora.yml`** — its `version:` field, if this repository has an Antora site and that field is meant to
  track the released version (skip for a `-SNAPSHOT` value — this catalog's convention is to only write a
  released version there, matching `iru-typescript-bump-version`/`iru-android-bump-version`/
  `iru-swift-bump-version`'s own Step 6/8).
- Any Antora page under `docs/modules/ROOT/pages/` showing a dependency snippet with a literal version string:
  ```bash
  grep -rl "<version>" docs/modules/ROOT/pages/*.adoc 2>/dev/null
  ```
  Update each match the same way as the README snippet above.

This is offered, not automatic — these files may be intentionally out of step with `pom.xml` (e.g. a README badge
pulling live from Maven Central rather than a hardcoded string), so don't rewrite anything the user didn't
confirm.

## Step 8 — Report

Summarize:

- Whether the project was treated as a **reactor** (`mvn versions:set` path) or a **single module** (direct
  `pom.xml` edit), and why (presence/absence of `<modules>`).
- The old version (Step 3) and the new version, and every file actually changed: `pom.xml` (or every module's
  `pom.xml` for a reactor), plus any Step 7 files accepted.
- Whether this was a `dry-run` (nothing written/run) or an actual write.
- The Step 6 sanity-check result — `mvn help:evaluate` output for the root (and, for a reactor, the spot-checked
  module) — passed, failed with the actual error, or not run because `dry-run: yes`.
- **Warn explicitly**: review the diff before committing (this skill doesn't commit anything); for a reactor,
  `versions:set -DgenerateBackupPoms=false` writes directly with no backup files to fall back on if the wrong
  version was passed — double-check `<new-version>` before confirming a non-dry-run call; a README/Antora badge
  that pulls the version live from Maven Central rather than hardcoding it should not have Step 7 applied to it.
