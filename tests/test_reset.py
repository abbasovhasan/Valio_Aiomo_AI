from backend.config import BUYER
from backend.store import Store
from scripts.backend_reset import reset_shared_demo


def test_shared_rehearsal_reset_preserves_private_and_security_records(tmp_path):
    db = Store(tmp_path / 'reset.sqlite', postgres=False)
    for kind in ['procurement', 'meal_plan', 'preferences', 'session', 'auth_rate']:
        db.save(kind, 'shared-'+kind, BUYER, {'kind':kind})
        db.save(kind, 'private-'+kind, 'buyer-private', {'kind':kind})
    with db.tx() as c:
        c.execute('INSERT INTO aimo_accounts(buyer_id,spent_cents) VALUES(?,?)', ('buyer-private',12345))
        c.execute('UPDATE aimo_accounts SET spent_cents=999 WHERE buyer_id=?',(BUYER,))
    reset_shared_demo(db)
    assert db.get('procurement','shared-procurement',BUYER) is None
    assert db.get('meal_plan','shared-meal_plan',BUYER) is None
    for kind in ['preferences','session','auth_rate']:
        assert db.get(kind,'shared-'+kind,BUYER)=={'kind':kind}
    for kind in ['procurement','meal_plan','preferences','session','auth_rate']:
        assert db.get(kind,'private-'+kind,'buyer-private')=={'kind':kind}
    assert db.spent()==0 and db.spent('buyer-private')==12345
