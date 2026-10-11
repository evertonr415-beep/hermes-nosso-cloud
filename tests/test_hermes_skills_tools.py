"""Regression tests for read-only Hermes skill inventory/view tools."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name("hermes-light-agent.py")
SPEC = importlib.util.spec_from_file_location("hermes_light_agent", SOURCE)
AGENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGENT)


class SkillsToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        skill = self.root / "sample-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: Sample Skill\ndescription: Test skill metadata\n---\n\nBody text.\n",
            encoding="utf-8",
        )
        os.environ["HERMES_SKILLS_ROOT"] = str(self.root)
        self.addCleanup(os.environ.pop, "HERMES_SKILLS_ROOT", None)

    def call_tool(self, name, args):
        return AGENT.run_tool(name, json.dumps(args))

    def test_list_and_metadata(self):
        result = self.call_tool("skills_list", {})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["skills"][0]["skill_id"], "sample-skill")
        self.assertEqual(result["skills"][0]["name"], "Sample Skill")

    def test_filter_and_view(self):
        result = self.call_tool("skills_list", {"query": "metadata"})
        self.assertEqual(result["count"], 1)
        view = self.call_tool("skill_view", {"skill_id": "sample-skill"})
        self.assertIn("Body text.", view["content"])

    def test_path_traversal_rejected(self):
        result = self.call_tool("skill_view", {"skill_id": "../outside"})
        self.assertEqual(result["error"], "invalid_skill_id")

    def test_symlinked_skill_is_not_listed(self):
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir(exist_ok=True)
        (outside / "SKILL.md").write_text("secret-ish test fixture", encoding="utf-8")
        link = self.root / "linked-skill"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this platform")
        result = self.call_tool("skills_list", {})
        self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
