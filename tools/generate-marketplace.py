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
"""Generate ``.claude-plugin/marketplace.json`` from the plugin membership map ``tools/plugins.json``.

The catalog keeps every skill under ``.claude/skills/<name>/`` and every agent under ``.claude/agents/``; this script
only decides which plugin each belongs to. One marketplace entry is written per plugin, with ``source`` set to the
repository root (``./``) and ``skills``/``agents`` listing exactly that plugin's directories and files.

It fails (exit 1) when

* a skill or agent on disk is not in exactly one plugin, or a listed name/pattern matches nothing;
* a ``Skill({skill: ...})`` call (computed by ``tools/catalog-audit.py``) crosses plugins and neither a declared
  ``depends_on`` edge nor an ``optional_calls`` entry in ``plugins.json`` covers it;
* the dependency graph is cyclic.

Usage::

    python3 tools/generate-marketplace.py            # write .claude-plugin/marketplace.json
    python3 tools/generate-marketplace.py --check    # exit 1 when the committed file is stale; also runs
                                                     # ``claude plugin validate`` when the CLI is on PATH

Requires Python 3.9+ and PyYAML (through catalog-audit.py).
"""

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
DEFAULT_MEMBERSHIP = os.path.join(TOOLS_DIR, "plugins.json")
DEFAULT_BUDGETS = os.path.join(TOOLS_DIR, "catalog-budgets.json")
MARKETPLACE_REL = os.path.join(".claude-plugin", "marketplace.json")
CHANGELOG_VERSION_RE = re.compile(r"^##\s+\[(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)\]")


class GenerationError(Exception):
    """Raised with a list of human-readable problems when the marketplace cannot be generated."""

    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = list(problems)


def load_audit(tools_dir=TOOLS_DIR):
    """Import ``catalog-audit.py`` (its file name is not a valid module name) so the Skill() graph is computed
    exactly as the audit computes it."""
    spec = importlib.util.spec_from_file_location(
        "catalog_audit", os.path.join(tools_dir, "catalog-audit.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("catalog_audit", module)
    spec.loader.exec_module(module)
    return module


def load_membership(path):
    with open(path, encoding="utf-8") as handle:
        membership = json.load(handle)
    for key in ("marketplace", "plugins"):
        if key not in membership:
            raise GenerationError([f"{path}: missing top-level key {key!r}"])
    return membership


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def resolve_skills(plugins, skill_names):
    """Map plugin name -> sorted skill names; raise when ownership is not exactly one plugin per skill or a
    pattern matches nothing."""
    problems = []
    owners = defaultdict(list)
    members = {plugin["name"]: [] for plugin in plugins}
    for plugin in plugins:
        patterns = plugin.get("skills", [])
        excluded = plugin.get("exclude", [])
        matched_by_pattern = {pattern: 0 for pattern in patterns}
        for skill in skill_names:
            for pattern in patterns:
                if fnmatch.fnmatchcase(skill, pattern):
                    matched_by_pattern[pattern] += 1
            if matches(skill, patterns) and not matches(skill, excluded):
                owners[skill].append(plugin["name"])
                members[plugin["name"]].append(skill)
        for pattern, count in matched_by_pattern.items():
            if count == 0:
                problems.append(
                    "plugin {}: skill entry {!r} matches no skill on disk".format(
                        plugin["name"], pattern
                    )
                )
    for skill in skill_names:
        found = owners.get(skill, [])
        if not found:
            problems.append(f"skill {skill} is not listed in any plugin")
        elif len(found) > 1:
            problems.append(
                "skill {} is listed in several plugins: {}".format(
                    skill, ", ".join(found)
                )
            )
    if problems:
        raise GenerationError(problems)
    return {name: sorted(skills) for name, skills in members.items()}


def resolve_agents(plugins, agent_names):
    """Map plugin name -> sorted agent names; every agent on disk must be listed exactly once and exist."""
    problems = []
    members = {plugin["name"]: [] for plugin in plugins}
    owners = defaultdict(list)
    for plugin in plugins:
        for agent in plugin.get("agents", []):
            if agent not in agent_names:
                problems.append(
                    "plugin {}: agent {!r} does not exist in .claude/agents/".format(
                        plugin["name"], agent
                    )
                )
                continue
            owners[agent].append(plugin["name"])
            members[plugin["name"]].append(agent)
    for agent in agent_names:
        found = owners.get(agent, [])
        if not found:
            problems.append(f"agent {agent} is not listed in any plugin")
        elif len(found) > 1:
            problems.append(
                "agent {} is listed in several plugins: {}".format(
                    agent, ", ".join(found)
                )
            )
    if problems:
        raise GenerationError(problems)
    return {name: sorted(agents) for name, agents in members.items()}


def skill_owner_map(skill_members):
    return {
        skill: plugin for plugin, skills in skill_members.items() for skill in skills
    }


def cross_plugin_calls(data, owner_of):
    """Return {(caller plugin, callee plugin): [(caller skill, callee skill, line)]} for every static ``Skill()``
    call that crosses a plugin boundary. Dynamic calls (``<name>``) and external targets are not part of the
    graph, exactly as in the audit."""
    edges = defaultdict(list)
    for caller, entry in sorted(data["skills"].items()):
        for call in entry["skill_calls"]:
            if call["dynamic"]:
                continue
            target = call["target"].split(":")[-1]
            if target not in owner_of:
                continue
            source_plugin, target_plugin = owner_of[caller], owner_of[target]
            if source_plugin != target_plugin:
                edges[(source_plugin, target_plugin)].append(
                    (caller, target, call["line"])
                )
    return edges


def dependency_map(plugins, root_plugin):
    """Declared dependencies per plugin: the root plugin for every other plugin plus ``depends_on``."""
    dependencies = {}
    for plugin in plugins:
        declared = list(plugin.get("depends_on", []))
        if plugin["name"] != root_plugin and root_plugin not in declared:
            declared.insert(0, root_plugin)
        dependencies[plugin["name"]] = declared
    return dependencies


def find_cycle(dependencies):
    """Return a list of plugin names forming a dependency cycle, or None."""
    state = {}
    path = []

    def visit(node):
        state[node] = 1
        path.append(node)
        for nxt in dependencies.get(node, []):
            if state.get(nxt) == 1:
                return path[path.index(nxt) :] + [nxt]
            if state.get(nxt) is None:
                found = visit(nxt)
                if found:
                    return found
        path.pop()
        state[node] = 2
        return None

    for name in sorted(dependencies):
        if state.get(name) is None:
            found = visit(name)
            if found:
                return found
    return None


def optional_covers(optional_calls, source_plugin, target_plugin):
    return any(
        item["from"] == source_plugin and item["to"] in ("*", target_plugin)
        for item in optional_calls
    )


def check_dependencies(plugins, dependencies, edges, optional_calls):
    """Fail when a call crosses plugins without a dependency edge or optional-call entry, when a dependency names an
    unknown plugin, or when the dependency graph has a cycle."""
    problems = []
    names = {plugin["name"] for plugin in plugins}
    for name, declared in dependencies.items():
        for dep in declared:
            if dep not in names:
                problems.append(f"plugin {name} depends on unknown plugin {dep}")
    for (source_plugin, target_plugin), calls in sorted(edges.items()):
        if target_plugin in dependencies.get(source_plugin, []):
            continue
        if optional_covers(optional_calls, source_plugin, target_plugin):
            continue
        caller, callee, line = calls[0]
        problems.append(
            f"Skill() call crosses plugins without a dependency: {caller} ({source_plugin}) calls {callee} "
            f"({target_plugin}) at line {line} ({len(calls)} call(s)); add {target_plugin} to depends_on of "
            f"{source_plugin} or declare it under optional_calls"
        )
    if not problems:
        cycle = find_cycle(dependencies)
        if cycle:
            problems.append("dependency cycle: {}".format(" -> ".join(cycle)))
    if problems:
        raise GenerationError(problems)


def changelog_version(changelog_path):
    """The newest released version heading (``## [x.y.z]``) of a Keep a Changelog file, or None when only
    ``[Unreleased]`` exists or the file is missing."""
    try:
        with open(changelog_path, encoding="utf-8") as handle:
            for line in handle:
                match = CHANGELOG_VERSION_RE.match(line)
                if match:
                    return match.group(1)
    except OSError:
        return None
    return None


def run_quiet(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def owner_from_environment(root, existing=None):
    """Owner from ``git config``, else ``gh api user``, else the owner already in the committed file."""
    name = run_quiet(["git", "config", "user.name"], cwd=root)
    email = run_quiet(["git", "config", "user.email"], cwd=root)
    if name:
        owner = {"name": name}
        if email:
            owner["email"] = email
        return owner
    if shutil.which("gh"):
        login = run_quiet(["gh", "api", "user", "--jq", ".login"])
        if login:
            return {"name": login}
    if existing and existing.get("owner"):
        return existing["owner"]
    raise GenerationError(
        [
            "cannot determine the marketplace owner: set git config user.name or pass --owner"
        ]
    )


def build_marketplace(
    membership, skill_members, agent_members, dependencies, owner, version
):
    marketplace = membership["marketplace"]
    entries = []
    for plugin in membership["plugins"]:
        name = plugin["name"]
        entry = {
            "name": name,
            "description": plugin["description"],
            "category": plugin["category"],
            "source": "./",
            "strict": False,
        }
        if version:
            entry["version"] = version
        if dependencies[name]:
            entry["dependencies"] = list(dependencies[name])
        entry["skills"] = [f"./.claude/skills/{skill}" for skill in skill_members[name]]
        if agent_members[name]:
            entry["agents"] = [
                f"./.claude/agents/{agent}.md" for agent in agent_members[name]
            ]
        entries.append(entry)
    document = {
        "name": marketplace["name"],
        "owner": owner,
        "description": marketplace["description"],
    }
    if version:
        document["metadata"] = {"version": version}
    document["plugins"] = entries
    return document


def render(document):
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def without_version(document):
    """A deep copy of a marketplace document with the release version removed everywhere it is written: the
    top-level ``metadata.version`` and each plugin's ``version``. ``--check`` compares documents this way so that
    a release (a new ``## [x.y.z]`` CHANGELOG heading) does not make the committed file stale on its own."""
    copy = json.loads(json.dumps(document))
    metadata = copy.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("version", None)
        if not metadata:
            copy.pop("metadata")
    for plugin in copy.get("plugins", []):
        if isinstance(plugin, dict):
            plugin.pop("version", None)
    return copy


def generate(
    root,
    membership_path=DEFAULT_MEMBERSHIP,
    budgets_path=DEFAULT_BUDGETS,
    owner=None,
    use_committed_owner=False,
):
    """Return (document, rendered text, report dict). Raises GenerationError on any problem."""
    audit = load_audit()
    membership = load_membership(membership_path)
    budgets = (
        audit.load_budgets(budgets_path, False) if os.path.exists(budgets_path) else {}
    )
    data = audit.analyse(root, budgets)
    plugins = membership["plugins"]
    root_plugin = membership["marketplace"].get("root_plugin", "iru-core")
    skill_members = resolve_skills(plugins, sorted(data["skills"]))
    agent_members = resolve_agents(plugins, sorted(data["agents"]))
    dependencies = dependency_map(plugins, root_plugin)
    edges = cross_plugin_calls(data, skill_owner_map(skill_members))
    check_dependencies(
        plugins, dependencies, edges, membership.get("optional_calls", [])
    )
    marketplace_path = os.path.join(root, MARKETPLACE_REL)
    existing = None
    if os.path.isfile(marketplace_path):
        try:
            with open(marketplace_path, encoding="utf-8") as handle:
                existing = json.load(handle)
        except ValueError:
            existing = None
    if owner is None:
        if use_committed_owner and existing and existing.get("owner"):
            owner = existing["owner"]
        else:
            owner = owner_from_environment(root, existing)
    version = changelog_version(os.path.join(root, "CHANGELOG.md"))
    document = build_marketplace(
        membership, skill_members, agent_members, dependencies, owner, version
    )
    report = {
        "skills": {name: len(items) for name, items in skill_members.items()},
        "agents": {name: len(items) for name, items in agent_members.items() if items},
        "cross_plugin_edges": {
            "{} -> {}".format(*key): len(value) for key, value in sorted(edges.items())
        },
    }
    return document, render(document), report


def validate_with_cli(root, run=subprocess.run, which=shutil.which):
    """Run ``claude plugin validate <root>``; return (ran, ok, output). ``ran`` is False when the CLI is absent."""
    executable = which("claude")
    if not executable:
        return False, True, ""
    try:
        result = run(
            [executable, "plugin", "validate", root],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return True, False, str(error)
    return True, result.returncode == 0, result.stdout


def main(argv=None, validate=validate_with_cli):
    parser = argparse.ArgumentParser(
        description="Generate .claude-plugin/marketplace.json from tools/plugins.json."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 when the committed marketplace.json is stale (the release version "
        "from CHANGELOG.md is ignored in the comparison), and run 'claude plugin validate' when the "
        "claude CLI is installed",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="with --check, skip 'claude plugin validate'",
    )
    parser.add_argument(
        "--root", default=ROOT, help="repository root (default: this repository)"
    )
    parser.add_argument(
        "--membership",
        default=DEFAULT_MEMBERSHIP,
        help="membership map (default: tools/plugins.json)",
    )
    parser.add_argument(
        "--budgets",
        default=DEFAULT_BUDGETS,
        help="budgets file read for the audit's settings",
    )
    parser.add_argument(
        "--owner",
        help="owner name (default: git config user.name, then gh, then the committed one)",
    )
    args = parser.parse_args(argv)

    owner = {"name": args.owner} if args.owner else None
    try:
        document, text, report = generate(
            args.root,
            args.membership,
            args.budgets,
            owner,
            use_committed_owner=args.check,
        )
    except GenerationError as error:
        for problem in error.problems:
            sys.stderr.write(f"ERROR {problem}\n")
        sys.stderr.write(f"generate-marketplace: {len(error.problems)} problem(s)\n")
        return 1

    target = os.path.join(args.root, MARKETPLACE_REL)
    if args.check:
        try:
            with open(target, encoding="utf-8") as handle:
                committed = handle.read()
        except OSError:
            sys.stderr.write(
                f"ERROR {MARKETPLACE_REL} is missing; run python3 tools/generate-marketplace.py\n"
            )
            return 1
        if committed != text:
            try:
                committed_document = json.loads(committed)
            except ValueError:
                committed_document = None
            if committed_document is None or without_version(
                committed_document
            ) != without_version(document):
                sys.stderr.write(
                    f"ERROR {MARKETPLACE_REL} is stale; run python3 tools/generate-marketplace.py and commit the result\n"
                )
                return 1
            committed_version = (committed_document.get("metadata") or {}).get("version")
            current_version = (document.get("metadata") or {}).get("version")
            sys.stderr.write(
                f"generate-marketplace: note: only the release version differs ({MARKETPLACE_REL} says "
                f"{committed_version or 'none'}, CHANGELOG.md says {current_version or 'none'}); "
                "run python3 tools/generate-marketplace.py when convenient\n"
            )
        if not args.no_validate:
            ran, ok, output = validate(args.root)
            if not ran:
                sys.stderr.write(
                    "generate-marketplace: claude CLI not found, 'claude plugin validate' skipped\n"
                )
            elif not ok:
                sys.stderr.write(f"ERROR 'claude plugin validate' failed:\n{output}\n")
                return 1
        sys.stdout.write(
            f"generate-marketplace: {MARKETPLACE_REL} is up to date ({len(document['plugins'])} plugins)\n"
        )
        return 0

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(text)
    sys.stdout.write(
        f"generate-marketplace: wrote {MARKETPLACE_REL} ({len(document['plugins'])} plugins, "
        f"{sum(report['skills'].values())} skills)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
