"""PreToolUse hook: the mechanical gate.

Blocks (exit code 2, reason on stderr, which Claude Code shows to the model):
- tools/send_reply.py without an APPROVE verdict matching the current draft;
- any write into review/ or outbox/sent/, and any change to the gate itself
  (.claude/ and tools/), except through the two scripts run on their own;
- anything at all if the gate itself fails: it fails closed.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
from verdict import check, root  # noqa: E402

GUARDED = ("review", "outbox/sent", ".claude", "tools")
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# The two scripts are allowed only as a whole command: no ;, &&, |, redirection or substitution.
SCRIPT = re.compile(r"python3 tools/(record_verdict|send_reply)\.py( [^;&|<>`$\n]*)?")
GUARDED_IN_SHELL = re.compile(r"(?<![\w.-])(review|outbox/sent|\.claude|tools)(?=/|\s|$|['\"])")


def inside_guarded(path, base):
    target = Path(path)
    if not target.is_absolute():
        target = base / target
    target = target.resolve()
    for guarded in GUARDED:
        try:
            target.relative_to((base / guarded).resolve())
            return True
        except ValueError:
            pass
    return False


def decide(event, base):
    """Return (allowed, reason) for one PreToolUse event."""
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if path and inside_guarded(path, base):
            return False, "review/, outbox/sent/, .claude/ and tools/ are off limits. Verdicts and sends go through the two scripts."
        return True, ""
    if tool == "Bash":
        command = tool_input.get("command", "").strip()
        script = SCRIPT.fullmatch(command)
        if script:
            return check(base) if script.group(1) == "send_reply" else (True, "")
        if "record_verdict.py" in command or "send_reply.py" in command:
            return False, "Run tools/record_verdict.py or tools/send_reply.py on its own, as a single command."
        if GUARDED_IN_SHELL.search(command):
            return False, "Shell commands may not touch review/, outbox/sent/, .claude/ or tools/."
    return True, ""


def main():
    try:
        allowed, reason = decide(json.load(sys.stdin), root())
    except Exception as error:  # fail closed: a broken gate blocks everything
        allowed, reason = False, "Gate error, blocked by default: %r" % error
    if not allowed:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
