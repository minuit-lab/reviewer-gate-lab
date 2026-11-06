"""Send the approved draft. "Sending" here means filing it in outbox/sent/.

The script checks the verdict itself too, so it refuses even when run outside Claude Code.
One verdict allows one send: the verdict is deleted after sending.
"""
import datetime
import sys

from verdict import DRAFT, SENT_DIR, VERDICT, check, root


def main():
    base = root()
    data = (base / DRAFT).read_bytes() if (base / DRAFT).exists() else b""
    ok, reason = check(base, data)  # the bytes checked are the bytes sent
    if not ok:
        print("Not sent. " + reason, file=sys.stderr)
        return 1
    (base / SENT_DIR).mkdir(parents=True, exist_ok=True)
    target = base / SENT_DIR / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".md")
    target.write_bytes(data)
    (base / VERDICT).unlink()
    print("Sent: %s" % target.relative_to(base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
