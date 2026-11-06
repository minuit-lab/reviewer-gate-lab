"""Shared verdict logic. A verdict is bound to one exact draft by its SHA-256."""
import hashlib
import json
import os
from pathlib import Path

DRAFT = Path("outbox/draft.md")
VERDICT = Path("review/verdict.json")
SENT_DIR = Path("outbox/sent")


def root():
    """Repository root. LAB_ROOT overrides it, so tests can run in a temp dir."""
    return Path(os.environ.get("LAB_ROOT") or Path(__file__).resolve().parent.parent)


def draft_hash(base):
    return hashlib.sha256((base / DRAFT).read_bytes()).hexdigest()


def check(base):
    """Return (ok, reason). ok only if an APPROVE verdict matches the current draft."""
    if not (base / DRAFT).exists():
        return False, "No draft at outbox/draft.md."
    path = base / VERDICT
    if not path.exists():
        return False, "No reviewer verdict. Ask the reviewer subagent to review outbox/draft.md first."
    try:
        verdict = json.loads(path.read_text())
    except ValueError:
        return False, "review/verdict.json is not valid JSON."
    if not isinstance(verdict, dict):
        return False, "review/verdict.json is not a verdict."
    if verdict.get("draft_sha256") != draft_hash(base):
        return False, "The draft changed after it was reviewed. Ask the reviewer to review it again."
    if verdict.get("verdict") != "APPROVE":
        return False, "The reviewer rejected this draft: %s" % verdict.get("reason", "")
    return True, "Draft approved by the reviewer."
