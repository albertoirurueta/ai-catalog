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
"""Unit tests for tools/build-packages.py. Run with: python3 -m unittest discover -s tools/tests"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("build_packages", TOOLS_DIR / "build-packages.py")
bp = importlib.util.module_from_spec(_SPEC)
sys.modules["build_packages"] = bp
_SPEC.loader.exec_module(bp)

PLUGINS = {
    "marketplace": {"name": "m"},
    "plugins": [
        {"name": "iru-core", "skills": ["iru-plan", "iru-code"], "agents": ["iru-gate-runner"]},
        {"name": "iru-java", "skills": ["iru-java-*"], "exclude": ["iru-java-skip"]},
        {"name": "iru-other", "skills": ["iru-skip-*", "iru-java-skip"]},
    ],
}


def make_repo(root, plugins=PLUGINS):
    (root / "tools").mkdir(parents=True)
    (root / "tools" / "plugins.json").write_text(json.dumps(plugins), encoding="utf-8")
    skills = ["iru-plan", "iru-code", "iru-java-test", "iru-java-skip", "iru-skip-x"]
    for name in skills:
        directory = root / ".claude" / "skills" / name / "templates"
        directory.mkdir(parents=True)
        (directory.parent / "SKILL.md").write_text(f"skill {name}\n", encoding="utf-8")
        (directory / "t.txt").write_text("t\n", encoding="utf-8")
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "iru-gate-runner.md").write_text("agent\n", encoding="utf-8")


def names(path):
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


class BuildPackagesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.out = Path(self._tmp.name) / "out"
        make_repo(self.root)

    def test_full_zip_layout(self):
        bp.build(self.root, self.out)
        listing = names(self.out / bp.FULL_ZIP)
        self.assertEqual(listing, sorted(listing))
        self.assertIn("skills/iru-plan/SKILL.md", listing)
        self.assertIn("skills/iru-java-test/templates/t.txt", listing)
        self.assertIn("agents/iru-gate-runner.md", listing)
        self.assertFalse(any(n.startswith(".claude") for n in listing))

    def test_plugin_membership_with_exclude(self):
        bp.build(self.root, self.out)
        java = names(self.out / "iru-java.zip")
        self.assertIn("skills/iru-java-test/SKILL.md", java)
        self.assertFalse(any("iru-java-skip" in n for n in java))
        self.assertTrue(any("iru-java-skip" in n for n in names(self.out / "iru-other.zip")))

    def test_agents_routed_to_core_only(self):
        bp.build(self.root, self.out)
        self.assertIn("agents/iru-gate-runner.md", names(self.out / "iru-core.zip"))
        self.assertFalse(any(n.startswith("agents/") for n in names(self.out / "iru-java.zip")))

    def test_deterministic(self):
        other = Path(self._tmp.name) / "out2"
        bp.build(self.root, self.out)
        bp.build(self.root, other)
        for path in self.out.glob("*.zip"):
            self.assertEqual(path.read_bytes(), (other / path.name).read_bytes())
        with zipfile.ZipFile(self.out / bp.FULL_ZIP) as archive:
            self.assertTrue(all(i.date_time == bp.FIXED_TIME for i in archive.infolist()))

    def test_empty_pattern_fails(self):
        bad = json.loads(json.dumps(PLUGINS))
        bad["plugins"][1]["skills"].append("nothing-*")
        (self.root / "tools" / "plugins.json").write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(bp.BuildError) as ctx:
            bp.build(self.root, self.out)
        self.assertIn("nothing-*", str(ctx.exception))

    def test_missing_agent_fails_via_cli(self):
        bad = json.loads(json.dumps(PLUGINS))
        bad["plugins"][0]["agents"].append("ghost")
        (self.root / "tools" / "plugins.json").write_text(json.dumps(bad), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = bp.main(["--root", str(self.root), "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("ghost", err.getvalue())

    def test_partial_content_and_cli_success(self):
        partial = Path(self._tmp.name) / "p" / "plugins.adoc"
        with contextlib.redirect_stdout(io.StringIO()):
            code = bp.main(["--root", str(self.root), "--out", str(self.out), "--partial", str(partial)])
        self.assertEqual(code, 0)
        text = partial.read_text(encoding="utf-8")
        self.assertIn(
            'image:download-zip-compact.svg["Download iru-java (zip)",width=110,xref=attachment$iru-java.zip]',
            text,
        )
        self.assertIn("|`iru-core` |2 |1 |", text)

    def test_size_format(self):
        self.assertEqual(bp.format_size(10), "1 KiB")
        self.assertEqual(bp.format_size(3 * 1024 * 1024), "3.0 MiB")

    def test_missing_dirs(self):
        self.assertEqual(bp.list_skills(Path(self._tmp.name) / "none"), [])
        self.assertEqual(bp.list_agents(Path(self._tmp.name) / "none"), [])


class EquivalenceTest(unittest.TestCase):
    def test_membership_matches_marketplace_resolution(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml is not installed")
        spec = importlib.util.spec_from_file_location("gm", TOOLS_DIR / "generate-marketplace.py")
        gm = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("gm", gm)
        spec.loader.exec_module(gm)
        root = TOOLS_DIR.parent
        plugins = json.loads((TOOLS_DIR / "plugins.json").read_text(encoding="utf-8"))["plugins"]
        skills, agents = bp.list_skills(root), bp.list_agents(root)
        expected_skills = gm.resolve_skills(plugins, skills)
        expected_agents = gm.resolve_agents(plugins, agents)
        for plugin in plugins:
            got_skills, got_agents, problems = bp.resolve_plugin(plugin, skills, agents)
            self.assertEqual(problems, [])
            self.assertEqual(got_skills, expected_skills[plugin["name"]])
            self.assertEqual(got_agents, expected_agents[plugin["name"]])





class BuildHygieneTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.out = Path(self._tmp.name) / "out"
        make_repo(self.root)

    def test_stale_zips_removed(self):
        self.out.mkdir(parents=True)
        (self.out / "iru-renamed.zip").write_bytes(b"old")
        (self.out / "keep.txt").write_text("x", encoding="utf-8")
        bp.build(self.root, self.out)
        self.assertFalse((self.out / "iru-renamed.zip").exists())
        self.assertTrue((self.out / "keep.txt").exists())

    def test_modes_are_regular_files_and_keep_executable_bit(self):
        script = self.root / ".claude" / "skills" / "iru-plan" / "templates" / "run.sh"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        os.chmod(script, 0o755)
        bp.build(self.root, self.out)
        with zipfile.ZipFile(self.out / bp.FULL_ZIP) as archive:
            modes = {info.filename: info.external_attr >> 16 for info in archive.infolist()}
        self.assertEqual(modes["skills/iru-plan/templates/run.sh"], 0o100755)
        self.assertEqual(modes["skills/iru-plan/SKILL.md"], 0o100644)

    def test_local_junk_excluded_without_git(self):
        skill = self.root / ".claude" / "skills" / "iru-plan"
        (skill / ".DS_Store").write_bytes(b"junk")
        (skill / "__pycache__").mkdir()
        (skill / "__pycache__" / "x.pyc").write_bytes(b"junk")
        bp.build(self.root, self.out)
        listing = names(self.out / bp.FULL_ZIP)
        self.assertFalse(any(".DS_Store" in n or "__pycache__" in n for n in listing))
        self.assertIn("skills/iru-plan/SKILL.md", listing)

    def test_git_ignored_files_excluded(self):
        try:
            subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        (self.root / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (self.root / ".claude" / "skills" / "iru-plan" / "debug.log").write_text("x", encoding="utf-8")
        bp.build(self.root, self.out)
        listing = names(self.out / bp.FULL_ZIP)
        self.assertNotIn("skills/iru-plan/debug.log", listing)
        self.assertIn("skills/iru-plan/templates/t.txt", listing)

if __name__ == "__main__":
    unittest.main()
