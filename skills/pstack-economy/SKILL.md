---
name: pstack-economy
description: >-
  Spending rules for pstack in Claude Code. Lean by default: cut duplicated
  agent work (races, same-prompt panels, repeated lanes, polling loops), keep
  divided work, ask before going wide, and route each role across two model
  families (Claude and Codex) by tier. Apply before any pstack fan-out, loop,
  or role-model choice.
---

# pstack economy

Upstream pstack assumes model calls are cheap. Here they draw on two subscription quotas, Claude Code's and Codex's. Apply these rules whenever a pstack skill would spawn more than one agent, arm a loop, or pick a model for a role. They override the widths that pstack's skills state. They never weaken a check. They only limit how many copies of the same check run, and they decide which family runs each seat.

## Duplicated and divided work

- **Divided work:** several agents each do a different piece. Examples are swarm coverage slices, `how` explorers on distinct angles, `why` investigators per evidence category, `reflect`'s three lenses, and poteto-mode delegates. Run it as the skill says, with subagents as needed.
- **Duplicated work:** several agents do the same piece. Examples are races, best-of, several candidates for one artifact, several reviewers with one prompt, repeated verification lanes, and periodic re-checks. Run the lean width below.
- **Free-executor exemption (dormant).** Duplicated work may run on a free executor when its output stays advisory, meaning it never merges, dispatches, stands down, or decides. No executor in Claude Code is free today, so this exemption applies only if one is added to the inventory.

Panel roles in `~/.claude/rules/pstack-models.md` list both families. Without going wide, run only these entries:
- architect runners: none, because the parent designs;
- interrogate reviewers: the one entry whose family differs from the author's;
- arena runners: the first two;
- arena cross-judge pool: none, because the parent judges.

The full list is the go-wide width, not the default.

## Lean widths

| Pattern | Lean default | Go wide (upstream) |
|---|---|---|
| swarm, coverage slices | one worker per slice, no cap | — |
| swarm, races and best-of | no race, one worker per arm | upstream races |
| architect | one design by the parent that names the alternatives it rejected and why, with no runners | 2 to 3 runners |
| arena | 2 candidates, one per family when Codex is available, judged by the parent against the rubric, with no separate cross-judge | 3 candidates plus a cross-judge |
| interrogate | 1 reviewer from the family that did not write the code | one reviewer per configured model |
| reflect, why, how, poteto-mode subagents | as upstream (divided work) | — |
| live verification | one lane per distinct check, with no repeats | ten lanes |
| autopilot audit tick | the background watcher (Audit tick) | full hourly `/loop 1h` tick on the root |
| second-opinion Codex runs (`/codex:review`, `/codex:rescue`) | only when the user asks, or as the cross-family seat a step already has | as configured |

Event-driven waits (a `/loop` or background task that watches CI or a merge) stay as upstream. They wait for something to happen; they don't repeat work.

## Going wide

Before any step wider than lean, post one message that names:
- the pattern;
- the width you want and the lean width it replaces;
- the executors involved, with their models and families from `~/.claude/rules/pstack-models.md`;
- a rough relative cost against each quota, for example "about 3x one pass: 2 runs on Claude, 1 on Codex".

Then wait for an explicit yes. "Go wide", "spare no expense", or a named width for the current task ("arena with 3") approves that task only. Approval never carries over to later tasks or sessions. When nobody is watching (autopilot, figure-it-out, the user stepped away), stay lean, and list in your report the steps you would have widened.

## Routing

`~/.claude/rules/pstack-models.md` starts with an inventory written by `setup-pstack`: model, family (`claude` or `codex`), tier (`frontier`, `strong`, `light`), `tools` (yes or no), executor, and cost class. If the inventory is missing, treat every role as Claude on the session model, say so once, and suggest running `/pstack:setup-pstack`.

**Executors:**
- `parent`: this session.
- `agent:<opus|sonnet|haiku|fable> <effort>`: an `Agent` subagent with `model` and `effort`.
- `codex:<model> <effort>`: a Codex agent, run per the `pstack-codex` skill.

Both families are `subscription`. No executor is `per-token` unless the inventory says so. If one ever is, never pick it unless it is the only executor at the tier the role needs, and say so before spending.

**Which work needs which tier:**
- `light`: exploration and grep sweeps, running tests and reporting results, reading transcripts or logs, and the Codex wrapper.
- `strong`: code-writing owners, reviewers, investigators.
- `frontier`: judgment, synthesis, the hardest tasks, final picks and verdicts.

**Rule:**
1. **Meet the role's tier.**
2. **Mix families for duplicated work.** When a duplicated-work step has two or more seats at lean width, draw them from both families. For example, arena's 2 candidates are one Claude and one Codex.
3. **Cross families between author and verifier.** A single reviewer, judge or verifier comes from the family that did not write the work.
4. **Otherwise, use headroom.** At equal tier, prefer the family with more quota headroom when you know it, else the session's family. Divided work picks per seat this way, and it is not required to mix.

When Codex is unavailable (see `pstack-codex`), every seat runs on Claude, and you say in one line which step lost its second family.

## Audit tick

A program's audit tick is a background watcher script. It does the mechanical liveness checks with no model involved, and wakes you only when something changes. Arm it on the operator's go. The hourly `/loop 1h` tick is the going-wide form only.

1. **Program dir.** Create `~/.claude/pstack-programs/<program>/`, outside any repo checkout. Write `plan.txt` there: the plan path, the execution playbook, and this session. The same dir is the agent store that skills mention.
2. **`owners.tsv`.** Write it in the program dir, tab-separated, with this header: `owner remote repo branch pr expected_minutes started_at executor job worktree`.
   - `remote` is the git URL, and `repo` is `owner/name` for `gh`.
   - `pr` is the PR number, or `-` before the PR exists.
   - `expected_minutes` and `started_at` (epoch seconds) are integers.
   - `executor` is `claude` or `codex`.
   - `job` is the agent id, or for a Codex pair `<codex job id>+<wrapper agent id>`.
   - `worktree` is the owner's worktree path, or `-`.
   - Blank rows and `#` rows are ignored.
   - Update it whenever an owner spawns, opens its PR, or finishes.
3. **Arm the watcher.** Copy `audit-watch/pstack-audit-watch.py` from this skill's folder into the program dir. From the program dir, start `python3 pstack-audit-watch.py --watch --interval 900` with Bash `run_in_background`.
   - It records a baseline, then checks every 15 minutes.
   - It prints nothing and costs nothing while nothing changes.
   - It exits, printing the changed owner lines, when a head moves, checks change, a bot comments, a Codex job ends, or an owner goes STUCK.

   Never use Monitor for this. A Monitor watch expires within 30 minutes, and re-arming it costs a turn every time.
4. **Check that it works.** Run `python3 pstack-audit-watch.py --once` once before arming. It must print one line per owner and no `ERROR` line. Fix the script path, `gh auth status`, or `owners.tsv` until it does.
5. **On wake.** The exit notification names the owners concerned. For those owners only, run the judgment half of the playbook's audit tick:
   - re-read the playbook;
   - fix drift;
   - stand down and replace stuck owners;
   - handle failed checks and bot comments;
   - for a Codex pair whose job is `done`, make sure its wrapper commits.

   Then arm the watcher again. It starts from the state it reported.
6. **Teardown.** When no delegated work is left, don't re-arm, and delete the program dir.

The watcher lives as long as this session. Closing the session ends the watcher and the owners together, by design.
