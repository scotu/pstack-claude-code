"""Whole-tree guards for the Principles in CUSTOMIZATIONS.md: every skill file, including ones upstream adds later."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
ADAPTER = (ROOT / "docs" / "harness" / "claude-code.md").read_text()
CODEX = (SKILLS / "pstack-codex" / "SKILL.md").read_text()
# The policy files themselves name the go-wide forms and Cursor names on purpose.
POLICY = {SKILLS / "pstack-economy", SKILLS / "pstack-codex", SKILLS / "setup-pstack"}
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
# Subagent types the adapter's Subagent fields table maps or names as Claude Code's own.
SUBAGENT_TYPES = {"generalPurpose", "general-purpose", "Explore", "poteto-agent", "comment-sicko",
                  "pstack:poteto-agent", "pstack:comment-sicko"}


def docs():
    for md in sorted(list(SKILLS.rglob("*.md")) + list((ROOT / "agents").glob("*.md"))):
        if "node_modules" not in md.parts and not any(md.is_relative_to(p) for p in POLICY):
            yield md, md.read_text()


def lines_with(pattern: str):
    rx = re.compile(pattern)
    for md, text in docs():
        for n, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                yield f"{md.relative_to(ROOT)}:{n}", line


class Guard(unittest.TestCase):
    def assertNone(self, problems):
        self.assertFalse(problems, "\n" + "\n".join(problems))


class EconomyPrincipleTest(Guard):
    """P-1: duplicated work and recurring ticks run lean unless the operator approves going wide."""

    def test_hourly_root_tick_only_when_going_wide(self):
        self.assertNone([w for w, line in lines_with(r"/loop 1h") if not re.search(r"(?i)going wide", line)])

    def test_ten_lanes_only_when_going_wide(self):
        self.assertNone([w for w, line in lines_with(r"(?i)\bten (live )?lanes\b")
                         if not re.search(r"(?i)going wide", line)])


class ClaudeCodePrincipleTest(Guard):
    """P-2: everything a skill points at exists in Claude Code or has a mapping in the adapter or pstack-codex."""

    def test_relative_links_resolve(self):
        # URLs and template placeholders such as (url) are not file links.
        self.assertNone([f"{md.relative_to(ROOT)}: {target}" for md, text in docs() for target in LINK.findall(text)
                         if not re.match(r"^[a-z]+:", target) and re.search(r"[./]", target)
                         and not (md.parent / target).exists()])

    def test_named_skills_exist_or_are_mapped(self):
        skills = {p.name for p in SKILLS.iterdir() if p.is_dir()}
        self.assertNone([f"{md.relative_to(ROOT)}: {name}" for md, text in docs()
                         for name in re.findall(r"\*\*([a-z0-9][a-z0-9-]+)\*\* skill", text)
                         + re.findall(r"`/([a-z0-9][a-z0-9-]+)`", text)
                         if name not in skills and not re.search(rf"`/?{re.escape(name)}`", ADAPTER + CODEX)])

    def test_companion_plugins_are_mapped(self):
        self.assertNone([f"{md.relative_to(ROOT)}: {plugin}" for md, text in docs()
                         for plugin in re.findall(r"from the `([\w-]+)` plugin", text) if plugin not in ADAPTER])

    def test_subagent_types_are_mapped(self):
        self.assertNone([f"{md.relative_to(ROOT)}: {kind}" for md, text in docs()
                         for kind in re.findall(r'subagent_type[^a-zA-Z"]*"([A-Za-z:-]+)"', text)
                         if kind not in SUBAGENT_TYPES])

    def test_non_claude_slugs_mapped(self):
        uses = [md for md, text in docs() if re.search(r"\b(grok|composer|gpt)-", text)]
        self.assertTrue(not uses or "\n## Codex\n" in ADAPTER, uses[:3])


if __name__ == "__main__":
    unittest.main()
