"""PreToolUse hook: the mechanical gate. It runs before every tool call (matcher ".*").

Blocks (exit code 2, reason on stderr, which Claude Code shows to the model):
- tools/send_reply.py without an APPROVE verdict matching the current draft;
- Write, Edit, MultiEdit and NotebookEdit anywhere except outbox/draft.md, and even
  there if the draft or its folder is a link;
- shell commands (Bash, or any tool that carries a "command") that name review/,
  outbox/, .claude/, tools/, .git or git, except the two scripts run on their own;
- every MCP tool (mcp__...): the lab needs none, and their inputs have no fixed shape;
- anything at all if the gate itself fails, including a broken import: it fails closed.

Paths and shell names are compared without case, because the default macOS disk
treats Outbox/Sent and outbox/sent as the same folder.

The shell check reads the text of a command. It is a tripwire, not a wall: a name
built at run time gets through. The wall is the Claude Code sandbox.
"""
import json
import re
import sys
from pathlib import Path

FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
WRITABLE = "outbox/draft.md"
# The two scripts are allowed only as a whole command. The reason is one quoted string:
# inside double quotes, no " $ ` or backslash, so nothing in it can run.
SCRIPT = re.compile(r"python3 tools/(?:(send_reply)\.py"
                    r"|record_verdict\.py (?:APPROVE|REJECT) (?:\"[^\"$`\\]*\"|'[^']*'))")
# The writer never needs the shell on these: it writes the draft with Write and sends with
# the script. git is guarded because it can bring back an older gate from history.
GUARDED_IN_SHELL = re.compile(r"(?<![\w-])(review|outbox|\.claude|tools|\.git|git)(?![\w-])", re.I)


def same_path(path, base, relative):
    target = Path(path)
    if not target.is_absolute():
        target = base / target
    return str(target.resolve()).casefold() == str((base / relative).resolve()).casefold()


def decide(event, base, check, draft_problem=lambda base: ""):
    """Return (allowed, reason) for one PreToolUse event."""
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        problem = draft_problem(base)  # a linked draft makes every resolved path suspect
        paths = [tool_input[key] for key in ("file_path", "notebook_path") if key in tool_input]
        if not paths or not all(same_path(path, base, WRITABLE) for path in paths):
            return False, "The writer may only write outbox/draft.md. Verdicts and sends go through the two scripts."
        return (False, problem) if problem else (True, "")
    if tool.startswith("mcp__"):
        return False, "The lab uses no MCP tool: an MCP server could write or run anything."
    command = tool_input.get("command")
    if command is not None:
        command = command.strip()
        script = SCRIPT.fullmatch(command)
        if script:
            return check(base) if script.group(1) == "send_reply" else (True, "")
        if "record_verdict.py" in command.lower() or "send_reply.py" in command.lower():
            return False, "Run tools/record_verdict.py or tools/send_reply.py on its own, as a single command."
        if GUARDED_IN_SHELL.search(command):
            return False, "Shell commands may not touch review/, outbox/, .claude/, tools/ or git. Write the draft with Write."
    return True, ""


def main():
    try:  # fail closed: a broken gate, even a broken import, blocks everything
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
        from verdict import check, draft_problem, root
        allowed, reason = decide(json.load(sys.stdin), root(), check, draft_problem)
    except BaseException as error:
        allowed, reason = False, "Gate error, blocked by default: %r" % error
    if not allowed:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
