---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes an always-applied rule that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

In Claude Code, read [the Claude Code adapter](../../docs/harness/claude-code.md) once per session before you follow this skill. It maps the Cursor names in pstack skills to Claude Code.

Write `~/.cursor/rules/pstack-models.mdc`, an always-applied rule that sets pstack's model per role.

## On this fork: inventory and two families

This build runs on Claude Code with Codex as a second model family. These rules change the steps below. Where they differ, these rules win.

**Inventory (before step 1).**
- **Detect Claude models** as the adapter's setup-pstack section says: the `Agent` tool's `model` values and their efforts.
- **Detect Codex:** `codex --version` and `codex login status`. When both pass, ask the user which Codex models they want pstack to use. Never assume a catalog. `default` means Codex's own configured model, run with no `-m`.
- **Confirm each model** with the user, with these fields:
  - family: `claude` or `codex`;
  - tier: `frontier`, `strong` or `light`;
  - `tools`: yes or no;
  - executor: `agent <model> <effort>` or `codex <model> <effort>`;
  - cost class: `subscription` unless the user says otherwise.
- **Recommend slots.** `frontier` for judgment, a `strong` model from each family for code-writing and review, and a `light` Claude model (`haiku` or `sonnet`) for the Codex wrapper.

**Budget (step 3).** Claude models use the adapter's ladder. Codex efforts are `max` > `xhigh` > `high` > `medium` > `low` > `minimal`, limited to the levels each model lists under `supported_reasoning_levels` in `~/.codex/models_cache.json`. A model without `max` falls back to `xhigh`, so `unlimited` puts Codex at `max` where the model has it. `ultra` stays out of the ladder: it adds Codex's own delegation, and a Codex seat is a leaf.

**Defaults (step 5).** With Codex available, start from this block, replacing each `codex default` with the Codex model the user confirmed for that tier. Every panel lists both families. `pstack-economy` decides how many entries run: architect runners none at lean width, interrogate reviewers the one entry whose family differs from the author's, and arena runners both. The rest of upstream's roles keep their defaults, with each `grok-*` slug written as `codex default <effort>`.

```
arena runners: opus xhigh, codex default xhigh
interrogate reviewers: opus xhigh, codex default xhigh
architect runners: opus xhigh, codex default xhigh
codex wrapper: haiku medium
```

Without Codex, the defaults are Claude-only: every `codex` entry becomes `inherit-parent`, and you say once that panels lose their second family.

**Write (step 5).** Write `~/.claude/rules/pstack-models.md` as the adapter says. Start it with a `# Models this profile can reach` comment block, one `#` line per inventory model with its fields, then the `# budget` line and the role lines.

**When chezmoi manages `~/.claude`** (`chezmoi source-path ~/.claude` succeeds), write the rule into the chezmoi source, because `chezmoi apply` would overwrite the target or flag it as drift.
- The file is `chezmoi source-path ~/.claude/rules/pstack-models.md` when the rule is already managed. Otherwise it is `pstack-models.md.tmpl` in the `rules/` folder under `chezmoi source-path ~/.claude`. Keep an existing file's name.
- In a `.tmpl`, put each Codex entry behind `{{ if lookPath "codex" }}`, with `inherit-parent` in the `else` branch, so a machine without Codex renders Claude-only panels.
- Check it with `chezmoi execute-template`, then ask the user to review it and run `chezmoi apply`. The rule applies from the next session after that.

## Steps

### 1. Detect available models

Enumerate the model slugs you can pass to a `Task` subagent in this session. That is the dependable source. If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness. If you cannot detect any, ask the user to paste the slugs they have access to. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.

### 2. Load current state

The default role-to-model mapping is the rule shape shown in step 5 below. If `~/.cursor/rules/pstack-models.mdc` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these four options with these exact labels, and name the current budget when the rule records one. With no rule, say that `large` matches the skill defaults.

- `unlimited — max reasoning`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). `unlimited`, `large`, `medium`, and `small` set the effort token of every real slug, panel entries included, to `max`, `xhigh`, `high`, or `medium`. The effort token is the last token, or the one before a trailing `fast`, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a detected slug, use the same family's detected slug with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `unlimited` turns `claude-opus-5-5-xhigh` into `claude-opus-5-5-max`. Grok slugs top out at `xhigh`, so under `unlimited` the fallback puts Grok at `xhigh` and keeps `grok-4.7-xhigh-fast` as it is. `large` keeps both defaults. `small` turns them into `claude-opus-5-5-medium` and `grok-4.7-medium-fast`.

**(c) Show the roles and confirm.** Show every role with its model, marking any real slug not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, which is how Auto users stay on Auto) as the options. Prefer AskQuestion over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.

### 5. Write the rule

Write `~/.cursor/rules/pstack-models.mdc` with `alwaysApply: true`, a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels poteto-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
---
description: pstack per-role model choices (overrides skill defaults)
alwaysApply: true
---
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.
# budget: large (xhigh)
feature, refactoring: grok-4.7-xhigh-fast
bug-fix: grok-4.7-xhigh-fast
perf-issue: grok-4.7-xhigh-fast
hillclimb: grok-4.7-xhigh-fast
judgment and prose: claude-opus-5-5-xhigh
hardest tasks: claude-opus-5-5-xhigh
how explorer: grok-4.7-xhigh-fast
how explainer: claude-opus-5-5-xhigh
why investigators: grok-4.7-xhigh-fast
why synthesizer: claude-opus-5-5-xhigh
reflect tooling: grok-4.7-xhigh-fast
reflect judgment, divergent, synthesizer: claude-opus-5-5-xhigh
arena runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
arena cross-judge pool: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
swarm workers: grok-4.7-xhigh-fast
architect runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
interrogate reviewers: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
```

### 6. Confirm

Tell the user the rule was written and that it applies to new sessions. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.

### 8. Offer a formal verification skill (optional)

Check whether the project already has a formal verification skill (a project skill that runs a model checker, a proof, or another verifier against the code). If not, offer once: "want a formal verification skill, so agents can prove a key property of your code holds in every case in scope, not only the cases tests reach? I can generate one with /create-formal-verification-skill." On yes, invoke `/create-formal-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.
