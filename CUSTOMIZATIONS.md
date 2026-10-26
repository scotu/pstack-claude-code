# pstack customizations

This file lists the personal changes made on top of the claude-code build of pstack. It exists only on the `main` branch.

- `upstream` holds the exact build output from agent-plugin-factory. Never edit it by hand.
- `main` is `upstream` plus the changes listed here. Install this branch.
- `git diff refs/heads/upstream main --` shows the full set of changes.
- Upstream comes in by merge (`python3 -m factory sync pstack`). Never rebase or rewrite `main`: `hermes plugins update` only fast-forwards.

Each change has one entry. Its commits start with its ID, for example `C-001: …`. When resolving a merge conflict, re-apply the **Intent** instead of keeping the old wording. Status is `active` or `retired`. Retire an entry when upstream covers it or you no longer want it, and keep it as history.

## Principles

A clean merge only means no customization collided with upstream. New or reworded upstream text can still break these rules. Every file on `main` must follow them, including files upstream adds later. Each active entry's Intent is one of them: `Touches:` lists the files the entry edited, but the Intent applies to every file.

- **P-1 Lean by default (C-001 to C-005).** Duplicated agent work runs at pstack-economy's lean width unless the operator approves going wide. Duplicated work means races, best-of, same-prompt panels, repeated verification lanes, and periodic re-checks. Divided work runs as upstream wrote it. A recurring audit tick is the background watcher. `/loop 1h` and ten lanes appear only as the going-wide form. A new duplicated-work pattern gets a row in pstack-economy's Lean widths. A new panel role also gets a lean default in setup-pstack. Duplicated-work seats at lean width, and every author/verifier pair, draw on both model families when Codex is available.
- **P-2 Runs on Claude Code.** Every tool, feature, skill, plugin, subagent type, model slug and path that a skill names either exists in Claude Code or has a mapping in the adapter (`docs/harness/claude-code.md`, including its Codex section) or in `pstack-codex`. Nothing points at a file the tree leaves out. Fix gaps in agent-plugin-factory's port hook or overlay (`plugins/pstack/claude-code/`), so the fix reaches every later build.
- **P-3 Intents apply to the whole tree.** An entry's `Touches:` lists the files it edited. Its Intent is a rule for every file.

`tests/test_principles.py` checks what can be checked mechanically across the whole tree. Everything else is caught by the audit.

`python3 -m factory audit pstack --target claude-code` writes `audits/<upstream sha12>.md`, with one row for every path the new upstream build changed. Read each change against these principles, then give every row a verdict:
- `complies`;
- `n/a`;
- `port`, when it was fixed in the port hook or overlay;
- the `C-NNN` it was fixed under.

`python3 -m factory push pstack --target claude-code` refuses a new upstream build until that audit is committed and complete.

Entry format:

```
## C-NNN — <area>: <short title>  [active]
Intent: what must be true afterwards, written so it survives upstream rewording.
Why: the reason for the change.
Touches: path/to/file, path/to/folder/
Check: how to confirm it still holds.
```

<!-- entries below, newest last -->

## C-001 — pstack-economy: lean-by-default spending, two-family routing  [active]
Intent: a pstack-economy skill defines lean widths for duplicated agent work (divided work untouched), per-task go-wide approval with a cost statement against each quota, routing by tier over the setup-pstack inventory where duplicated-work seats at lean width and every author/verifier pair span the Claude and Codex families when Codex is available (divided work may use Codex by headroom but need not mix), and the audit tick as a background watcher.
Why: both Claude Code and Codex are subscription quotas; the saving comes from smaller widths, and model choice serves heterogeneity, not price.
Spec: https://github.com/scotu/agent-plugin-factory/blob/main/docs/specs/2026-10-26-pstack-claude-code-design.md
Touches: skills/pstack-economy/SKILL.md, tests/test_skills.py
Check: python3 -m unittest tests.test_skills.EconomySkillTest passes

## C-002 — adapter: route every fan-out through pstack-economy  [active]
Intent: the Claude Code adapter, which pstack skills read once per session, tells the agent to read and apply pstack-economy before any fan-out, loop, or role-model choice, and to give its lean widths when explaining cost or widths.
Why: one hook makes the economy policy reach every skill without editing each.
Spec: https://github.com/scotu/agent-plugin-factory/blob/main/docs/specs/2026-10-26-pstack-claude-code-design.md
Touches: docs/harness/claude-code.md
Check: python3 -m unittest tests.test_skills.OnAdapterHookTest passes

## C-005 — audit tick: background watcher instead of an hourly root loop  [active]
Intent: programs arm a background watcher (pstack-audit-watch.py --watch via Bash run_in_background, never Monitor) that does mechanical liveness checks for free and exits only on a change, waking the root for the judgment half; the hourly /loop 1h root tick only when going wide. check-plan.mjs accepts /loop 1h or pstack-audit-watch as the program marker.
Why: an hourly tick on a subscription model re-audits unchanged state; mechanical checks need no model, and judgment is needed only when something changed.
Spec: https://github.com/scotu/agent-plugin-factory/blob/main/docs/specs/2026-10-26-pstack-claude-code-design.md
Touches: skills/pstack-economy/SKILL.md, skills/pstack-economy/audit-watch/
Check: python3 -m unittest tests.test_audit_watch passes

## C-003 — setup-pstack: two-family inventory and panel defaults  [active]
Intent: setup-pstack builds a confirmed inventory of Claude and Codex models (family, tier, tools, executor, cost class), detects Codex with codex --version and codex login status, uses a Codex effort ladder without max, writes ~/.claude/rules/pstack-models.md with the inventory as comment lines, and defaults every panel (arena runners, interrogate reviewers, architect runners) to one Claude and one Codex entry, with grok slugs written as codex default; Claude-only with a note when Codex is missing. pstack-economy names how many panel entries run at lean width.
Why: model diversity across families is the point of the panels; lean widths keep the cost down.
Spec: https://github.com/scotu/agent-plugin-factory/blob/main/docs/specs/2026-10-26-pstack-claude-code-design.md
Touches: skills/setup-pstack/SKILL.md, skills/pstack-economy/SKILL.md
Check: python3 -m unittest tests.test_skills.SetupInventoryTest passes
