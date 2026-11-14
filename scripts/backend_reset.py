"""Local operator-only reset of this prototype's SIMULATED data.

Never exposed over HTTP. Existing research, raw data, credentials and other DB
schemas remain untouched. Use only for a new rehearsal after saving evidence.
"""

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.store import Store

p = argparse.ArgumentParser()
p.add_argument("--confirm-example-data", action="store_true")
a = p.parse_args()
if not a.confirm_example_data:
    p.error("Requires --confirm-example-data; deletes only aimo simulator records.")
db = Store()
with db.tx() as c:
    for table in ["aimo_orders", "aimo_audit", "aimo_documents"]:
        c.execute("DELETE FROM " + table)
    c.execute("UPDATE aimo_accounts SET spent_cents=0")
print(
    "Reset only Aimo simulated orders, offers, audit events and synthetic spend. Storage:",
    db.backend,
)
