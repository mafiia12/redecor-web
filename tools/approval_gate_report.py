"""Dry-run of the approvals gate: which projects and client logos the public site would show WITHOUT the gate
but hides WITH it (no current approval on record), and which photos are hidden for having no Render/Executed
label. Items already hidden for other reasons (draft, [placeholder], test-project-*, no logo) are not listed.
Read-only.

    python tools/approval_gate_report.py            # uses DATABASE_URL / backend/.env
    python tools/approval_gate_report.py --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    import app.models  # noqa: F401
    from app import migrations
    from app.db import SessionLocal
    from app.routers.admin_content import gate_report

    if migrations.pending():
        print("Note: the database has pending migrations; run `python tools/migrate.py up` first (it backs up).")
        if any(m.id == "0003_approvals" for m in migrations.pending()):
            print("The approvals table does not exist yet, so EVERY published project and logo would be hidden.")
            return 0
    with SessionLocal() as db:
        r = gate_report(db)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    print(f"Gate enforced: {r['enforced']}")
    print(f"Projects hidden: {r['counts']['projects']}")
    for p in r["projects_hidden"]:
        print(f"  - {p['slug']}  (approval: {p['status']})")
    print(f"Client logos hidden: {r['counts']['clients']}")
    for c in r["clients_hidden"]:
        print(f"  - client #{c['id']}  (approval: {c['status']})")
    print(f"Photos hidden (no Render/Executed label): {r['counts']['photos']}")
    for x in r["photos_hidden"]:
        print(f"  - {x['slug']}: {x['photos_without_label']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
