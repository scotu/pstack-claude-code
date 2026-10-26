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


def role(text: str, name: str) -> list[str]:
    line = re.search(rf"^{re.escape(name)}: (.+)$", text, re.M)
    return [entry.strip() for entry in line.group(1).split(",")] if line else []


class SetupInventoryTest(unittest.TestCase):
    def fork(self) -> str:
        return skill("setup-pstack").split("## On this fork: inventory and two families\n", 1)[1]

    def test_inventory_fields(self):
        text = self.fork()
        for needle in ("family", "tier", "tools", "executor", "cost class", "codex --version", "codex login status",
                       "~/.claude/rules/pstack-models.md", "# Models this profile can reach"):
            self.assertIn(needle, text)

    def test_alternating_defaults(self):
        text = self.fork()
        for panel in ("arena runners", "interrogate reviewers", "architect runners"):
            entries = role(text, panel)
            self.assertEqual(len(entries), 2, panel)
            self.assertFalse(entries[0].startswith("codex"), panel)
            self.assertTrue(entries[1].startswith("codex "), panel)
        self.assertIn("Claude-only", text)

    def test_codex_effort_ladder_has_no_max(self):
        self.assertIn("`xhigh` > `high` > `medium` > `low` > `minimal`", self.fork())

    def test_economy_names_lean_runs_per_panel(self):
        text = skill("pstack-economy")
        self.assertIn("architect runners: none", text)
        self.assertIn("interrogate reviewers: the one entry whose family differs", text)


class OnAdapterHookTest(unittest.TestCase):
    def test_adapter_points_at_economy_early(self):
        head = "\n".join(ADAPTER.read_text().splitlines()[:15])
        self.assertIn("pstack-economy", head)
        self.assertIn("lean widths", head)


if __name__ == "__main__":
    unittest.main()
