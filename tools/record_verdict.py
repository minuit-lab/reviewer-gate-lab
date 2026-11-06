"""Record the reviewer's verdict on the current draft.

Usage: python3 tools/record_verdict.py APPROVE|REJECT "reason"
"""
import datetime
import json
import sys

from verdict import DRAFT, VERDICT, draft_hash, root


def main(argv):
    if len(argv) != 3 or argv[1] not in ("APPROVE", "REJECT"):
        print(__doc__, file=sys.stderr)
        return 2
    base = root()
    if not (base / DRAFT).exists():
        print("No draft at outbox/draft.md.", file=sys.stderr)
        return 1
    (base / VERDICT).parent.mkdir(parents=True, exist_ok=True)
    record = {
        "verdict": argv[1],
        "reason": argv[2],
        "draft_sha256": draft_hash(base),
        "recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    (base / VERDICT).write_text(json.dumps(record, indent=2) + "\n")
    print("Recorded %s for draft %s." % (argv[1], record["draft_sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
