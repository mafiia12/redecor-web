"""Daily enquiries digest (new in the last day, overdue and due follow-ups) to NOTIFY_TO.

    python tools/digest.py --dry-run     # print the e-mail, send nothing, record nothing
    python tools/digest.py               # send today's digest unless it was already sent today
    python tools/digest.py --force       # send again even if today's digest already went out

Inside the stack it runs by itself every day at DIGEST_TIME (HH:MM) in DIGEST_TZ (default Africa/Cairo);
leave DIGEST_TIME empty to switch it off. Without SMTP settings it logs and skips. Files are never attached.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print the digest; send and record nothing")
    ap.add_argument("--force", action="store_true", help="send even if today's digest was already sent")
    a = ap.parse_args()

    import app.models  # noqa: F401
    from app import crm

    result = crm.run_digest(dry_run=a.dry_run, force=a.force)
    print(result if a.dry_run else f"digest: {result}")
    return 1 if result.startswith("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
