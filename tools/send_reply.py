"""Send the approved draft. "Sending" here means filing it in outbox/sent/.

The script checks the verdict itself too, so it refuses even when run outside Claude Code.
One verdict allows one send: the verdict is deleted after sending.
"""
import datetime
import shutil
import sys

from verdict import DRAFT, SENT_DIR, VERDICT, check, root


def main():
    base = root()
    ok, reason = check(base)
    if not ok:
        print("Not sent. " + reason, file=sys.stderr)
        return 1
    (base / SENT_DIR).mkdir(parents=True, exist_ok=True)
    target = base / SENT_DIR / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".md")
    shutil.copyfile(base / DRAFT, target)
    (base / VERDICT).unlink()
    print("Sent: %s" % target.relative_to(base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
