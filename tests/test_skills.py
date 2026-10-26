"""Text checks for the economy customizations (C-001, C-002, C-003)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
ADAPTER = ROOT / "docs" / "harness" / "claude-code.md"


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def table_patterns(text: str, heading: str) -> list[str]:
    body = text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in body.splitlines() if line.startswith("| ") and not line.startswith("| Pattern")]
    return [row.split("|")[1].strip() for row in rows if not set(row) <= set("|- ")]


class EconomySkillTest(unittest.TestCase):
    def test_sections(self):
        text = skill("pstack-economy")
        for heading in ("## Duplicated and divided work", "## Lean widths", "## Going wide", "## Routing",
                        "## Audit tick"):
            self.assertIn(heading, text)

    def test_lean_table_matches_hermes(self):
        self.assertEqual(table_patterns(skill("pstack-economy"), "Lean widths"), [
            "swarm, coverage slices", "swarm, races and best-of", "architect", "arena", "interrogate",
            "reflect, why, how, poteto-mode subagents", "live verification", "autopilot audit tick",
            "second-opinion Codex runs (`/codex:review`, `/codex:rescue`)"])

    def test_routing_rule(self):
        routing = skill("pstack-economy").split("## Routing\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("both families", routing)
        self.assertIn("family that did not write", routing)
        self.assertRegex(routing, r"Divided work[^.]*not required to mix")
        self.assertNotIn("cheapest executor", routing)

    def test_executors(self):
        text = skill("pstack-economy")
        self.assertIn("`agent:<opus|sonnet|haiku|fable> <effort>`", text)
        self.assertIn("`codex:<model> <effort>`", text)


class OnAdapterHookTest(unittest.TestCase):
    def test_adapter_points_at_economy_early(self):
        head = "\n".join(ADAPTER.read_text().splitlines()[:15])
        self.assertIn("pstack-economy", head)
        self.assertIn("lean widths", head)


if __name__ == "__main__":
    unittest.main()
