"""Shared verdict logic. A verdict is bound to one exact draft by its SHA-256."""
import hashlib
import json
import os
import stat
from pathlib import Path

DRAFT = Path("outbox/draft.md")
VERDICT = Path("review/verdict.json")
SENT_DIR = Path("outbox/sent")


def root():
    """Repository root. LAB_ROOT overrides it, so tests can run in a temp dir."""
    return Path(os.environ.get("LAB_ROOT") or Path(__file__).resolve().parent.parent)


def draft_problem(base):
    """Why the draft cannot be trusted as a plain file, or "" if it can.

    A link would let a write to the draft land on another file, the gate for instance.
    """
    for path in (base / DRAFT.parent, base / DRAFT):
        try:
            info = os.lstat(str(path))
        except FileNotFoundError:
            return ""
        if stat.S_ISLNK(info.st_mode):
            return "%s is a link. The draft must be a plain file." % path.relative_to(base)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        return "outbox/draft.md is not a plain file with a single name."
    return ""


def draft_hash(base, data=None):
    if data is None:
        data = (base / DRAFT).read_bytes()
    return hashlib.sha256(data).hexdigest()


def check(base, data=None):
    """Return (ok, reason). ok only if an APPROVE verdict matches the draft.

    data: the draft bytes the caller is about to send, read once, so that what is
    checked is exactly what is sent.
    """
    if not (base / DRAFT).exists():
        return False, "No draft at outbox/draft.md."
    problem = draft_problem(base)
    if problem:
        return False, problem
    path = base / VERDICT
    if not path.exists():
        return False, "No reviewer verdict. Ask the reviewer subagent to review outbox/draft.md first."
    try:
        verdict = json.loads(path.read_text())
    except ValueError:
        return False, "review/verdict.json is not valid JSON."
    if not isinstance(verdict, dict):
        return False, "review/verdict.json is not a verdict."
    if verdict.get("draft_sha256") != draft_hash(base, data):
        return False, "The draft changed after it was reviewed. Ask the reviewer to review it again."
    if verdict.get("verdict") != "APPROVE":
        return False, "The reviewer rejected this draft: %s" % verdict.get("reason", "")
    return True, "Draft approved by the reviewer."
