"""Operator-only reset of the shared demonstration's simulated buying records.

Private workspaces, credentials, sessions, security throttles and saved
preferences are preserved. Never exposed over HTTP. Save evidence before use.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import BUYER
from backend.store import Store


def reset_shared_demo(db):
    document_kinds = ('run', 'offer', 'receipt', 'procurement', 'meal_plan')
    audit_kinds = ('run_completed', 'offer_approved', 'meal_plan_created', 'procurement_created', 'meal_plan_quoted', 'procurement_updated', 'basket_approved')
    with db.tx() as c:
        c.execute('DELETE FROM aimo_orders WHERE buyer_id=?', (BUYER,))
        c.execute('DELETE FROM aimo_audit WHERE buyer_id=? AND kind IN (' + ','.join('?' for _ in audit_kinds) + ')', (BUYER, *audit_kinds))
        c.execute('DELETE FROM aimo_documents WHERE buyer_id=? AND kind IN (' + ','.join('?' for _ in document_kinds) + ')', (BUYER, *document_kinds))
        c.execute('UPDATE aimo_accounts SET spent_cents=0 WHERE buyer_id=?', (BUYER,))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm-example-data', action='store_true')
    args = parser.parse_args()
    if not args.confirm_example_data:
        parser.error('Requires --confirm-example-data; deletes shared demonstration purchasing records.')
    store = Store()
    reset_shared_demo(store)
    print('Reset shared demonstration purchasing records only. Private workspaces and authentication preserved. Storage:', store.backend)
