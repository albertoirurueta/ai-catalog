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
"""Unit tests for tools/generate-marketplace.py. Run with: python3 -m unittest discover -s tools/tests"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
_SPEC = importlib.util.spec_from_file_location(
    "generate_marketplace", os.path.join(TOOLS_DIR, "generate-marketplace.py")
)
gen = importlib.util.module_from_spec(_SPEC)
sys.modules["generate_marketplace"] = gen
_SPEC.loader.exec_module(gen)

OWNER = {"name": "Test Owner", "email": "owner@example.com"}


def skill_text(name, body=""):
    return f"---\nname: {name}\ndescription: Does {name}. Invoke as `/{name}`.\nmodel: sonnet\n---\n\n# {name}\n\n{body}"


def membership(**overrides):
    base = {
        "marketplace": {
            "name": "demo",
            "description": "Demo marketplace",
            "root_plugin": "demo-core",
        },
        "plugins": [
            {
                "name": "demo-core",
                "category": "core",
                "description": "Core",
                "skills": ["demo-main"],
                "agents": ["demo-agent"],
            },
            {
                "name": "demo-java",
                "category": "stack",
                "description": "Java",
                "skills": ["demo-java-*"],
            },
            {
                "name": "demo-spring",
                "category": "stack",
                "description": "Spring",
                "skills": ["demo-spring-*"],
                "depends_on": ["demo-java"],
            },
        ],
    }
    base.update(overrides)
    return base


class MarketplaceTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="generate-marketplace-test-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.membership_path = os.path.join(self.root, "plugins.json")

    def write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def skill(self, name, body=""):
        return self.write(f".claude/skills/{name}/SKILL.md", skill_text(name, body))

    def agent(self, name):
        return self.write(
            f".claude/agents/{name}.md",
            f"---\nname: {name}\ndescription: An agent.\nmodel: haiku\n---\n\nBody\n",
        )

    def save_membership(self, data):
        with open(self.membership_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def standard_tree(self):
        self.skill("demo-main")
        self.skill("demo-java-test")
        self.skill("demo-spring-code")
        self.agent("demo-agent")
        self.save_membership(membership())

    def run_main(self, *argv, validate=None):
        out, err = io.StringIO(), io.StringIO()
        extra = {} if validate is None else {"validate": validate}
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = gen.main(
                [
                    "--root",
                    self.root,
                    "--membership",
                    self.membership_path,
                    "--budgets",
                    os.path.join(self.root, "none.json"),
                    *argv,
                ],
                **extra,
            )
        return status, out.getvalue(), err.getvalue()


class ResolveSkillsTests(MarketplaceTestCase):
    def test_each_skill_in_exactly_one_plugin(self):
        plugins = membership()["plugins"]
        members = gen.resolve_skills(
            plugins, ["demo-main", "demo-java-test", "demo-spring-code"]
        )
        self.assertEqual(
            members,
            {
                "demo-core": ["demo-main"],
                "demo-java": ["demo-java-test"],
                "demo-spring": ["demo-spring-code"],
            },
        )

    def test_exclude_removes_a_match(self):
        plugins = [
            {"name": "a", "skills": ["x-*"], "exclude": ["x-b"]},
            {"name": "b", "skills": ["x-b"]},
        ]
        members = gen.resolve_skills(plugins, ["x-a", "x-b"])
        self.assertEqual(members, {"a": ["x-a"], "b": ["x-b"]})

    def test_unlisted_skill_fails(self):
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.resolve_skills(
                membership()["plugins"],
                ["demo-main", "demo-java-test", "demo-spring-code", "orphan"],
            )
        self.assertEqual(
            ctx.exception.problems, ["skill orphan is not listed in any plugin"]
        )

    def test_skill_in_two_plugins_fails(self):
        plugins = [{"name": "a", "skills": ["x"]}, {"name": "b", "skills": ["x"]}]
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.resolve_skills(plugins, ["x"])
        self.assertIn("several plugins: a, b", ctx.exception.problems[0])

    def test_pattern_matching_nothing_fails(self):
        plugins = [{"name": "a", "skills": ["x", "ghost-*"]}]
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.resolve_skills(plugins, ["x"])
        self.assertIn("'ghost-*' matches no skill", ctx.exception.problems[0])


class ResolveAgentsTests(MarketplaceTestCase):
    def test_agents_resolved(self):
        members = gen.resolve_agents(membership()["plugins"], ["demo-agent"])
        self.assertEqual(members["demo-core"], ["demo-agent"])
        self.assertEqual(members["demo-java"], [])

    def test_missing_unlisted_and_duplicate_agents_fail(self):
        plugins = [
            {"name": "a", "agents": ["gone", "dup"]},
            {"name": "b", "agents": ["dup"]},
        ]
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.resolve_agents(plugins, ["dup", "unlisted"])
        text = "\n".join(ctx.exception.problems)
        self.assertIn("'gone' does not exist", text)
        self.assertIn("unlisted is not listed", text)
        self.assertIn("dup is listed in several plugins", text)


class DependencyTests(MarketplaceTestCase):
    def test_dependency_map_adds_root_plugin(self):
        deps = gen.dependency_map(membership()["plugins"], "demo-core")
        self.assertEqual(
            deps,
            {
                "demo-core": [],
                "demo-java": ["demo-core"],
                "demo-spring": ["demo-core", "demo-java"],
            },
        )

    def test_declared_root_dependency_is_not_duplicated(self):
        plugins = [{"name": "core"}, {"name": "x", "depends_on": ["core"]}]
        self.assertEqual(gen.dependency_map(plugins, "core")["x"], ["core"])

    def test_cycle_detected(self):
        self.assertEqual(
            gen.find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}), ["a", "b", "c", "a"]
        )
        self.assertIsNone(gen.find_cycle({"a": ["b"], "b": [], "c": ["a", "b"]}))

    def test_call_without_dependency_fails(self):
        self.skill("demo-main")
        self.skill("demo-java-test")
        self.skill("demo-spring-code", body='Skill({skill: "demo-java-test"})')
        self.agent("demo-agent")
        data = membership()
        data["plugins"][2].pop("depends_on")
        self.save_membership(data)
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.generate(self.root, self.membership_path, owner=OWNER)
        self.assertIn(
            "demo-spring-code (demo-spring) calls demo-java-test (demo-java)",
            ctx.exception.problems[0],
        )

    def test_call_with_dependency_passes_and_is_reported(self):
        self.skill("demo-main")
        self.skill("demo-java-test")
        self.skill("demo-spring-code", body='Skill({skill: "demo-java-test"})')
        self.agent("demo-agent")
        self.save_membership(membership())
        document, _text, report = gen.generate(
            self.root, self.membership_path, owner=OWNER
        )
        self.assertEqual(report["cross_plugin_edges"], {"demo-spring -> demo-java": 1})
        self.assertEqual(
            document["plugins"][2]["dependencies"], ["demo-core", "demo-java"]
        )

    def test_optional_call_is_allowed_without_dependency(self):
        self.skill("demo-main", body='Skill({skill: "demo-java-test"})')
        self.skill("demo-java-test")
        self.skill("demo-spring-code")
        self.agent("demo-agent")
        data = membership()
        data["optional_calls"] = [
            {"from": "demo-core", "to": "*", "reason": "front door"}
        ]
        self.save_membership(data)
        document, _text, _report = gen.generate(
            self.root, self.membership_path, owner=OWNER
        )
        self.assertNotIn("dependencies", document["plugins"][0])

    def test_optional_call_for_other_target_does_not_cover(self):
        self.assertFalse(gen.optional_covers([{"from": "a", "to": "b"}], "a", "c"))
        self.assertTrue(gen.optional_covers([{"from": "a", "to": "b"}], "a", "b"))

    def test_unknown_dependency_and_cycle_fail(self):
        plugins = [{"name": "a"}, {"name": "b"}]
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.check_dependencies(plugins, {"a": ["zzz"], "b": []}, {}, [])
        self.assertIn("unknown plugin zzz", ctx.exception.problems[0])
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.check_dependencies(plugins, {"a": ["b"], "b": ["a"]}, {}, [])
        self.assertIn("dependency cycle: a -> b -> a", ctx.exception.problems[0])

    def test_dynamic_and_external_calls_are_ignored(self):
        self.skill(
            "demo-main",
            body='Skill({skill: "<key>-code"}) and Skill({skill: "code-review"})',
        )
        self.skill("demo-java-test")
        self.skill("demo-spring-code")
        self.agent("demo-agent")
        self.save_membership(membership())
        _doc, _text, report = gen.generate(self.root, self.membership_path, owner=OWNER)
        self.assertEqual(report["cross_plugin_edges"], {})


class ChangelogVersionTests(MarketplaceTestCase):
    def test_latest_released_heading(self):
        path = self.write(
            "CHANGELOG.md",
            "# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n\n## [1.0.0]\n",
        )
        self.assertEqual(gen.changelog_version(path), "1.2.3")

    def test_unreleased_only_or_missing_file(self):
        path = self.write("CHANGELOG.md", "## [Unreleased]\n")
        self.assertIsNone(gen.changelog_version(path))
        self.assertIsNone(gen.changelog_version(os.path.join(self.root, "nope.md")))


class OwnerTests(MarketplaceTestCase):
    def test_owner_from_git_config(self):
        values = {"user.name": "Git Name", "user.email": "git@example.com"}
        with mock.patch.object(
            gen, "run_quiet", side_effect=lambda cmd, cwd=None: values.get(cmd[-1])
        ):
            self.assertEqual(
                gen.owner_from_environment(self.root),
                {"name": "Git Name", "email": "git@example.com"},
            )

    def test_owner_name_without_email(self):
        with mock.patch.object(
            gen,
            "run_quiet",
            side_effect=lambda cmd, cwd=None: (
                "Only Name" if cmd[-1] == "user.name" else None
            ),
        ):
            self.assertEqual(
                gen.owner_from_environment(self.root), {"name": "Only Name"}
            )

    def test_owner_from_gh_then_existing(self):
        with (
            mock.patch.object(
                gen,
                "run_quiet",
                side_effect=lambda cmd, cwd=None: "ghuser" if cmd[0] == "gh" else None,
            ),
            mock.patch.object(gen.shutil, "which", return_value="/usr/bin/gh"),
        ):
            self.assertEqual(gen.owner_from_environment(self.root), {"name": "ghuser"})
        with (
            mock.patch.object(gen, "run_quiet", return_value=None),
            mock.patch.object(gen.shutil, "which", return_value=None),
        ):
            self.assertEqual(
                gen.owner_from_environment(self.root, {"owner": {"name": "Old"}}),
                {"name": "Old"},
            )
            with self.assertRaises(gen.GenerationError):
                gen.owner_from_environment(self.root)

    def test_run_quiet(self):
        self.assertEqual(gen.run_quiet([sys.executable, "-c", "print('hi')"]), "hi")
        self.assertIsNone(
            gen.run_quiet([sys.executable, "-c", "import sys; sys.exit(3)"])
        )
        self.assertIsNone(gen.run_quiet(["definitely-not-a-command-xyz"]))


class BuildAndMainTests(MarketplaceTestCase):
    def test_document_shape(self):
        self.standard_tree()
        self.write("CHANGELOG.md", "## [Unreleased]\n\n## [2.0.0] - 2026-02-02\n")
        document, text, report = gen.generate(
            self.root, self.membership_path, owner=OWNER
        )
        self.assertEqual(document["name"], "demo")
        self.assertEqual(document["owner"], OWNER)
        self.assertEqual(document["metadata"], {"version": "2.0.0"})
        core = document["plugins"][0]
        self.assertEqual(core["source"], "./")
        self.assertFalse(core["strict"])
        self.assertEqual(core["version"], "2.0.0")
        self.assertEqual(core["skills"], ["./.claude/skills/demo-main"])
        self.assertEqual(core["agents"], ["./.claude/agents/demo-agent.md"])
        self.assertNotIn("dependencies", core)
        self.assertEqual(document["plugins"][1]["dependencies"], ["demo-core"])
        self.assertNotIn("agents", document["plugins"][1])
        self.assertTrue(text.endswith("}\n"))
        self.assertEqual(
            report["skills"], {"demo-core": 1, "demo-java": 1, "demo-spring": 1}
        )
        self.assertEqual(report["agents"], {"demo-core": 1})

    def test_no_version_when_changelog_has_no_release(self):
        self.standard_tree()
        document, _text, _report = gen.generate(
            self.root, self.membership_path, owner=OWNER
        )
        self.assertNotIn("metadata", document)
        self.assertNotIn("version", document["plugins"][0])

    def test_write_then_check_roundtrip(self):
        self.standard_tree()
        status, out, _err = self.run_main("--owner", "Test Owner")
        self.assertEqual(status, 0)
        self.assertIn(
            "wrote .claude-plugin/marketplace.json (3 plugins, 3 skills)", out
        )
        status, out, _err = self.run_main("--check", "--no-validate")
        self.assertEqual(status, 0)
        self.assertIn("up to date (3 plugins)", out)

    def test_check_uses_committed_owner(self):
        self.standard_tree()
        self.run_main("--owner", "Someone Else")
        with mock.patch.object(
            gen,
            "owner_from_environment",
            side_effect=AssertionError("must not be called"),
        ):
            status, _out, _err = self.run_main("--check", "--no-validate")
        self.assertEqual(status, 0)

    def test_check_fails_when_stale_or_missing(self):
        self.standard_tree()
        status, _out, err = self.run_main("--check", "--no-validate", "--owner", "X")
        self.assertEqual(status, 1)
        self.assertIn("is missing", err)
        self.run_main("--owner", "X")
        self.skill("demo-java-extra")
        status, _out, err = self.run_main("--check", "--no-validate", "--owner", "X")
        self.assertEqual(status, 1)
        self.assertIn("is stale", err)

    def test_check_ignores_the_release_version(self):
        self.standard_tree()
        self.write("CHANGELOG.md", "## [Unreleased]\n\n## [2.0.0] - 2026-02-02\n")
        self.run_main("--owner", "X")
        self.write("CHANGELOG.md", "## [Unreleased]\n\n## [2.1.0] - 2026-03-03\n\n## [2.0.0] - 2026-02-02\n")
        status, out, err = self.run_main("--check", "--no-validate", "--owner", "X")
        self.assertEqual(status, 0)
        self.assertIn("up to date", out)
        self.assertIn("only the release version differs", err)
        self.assertIn("2.0.0", err)
        self.assertIn("2.1.0", err)
        self.assertEqual(
            gen.without_version({"metadata": {"version": "1"}, "plugins": [{"name": "p", "version": "1"}]}),
            {"plugins": [{"name": "p"}]},
        )

    def test_generation_problems_exit_one(self):
        self.standard_tree()
        self.skill("orphan")
        status, _out, err = self.run_main("--owner", "X")
        self.assertEqual(status, 1)
        self.assertIn("ERROR skill orphan is not listed in any plugin", err)
        self.assertIn("1 problem(s)", err)

    def test_check_runs_validate_when_available(self):
        self.standard_tree()
        self.run_main("--owner", "X")
        calls = []

        def ok(root):
            calls.append(root)
            return True, True, ""

        status, _out, _err = self.run_main("--check", validate=ok)
        self.assertEqual((status, calls), (0, [self.root]))

        status, _out, err = self.run_main(
            "--check", validate=lambda root: (True, False, "bad manifest")
        )
        self.assertEqual(status, 1)
        self.assertIn("bad manifest", err)

        status, _out, err = self.run_main(
            "--check", validate=lambda root: (False, True, "")
        )
        self.assertEqual(status, 0)
        self.assertIn("skipped", err)

    def test_unreadable_existing_marketplace_is_ignored(self):
        self.standard_tree()
        self.write(".claude-plugin/marketplace.json", "{not json")
        document, _text, _report = gen.generate(
            self.root, self.membership_path, owner=OWNER
        )
        self.assertEqual(document["owner"], OWNER)

    def test_missing_membership_keys(self):
        self.save_membership({"plugins": []})
        with self.assertRaises(gen.GenerationError):
            gen.load_membership(self.membership_path)


class ValidateWithCliTests(unittest.TestCase):
    def test_cli_absent(self):
        self.assertEqual(
            gen.validate_with_cli("/x", which=lambda name: None), (False, True, "")
        )

    def test_cli_success_and_failure(self):
        def runner(code):
            return lambda *a, **k: subprocess.CompletedProcess(a[0], code, stdout="out")

        self.assertEqual(
            gen.validate_with_cli("/x", run=runner(0), which=lambda n: "/bin/claude"),
            (True, True, "out"),
        )
        self.assertEqual(
            gen.validate_with_cli("/x", run=runner(1), which=lambda n: "/bin/claude"),
            (True, False, "out"),
        )

    def test_cli_error(self):
        def boom(*a, **k):
            raise OSError("cannot exec")

        ran, ok, output = gen.validate_with_cli(
            "/x", run=boom, which=lambda n: "/bin/claude"
        )
        self.assertEqual((ran, ok), (True, False))
        self.assertIn("cannot exec", output)


class RealCatalogTests(unittest.TestCase):
    """The committed membership map must cover this very repository and match the committed marketplace.json."""

    def test_committed_marketplace_is_current(self):
        document, text, _report = gen.generate(REPO_ROOT, use_committed_owner=True)
        with open(
            os.path.join(REPO_ROOT, gen.MARKETPLACE_REL), encoding="utf-8"
        ) as handle:
            self.assertEqual(
                handle.read(), text, "run python3 tools/generate-marketplace.py"
            )
        skills = [s for plugin in document["plugins"] for s in plugin["skills"]]
        self.assertEqual(len(skills), len(set(skills)))
        self.assertEqual(
            len(skills), len(os.listdir(os.path.join(REPO_ROOT, ".claude", "skills")))
        )


if __name__ == "__main__":
    unittest.main()
