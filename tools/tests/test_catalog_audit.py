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
"""Unit tests for tools/catalog-audit.py. Run with: python3 -m unittest discover -s tools/tests"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import ClassVar

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "catalog_audit", os.path.join(TOOLS_DIR, "catalog-audit.py")
)
audit = importlib.util.module_from_spec(_SPEC)
sys.modules["catalog_audit"] = audit
_SPEC.loader.exec_module(audit)

SHARED = "same shared content\n"


def skill_text(name, model="sonnet", description=None, body=""):
    description = (
        description if description is not None else f"Does {name}. Invoke as `/{name}`."
    )
    return f"---\nname: {name}\ndescription: {description}\nmodel: {model}\n---\n\n# {name}\n\n{body}"


class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="catalog-audit-test-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def skill(self, name, **kwargs):
        return self.write(f".claude/skills/{name}/SKILL.md", skill_text(name, **kwargs))

    def agent(self, name, text):
        return self.write(f".claude/agents/{name}.md", text)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = audit.main(list(argv))
            except SystemExit as exit_info:
                code = exit_info.code
        return code, out.getvalue(), err.getvalue()


class ParsingTests(unittest.TestCase):
    def test_split_frontmatter(self):
        self.assertEqual(
            audit.split_frontmatter("---\na: 1\n---\nbody"), ("a: 1", "body")
        )
        self.assertEqual(audit.split_frontmatter("no frontmatter")[0], None)
        self.assertEqual(audit.split_frontmatter("---\nnever closed")[0], None)

    def test_parse_frontmatter_ok(self):
        info, body = audit.parse_frontmatter("---\nname: x\nmodel: haiku\n---\nbody")
        self.assertTrue(info["parses"])
        self.assertEqual(info["keys"], ["name", "model"])
        self.assertEqual(body, "body")

    def test_parse_frontmatter_failure_falls_back_to_lenient(self):
        text = "---\nname: x\ndescription: Does it: badly\nmodel: haiku\n---\nbody"
        info, _ = audit.parse_frontmatter(text)
        self.assertFalse(info["parses"])
        self.assertTrue(info["lenient"])
        self.assertEqual(info["data"]["model"], "haiku")
        self.assertEqual(info["data"]["description"], "Does it: badly")
        self.assertIn("mapping values", info["error"])

    def test_parse_frontmatter_without_block_or_mapping(self):
        info, _ = audit.parse_frontmatter("plain text")
        self.assertFalse(info["has_frontmatter"])
        info, _ = audit.parse_frontmatter("---\n- a\n- b\n---\nbody")
        self.assertFalse(info["parses"])

    def test_lenient_frontmatter_joins_continuation_lines(self):
        result = audit.lenient_frontmatter("description: first\n  second\nmodel: haiku")
        self.assertEqual(result, {"description": "first second", "model": "haiku"})

    def test_fenced_bytes_counts_only_inner_lines(self):
        text = "intro\n```yaml\nabc\ndef\n```\nafter\n~~~\nxy\n~~~\n"
        self.assertEqual(
            audit.fenced_bytes(text), len("abc\n") + len("def\n") + len("xy\n")
        )

    def test_fenced_bytes_longer_fence_and_nested(self):
        text = "````md\n```\ninner\n```\n````\n"
        self.assertEqual(audit.fenced_bytes(text), len("```\n") * 2 + len("inner\n"))

    def test_fenced_bytes_unterminated_fence_counts_to_end(self):
        self.assertEqual(audit.fenced_bytes("```\nabc\n"), 4 + 1)

    def test_first_invocation_position(self):
        self.assertEqual(audit.first_invocation_position("abc /iru-x"), 4)
        self.assertEqual(audit.first_invocation_position("Invoke as foo /iru-x"), 0)
        self.assertIsNone(audit.first_invocation_position("nothing here"))

    def test_skill_calls_detects_forms(self):
        text = (
            'Run `Skill({skill: "iru-a"})`.\n'
            'Agent({description: "d", subagent_type: "iru-gate-runner", prompt: "Invoke Skill({skill: '
            '\\"iru-b\\", args: \\"x\\"}) now"})\n'
            'Outside: Skill({skill:\n"iru-c"}) and Skill({skill: "iru-<key>-x"}).\n'
        )
        calls = audit.skill_calls(text)
        self.assertEqual(
            [c["target"] for c in calls], ["iru-a", "iru-b", "iru-c", "iru-<key>-x"]
        )
        self.assertEqual(
            [c["in_agent_prompt"] for c in calls], [False, True, False, False]
        )
        self.assertEqual([c["dynamic"] for c in calls], [False, False, False, True])
        self.assertTrue(calls[1]["near_agent_mention"])
        self.assertFalse(calls[0]["near_agent_mention"])

    def test_inside_agent_call_multiline_unescaped(self):
        text = 'Agent({\n  description: "d",\n  prompt: "Invoke Skill({skill: "iru-x"})"\n})\nlater Skill({skill: "iru-y"})'
        calls = audit.skill_calls(text)
        self.assertTrue(calls[0]["in_agent_prompt"])
        self.assertFalse(calls[1]["in_agent_prompt"])

    def test_inside_agent_call_without_agent(self):
        self.assertFalse(audit.inside_agent_call('Skill({skill: "iru-x"})', 10))


class CollectionTests(CatalogTestCase):
    def test_empty_root(self):
        data = audit.analyse(self.root)
        self.assertEqual(data["skills"], {})
        self.assertEqual(data["agents"], {})
        self.assertEqual(audit.public_view(data)["totals"]["skills"], 0)

    def test_collects_skill_metrics(self):
        self.skill("iru-a", model="haiku", body="```\ncode line\n```\n")
        self.write(".claude/skills/iru-a/reference/ref.md", "12345")
        self.write(".claude/skills/iru-a/notes/more.md", "123")
        self.write(".claude/skills/not-a-skill/readme.md", "ignored")
        data = audit.analyse(self.root)
        entry = data["skills"]["iru-a"]
        self.assertEqual(list(data["skills"]), ["iru-a"])
        self.assertEqual(entry["model"], "haiku")
        self.assertEqual(entry["support_files"], 2)
        self.assertEqual(entry["support_bytes"], 8)
        self.assertEqual(entry["fenced_bytes"], len("code line\n"))
        self.assertTrue(entry["frontmatter_parses"])
        self.assertEqual(
            entry["description_invocation_position"],
            entry["_description"].find("Invoke as"),
        )
        self.assertEqual(data["support_file_count"], 2)

    def test_collects_agents_and_ignores_non_markdown(self):
        self.agent(
            "iru-gate",
            "---\nname: iru-gate\ndescription: Runs.\nmodel: haiku\n---\nbody\n"
            'Agent({subagent_type: "iru-gate-runner"})',
        )
        self.write(".claude/agents/notes.txt", "x")
        data = audit.analyse(self.root)
        self.assertEqual(list(data["agents"]), ["iru-gate"])
        self.assertEqual(
            data["agents"]["iru-gate"]["subagent_dispatches"], {"iru-gate-runner": 1}
        )

    def test_duplicates_and_shared_files(self):
        for name in ("iru-a", "iru-b", "iru-c"):
            self.skill(name)
            self.write(f".claude/skills/{name}/reference/ui-contract.md", SHARED)
        self.write(".claude/skills/iru-c/reference/cli-contract.md", "different")
        self.write(".claude/skills/iru-b/reference/cli-contract.md", "other")
        data = audit.analyse(
            self.root, {"shared_identical_files": ["ui-contract.md", "cli-contract.md"]}
        )
        self.assertEqual(len(data["duplicate_support_files"]), 1)
        group = data["duplicate_support_files"][0]
        self.assertEqual(
            (group["copies"], group["redundant_bytes"]), (3, 2 * len(SHARED))
        )
        self.assertEqual(len(data["shared_files"]["ui-contract.md"]["distinct_md5"]), 1)
        self.assertEqual(
            len(data["shared_files"]["cli-contract.md"]["distinct_md5"]), 2
        )

    def test_missing_external_and_cross_model(self):
        self.skill(
            "iru-caller",
            model="sonnet",
            body=(
                'Inline `Skill({skill: "iru-haiku"})`, same-model `Skill({skill: "iru-sonnet"})`, missing '
                '`Skill({skill: "iru-ghost"})`, external `Skill({skill: "code-review"})`, prefixed '
                '`Skill({skill: "plugin:iru-haiku"})`, delegated Agent({description: "d", subagent_type: '
                '"iru-gate-runner", prompt: "Invoke Skill({skill: \\"iru-haiku\\"})"}).'
            ),
        )
        self.skill("iru-haiku", model="haiku")
        self.skill("iru-sonnet", model="sonnet")
        self.agent(
            "iru-agent",
            "---\nname: a\ndescription: d\nmodel: haiku\n---\n"
            'Skill({skill: "iru-nowhere"}) and Skill({skill: "code-review"})',
        )
        data = audit.analyse(self.root, {"external_skills": ["code-review"]})
        self.assertEqual(
            sorted(m["target"] for m in data["missing_skill_targets"]),
            ["iru-ghost", "iru-nowhere"],
        )
        self.assertEqual(data["external_skill_targets"], {"code-review": 2})
        self.assertEqual(len(data["inline_cross_model_calls"]), 2)
        self.assertEqual(
            {c["callee"] for c in data["inline_cross_model_calls"]}, {"iru-haiku"}
        )

    def test_public_view_totals(self):
        self.skill("iru-a", model="haiku")
        self.skill("iru-b", model="opus", description="x" * 2000)
        self.skill("iru-c", model="sonnet", description="Broken: yaml: here")
        self.agent("iru-agent", "---\nname: a\ndescription: d\n---\nbody")
        view = audit.public_view(audit.analyse(self.root))
        totals = view["totals"]
        self.assertEqual(totals["skills"], 3)
        self.assertEqual(totals["agents"], 1)
        self.assertEqual(totals["descriptions_over_1024"], 1)
        self.assertEqual(totals["descriptions_over_1536"], 1)
        self.assertEqual(totals["frontmatter_parse_failures"], 1)
        self.assertEqual(view["models"]["skills"], {"haiku": 1, "opus": 1, "sonnet": 1})
        self.assertEqual(view["models"]["agents"], {"(none)": 1})
        self.assertNotIn("_description", view["skills"]["iru-a"])
        json.dumps(view)


class CheckTests(CatalogTestCase):
    BUDGETS: ClassVar[dict] = {
        "description_max": 100,
        "description_internal_target": 40,
        "invocation_form_within": 50,
        "skill_lines_max": 30,
        "skill_lines_warn": 12,
        "agent_description_max": 60,
        "require_agent_model": True,
        "shared_identical_files": ["ui-contract.md"],
        "internal_skills": ["iru-internal", "iru-ghost"],
        "allowed_models": ["haiku", "sonnet", "opus"],
        "agent_allowed_models": ["haiku", "inherit"],
    }

    def rules(self, budgets=None):
        data = audit.analyse(self.root, budgets or self.BUDGETS)
        violations = audit.run_checks(data, budgets or self.BUDGETS)
        return {(v["level"], v["rule"], v["subject"]) for v in violations}

    def test_clean_catalog_has_no_violations(self):
        self.skill("iru-ok", model="haiku")
        self.agent(
            "iru-agent",
            "---\nname: a\ndescription: Short. Invoke as /a.\nmodel: inherit\n---\nbody",
        )
        self.assertEqual(
            self.rules(),
            {
                ("error", "internal-skill-unknown", "iru-ghost"),
                ("error", "internal-skill-unknown", "iru-internal"),
            },
        )

    def test_skill_violations(self):
        self.skill("iru-long", description="y" * 150)
        self.skill("iru-late", description="z" * 60 + " Invoke as /iru-late")
        self.skill("iru-noform", description="No form here")
        self.skill("iru-internal", description="i" * 60 + " no form")
        self.skill("iru-nomodel", description="d. Invoke as x")
        self.write(
            ".claude/skills/iru-nomodel/SKILL.md",
            "---\nname: iru-nomodel\ndescription: d. Invoke as x\n---\n",
        )
        self.skill("iru-badmodel", model="gpt")
        self.skill("iru-broken", description="Has: a colon")
        self.skill("iru-nodesc", description="''")
        self.skill("iru-lines", body="line\n" * 40)
        self.skill("iru-warnlines", body="line\n" * 10)
        found = self.rules()
        self.assertIn(("error", "description-max", "iru-long"), found)
        self.assertIn(("error", "invocation-form-position", "iru-late"), found)
        self.assertIn(("warning", "invocation-form-missing", "iru-noform"), found)
        self.assertIn(("warning", "description-internal-target", "iru-internal"), found)
        self.assertNotIn(("warning", "invocation-form-missing", "iru-internal"), found)
        self.assertIn(("error", "model-missing", "iru-nomodel"), found)
        self.assertIn(("error", "model-not-allowed", "iru-badmodel"), found)
        self.assertIn(("error", "frontmatter-parse", "iru-broken"), found)
        self.assertIn(("error", "description-missing", "iru-nodesc"), found)
        self.assertIn(("error", "skill-lines-max", "iru-lines"), found)
        self.assertIn(("warning", "skill-lines-warn", "iru-warnlines"), found)

    def test_agent_violations(self):
        self.agent("a-nomodel", "---\nname: a\ndescription: ok\n---\nbody")
        self.agent(
            "b-long",
            "---\nname: b\ndescription: " + "q" * 80 + "\nmodel: haiku\n---\nbody",
        )
        self.agent(
            "c-bad",
            "---\nname: c\ndescription: "
            + "p" * 55
            + " /iru-c\nmodel: opus\n---\nbody",
        )
        self.agent(
            "d-broken", "---\nname: d\ndescription: x: y\nmodel: haiku\n---\nbody"
        )
        found = self.rules()
        self.assertIn(("error", "agent-model-missing", "agent:a-nomodel"), found)
        self.assertIn(("error", "agent-description-max", "agent:b-long"), found)
        self.assertIn(("error", "model-not-allowed", "agent:c-bad"), found)
        self.assertIn(("error", "invocation-form-position", "agent:c-bad"), found)
        self.assertIn(("error", "frontmatter-parse", "agent:d-broken"), found)

    def test_agent_model_not_required(self):
        self.agent("a-nomodel", "---\nname: a\ndescription: ok\n---\nbody")
        budgets = dict(self.BUDGETS, require_agent_model=False)
        self.assertNotIn(
            ("error", "agent-model-missing", "agent:a-nomodel"), self.rules(budgets)
        )

    def test_catalog_wide_violations(self):
        self.skill(
            "iru-a",
            model="sonnet",
            body='`Skill({skill: "iru-b"})` `Skill({skill: "iru-none"})`',
        )
        self.skill("iru-b", model="haiku")
        self.write(".claude/skills/iru-a/reference/ui-contract.md", "one")
        self.write(".claude/skills/iru-b/reference/ui-contract.md", "two")
        found = self.rules()
        self.assertIn(("error", "shared-file-drift", "ui-contract.md"), found)
        self.assertIn(("error", "skill-target-missing", "iru-a"), found)
        self.assertIn(("warning", "inline-cross-model-call", "iru-a"), found)
        escalated = self.rules(dict(self.BUDGETS, inline_cross_model_level="error"))
        self.assertIn(("error", "inline-cross-model-call", "iru-a"), escalated)


class AssetPathTests(CatalogTestCase):
    def violations(self, budgets=None):
        data = audit.analyse(self.root, budgets or {})
        return data, audit.run_checks(data, budgets or {})

    def test_asset_mentions_skips_placeholders_and_foreign_prefixes(self):
        text = (
            "Read `templates/library/build.yml`, reference/ui-contract.md and `reference/<lang>.md`, "
            "templates/*.yml, src/templates/foo.html, .claude/skills/x/reference/a.md and {{templates/x}}."
        )
        self.assertEqual(
            audit.asset_mentions(text),
            ["reference/ui-contract.md", "templates/library/build.yml"],
        )

    def test_existing_template_and_reference_paths_pass(self):
        self.skill(
            "iru-a",
            body="Template: `templates/lib/.github/workflows/build.yml` and `reference/guide.md`.\n",
        )
        self.write(
            ".claude/skills/iru-a/templates/lib/.github/workflows/build.yml",
            "on: push\n",
        )
        self.write(".claude/skills/iru-a/reference/guide.md", "guide\n")
        data, violations = self.violations()
        self.assertEqual(violations, [])
        self.assertEqual(
            data["skills"]["iru-a"]["template_files"],
            ["templates/lib/.github/workflows/build.yml"],
        )
        self.assertEqual(
            data["skills"]["iru-a"]["reference_files"], ["reference/guide.md"]
        )

    def test_missing_template_path_is_an_error(self):
        self.skill("iru-a", body="Template: `templates/lib/build.yml`.\n")
        data, violations = self.violations()
        self.assertEqual(
            data["missing_asset_paths"],
            [{"skill": "iru-a", "path": "templates/lib/build.yml"}],
        )
        self.assertEqual(
            [(v["level"], v["rule"]) for v in violations],
            [("error", "asset-path-missing")],
        )

    def test_unreferenced_template_file_is_an_error(self):
        self.skill("iru-a", body="Nothing about templates.\n")
        self.write(".claude/skills/iru-a/templates/lib/build.yml", "x\n")
        data, violations = self.violations()
        self.assertEqual(
            data["unreferenced_templates"],
            [{"skill": "iru-a", "path": "templates/lib/build.yml"}],
        )
        self.assertEqual([v["rule"] for v in violations], ["template-unreferenced"])

    def test_reference_path_owned_by_a_sibling_skill_is_accepted(self):
        self.skill(
            "iru-a", body="See `reference/ui-contract.md` and `reference/sub`.\n"
        )
        self.skill("iru-b")
        self.write(".claude/skills/iru-b/reference/ui-contract.md", "c\n")
        self.write(".claude/skills/iru-b/reference/sub/x.md", "c\n")
        _, violations = self.violations()
        self.assertEqual(violations, [])
        self.skill("iru-c", body="See `reference/nowhere.md`.\n")
        data, violations = self.violations()
        self.assertEqual(
            data["missing_asset_paths"],
            [{"skill": "iru-c", "path": "reference/nowhere.md"}],
        )

    def test_templates_are_not_accepted_from_a_sibling_skill(self):
        self.skill("iru-a", body="Template: `templates/x/y.yml`.\n")
        self.skill("iru-b", body="Template: `templates/x/y.yml`.\n")
        self.write(".claude/skills/iru-b/templates/x/y.yml", "x\n")
        data, _ = self.violations()
        self.assertEqual(
            data["missing_asset_paths"],
            [{"skill": "iru-a", "path": "templates/x/y.yml"}],
        )

    def test_asset_path_ignore_budget(self):
        self.skill(
            "iru-a", body="Creates `templates/index.html` in the target repository.\n"
        )
        _, violations = self.violations(
            {"asset_path_ignore": {"iru-a": ["templates/index.html"]}}
        )
        self.assertEqual(violations, [])


class AcceptedCrossModelTests(CatalogTestCase):
    def setUp(self):
        super().setUp()
        self.skill(
            "iru-a",
            model="sonnet",
            body='Run `Skill({skill: "iru-b"})` then `Skill({skill: "iru-c"})`.\n',
        )
        self.skill("iru-b", model="opus")
        self.skill("iru-c", model="haiku")

    def test_unaccepted_calls_are_warnings(self):
        data = audit.analyse(self.root, {})
        self.assertEqual(
            [c["callee"] for c in data["inline_cross_model_calls"]], ["iru-b", "iru-c"]
        )
        violations = audit.run_checks(data, {})
        self.assertEqual(
            [v["rule"] for v in violations], ["inline-cross-model-call"] * 2
        )

    def test_accepted_call_is_recorded_not_flagged(self):
        budgets = {
            "accepted_cross_model_calls": [
                {"caller": "iru-a", "callee": "iru-b", "reason": "opus on purpose"}
            ]
        }
        data = audit.analyse(self.root, budgets)
        reasons = {
            c["callee"]: c["accepted_reason"] for c in data["inline_cross_model_calls"]
        }
        self.assertEqual(reasons, {"iru-b": "opus on purpose", "iru-c": None})
        violations = audit.run_checks(data, budgets)
        self.assertEqual(len(violations), 1)
        self.assertIn("iru-c", violations[0]["message"])
        view = audit.public_view(data)
        self.assertEqual(view["totals"]["inline_cross_model_calls_accepted"], 1)
        report = audit.markdown_report(data)
        self.assertIn("1 recorded as accepted", report)
        self.assertIn("accepted: opus on purpose", report)
        self.assertIn("| open |", report)


GOOD_PLAN = """# Implementation plan

## Task summary

Open clarifications: none

## Acceptance criteria coverage

| # | Criterion | Covered by tasks |
|---|---|---|
| 1 | "Users can log in" | Task 1, Task 2.1 |
| 2 | derived: errors are reported | Task 3 |

## Current code state

text
"""


class PlanShapeTests(CatalogTestCase):
    def rules(self, text):
        return sorted(v["rule"] for v in audit.check_plan(text))

    def test_good_plan_has_no_violations(self):
        self.assertEqual(audit.check_plan(GOOD_PLAN), [])

    def test_missing_coverage_section(self):
        self.assertEqual(
            self.rules("# Plan\n\n## Task summary\n\nOpen clarifications: none\n"),
            ["plan-coverage-missing"],
        )

    def test_heading_level_and_case_are_flexible(self):
        self.assertEqual(
            self.rules(
                GOOD_PLAN.replace(
                    "## Acceptance criteria coverage",
                    "### acceptance Criteria Coverage",
                )
            ),
            [],
        )

    def test_empty_coverage_section(self):
        text = "## Acceptance criteria coverage\n\n| # | Criterion | Covered by tasks |\n|---|---|---|\n\n## Next\n"
        self.assertEqual(self.rules(text), ["plan-coverage-empty"])
        self.assertEqual(
            self.rules("## Acceptance criteria coverage\n\nnothing here\n"),
            ["plan-coverage-empty"],
        )

    def test_uncovered_row(self):
        text = GOOD_PLAN.replace(
            "| 2 | derived: errors are reported | Task 3 |", "| 2 | derived: errors | |"
        )
        violations = audit.check_plan(text)
        self.assertEqual([v["rule"] for v in violations], ["plan-coverage-uncovered"])
        self.assertIn("criterion 2", violations[0]["message"])
        short = GOOD_PLAN.replace(
            "| 2 | derived: errors are reported | Task 3 |", "| 2 | derived: errors |"
        )
        self.assertEqual(self.rules(short), ["plan-coverage-uncovered"])

    def test_rows_after_the_section_do_not_count(self):
        text = (
            "## Acceptance criteria coverage\n\n| # | C | T |\n|---|---|---|\n\n## Other\n\n"
            "| 1 | x | Task 1 |\n"
        )
        self.assertEqual(self.rules(text), ["plan-coverage-empty"])

    def test_open_marker_is_reported_with_its_line(self):
        text = (
            GOOD_PLAN
            + "- [ ] Task 1 [NEEDS CLARIFICATION: which db? \u2014 options: a | b; recommended: a]\n"
        )
        violations = audit.check_plan(text)
        self.assertEqual([v["rule"] for v in violations], ["plan-clarification-open"])
        self.assertIn(
            "line {}".format(len(GOOD_PLAN.split("\n"))), violations[0]["message"]
        )

    def test_markers_in_code_spans_and_fences_are_ignored(self):
        text = (
            GOOD_PLAN + "The `[NEEDS CLARIFICATION: x]` marker is documented here.\n\n"
            "```\n[NEEDS CLARIFICATION: y]\n```\n\n~~~~\n[NEEDS CLARIFICATION: z]\n```\n~~~~\n"
        )
        self.assertEqual(audit.check_plan(text), [])

    def test_missing_section_and_marker_are_both_reported(self):
        self.assertEqual(
            self.rules("[NEEDS CLARIFICATION: q]\n"),
            ["plan-clarification-open", "plan-coverage-missing"],
        )

    def test_plan_cli_exit_codes(self):
        good = self.write("good/implementation_plan.md", GOOD_PLAN)
        code, _, err = self.run_main("--plan", good)
        self.assertEqual(code, 0)
        self.assertIn("0 violation(s)", err)
        bad = self.write(
            "bad/implementation_plan.md", "# Plan\n[NEEDS CLARIFICATION: q]\n"
        )
        code, _, err = self.run_main("--plan", bad)
        self.assertEqual(code, 1)
        self.assertIn("ERROR [plan-coverage-missing]", err)
        self.assertIn("ERROR [plan-clarification-open]", err)
        code, _, err = self.run_main("--plan", os.path.join(self.root, "absent.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read plan", err)

    def test_plan_combined_with_check(self):
        self.skill("iru-a", model="haiku")
        budgets = self.write(
            "budgets.json",
            json.dumps(
                {
                    "description_max": 1024,
                    "shared_identical_files": [],
                    "internal_skills": [],
                }
            ),
        )
        good = self.write("good.md", GOOD_PLAN)
        bad = self.write("bad.md", "# Plan\n")
        code, _, err = self.run_main(
            "--root", self.root, "--check", "--budgets", budgets, "--plan", good
        )
        self.assertEqual(code, 0)
        self.assertIn("0 error(s)", err)
        code, _, err = self.run_main(
            "--root", self.root, "--check", "--budgets", budgets, "--plan", bad
        )
        self.assertEqual(code, 1)
        self.skill("iru-b", description="x" * 2000)
        code, _, _ = self.run_main(
            "--root", self.root, "--check", "--budgets", budgets, "--plan", good
        )
        self.assertEqual(code, 1)
        code, _, _ = self.run_main(
            "--root", self.root, "--markdown", "--budgets", budgets, "--plan", bad
        )
        self.assertEqual(code, 1)


class MainTests(CatalogTestCase):
    def budgets_file(self, **overrides):
        budgets = {
            "description_max": 1024,
            "shared_identical_files": [],
            "internal_skills": [],
        }
        budgets.update(overrides)
        return self.write("budgets.json", json.dumps(budgets))

    def test_requires_a_mode(self):
        code, _, err = self.run_main("--root", self.root)
        self.assertEqual(code, 2)
        self.assertIn("choose at least one", err)

    def test_json_and_markdown_outputs(self):
        self.skill("iru-a", model="haiku")
        self.agent("iru-agent", "---\nname: a\ndescription: d\nmodel: haiku\n---\nbody")
        target = os.path.join(self.root, "out", "audit.json")
        code, out, _ = self.run_main(
            "--root",
            self.root,
            "--json",
            target,
            "--markdown",
            "--budgets",
            self.budgets_file(),
        )
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["totals"]["skills"], 1)
        for heading in (
            "## Totals",
            "## Top 20 skills by size",
            "## Top 20 descriptions by length",
            "## Models",
            "## Duplicate supporting files",
            "## Inline cross-model",
            "## Missing `Skill()` targets",
            "## Frontmatter parse failures",
        ):
            self.assertIn(heading, out)
        _code2, out2, _ = self.run_main(
            "--root", self.root, "--markdown", "--budgets", self.budgets_file()
        )
        self.assertEqual(out, out2)

    def test_markdown_lists_problems(self):
        self.skill(
            "iru-a",
            model="sonnet",
            body='`Skill({skill: "iru-b"})` `Skill({skill: "iru-ghost"})`'
            ' `Skill({skill: "code-review"})`',
        )
        self.skill("iru-b", model="haiku")
        self.skill("iru-broken", description="Has: a colon")
        for name in ("iru-a", "iru-b"):
            self.write(f".claude/skills/{name}/reference/dup.md", "same bytes")
        budgets = self.budgets_file(
            external_skills=["code-review"], shared_identical_files=["dup.md"]
        )
        _, out, _ = self.run_main(
            "--root", self.root, "--markdown", "--budgets", budgets
        )
        self.assertIn("iru-ghost", out)
        self.assertIn("`code-review` (1)", out)
        self.assertIn("| iru-a | sonnet | iru-b | haiku |", out)
        self.assertIn("iru-broken", out)
        self.assertIn("dup.md", out)

    def test_check_exit_codes(self):
        self.skill("iru-a", model="haiku")
        budgets = self.budgets_file()
        code, _, err = self.run_main(
            "--root", self.root, "--check", "--budgets", budgets
        )
        self.assertEqual(code, 0)
        self.assertIn("0 error(s)", err)
        self.skill("iru-b", description="x" * 2000)
        code, _, err = self.run_main(
            "--root", self.root, "--check", "--budgets", budgets
        )
        self.assertEqual(code, 1)
        self.assertIn("ERROR [description-max] iru-b", err)

    def test_check_with_missing_budgets_file_fails_but_other_modes_use_defaults(self):
        self.skill("iru-a")
        missing = os.path.join(self.root, "nope.json")
        code, _, err = self.run_main(
            "--root", self.root, "--check", "--budgets", missing
        )
        self.assertEqual(code, 2)
        self.assertIn("cannot read budgets file", err)
        code, out, _ = self.run_main(
            "--root", self.root, "--markdown", "--budgets", missing
        )
        self.assertEqual(code, 0)
        self.assertIn("# Catalog audit", out)

    def test_this_repository_budgets_file_is_valid(self):
        with open(
            os.path.join(TOOLS_DIR, "catalog-budgets.json"), encoding="utf-8"
        ) as handle:
            budgets = json.load(handle)
        self.assertEqual(budgets["description_max"], 1024)
        self.assertEqual(
            sorted(budgets["shared_identical_files"]),
            [
                "accessibility-detection.md",
                "cli-contract.md",
                "ui-contract.md",
                "ui-docs.md",
            ],
        )
        self.assertEqual(budgets["internal_skills"], sorted(budgets["internal_skills"]))
        repo = os.path.dirname(TOOLS_DIR)
        for name in budgets["internal_skills"]:
            self.assertTrue(
                os.path.isfile(
                    os.path.join(repo, ".claude", "skills", name, "SKILL.md")
                ),
                name,
            )


if __name__ == "__main__":
    unittest.main()
