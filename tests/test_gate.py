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

    def test_case_does_not_open_a_way_round(self):
        # The default macOS disk treats Outbox/Sent and outbox/sent as one folder.
        for path in ("Outbox/Sent/x.md", "REVIEW/verdict.json", ".Claude/hooks/send_gate.py", "Tools/verdict.py"):
            self.assertEqual(self.hook("Write", file_path=path, content="x").returncode, 2, path)
        for command in ("cp outbox/draft.md Outbox/Sent/x.md", "echo '{}' > REVIEW/verdict.json",
                        "PYTHON3 TOOLS/SEND_REPLY.PY"):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_writer_may_write_only_the_draft(self):
        for path in ("outbox/x.sh", "domain/policy.md", "notes.md", str(Path.home() / ".claude/settings.json")):
            self.assertEqual(self.hook("Write", file_path=path, content="x").returncode, 2, path)

    def test_any_tool_with_a_command_is_checked(self):
        result = self.hook("Monitor", command="cp outbox/draft.md outbox/sent/x.md")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.hook("Monitor", command="python3 tools/send_reply.py").returncode, 2)

    def test_broken_import_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp)
            (copy / ".claude/hooks").mkdir(parents=True)
            (copy / "tools").mkdir()
            (copy / ".claude/hooks/send_gate.py").write_text(HOOK.read_text())
            (copy / "tools/verdict.py").write_text("def (\n")
            result = subprocess.run([sys.executable, str(copy / ".claude/hooks/send_gate.py")],
                                    input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                                    env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_hook_wiring_turns_any_crash_into_a_block(self):
        settings = json.loads((REPO / ".claude/settings.json").read_text())
        entry = settings["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], ".*")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".claude/hooks").mkdir(parents=True)
            (Path(tmp) / ".claude/hooks/send_gate.py").write_text("def (\n")  # a gate that cannot even start
            result = subprocess.run(["sh", "-c", entry["hooks"][0]["command"]], input="{}",
                                    env=dict(self.env, CLAUDE_PROJECT_DIR=tmp), capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    # Third independent check, 6 November 2026: each test below passed through the previous gate.

    def test_separators_do_not_hide_a_guarded_name(self):
        for command in ("cd .claude;sed -i '' 's/return 2$/return 0/' hooks/send_gate.py",
                        "cd tools&&sed -i '' 's/a/b/' verdict.py",
                        "cp outbox/draft.md outbox/sent;",
                        "cp outbox/draft.md {outbox/sent,x}/r.md",
                        "(cd review)&&ls"):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_the_draft_cannot_be_run_or_replaced_from_the_shell(self):
        for command in ("bash outbox/draft.md", "sh < outbox/draft.md", ". outbox/draft.md",
                        "python3 outbox/draft.md", "git apply outbox/draft.md", "patch -p1 < outbox/draft.md",
                        'ln -sf "$PWD"/x outbox/draft.md'):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_git_cannot_bring_back_an_old_gate(self):
        for command in ("git checkout HEAD~1 -- .", "git stash", "git restore ."):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_a_linked_draft_is_refused(self):
        target = self.base / "gate_stand_in.py"
        target.write_text("return 2\n")
        draft = self.base / "outbox/draft.md"
        draft.unlink()
        draft.symlink_to(target)
        self.assertEqual(self.hook("Write", file_path=str(target), content="x").returncode, 2)
        self.assertEqual(self.hook("Write", file_path=str(draft), content="x").returncode, 2)
        draft.unlink()
        os.link(target, draft)
        self.assertEqual(self.hook("Write", file_path=str(draft), content="x").returncode, 2)
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        self.assertEqual(self.tool("send_reply.py").returncode, 1)

    def test_send_files_the_bytes_it_checked(self):
        # A draft swapped between the check and the copy must not reach outbox/sent/.
        self.tool("record_verdict.py", "APPROVE", "all checks pass")
        code = ("import sys, send_reply\n"
                "real = send_reply.check\n"
                "def check(*args, **kwargs):\n"
                "    result = real(*args, **kwargs)\n"
                "    (send_reply.root() / 'outbox/draft.md').write_text('NEVER REVIEWED')\n"
                "    return result\n"
                "send_reply.check = check\n"
                "sys.exit(send_reply.main())\n")
        result = subprocess.run([sys.executable, "-c", code], cwd=REPO / "tools",
                                env=dict(self.env, PYTHONPATH=str(REPO / "tools")), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        sent = list((self.base / "outbox/sent").iterdir())
        self.assertEqual(sent[0].read_text(), "Hello Jonas,\n\nYour book shipped on 9 March.\n")

    def test_hook_interpreter_ignores_planted_code(self):
        # The shell can write outside the repo, for instance a usercustomize.py that Python loads at start.
        command = json.loads((REPO / ".claude/settings.json").read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        with tempfile.TemporaryDirectory() as home:
            env = {k: v for k, v in self.env.items() if not k.startswith("PYTHON")}
            env.update(HOME=home, CLAUDE_PROJECT_DIR=str(REPO))
            for python in ("python3", "/usr/bin/python3"):
                site = subprocess.run([python, "-c", "import site; print(site.getusersitepackages())"],
                                      env=env, capture_output=True, text=True).stdout.strip()
                Path(site).mkdir(parents=True, exist_ok=True)
                (Path(site) / "usercustomize.py").write_text("import os\nos._exit(0)\n")
            event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "cp outbox/draft.md outbox/sent/x.md"}})
            result = subprocess.run(["sh", "-c", command], input=event, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_reviewer_can_record_a_realistic_reason(self):
        reason = 'python3 tools/record_verdict.py REJECT "R4: draft says 9.99 EUR; order says 7.99 EUR\nR3: promises a day"'
        self.assertEqual(self.hook("Bash", command=reason).returncode, 0)
        self.assertEqual(self.hook("Bash", command="python3 tools/record_verdict.py REJECT 'R6: offers a voucher'").returncode, 0)
        for command in ('python3 tools/record_verdict.py APPROVE "$(cp outbox/draft.md outbox/sent/x)"',
                        'python3 tools/record_verdict.py APPROVE "ok"; ls',
                        "python3 tools/record_verdict.py APPROVE\nls",
                        'python3 tools/record_verdict.py APPROVE "a" "b"'):
            self.assertEqual(self.hook("Bash", command=command).returncode, 2, command)

    def test_every_path_key_is_checked_and_mcp_tools_are_refused(self):
        self.assertEqual(self.hook("NotebookEdit", file_path="outbox/draft.md", notebook_path="review/x.ipynb",
                                   new_source="x").returncode, 2)
        self.assertEqual(self.hook("mcp__filesystem__write_file", path="review/verdict.json", content="{}").returncode, 2)
        self.assertEqual(self.hook("mcp__ide__executeCode", code="open('outbox/sent/x.md', 'w')").returncode, 2)

    def test_ordinary_work_passes(self):
        self.assertEqual(self.hook("Write", file_path=str(self.base / "outbox/draft.md"), content="hi").returncode, 0)
        self.assertEqual(self.hook("Bash", command="ls domain").returncode, 0)
        self.assertEqual(self.hook("Read", file_path="domain/policy.md").returncode, 0)


if __name__ == "__main__":
    unittest.main()
