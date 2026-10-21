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
"""Audit the skills and agents of this catalog.

For every ``.claude/skills/*/SKILL.md`` and ``.claude/agents/*.md`` it collects size, frontmatter and
cross-reference metrics, and it can report them as JSON, as Markdown summary tables, or check them against the
budgets in ``tools/catalog-budgets.json``.

Usage::

    python3 tools/catalog-audit.py --json out.json          # full data
    python3 tools/catalog-audit.py --markdown               # summary tables on stdout
    python3 tools/catalog-audit.py --check                  # exit 1 on any error-level violation
    python3 tools/catalog-audit.py --plan implementation_plan.md   # plan-shape rule, exit 1 on any violation

The modes can be combined. Output is deterministic (no timestamps) so snapshots diff cleanly.
Requires Python 3.9+ and PyYAML.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    sys.stderr.write("catalog-audit: PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
DEFAULT_BUDGETS = os.path.join(TOOLS_DIR, "catalog-budgets.json")

SKILL_CALL_RE = re.compile(r'Skill\(\{\s*skill:\s*(\\?)"([^"\\]+)\\?"')
SUBAGENT_RE = re.compile(r'subagent_type:\s*\\?"([^"\\]+)\\?"')
AGENT_OPEN_RE = re.compile(r"Agent\(\{")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(:[A-Za-z0-9][A-Za-z0-9._-]*)?$")
ASSET_PATH_RE = re.compile(
    r"(?<![\w/.\-])((?:templates|reference)/[\w.\-/{}<>*]*[\w}>*])"
)
AGENT_LOOKBACK = 4000
COVERAGE_HEADING_RE = re.compile(
    r"^#{1,6}\s+Acceptance criteria coverage\s*$", re.IGNORECASE
)
HEADING_RE = re.compile(r"^#{1,6}\s+\S")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
CLARIFICATION_MARKER = "[NEEDS CLARIFICATION"
DEFAULT_SHARED = [
    "ui-contract.md",
    "cli-contract.md",
    "ui-docs.md",
    "accessibility-detection.md",
]


# --------------------------------------------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------------------------------------------


def split_frontmatter(text):
    """Return (frontmatter_text, body_text); frontmatter_text is None when there is no ``---`` block."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def lenient_frontmatter(frontmatter_text):
    """Best-effort ``key: value`` extraction for frontmatter that a strict YAML parser rejects."""
    result = {}
    current = None
    for line in frontmatter_text.split("\n"):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            current = match.group(1)
            result[current] = match.group(2).strip()
        elif current and line.startswith((" ", "\t")):
            result[current] = (result[current] + " " + line.strip()).strip()
    return result


def parse_frontmatter(text):
    """Return a dict with ``parses``, ``error``, ``keys``, ``data`` (strict or lenient) for the file text."""
    frontmatter_text, body = split_frontmatter(text)
    info = {
        "has_frontmatter": frontmatter_text is not None,
        "parses": False,
        "error": None,
        "keys": [],
        "data": {},
        "lenient": False,
    }
    if frontmatter_text is None:
        info["error"] = "no frontmatter block"
        return info, body
    try:
        data = yaml.safe_load(frontmatter_text)
        if not isinstance(data, dict):
            raise TypeError("frontmatter is not a mapping")
        info["parses"] = True
        info["data"] = data
        info["keys"] = list(data.keys())
    except (yaml.YAMLError, ValueError, TypeError) as error:
        info["error"] = " ".join(str(error).split())[:200]
        info["data"] = lenient_frontmatter(frontmatter_text)
        info["keys"] = list(info["data"].keys())
        info["lenient"] = True
    return info, body


def fenced_bytes(text):
    """Number of UTF-8 bytes (newlines included) of the lines inside fenced code blocks, fences excluded."""
    total = 0
    fence = None
    for line in text.split("\n"):
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
            continue
        if (
            match
            and match.group(1)[0] == fence[0]
            and len(match.group(1)) >= len(fence)
            and line.strip() == match.group(1)
        ):
            fence = None
            continue
        total += len(line.encode("utf-8")) + 1
    return total


def first_invocation_position(description):
    positions = [
        p for p in (description.find("/iru-"), description.find("Invoke as")) if p >= 0
    ]
    return min(positions) if positions else None


def inside_agent_call(text, position):
    """True when ``position`` sits inside the ``{ ... }`` argument object of an ``Agent({ ... })`` call."""
    start = text.rfind("Agent({", max(0, position - AGENT_LOOKBACK), position)
    if start < 0:
        return False
    depth = 0
    for char in text[start + len("Agent(") : position]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth <= 0:
                return False
    return depth > 0


def skill_calls(text):
    """Every ``Skill({skill: "x"})`` call as dicts with the target and whether it is inside an Agent prompt."""
    calls = []
    for match in SKILL_CALL_RE.finditer(text):
        target = match.group(2).strip()
        escaped = bool(match.group(1))
        calls.append(
            {
                "target": target,
                "dynamic": NAME_RE.match(target) is None,
                "in_agent_prompt": escaped or inside_agent_call(text, match.start()),
                "line": text.count("\n", 0, match.start()) + 1,
                "near_agent_mention": any(
                    agent in text[max(0, match.start() - 250) : match.start()]
                    for agent in ("iru-gate-runner", "iru-isolated-skill-executor")
                ),
            }
        )
    return calls


def asset_mentions(text):
    """Sorted unique ``templates/...`` and ``reference/...`` paths a SKILL.md names, wildcards/placeholders excluded."""
    return sorted(
        m for m in set(ASSET_PATH_RE.findall(text)) if not any(c in m for c in "{}<>*")
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------------------------------------------


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def entry_common(kind, rel_path, text):
    info, body = parse_frontmatter(text)
    data = info["data"]
    description = data.get("description")
    description = (
        description
        if isinstance(description, str)
        else ("" if description is None else str(description))
    )
    model = data.get("model")
    return {
        "kind": kind,
        "path": rel_path,
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "frontmatter_keys": info["keys"],
        "frontmatter_parses": info["parses"],
        "frontmatter_error": info["error"],
        "frontmatter_lenient": info["lenient"],
        "model": model if model is None else str(model),
        "description_length": len(description),
        "description_invocation_position": first_invocation_position(description),
        "fenced_bytes": fenced_bytes(body),
        "skill_calls": skill_calls(text),
        "subagent_dispatches": dict(sorted(Counter(SUBAGENT_RE.findall(text)).items())),
        "_description": description,
    }


def collect_skills(root):
    skills_dir = os.path.join(root, ".claude", "skills")
    skills = {}
    support_files = []
    if not os.path.isdir(skills_dir):
        return skills, support_files
    for name in sorted(os.listdir(skills_dir)):
        skill_dir = os.path.join(skills_dir, name)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        entry = entry_common(
            "skill", os.path.relpath(skill_md, root), read_text(skill_md)
        )
        entry["name"] = name
        entry["frontmatter_name"] = None
        support_bytes = 0
        support_count = 0
        for dirpath, dirnames, filenames in os.walk(skill_dir):
            dirnames.sort()
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                if full == skill_md or not os.path.isfile(full):
                    continue
                size = os.path.getsize(full)
                support_bytes += size
                support_count += 1
                support_files.append(
                    {
                        "skill": name,
                        "path": os.path.relpath(full, root),
                        "basename": filename,
                        "bytes": size,
                        "sha256": sha256_file(full),
                        "md5": md5_file(full),
                    }
                )
        entry["support_files"] = support_count
        entry["support_bytes"] = support_bytes
        entry["asset_mentions"] = asset_mentions(read_text(skill_md))
        entry["template_files"] = sorted(
            os.path.relpath(os.path.join(dp, fn), skill_dir).replace(os.sep, "/")
            for dp, _dn, fns in os.walk(os.path.join(skill_dir, "templates"))
            for fn in fns
        )
        entry["reference_files"] = sorted(
            os.path.relpath(os.path.join(dp, fn), skill_dir).replace(os.sep, "/")
            for dp, _dn, fns in os.walk(os.path.join(skill_dir, "reference"))
            for fn in fns
        )
        skills[name] = entry
    return skills, support_files


def collect_agents(root):
    agents_dir = os.path.join(root, ".claude", "agents")
    agents = {}
    if not os.path.isdir(agents_dir):
        return agents
    for filename in sorted(os.listdir(agents_dir)):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(agents_dir, filename)
        entry = entry_common("agent", os.path.relpath(path, root), read_text(path))
        entry["name"] = filename[:-3]
        agents[entry["name"]] = entry
    return agents


def analyse(root, budgets=None):
    budgets = budgets or {}
    external_skills = set(budgets.get("external_skills", []))
    accepted_calls = {
        (a.get("caller"), a.get("callee")): a.get("reason", "")
        for a in budgets.get("accepted_cross_model_calls", [])
    }
    skills, support_files = collect_skills(root)
    agents = collect_agents(root)

    # Duplicate supporting files by content hash.
    by_hash = defaultdict(list)
    for item in support_files:
        by_hash[item["sha256"]].append(item)
    duplicate_groups = []
    for digest, items in by_hash.items():
        if len(items) > 1:
            duplicate_groups.append(
                {
                    "sha256": digest,
                    "bytes": items[0]["bytes"],
                    "copies": len(items),
                    "redundant_bytes": items[0]["bytes"] * (len(items) - 1),
                    "files": sorted(i["path"] for i in items),
                }
            )
    duplicate_groups.sort(key=lambda g: (-g["redundant_bytes"], g["files"][0]))

    # md5 set per shared file name (names come from the budgets file when present, else the known four).
    names = sorted(set(budgets.get("shared_identical_files", DEFAULT_SHARED)))
    shared = {}
    for name in names:
        copies = [i for i in support_files if i["basename"] == name]
        md5s = sorted({i["md5"] for i in copies})
        shared[name] = {
            "copies": len(copies),
            "distinct_md5": md5s,
            "files_by_md5": {
                m: sorted(i["path"] for i in copies if i["md5"] == m) for m in md5s
            },
        }

    # Skill() graph, missing targets and inline cross-model calls.
    missing = []
    external = Counter()
    cross_model = []
    for caller_name, caller in sorted(skills.items()):
        for call in caller["skill_calls"]:
            if call["dynamic"]:
                continue
            target = call["target"].split(":")[-1]
            callee = skills.get(target)
            if callee is None and target in external_skills:
                external[target] += 1
                continue
            if callee is None:
                missing.append(
                    {
                        "caller": caller_name,
                        "target": call["target"],
                        "line": call["line"],
                    }
                )
                continue
            if call["in_agent_prompt"]:
                continue
            if caller["model"] != callee["model"]:
                cross_model.append(
                    {
                        "caller": caller_name,
                        "caller_model": caller["model"],
                        "callee": target,
                        "callee_model": callee["model"],
                        "line": call["line"],
                        "near_agent_mention": call["near_agent_mention"],
                        "accepted_reason": accepted_calls.get((caller_name, target)),
                    }
                )
    for agent in agents.values():
        for call in agent["skill_calls"]:
            target = call["target"].split(":")[-1]
            if (
                not call["dynamic"]
                and target in external_skills
                and target not in skills
            ):
                external[target] += 1
            elif not call["dynamic"] and target not in skills:
                missing.append(
                    {
                        "caller": "agent:" + agent["name"],
                        "target": call["target"],
                        "line": call["line"],
                    }
                )

    # Asset paths: a mentioned ``templates/...`` path must exist in the skill; a ``reference/...`` path must exist in
    # the skill or in some other skill (sibling skills legitimately point at each other's reference files).
    ignored_assets = budgets.get("asset_path_ignore", {})
    any_reference = set()
    for skill in skills.values():
        for ref in skill["reference_files"]:
            parts = ref.split("/")
            any_reference.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    missing_assets = []
    unreferenced_templates = []
    for name, skill in sorted(skills.items()):
        skill_dir = os.path.join(root, ".claude", "skills", name)
        ignore = set(ignored_assets.get(name, []))
        for mention in skill["asset_mentions"]:
            if mention in ignore or os.path.exists(os.path.join(skill_dir, mention)):
                continue
            if mention.startswith("reference/") and mention in any_reference:
                continue
            missing_assets.append({"skill": name, "path": mention})
        text = read_text(os.path.join(skill_dir, "SKILL.md"))
        for template in skill["template_files"]:
            if template not in text:
                unreferenced_templates.append({"skill": name, "path": template})

    for entry in list(skills.values()) + list(agents.values()):
        entry["skill_targets"] = sorted(
            Counter(c["target"] for c in entry["skill_calls"]).items()
        )
        entry["skill_targets"] = [
            {"target": t, "count": n} for t, n in entry["skill_targets"]
        ]

    return {
        "skills": skills,
        "agents": agents,
        "duplicate_support_files": duplicate_groups,
        "shared_files": shared,
        "external_skill_targets": dict(sorted(external.items())),
        "missing_skill_targets": sorted(
            missing, key=lambda m: (m["caller"], m["target"], m["line"])
        ),
        "inline_cross_model_calls": cross_model,
        "missing_asset_paths": missing_assets,
        "unreferenced_templates": unreferenced_templates,
        "support_file_count": len(support_files),
        "support_bytes_total": sum(i["bytes"] for i in support_files),
    }


def public_view(data):
    """Strip internal-only fields and add totals; the result is what ``--json`` writes."""
    out = json.loads(json.dumps(data))  # deep copy
    for group in ("skills", "agents"):
        for entry in out[group].values():
            entry.pop("_description", None)
            entry["skill_calls"] = [
                {
                    "target": c["target"],
                    "line": c["line"],
                    "dynamic": c["dynamic"],
                    "in_agent_prompt": c["in_agent_prompt"],
                    "near_agent_mention": c["near_agent_mention"],
                }
                for c in entry["skill_calls"]
            ]
    skills = list(data["skills"].values())
    agents = list(data["agents"].values())
    out["totals"] = {
        "skills": len(skills),
        "agents": len(agents),
        "skill_md_bytes": sum(s["bytes"] for s in skills),
        "skill_md_lines": sum(s["lines"] for s in skills),
        "skill_md_fenced_bytes": sum(s["fenced_bytes"] for s in skills),
        "support_files": data["support_file_count"],
        "support_bytes": data["support_bytes_total"],
        "duplicate_redundant_bytes": sum(
            g["redundant_bytes"] for g in data["duplicate_support_files"]
        ),
        "description_chars": sum(s["description_length"] for s in skills),
        "agent_description_chars": sum(a["description_length"] for a in agents),
        "descriptions_over_1024": sum(
            1 for s in skills + agents if s["description_length"] > 1024
        ),
        "descriptions_over_1536": sum(
            1 for s in skills + agents if s["description_length"] > 1536
        ),
        "skills_over_500_lines": sum(1 for s in skills if s["lines"] > 500),
        "skills_over_1000_lines": sum(1 for s in skills if s["lines"] > 1000),
        "frontmatter_parse_failures": sum(
            1 for s in skills + agents if not s["frontmatter_parses"]
        ),
        "missing_skill_targets": len(data["missing_skill_targets"]),
        "inline_cross_model_calls": len(data["inline_cross_model_calls"]),
        "inline_cross_model_calls_accepted": sum(
            1
            for c in data["inline_cross_model_calls"]
            if c.get("accepted_reason") is not None
        ),
        "skill_call_sites": sum(len(s["skill_calls"]) for s in skills + agents),
        "subagent_dispatch_sites": sum(
            sum(s["subagent_dispatches"].values()) for s in skills + agents
        ),
    }
    out["models"] = {
        "skills": dict(
            sorted(Counter((s["model"] or "(none)") for s in skills).items())
        ),
        "agents": dict(
            sorted(Counter((a["model"] or "(none)") for a in agents).items())
        ),
    }
    return out


# --------------------------------------------------------------------------------------------------------------
# Budgets and checks
# --------------------------------------------------------------------------------------------------------------


def load_budgets(path, required):
    """Load the budgets JSON; when it is unreadable, fail if ``required`` else fall back to built-in defaults."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        if required:
            sys.stderr.write(
                f"catalog-audit: cannot read budgets file {path}: {error}\n"
            )
            sys.exit(2)
        return {"shared_identical_files": DEFAULT_SHARED}


def run_checks(data, budgets):
    """Return a list of ``{"level": "error"|"warning", "rule", "subject", "message"}`` violations."""
    violations = []

    def add(level, rule, subject, message):
        violations.append(
            {"level": level, "rule": rule, "subject": subject, "message": message}
        )

    description_max = budgets.get("description_max", 1024)
    internal_target = budgets.get("description_internal_target", 400)
    invocation_within = budgets.get("invocation_form_within", 200)
    lines_max = budgets.get("skill_lines_max", 1000)
    lines_warn = budgets.get("skill_lines_warn", 500)
    agent_description_max = budgets.get("agent_description_max", description_max)
    require_agent_model = budgets.get("require_agent_model", True)
    internal = set(budgets.get("internal_skills", []))
    allowed_models = set(budgets.get("allowed_models", ["haiku", "sonnet", "opus"]))
    agent_models = set(
        budgets.get("agent_allowed_models", sorted(allowed_models | {"inherit"}))
    )
    cross_level = budgets.get("inline_cross_model_level", "warning")

    for name, skill in sorted(data["skills"].items()):
        if not skill["frontmatter_parses"]:
            add(
                "error",
                "frontmatter-parse",
                name,
                "frontmatter does not parse with yaml.safe_load: {}".format(
                    skill["frontmatter_error"]
                ),
            )
        if skill["description_length"] == 0:
            add("error", "description-missing", name, "no description")
        elif skill["description_length"] > description_max:
            add(
                "error",
                "description-max",
                name,
                "description is {} chars (max {})".format(
                    skill["description_length"], description_max
                ),
            )
        elif name in internal and skill["description_length"] > internal_target:
            add(
                "warning",
                "description-internal-target",
                name,
                "internal skill description is {} chars (target {})".format(
                    skill["description_length"], internal_target
                ),
            )
        position = skill["description_invocation_position"]
        if position is None:
            if name not in internal and skill["description_length"] > 0:
                add(
                    "warning",
                    "invocation-form-missing",
                    name,
                    "description has no '/iru-' or 'Invoke as' form",
                )
        elif position > invocation_within:
            add(
                "error",
                "invocation-form-position",
                name,
                f"invocation form starts at char {position} (must be within "
                f"the first {invocation_within})",
            )
        if skill["lines"] > lines_max:
            add(
                "error",
                "skill-lines-max",
                name,
                "SKILL.md has {} lines (max {})".format(skill["lines"], lines_max),
            )
        elif skill["lines"] > lines_warn:
            add(
                "warning",
                "skill-lines-warn",
                name,
                "SKILL.md has {} lines (warn above {})".format(
                    skill["lines"], lines_warn
                ),
            )
        if not skill["model"]:
            add("error", "model-missing", name, "no model in frontmatter")
        elif skill["model"] not in allowed_models:
            add(
                "error",
                "model-not-allowed",
                name,
                "model {!r} not in {}".format(skill["model"], sorted(allowed_models)),
            )

    for name, agent in sorted(data["agents"].items()):
        if not agent["frontmatter_parses"]:
            add(
                "error",
                "frontmatter-parse",
                "agent:" + name,
                "frontmatter does not parse with yaml.safe_load: {}".format(
                    agent["frontmatter_error"]
                ),
            )
        if agent["description_length"] > agent_description_max:
            add(
                "error",
                "agent-description-max",
                "agent:" + name,
                "description is {} chars (max {})".format(
                    agent["description_length"], agent_description_max
                ),
            )
        position = agent["description_invocation_position"]
        if position is not None and position > invocation_within:
            add(
                "error",
                "invocation-form-position",
                "agent:" + name,
                f"invocation form starts at char {position} "
                f"(must be within the first {invocation_within})",
            )
        if require_agent_model and not agent["model"]:
            add(
                "error",
                "agent-model-missing",
                "agent:" + name,
                "agent has no explicit model",
            )
        elif agent["model"] and agent["model"] not in agent_models:
            add(
                "error",
                "model-not-allowed",
                "agent:" + name,
                "model {!r} not in {}".format(agent["model"], sorted(agent_models)),
            )

    for name in budgets.get("shared_identical_files", []):
        shared = data["shared_files"].get(name)
        if shared and len(shared["distinct_md5"]) > 1:
            add(
                "error",
                "shared-file-drift",
                name,
                "{} copies but {} distinct contents".format(
                    shared["copies"], len(shared["distinct_md5"])
                ),
            )

    for item in data["missing_skill_targets"]:
        add(
            "error",
            "skill-target-missing",
            item["caller"],
            "Skill() target {!r} does not exist (line {})".format(
                item["target"], item["line"]
            ),
        )

    for item in data["inline_cross_model_calls"]:
        if item.get("accepted_reason") is not None:
            continue
        add(
            cross_level,
            "inline-cross-model-call",
            item["caller"],
            "calls {} inline ({} -> {}, line {})".format(
                item["callee"], item["caller_model"], item["callee_model"], item["line"]
            ),
        )

    for item in data["missing_asset_paths"]:
        add(
            "error",
            "asset-path-missing",
            item["skill"],
            "SKILL.md names {} but no such file exists".format(item["path"]),
        )
    for item in data["unreferenced_templates"]:
        add(
            "error",
            "template-unreferenced",
            item["skill"],
            "{} is not referenced by SKILL.md".format(item["path"]),
        )

    unknown_internal = sorted(n for n in internal if n not in data["skills"])
    for name in unknown_internal:
        add(
            "error",
            "internal-skill-unknown",
            name,
            "listed in internal_skills but no such skill exists",
        )
    return violations


# --------------------------------------------------------------------------------------------------------------
# Plan-shape rule (implementation_plan.md)
# --------------------------------------------------------------------------------------------------------------


def plan_lines_outside_code(text):
    """Yield (line_number, text) for every plan line outside fenced code blocks, inline code spans removed."""
    fence = None
    for number, line in enumerate(text.split("\n"), 1):
        match = FENCE_RE.match(line)
        if fence is None and match:
            fence = match.group(1)
            continue
        if fence is not None:
            if (
                match
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= len(fence)
            ):
                fence = None
            continue
        yield number, INLINE_CODE_RE.sub("", line)


def coverage_rows(lines):
    """Data rows (cells lists) of the tables found in the coverage section's lines, header and separator skipped."""
    rows = []
    for _number, line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell) and any(
            cells
        ):
            continue
        rows.append(cells)
    return rows[1:]  # the first table row is the header


def check_plan(text):
    """Check the shape of an implementation plan; return a list of violations (all of error level).

    Rules: ``plan-coverage-missing`` (no ``## Acceptance criteria coverage`` section), ``plan-coverage-empty`` (the
    section has no table rows), ``plan-coverage-uncovered`` (a row with no task in its last cell) and
    ``plan-clarification-open`` (a ``[NEEDS CLARIFICATION`` marker remains outside code spans and fences).
    """
    violations = []

    def add(rule, message):
        violations.append(
            {"level": "error", "rule": rule, "subject": "plan", "message": message}
        )

    lines = list(plan_lines_outside_code(text))
    section = None
    for number, line in lines:
        if COVERAGE_HEADING_RE.match(line.strip()):
            section = (number, [])
        elif HEADING_RE.match(line):
            if section is not None:
                break
        elif section is not None:
            section[1].append((number, line))

    if section is None:
        add("plan-coverage-missing", "no '## Acceptance criteria coverage' section")
    else:
        rows = coverage_rows(section[1])
        if not rows:
            add(
                "plan-coverage-empty",
                f"'## Acceptance criteria coverage' (line {section[0]}) has no table rows",
            )
        for cells in rows:
            if len(cells) < 3 or not cells[-1]:
                add(
                    "plan-coverage-uncovered",
                    "criterion {} names no covering task".format(cells[0] or "?"),
                )

    for number, line in lines:
        if CLARIFICATION_MARKER in line:
            add(
                "plan-clarification-open",
                f"unresolved '[NEEDS CLARIFICATION' marker at line {number}",
            )
    return violations


# --------------------------------------------------------------------------------------------------------------
# Markdown report
# --------------------------------------------------------------------------------------------------------------


def table(headers, rows, align_right=()):
    lines = [
        "| " + " | ".join(headers) + " |",
        "|"
        + "|".join(("---:" if i in align_right else "---") for i in range(len(headers)))
        + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
    return "\n".join(lines)


def kb(value):
    return "%.1f KB" % (value / 1024.0)


def markdown_report(data):
    view = public_view(data)
    totals = view["totals"]
    skills = list(data["skills"].values())
    out = ["# Catalog audit", ""]

    out += [
        "## Totals",
        "",
        table(
            ["Metric", "Value"],
            [
                ["Skills", totals["skills"]],
                ["Agents", totals["agents"]],
                [
                    "SKILL.md bytes (total)",
                    "{} ({})".format(
                        totals["skill_md_bytes"], kb(totals["skill_md_bytes"])
                    ),
                ],
                ["SKILL.md lines (total)", totals["skill_md_lines"]],
                [
                    "Bytes inside fenced code blocks (SKILL.md)",
                    "{} ({})".format(
                        totals["skill_md_fenced_bytes"],
                        kb(totals["skill_md_fenced_bytes"]),
                    ),
                ],
                ["Supporting files", totals["support_files"]],
                [
                    "Supporting file bytes",
                    "{} ({})".format(
                        totals["support_bytes"], kb(totals["support_bytes"])
                    ),
                ],
                [
                    "Redundant bytes in duplicate supporting files",
                    "{} ({})".format(
                        totals["duplicate_redundant_bytes"],
                        kb(totals["duplicate_redundant_bytes"]),
                    ),
                ],
                ["Skill description characters (total)", totals["description_chars"]],
                [
                    "Agent description characters (total)",
                    totals["agent_description_chars"],
                ],
                [
                    "Descriptions over 1,024 chars (skills + agents)",
                    totals["descriptions_over_1024"],
                ],
                [
                    "Descriptions over 1,536 chars (listing cap)",
                    totals["descriptions_over_1536"],
                ],
                ["SKILL.md over 500 lines", totals["skills_over_500_lines"]],
                ["SKILL.md over 1,000 lines", totals["skills_over_1000_lines"]],
                [
                    "Frontmatter parse failures (yaml.safe_load)",
                    totals["frontmatter_parse_failures"],
                ],
                ["`Skill()` call sites", totals["skill_call_sites"]],
                ["`subagent_type` dispatch sites", totals["subagent_dispatch_sites"]],
                ["Missing `Skill()` targets", totals["missing_skill_targets"]],
                [
                    "Inline cross-model `Skill()` calls",
                    "{} ({} accepted)".format(
                        totals["inline_cross_model_calls"],
                        totals["inline_cross_model_calls_accepted"],
                    ),
                ],
            ],
            align_right=(1,),
        ),
        "",
    ]

    out += [
        "## Top 20 skills by size (SKILL.md bytes)",
        "",
        table(
            [
                "Skill",
                "Model",
                "SKILL.md bytes",
                "Lines",
                "Fenced bytes",
                "Supporting bytes",
            ],
            [
                [
                    s["name"],
                    s["model"] or "-",
                    s["bytes"],
                    s["lines"],
                    s["fenced_bytes"],
                    s["support_bytes"],
                ]
                for s in sorted(skills, key=lambda s: (-s["bytes"], s["name"]))[:20]
            ],
            align_right=(2, 3, 4, 5),
        ),
        "",
    ]

    out += [
        "## Top 20 descriptions by length",
        "",
        table(
            ["Skill", "Model", "Description chars", "Invocation form at", "Parses"],
            [
                [
                    s["name"],
                    s["model"] or "-",
                    s["description_length"],
                    "-"
                    if s["description_invocation_position"] is None
                    else s["description_invocation_position"],
                    "yes" if s["frontmatter_parses"] else "NO",
                ]
                for s in sorted(
                    skills, key=lambda s: (-s["description_length"], s["name"])
                )[:20]
            ],
            align_right=(2, 3),
        ),
        "",
    ]

    model_rows = []
    for model in sorted(set(view["models"]["skills"]) | set(view["models"]["agents"])):
        model_rows.append(
            [
                model,
                view["models"]["skills"].get(model, 0),
                view["models"]["agents"].get(model, 0),
            ]
        )
    out += [
        "## Models",
        "",
        table(["Model", "Skills", "Agents"], model_rows, align_right=(1, 2)),
        "",
    ]

    out += [
        "## Agents",
        "",
        table(
            [
                "Agent",
                "Model",
                "Description chars",
                "Bytes",
                "Skill() calls",
                "Dispatches",
            ],
            [
                [
                    a["name"],
                    a["model"] or "(none)",
                    a["description_length"],
                    a["bytes"],
                    len(a["skill_calls"]),
                    sum(a["subagent_dispatches"].values()),
                ]
                for a in data["agents"].values()
            ],
            align_right=(2, 3, 4, 5),
        ),
        "",
    ]

    dispatch = Counter()
    for entry in list(data["skills"].values()) + list(data["agents"].values()):
        dispatch.update(entry["subagent_dispatches"])
    out += [
        "## Agent dispatch sites",
        "",
        table(["subagent_type", "Sites"], sorted(dispatch.items()), align_right=(1,)),
        "",
    ]

    groups = data["duplicate_support_files"]
    out += [
        "## Duplicate supporting files (by SHA-256)",
        "",
        "{} duplicate groups, {} redundant.".format(
            len(groups), kb(totals["duplicate_redundant_bytes"])
        ),
        "",
    ]
    if groups:
        out += [
            table(
                ["File name", "Copies", "Bytes each", "Redundant bytes"],
                [
                    [
                        os.path.basename(g["files"][0]),
                        g["copies"],
                        g["bytes"],
                        g["redundant_bytes"],
                    ]
                    for g in groups[:20]
                ],
                align_right=(1, 2, 3),
            ),
            "",
        ]
    shared_rows = [
        [
            name,
            v["copies"],
            len(v["distinct_md5"]),
            "identical" if len(v["distinct_md5"]) <= 1 else "DRIFT",
        ]
        for name, v in sorted(data["shared_files"].items())
    ]
    out += [
        "### Shared byte-identical files",
        "",
        table(
            ["File", "Copies", "Distinct md5", "Status"],
            shared_rows,
            align_right=(1, 2),
        ),
        "",
    ]

    cross = data["inline_cross_model_calls"]
    out += [
        "## Inline cross-model `Skill()` calls",
        "",
        "{} calls where caller and callee `model` differ and the call is not inside an `Agent({{...}})` prompt "
        "({} recorded as accepted under `accepted_cross_model_calls` in the budgets file).".format(
            len(cross), totals["inline_cross_model_calls_accepted"]
        ),
        "",
    ]
    if cross:
        out += [
            table(
                [
                    "Caller",
                    "Caller model",
                    "Callee",
                    "Callee model",
                    "Line",
                    "Near agent mention",
                    "Decision",
                ],
                [
                    [
                        c["caller"],
                        c["caller_model"] or "-",
                        c["callee"],
                        c["callee_model"] or "-",
                        c["line"],
                        "yes" if c["near_agent_mention"] else "no",
                        "accepted: " + c["accepted_reason"]
                        if c.get("accepted_reason") is not None
                        else "open",
                    ]
                    for c in cross
                ],
                align_right=(4,),
            ),
            "",
            (
                "`Near agent mention = yes` means the 250 characters before the call name `iru-gate-runner` or "
                "`iru-isolated-skill-executor` in prose: likely already delegated, review by hand."
            ),
            "",
        ]

    missing = data["missing_skill_targets"]
    out += ["## Missing `Skill()` targets", "", f"{len(missing)} missing.", ""]
    if data["external_skill_targets"]:
        out += [
            "Calls to skills outside this catalog (listed as `external_skills` in the budgets file, not "
            "counted as missing): "
            + ", ".join(
                "`{}` ({})".format(*kv) for kv in data["external_skill_targets"].items()
            )
            + ".",
            "",
        ]
    if missing:
        out += [
            table(
                ["Caller", "Target", "Line"],
                [[m["caller"], m["target"], m["line"]] for m in missing],
                align_right=(2,),
            ),
            "",
        ]

    failures = [
        e
        for e in list(data["skills"].values()) + list(data["agents"].values())
        if not e["frontmatter_parses"]
    ]
    out += [
        "## Frontmatter parse failures (`yaml.safe_load`)",
        "",
        f"{len(failures)} files.",
        "",
    ]
    if failures:
        out += [
            table(
                ["Name", "Kind", "Error"],
                [
                    [e["name"], e["kind"], (e["frontmatter_error"] or "")[:120]]
                    for e in failures
                ],
            ),
            "",
        ]
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------------------------------


def run_plan_check(path):
    """Print the plan's violations to stderr; return them, or None when the file cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        sys.stderr.write(f"catalog-audit: cannot read plan {path}: {error}\n")
        return None
    violations = check_plan(text)
    for violation in violations:
        sys.stderr.write(
            "{} [{}] {}: {}\n".format(
                violation["level"].upper(),
                violation["rule"],
                path,
                violation["message"],
            )
        )
    sys.stderr.write(f"catalog-audit: plan {path}: {len(violations)} violation(s)\n")
    return violations


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit the skills and agents of this catalog."
    )
    parser.add_argument(
        "--json", metavar="FILE", help="write the full audit data as JSON to FILE"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="print summary tables as Markdown on stdout",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check against the budgets file; exit 1 on any error-level violation",
    )
    parser.add_argument(
        "--plan",
        metavar="FILE",
        help="check the shape of an implementation plan (coverage section present and filled, no "
        "[NEEDS CLARIFICATION marker left); exit 1 on any violation",
    )
    parser.add_argument(
        "--budgets",
        metavar="FILE",
        default=DEFAULT_BUDGETS,
        help="budgets file (default: tools/catalog-budgets.json)",
    )
    parser.add_argument(
        "--root",
        metavar="DIR",
        default=ROOT,
        help="repository root (default: this repository)",
    )
    args = parser.parse_args(argv)

    if not (args.json or args.markdown or args.check or args.plan):
        parser.error("choose at least one of --json, --markdown, --check, --plan")

    status = 0
    if args.plan:
        plan_violations = run_plan_check(args.plan)
        status = 2 if plan_violations is None else (1 if plan_violations else 0)
        if not (args.json or args.markdown or args.check):
            return status

    budgets = load_budgets(args.budgets, args.check)
    data = analyse(args.root, budgets)

    if args.json:
        directory = os.path.dirname(os.path.abspath(args.json))
        os.makedirs(directory, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(
                public_view(data), handle, indent=2, sort_keys=True, ensure_ascii=False
            )
            handle.write("\n")
    if args.markdown:
        sys.stdout.write(markdown_report(data))

    if args.check:
        violations = run_checks(data, budgets)
        errors = [v for v in violations if v["level"] == "error"]
        warnings = [v for v in violations if v["level"] != "error"]
        for violation in errors + warnings:
            sys.stderr.write(
                "{} [{}] {}: {}\n".format(
                    violation["level"].upper(),
                    violation["rule"],
                    violation["subject"],
                    violation["message"],
                )
            )
        sys.stderr.write(
            f"catalog-audit: {len(errors)} error(s), {len(warnings)} warning(s)\n"
        )
        return 1 if errors else status
    return status


if __name__ == "__main__":
    sys.exit(main())
