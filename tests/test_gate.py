"""The gate, tested end to end: real hook script, real tools, temp repo copy."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".claude/hooks/send_gate.py"


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "outbox").mkdir()
        self.write_draft("Hello Jonas,\n\nYour book shipped on 9 March.\n")
        self.env = dict(os.environ, LAB_ROOT=str(self.base))

    def tearDown(self):
        self.tmp.cleanup()

    def write_draft(self, text):
        (self.base / "outbox/draft.md").write_text(text)

    def tool(self, script, *args):
        return subprocess.run([sys.executable, str(REPO / "tools" / script), *args],
                              env=self.env, capture_output=True, text=True)

    def hook(self, tool_name, **tool_input):
        event = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                              env=self.env, capture_output=True, text=True)

    def send_attempt(self):
        return self.hook("Bash", command="python3 tools/send_reply.py")

    def test_send_blocked_without_verdict(self):
        result = self.send_attempt()
        self.assertEqual(result.returncode, 2)
        self.assertIn("No reviewer verdict", result.stderr)

    def test_send_blocked_after_reject(self):
        self.tool("record_verdict.py", "REJECT", "R3: promises a delivery day")
        result = self.send_attempt()
        self.assertEqual(result.returncode, 2)
        self.assertIn("R3: promises a delivery day", result.stderr)

    def test_send_allowed_after_approve(self):
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        self.assertEqual(self.send_attempt().returncode, 0)
        sent = self.tool("send_reply.py")
        self.assertEqual(sent.returncode, 0, sent.stderr)
        self.assertEqual(len(list((self.base / "outbox/sent").iterdir())), 1)

    def test_editing_the_draft_cancels_the_approval(self):
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        self.write_draft("Hello Jonas,\n\nIt will arrive tomorrow before noon.\n")
        result = self.send_attempt()
        self.assertEqual(result.returncode, 2)
        self.assertIn("changed after it was reviewed", result.stderr)

    def test_one_verdict_allows_one_send(self):
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        self.assertEqual(self.tool("send_reply.py").returncode, 0)
        self.assertEqual(self.send_attempt().returncode, 2)

    def test_send_script_refuses_on_its_own(self):
        result = self.tool("send_reply.py")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.base / "outbox/sent").exists())

    def test_writer_cannot_write_a_verdict_file(self):
        result = self.hook("Write", file_path=str(self.base / "review/verdict.json"), content="{}")
        self.assertEqual(result.returncode, 2)

    def test_writer_cannot_write_into_sent(self):
        self.assertEqual(self.hook("Write", file_path="outbox/sent/reply.md", content="hi").returncode, 2)
        for command in ("cp outbox/draft.md outbox/sent/x.md",
                        "cp outbox/draft.md outbox/sent",
                        "cd outbox/sent && cp ../draft.md x.md",
                        "echo '{}' > review/verdict.json",
                        "cd review && echo '{}' > verdict.json"):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_scripts_pass_only_as_a_whole_command(self):
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        for command in ("echo '{}' > review/verdict.json # record_verdict.py",
                        "python3 tools/send_reply.py; cp outbox/draft.md outbox/sent/y.md",
                        "python3 tools/record_verdict.py APPROVE ok && echo hi > x"):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)
        self.assertEqual(self.hook("Bash", command='python3 tools/record_verdict.py APPROVE "all checks pass"').returncode, 0)

    def test_writer_cannot_change_the_gate(self):
        for path in ("tools/verdict.py", "tools/send_reply.py", ".claude/hooks/send_gate.py", ".claude/settings.json"):
            self.assertEqual(self.hook("Edit", file_path=path, old_string="a", new_string="b").returncode, 2, path)
        self.assertEqual(self.hook("Bash", command="sed -i '' 's/2/0/' .claude/hooks/send_gate.py").returncode, 2)

    def test_gate_fails_closed(self):
        broken = subprocess.run([sys.executable, str(HOOK)], input="not json",
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(broken.returncode, 2)
        (self.base / "review").mkdir()
        (self.base / "review/verdict.json").write_text("[]")
        self.assertEqual(self.send_attempt().returncode, 2)

    def test_ordinary_work_passes(self):
        self.assertEqual(self.hook("Write", file_path=str(self.base / "outbox/draft.md"), content="hi").returncode, 0)
        self.assertEqual(self.hook("Bash", command="ls domain").returncode, 0)
        self.assertEqual(self.hook("Read", file_path="domain/policy.md").returncode, 0)


if __name__ == "__main__":
    unittest.main()
