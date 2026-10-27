# pstack in Claude Code

pstack skills use Cursor names. In Claude Code, read this file once per session, then map each Cursor name in a skill with the tables below. `<pstack>` means the folder that holds `skills/` and `docs/`. If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

Before any fan-out, loop, or role-model choice, read `<pstack>/skills/pstack-economy/SKILL.md` and apply it. Its lean widths override the widths skills state, and when you explain cost or widths, give its lean widths.

## Tools

| Cursor | Claude Code |
| --- | --- |
| `Task` | `Agent` |
| `AskQuestion` | `AskUserQuestion`. In `-p` mode it is absent, so ask in plain text. |
| Open a todolist | Use `TodoWrite` if the session offers it. Otherwise keep the list in your reply and update it at each phase. |
| Run another pstack skill (`/name` or "the **name** skill") | `Read` `<pstack>/skills/<name>/SKILL.md` and follow it. The `Skill` tool refuses most pstack skills. When you tell the user to type it, write `/pstack:<name>`. |
| `Grep`, `Glob` | `Bash` with `rg` when the session has no `Grep` or `Glob`. |

## Subagent fields

| Cursor | Claude Code |
| --- | --- |
| `subagent_type: generalPurpose` | `subagent_type: "general-purpose"` |
| `poteto-agent`, `comment-sicko` | `pstack:poteto-agent`, `pstack:comment-sicko` |
| `readonly: true` | `subagent_type: "Explore"`. It keeps `Bash`, so the brief also says "do not edit files", and you check `git status` afterward. |
| `readonly: false` | `general-purpose`. It keeps the session's MCP servers. |
| `environment: "cloud"` | `isolation: "worktree"`. Name the branch or commit the worker checks out. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first. |
| `run_in_background: true` | Omit. Subagents run in the background by default and notify you when they finish. |
| `resume` | Spawn a new agent and paste the earlier result into its brief. |
| `file_attachments` | List the paths in the brief. |

## Models

| Cursor | Claude Code |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, such as `claude-opus-5-5-xhigh` | `model: "opus"` and `effort: "xhigh"`. `model` takes only `opus`, `sonnet`, `haiku`, `fable`. Drop `-fast`. |
| A `grok-*`, `gpt-*`, or other non-Claude slug | Omit `model` so the agent runs on the session model, and say so. |
| `auto` or `inherit-parent` | Omit `model`. |
| The `pstack-models.mdc` rule, `~/.cursor/rules/pstack-models.mdc` | `~/.claude/rules/pstack-models.md`. Claude Code loads it into every new session, so its role lines are already in context. If they are not, read the file. If the file or the role's line is missing, use the skill's default slug. |
| A role value `<model> <effort>`, such as `opus high` | `model: "opus"` and `effort: "high"`. |

## setup-pstack

Claude Code loads every `.md` file in `~/.claude/rules/` into each new session, so `setup-pstack` writes its rule there. Follow its steps with these changes:

- Detect. The detected models are the `model` values that the `Agent` tool schema lists, each with an effort from its `effort` values. Write a real model as `<model> <effort>`, such as `opus xhigh`. The effort is the last token, so the budget step works as written.
- Defaults. Map each default slug with the rows above: `claude-opus-5-5-xhigh` is `opus xhigh`, and `grok-4.7-xhigh-fast` is `inherit-parent`.
- Write. Write `~/.claude/rules/pstack-models.md` with no frontmatter, then the comment lines, the `# budget` line, and one line per role from step 5. Overwrite the whole file. Never put the role lines in `CLAUDE.md` or `AGENTS.md`.

## Paths

| Cursor | Claude Code |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | `.claude/skills/`, `~/.claude/skills/` |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `~/.claude/plugins/`, `.claude-plugin/plugin.json` |
| `.cursor/rules/*.mdc`, always-applied rules | `CLAUDE.md`, or `AGENTS.md` when no `CLAUDE.md` exists. Claude Code never reads `.mdc` files. The model rule is the exception. See Models. |
| `https://github.com/cursor/plugins/blob/ab69380dd50ee47d426b35cb8369cffdddafc218/pstack/<path>` | `<pstack>/<path>` when that file exists. The plugin ships the skills, `docs/guide/`, and `README.md`. Read the local copy and never fetch it. Give the user the URL when they need a link. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.claude/projects/<slug>/<session>.jsonl`. The slug is the workspace path with each `/` and `.` changed to `-`, so `/Users/you/proj` is `-Users-you-proj`. The newest `.jsonl` directly in that folder is the current session. Its `<session>/subagents/` folder holds subagent transcripts. Read only this workspace's folder. |

## Cursor-only features

Claude Code has no Cursor Automations, Bugbot, Cursor cloud agents, or built-in PR tool. When a step needs one, put one line in your reply, `Skipped in Claude Code: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| Cursor | Claude Code |
| --- | --- |
| Cursor Automations: routines, `update_state` routine calls, `api2.cursor.sh/automations` webhooks, routine wakes, and `SendToUser` secret requests | Skip with the line. |
| Bugbot | Bugbot comments on a GitHub PR are ordinary review threads, so triage them with the forge command that the step gives. Skip a step that starts, waits for, or configures Bugbot when the PR has no Bugbot check or comment. |
| Cursor cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | Use the forge command that the step gives, such as `gh pr create`. That is not a skip, so write no line. |

## More Cursor names

Upstream's tables above leave these out.

| Cursor | Claude Code |
| --- | --- |
| `cursor-team-kit` | Not available. Its skills map as follows. |
| `deslop` / `/deslop` (from `cursor-team-kit`) | pstack's `unslop` skill over the diff. |
| `control-ui` (from `cursor-team-kit`) | The session's browser tools: Claude in Chrome, the built-in browser, or a Chrome DevTools MCP, whichever the session has. For native apps, computer use. |
| `control-cli` (from `cursor-team-kit`) | `Bash`, driving the real binary. |
| A named driver the project already has (a `verify-*` skill) | Use it. It wins over the rows above. |
| `/create-skill` (Cursor built-in) | Write `SKILL.md` with `name` and `description` frontmatter in `.claude/skills/<name>/` or `~/.claude/skills/<name>/`. Its YAML and writing rules: kebab-case `name` matching the folder, and a `description` that says what the skill does and when to use it. Its draft, test and iterate loop and its description-optimization loop: use a skill-creator skill if the session has one, otherwise read the draft through once yourself. |
| `/loop` (Cursor built-in) | Claude Code's own `/loop`, which has the same idea. Give it a check that can pass or fail. |
| `/visualize` (Cursor's chart renderer) | Not available. Draw numbers as a Mermaid `xychart-beta` or `pie` block, or give them in one sentence. |
| `/orchestrate` | poteto-mode's Orchestrate playbook (`playbooks/orchestrate.md`). The separate `orchestrate` plugin is not installed. |
| `allow_multiple: true` on `AskQuestion` | `multiSelect: true` on `AskUserQuestion`. |
| Matching a transcript by its first JSONL line | Match the first `type: user` record. In Claude Code the first lines are metadata. |
| The agent's store ("path in the system prompt") | `~/.claude/pstack-programs/<program>/`, the program dir that `pstack-economy`'s Audit tick uses. Decision trails, subagent records, orchestrate's project folder, and the store's `docs/` live there. Create it if it is missing. |
| `pstack/<path>`, `git show origin/main:pstack/<path>` | `<pstack>/<path>`, read locally. "Re-read the playbook from trunk" means re-read the installed copy. |
| A Cursor restart | A Claude Code session that ends or restarts. Its subagents and background tasks are gone; worktrees and pushed branches remain. |
| Nested subagents (a sub-coordinator spawning workers) | If a subagent cannot spawn subagents of its own, the coordinator spawns every worker, and sub-coordinators become tracks it keeps in its records. |
| A live lane's own cloud VM, or a video on a lane VM | A worktree on this machine. Give each lane distinct ports, or run live lanes one at a time. Record video with the session's browser or computer-use tools, otherwise skip it with the line. |
| Pinned or active chats, the sidebar | Ask the user which sessions are live, and check for running `claude` processes. |
| `.cursor/worktrees/`, `~/Library/Application Support/Cursor` caches | `.claude/worktrees/`; skip the Cursor caches. |
| Cursor's `mcps/` directory, the enabled MCP servers | The session's MCP tools (`mcp__<server>__*`) and their server instructions. |
| The image-generation tool, a generated image | Not available. Draw a Mermaid or ASCII diagram, and say the picture was skipped. |
| Embedding a screenshot or video inline in the reply | Give its absolute path, or an Artifact link when the session offers one. |
| A Custom Mode, "Use as Mode", Option+Enter, the Agents Window, Plan Mode | Not available. Start each task with `/pstack:poteto-mode`. For planning, use the Multi-phase plan playbook. |
| A Cursor Project (one persistent coordinator thread) | One long-lived Claude Code session per program, with worktree subagents. |
| `/in-cloud` | `isolation: "worktree"` on the `Agent` call. |
| `/add-plugin pstack`, Customize in the sidebar, `/plugin marketplace add cursor/plugins` | `claude plugin marketplace add scotu/pstack-claude-code`, then `claude plugin install pstack@scotu-pstack`. This fork, not upstream's marketplace. |
| `/make-bot-ui` | Not in this build. It drives Cursor Automations (routines and webhooks), which Claude Code does not have. |

## Codex

When Codex is available, it is pstack's second model family in Claude Code. Read `<pstack>/skills/pstack-codex/SKILL.md` for how to run a Codex agent. When Codex is available, this table overrides the Models row for non-Claude slugs. It also overrides the setup-pstack Defaults bullet that writes `grok-4.7-xhigh-fast` as `inherit-parent`: with Codex available, write `codex <model> <effort>` with a Codex model the user confirmed. `inherit-parent` stays the mapping only without Codex.

| Cursor | Claude Code |
| --- | --- |
| A role value `codex <model> <effort>` | A Codex agent per `pstack-codex`, with that model and effort. |
| A `grok-*`, `cursor-grok-*`, `composer-*`, or `gpt-*` slug | When Codex is available: a Codex agent on Codex's configured default model (no `-m`). When it is not: omit `model` as in the Models table, and say in one line that the panel lost its second family. |
