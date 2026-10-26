"""pstack-audit-watch.py, the background watcher audit tick (C-005)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "pstack-economy" / "audit-watch" / "pstack-audit-watch.py"
HEADER = "owner\tremote\trepo\tbranch\tpr\texpected_minutes\tstarted_at\texecutor\tjob\tworktree\n"
CLAUDE = "\tclaude\t-\t-"
GH_STUB = """#!/bin/sh
# Stub gh. `gh pr checks <n> ...` prints $GH_FIXTURES/checks-<n>.json and exits with checks-<n>.code (default 0).
# `gh api ... <endpoint>` prints $GH_FIXTURES/api_<endpoint with / as _>.json. A missing fixture exits 1.
if [ "$1" = api ]; then
  for last; do :; done
  f="$GH_FIXTURES/api_$(echo "$last" | tr / _).json"
  [ -f "$f" ] || exit 1
  cat "$f"; exit 0
fi
f="$GH_FIXTURES/$2-$3.json"
[ -f "$f" ] || exit 1
cat "$f"
c="$GH_FIXTURES/$2-$3.code"
[ -f "$c" ] && exit "$(cat "$c")"
exit 0
"""


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


class AuditWatchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.remote = base / "remote.git"
        git(base, "init", "-q", "--bare", str(self.remote))
        self.work = base / "work"
        git(base, "clone", "-q", str(self.remote), str(self.work))
        self.push("1")
        self.bin = base / "bin"
        self.bin.mkdir()
        (self.bin / "gh").write_text(GH_STUB)
        (self.bin / "gh").chmod(0o755)
        self.fx = base / "fx"
        self.fx.mkdir()
        self.fixture("checks", [{"bucket": "pass"}, {"bucket": "pending"}])
        self.api("issues/7/comments", [[{"user": {"login": "github-actions", "type": "Bot"}},
                                         {"user": {"login": "talbot", "type": "User"}}]])
        self.api("pulls/7/comments", [[]])
        self.api("pulls/7/reviews", [[{"user": {"login": "matteo", "type": "User"}}]])
        self.program = base / "program"
        self.program.mkdir()
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t1000{CLAUDE}\n")

    def tearDown(self):
        self._tmp.cleanup()

    def push(self, content):
        (self.work / "f").write_text(content)
        git(self.work, "add", "f")
        git(self.work, "commit", "-qm", content)
        git(self.work, "push", "-q", "origin", "HEAD:refs/heads/feat-a")
        return git(self.work, "rev-parse", "--short=7", "HEAD")

    def fixture(self, kind, data, code=0):
        (self.fx / f"{kind}-7.json").write_text(json.dumps(data))
        (self.fx / f"{kind}-7.code").write_text(str(code))

    def api(self, endpoint, pages):
        (self.fx / ("api_repos_me_demo_" + endpoint.replace("/", "_") + ".json")).write_text(json.dumps(pages))

    def owners(self, rows):
        (self.program / "owners.tsv").write_text(HEADER + rows)

    def watch(self, now):
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "GH_FIXTURES": str(self.fx), "PSTACK_AUDIT_NOW": str(now)}
        r = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.program, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_line_format(self):
        head = git(self.work, "rev-parse", "--short=7", "HEAD")
        self.assertEqual(self.watch(1100),
                         f"owner-a branch=feat-a head={head} expected=40m checks=pending bot_comments=1\n")

    def test_stable_output_without_changes(self):
        first, second = self.watch(1100), self.watch(1200)
        self.assertEqual(first, second)
        self.assertNotIn("1100", first)

    def test_new_push_changes_only_head(self):
        before = self.watch(1100)
        new = self.push("2")
        after = self.watch(1200)
        self.assertNotEqual(before, after)
        self.assertIn(f"head={new}", after)
        self.assertEqual(before.split("head=")[0], after.split("head=")[0])
        self.assertEqual(before.split(" checks=")[1], after.split(" checks=")[1])

    def test_stuck_after_expected_runtime(self):
        self.watch(1100)
        self.assertNotIn("STUCK", self.watch(1100 + 39 * 60))
        self.assertTrue(self.watch(1100 + 41 * 60).rstrip().endswith(" STUCK"))

    def test_stuck_clears_on_push(self):
        self.watch(1100)
        self.assertIn("STUCK", self.watch(1100 + 41 * 60))
        self.push("2")
        now = 1100 + 42 * 60
        self.assertNotIn("STUCK", self.watch(now))
        self.assertNotIn("STUCK", self.watch(now + 39 * 60))
        self.assertIn("STUCK", self.watch(now + 41 * 60))

    def test_checks_summary_reads_json_on_nonzero_exit(self):
        self.fixture("checks", [{"bucket": "pass"}, {"bucket": "fail"}], code=1)
        self.assertIn("checks=fail", self.watch(1100))
        self.fixture("checks", [{"bucket": "pending"}], code=8)
        self.assertIn("checks=pending", self.watch(1100))
        self.fixture("checks", [{"bucket": "pass"}, {"bucket": "skipping"}])
        self.assertIn("checks=pass", self.watch(1100))
        self.fixture("checks", [])
        self.assertIn("checks=none", self.watch(1100))

    def test_gh_failure_is_unknown(self):
        (self.fx / "checks-7.json").unlink()
        (self.fx / "api_repos_me_demo_issues_7_comments.json").unlink()
        self.assertIn("checks=unknown bot_comments=unknown", self.watch(1100))

    def test_no_pr_yet(self):
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t-\t40\t1000{CLAUDE}\n")
        self.assertIn("checks=nopr bot_comments=nopr", self.watch(1100))

    def test_missing_branch(self):
        self.owners(f"owner-a\t{self.remote}\tme/demo\tnope\t7\t40\t1000{CLAUDE}\n")
        self.assertIn("head=missing", self.watch(1100))

    def test_missing_owners_file(self):
        (self.program / "owners.tsv").unlink()
        self.assertEqual(self.watch(1100), "ERROR owners.tsv not found\n")

    def test_malformed_row(self):
        self.owners("owner-a\tonly-two\n")
        self.assertEqual(self.watch(1100), "ERROR owners.tsv line 2: expected 10 columns\n")


    # --- review fixes ---

    def test_bot_comments_count_bot_users_across_review_endpoints(self):
        self.api("pulls/7/comments", [[{"user": {"login": "coderabbitai", "type": "Bot"}}],
                                      [{"user": {"login": "cursor", "type": "Bot"}}]])
        self.api("pulls/7/reviews", [[{"user": {"login": "talbot", "type": "User"}}]])
        self.assertIn("bot_comments=3", self.watch(1100))

    def test_blank_and_comment_rows_are_skipped(self):
        self.owners(f"\n# a comment\nowner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t1000{CLAUDE}\n\n")
        out = self.watch(1100)
        self.assertTrue(out.startswith("owner-a branch=feat-a"), out)
        self.assertNotIn("ERROR", out)

    def test_non_integer_fields_print_one_error(self):
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t30m\t1000{CLAUDE}\n")
        self.assertEqual(self.watch(1100), "ERROR owners.tsv line 2: expected_minutes and started_at must be integers\n")
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t{CLAUDE}\n")
        self.assertEqual(self.watch(1100), "ERROR owners.tsv line 2: expected_minutes and started_at must be integers\n")

    def test_corrupt_state_is_reset(self):
        (self.program / ".pstack-audit-state.json").write_text("[1]")
        self.assertIn("owner-a branch=feat-a", self.watch(1100))

    def test_unknown_head_keeps_the_stuck_timer(self):
        self.watch(1100)
        self.owners(f"owner-a\t{self.remote}-gone\tme/demo\tfeat-a\t7\t40\t1000{CLAUDE}\n")
        flaky = self.watch(1100 + 41 * 60)
        self.assertIn("head=unknown", flaky)
        self.assertIn("STUCK", flaky)
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t1000{CLAUDE}\n")
        self.assertIn("STUCK", self.watch(1100 + 42 * 60))

    def test_expected_runtime_is_reported(self):
        self.assertIn(" expected=40m", self.watch(1100))


COMPANION_STUB = """const fs = require("fs");
const args = process.argv.slice(2);
const job = args[1];
const f = `${process.env.CODEX_FIXTURES}/${job}.json`;
if (args[0] !== "status" || !fs.existsSync(f)) process.exit(1);
process.stdout.write(fs.readFileSync(f, "utf8"));
"""


def load_watcher():
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_watch", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WatchLoopTest(AuditWatchTest):
    def setUp(self):
        super().setUp()
        self.mod = load_watcher()
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{os.environ['PATH']}"
        os.environ["GH_FIXTURES"] = str(self.fx)
        self.cx = self.program.parent / "codex"
        self.cx.mkdir()
        (self.cx / "companion.js").write_text(COMPANION_STUB)
        os.environ["CODEX_FIXTURES"] = str(self.cx)
        os.environ["PSTACK_CODEX_COMPANION"] = str(self.cx / "companion.js")

    def tearDown(self):
        for key in ("GH_FIXTURES", "CODEX_FIXTURES", "PSTACK_CODEX_COMPANION"):
            os.environ.pop(key, None)
        super().tearDown()

    def codex_job(self, status):
        (self.cx / "job1.json").write_text(json.dumps({"job": {"id": "job1", "status": status}}))

    def test_loop_silent_until_change(self):
        self.assertEqual(self.mod.watch(self.program, interval=0, max_cycles=3), [])

    def test_loop_exits_on_new_head(self):
        calls = []

        def sleep(_):
            calls.append(1)
            if len(calls) == 2:
                self.push("2")
        changed = self.mod.watch(self.program, interval=0, max_cycles=5, sleep=sleep)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(changed), 1)
        self.assertTrue(changed[0].startswith("owner-a branch=feat-a"))

    def test_rearm_is_silent_on_the_state_it_exited_on(self):
        self.mod.watch(self.program, interval=0, max_cycles=1)
        self.push("2")
        self.assertEqual(len(self.mod.watch(self.program, interval=0, max_cycles=2)), 1)
        self.assertEqual(self.mod.watch(self.program, interval=0, max_cycles=2), [])

    def test_codex_job_done_without_commit_escalates(self):
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t1000\tcodex\tjob1+agent9\t{self.work}\n")
        self.codex_job("running")
        state = []

        def sleep(_):
            state.append(1)
            if len(state) == 2:
                self.codex_job("completed")
        changed = self.mod.watch(self.program, interval=0, max_cycles=5, sleep=sleep)
        self.assertEqual(len(changed), 1)
        self.assertIn("codex=done", changed[0])

    def test_codex_states(self):
        self.owners(f"owner-a\t{self.remote}\tme/demo\tfeat-a\t7\t40\t1000\tcodex\tjob1+agent9\t{self.work}\n")
        for status, shown in (("queued", "running"), ("running", "running"), ("completed", "done"),
                              ("failed", "failed"), ("cancelled", "cancelled"), ("weird", "unknown")):
            self.codex_job(status)
            self.assertIn(f" codex={shown}", self.watch(1100))
        (self.cx / "job1.json").unlink()
        self.assertIn(" codex=unknown", self.watch(1100))

    def test_claude_owner_has_no_codex_field(self):
        self.assertNotIn("codex=", self.watch(1100))

    def test_no_timestamps(self):
        import re as _re
        for line in self.watch(1100).splitlines():
            self.assertNotRegex(line, r"\d{4}-\d{2}-\d{2}|\b1\d{9}\b")


if __name__ == "__main__":
    unittest.main()
