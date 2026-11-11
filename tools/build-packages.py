#!/usr/bin/env python3
# Copyright 2026 Alberto Irurueta Carro (albertoirurueta@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Build the downloadable zip packages of the catalog.

Writes, into ``--out``:

* ``ai-catalog-skills-agents.zip`` with every ``skills/<name>/**`` and ``agents/*.md`` of ``.claude/``;
* one ``<plugin-name>.zip`` per plugin of ``tools/plugins.json`` with that plugin's skills and agents.

Zip paths are relative to ``.claude/`` (``skills/iru-plan/SKILL.md``, ``agents/iru-gate-runner.md``). Output is
deterministic (sorted entries, fixed timestamp, regular-file modes 644 or 755 from the source's executable bit).
Only files git would track are packed (tracked or untracked-but-not-ignored, via ``git ls-files``), never local junk
such as ``.DS_Store`` or ``__pycache__``. Existing ``*.zip`` files in ``--out`` are removed first, so a removed or
renamed plugin leaves no stale zip behind. With ``--partial`` an AsciiDoc table fragment with a download button per
plugin is written too. Nothing is written inside ``.claude/``.

Usage::

    python3 tools/build-packages.py --out <dir> [--root <repo>] [--partial <file>]

Standard library only (Python 3.9+).
"""

import argparse
import fnmatch
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

FULL_ZIP = "ai-catalog-skills-agents.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
JUNK_NAMES = {".DS_Store", "Thumbs.db", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
JUNK_SUFFIXES = (".pyc", ".pyo", ".swp", ".swo", "~")
DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class BuildError(Exception):
    """Raised with a list of human-readable problems when the packages cannot be built."""

    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = list(problems)


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def list_skills(root):
    base = root / ".claude" / "skills"
    return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


def list_agents(root):
    base = root / ".claude" / "agents"
    return sorted(p.stem for p in base.glob("*.md")) if base.is_dir() else []


def resolve_plugin(plugin, skill_names, agent_names):
    """Return (skills, agents, problems) for one plugin entry."""
    problems = []
    patterns = plugin.get("skills", [])
    excluded = plugin.get("exclude", [])
    for pattern in patterns:
        if not any(fnmatch.fnmatchcase(skill, pattern) for skill in skill_names):
            problems.append(
                f"plugin {plugin['name']}: skill entry {pattern!r} matches no skill on disk"
            )
    skills = sorted(
        s for s in skill_names if matches(s, patterns) and not matches(s, excluded)
    )
    agents = []
    for agent in plugin.get("agents", []):
        if agent in agent_names:
            agents.append(agent)
        else:
            problems.append(
                f"plugin {plugin['name']}: agent {agent!r} does not exist in .claude/agents/"
            )
    return skills, sorted(agents), problems


def is_junk(relative):
    parts = Path(relative).parts
    return any(part in JUNK_NAMES for part in parts) or parts[-1].endswith(JUNK_SUFFIXES)


def git_files(root):
    """Return the set of files under .claude/ that git tracks or would track, or None outside a git worktree."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".claude"],
            cwd=root, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {entry for entry in result.stdout.decode("utf-8").split("\0") if entry}


def file_mode(source):
    """Regular-file mode for a zip entry: 755 when the source is executable, else 644."""
    permissions = 0o755 if source.stat().st_mode & 0o111 else 0o644
    return (stat.S_IFREG | permissions) << 16


def collect_entries(root, skills, agents, allowed=None):
    """Return sorted [(zip path, source file)] for the given skills and agents.

    ``allowed`` is the set of repository-relative paths git knows (see ``git_files``); None packs every file that
    is not local junk.
    """
    claude = root / ".claude"
    entries = []
    for skill in skills:
        for path in (claude / "skills" / skill).rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if is_junk(relative) or (allowed is not None and relative not in allowed):
                continue
            entries.append((path.relative_to(claude).as_posix(), path))
    for agent in agents:
        path = claude / "agents" / f"{agent}.md"
        entries.append((path.relative_to(claude).as_posix(), path))
    return sorted(entries)


def write_zip(target, entries):
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for arcname, source in entries:
            info = zipfile.ZipInfo(arcname, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = file_mode(source)
            archive.writestr(info, source.read_bytes())


def format_size(size):
    return f"{size / (1024 * 1024):.1f} MiB" if size >= 1024 * 1024 else f"{max(1, round(size / 1024))} KiB"


def render_partial(rows):
    lines = ["[cols=\"2,1,1,1,2\",options=\"header\"]", "|===", "|Plugin |Skills |Agents |Size |Download"]
    for name, skill_count, agent_count, size in rows:
        button = (
            f'image:download-zip-compact.svg["Download {name} (zip)",width=110,'
            f"xref=attachment${name}.zip]"
        )
        lines.append(f"|`{name}` |{skill_count} |{agent_count} |{format_size(size)} |{button}")
    lines.append("|===")
    return "\n".join(lines) + "\n"


def build(root, out, partial=None):
    """Build all zips under ``out``; return the list of (plugin, skills, agents, size) rows."""
    root, out = Path(root), Path(out)
    membership = json.loads((root / "tools" / "plugins.json").read_text(encoding="utf-8"))
    skill_names, agent_names = list_skills(root), list_agents(root)
    resolved, problems = [], []
    for plugin in membership["plugins"]:
        skills, agents, found = resolve_plugin(plugin, skill_names, agent_names)
        problems.extend(found)
        resolved.append((plugin["name"], skills, agents))
    if problems:
        raise BuildError(problems)
    if out.is_dir():
        for stale in out.glob("*.zip"):
            stale.unlink()
    allowed = git_files(root)
    write_zip(out / FULL_ZIP, collect_entries(root, skill_names, agent_names, allowed))
    rows = []
    for name, skills, agents in resolved:
        target = out / f"{name}.zip"
        write_zip(target, collect_entries(root, skills, agents, allowed))
        rows.append((name, len(skills), len(agents), target.stat().st_size))
    if partial is not None:
        partial = Path(partial)
        partial.parent.mkdir(parents=True, exist_ok=True)
        partial.write_text(render_partial(rows), encoding="utf-8")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="directory receiving the zip files")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root (default: this repository)")
    parser.add_argument("--partial", help="write an AsciiDoc table fragment to this file")
    args = parser.parse_args(argv)
    try:
        rows = build(args.root, args.out, args.partial)
    except BuildError as error:
        print("build-packages: " + "\nbuild-packages: ".join(error.problems), file=sys.stderr)
        return 1
    print(f"Wrote {FULL_ZIP} and {len(rows)} plugin zips to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
