#!/usr/bin/env python3
"""pstack audit tick for Claude Code: a background watcher (pstack-economy, C-005).

Runs in the program dir. Reads owners.tsv (tab-separated, header row):
  owner  remote  repo  branch  pr  expected_minutes  started_at  executor  job  worktree
and builds one stable line per owner, with no timestamps:
  <owner> branch=<branch> head=<sha7|missing|unknown> expected=<n>m checks=<pass|pending|fail|none|unknown|nopr>
  bot_comments=<n|unknown|nopr> [codex=<running|done|failed|cancelled|unknown|->] [STUCK]
`codex=` appears for executor `codex`. Its job is `<codex job id>+<wrapper agent id>`, read with the Codex
companion's `status <job> --cwd <worktree> --json`. Blank rows and rows starting with # are skipped. STUCK means
both the owner and its last known head have been idle longer than expected_minutes; an `unknown` head (a failed
ls-remote) leaves that timer alone. bot_comments counts comments, inline review comments and reviews whose author
is a GitHub Bot account.

  --once (default)   print the lines and exit 0
  --watch            loop: sleep --interval seconds (default 900), rebuild the lines, and exit 0 printing only the
                     lines that changed since the last report. Stays silent while nothing changes. The first run
                     records a baseline and reports only STUCK or ERROR lines in it.

State lives in .pstack-audit-state.json (when each head was first seen) and .pstack-audit-last.txt (the lines last
reported). PSTACK_AUDIT_NOW overrides the clock, PSTACK_CODEX_COMPANION the companion script, for tests.
Problems are reported as ERROR lines, never as a crash.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import subprocess
import time
from pathlib import Path

OWNERS = "owners.tsv"
STATE = ".pstack-audit-state.json"
LAST = ".pstack-audit-last.txt"
COLUMNS = 10
COMPANION = "~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs"
CODEX_STATES = {"queued": "running", "running": "running", "completed": "done", "failed": "failed",
                "cancelled": "cancelled", "canceled": "cancelled"}


def run(*cmd: str) -> tuple[int, str] | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.returncode, r.stdout


def head(remote: str, branch: str) -> str:
    result = run("git", "ls-remote", remote, f"refs/heads/{branch}")
    if result is None or result[0] != 0:
        return "unknown"
    return result[1].split()[0][:7] if result[1].strip() else "missing"


def gh_json(*args: str):
    """gh output as JSON. `gh pr checks` exits non-zero while checks pend or fail but still prints JSON."""
    result = run("gh", *args)
    if result is None:
        return None
    try:
        return json.loads(result[1])
    except ValueError:
        return None


def checks(repo: str, pr: str) -> str:
    data = gh_json("pr", "checks", pr, "-R", repo, "--json", "bucket")
    if not isinstance(data, list):
        return "unknown"
    buckets = {c.get("bucket") for c in data}
    if not buckets:
        return "none"
    if buckets & {"fail", "cancel"}:
        return "fail"
    if "pending" in buckets:
        return "pending"
    return "pass"


def bot_comments(repo: str, pr: str) -> str:
    """Bot-authored items across issue comments, inline review comments and reviews (where review bots post)."""
    total = 0
    for endpoint in (f"repos/{repo}/issues/{pr}/comments", f"repos/{repo}/pulls/{pr}/comments",
                     f"repos/{repo}/pulls/{pr}/reviews"):
        pages = gh_json("api", "--paginate", "--slurp", endpoint)
        if not isinstance(pages, list):
            return "unknown"
        items = [item for page in pages if isinstance(page, list) for item in page]
        total += sum(1 for item in items if isinstance(item, dict) and (item.get("user") or {}).get("type") == "Bot")
    return str(total)


def companion() -> str | None:
    if os.environ.get("PSTACK_CODEX_COMPANION"):
        return os.environ["PSTACK_CODEX_COMPANION"]
    found = sorted(glob.glob(os.path.expanduser(COMPANION)))
    return found[-1] if found else None


def codex(job: str, worktree: str) -> str:
    codex_job = job.split("+", 1)[0]
    if codex_job in ("", "-"):
        return "-"
    script = companion()
    result = run("node", script, "status", codex_job, "--cwd", worktree, "--json") if script else None
    if result is None or result[0] != 0:
        return "unknown"
    try:
        data = json.loads(result[1])
    except ValueError:
        return "unknown"
    job_data = data.get("job") if isinstance(data, dict) and isinstance(data.get("job"), dict) else data
    status = job_data.get("status") if isinstance(job_data, dict) else None
    return CODEX_STATES.get(status, "unknown")


def load_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text()) if path.exists() else {}
    except ValueError:
        return {}
    return state if isinstance(state, dict) else {}


def snapshot(program: Path, now: int | None = None) -> list[str]:
    owners = program / OWNERS
    if not owners.exists():
        return ["ERROR owners.tsv not found"]
    rows = list(csv.reader(owners.read_text().splitlines(), delimiter="\t"))
    now = now if now is not None else int(os.environ.get("PSTACK_AUDIT_NOW") or time.time())
    state = load_state(program / STATE)
    lines = []
    for n, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row) or row[0].startswith("#"):
            continue
        if len(row) != COLUMNS:
            return [f"ERROR owners.tsv line {n}: expected {COLUMNS} columns"]
        owner, remote, repo, branch, pr, expected, started, executor, job, worktree = row
        try:
            minutes, started_at = int(expected), int(started)
        except ValueError:
            return [f"ERROR owners.tsv line {n}: expected_minutes and started_at must be integers"]
        sha = head(remote, branch)
        seen = state.get(owner) if isinstance(state.get(owner), dict) else {}
        if sha != "unknown" and seen.get("sha") != sha:
            seen = {"sha": sha, "first_seen": now}
            state[owner] = seen
        limit = minutes * 60
        stuck = "first_seen" in seen and now - seen["first_seen"] > limit and now - started_at > limit
        if pr == "-":
            status = "checks=nopr bot_comments=nopr"
        else:
            status = f"checks={checks(repo, pr)} bot_comments={bot_comments(repo, pr)}"
        if executor == "codex":
            status += f" codex={codex(job, worktree)}"
        lines.append(f"{owner} branch={branch} head={sha} expected={minutes}m {status}" + (" STUCK" if stuck else ""))
    (program / STATE).write_text(json.dumps(state, indent=1, sort_keys=True))
    return lines


def watch(program: Path, interval: int = 900, max_cycles: int | None = None, sleep=time.sleep) -> list[str]:
    """Return (and record) the lines that changed since the last report; [] if max_cycles ran out quietly."""
    last_file = program / LAST
    if last_file.exists():
        last = set(last_file.read_text().splitlines())
    else:
        first = snapshot(program)
        last_file.write_text("\n".join(first))
        alarms = [line for line in first if line.startswith("ERROR") or line.endswith(" STUCK")]
        if alarms:
            return alarms
        last = set(first)
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        sleep(interval)
        lines = snapshot(program)
        changed = [line for line in lines if line not in last]
        if changed:
            last_file.write_text("\n".join(lines))
            return changed
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--max-cycles", type=int)
    args = parser.parse_args()
    program = Path.cwd()
    if args.watch:
        changed = watch(program, args.interval, args.max_cycles)
        if changed:
            print("\n".join(changed))
    else:
        print("\n".join(snapshot(program)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # the root must see a stable line, never a crash
        print(f"ERROR internal {type(exc).__name__}")
