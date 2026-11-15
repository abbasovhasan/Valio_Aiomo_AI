"""Actual long catalog names survive typed conversational cart follow-ups."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend import catalog, interpretation, procurement, product_facts
from backend.config import BUYER, CUSTOMER
from backend.store import Store


def test_every_actual_long_name_can_be_selected_and_followed_up_without_losing_requirements(tmp_path, monkeypatch):
    rows = catalog.load_catalog()
    if not rows:
        pytest.skip('Original private challenge catalog is not installed')
    long_ids = [pid for pid, raw in rows.items()
                if not raw.get('deleted') and len(product_facts.localized(raw.get('synkkaData', {}).get('names', [])) or '') > 120]
    assert long_ids, 'The source regression needs actual catalog names beyond the old limit'
    assert all(len(product_facts.localized(rows[pid].get('synkkaData', {}).get('names', [])) or '') <= 200 for pid in long_ids)

    def no_provider(*args, **kwargs):
        raise AssertionError('Long-name regression must never call a model or supplier')

    monkeypatch.setattr(interpretation, '_model', no_provider)
    monkeypatch.setattr(procurement.upstream, 'sponsor_lookup', no_provider)
    app = FastAPI()
    store = Store(tmp_path / 'long-name-cart.sqlite', postgres=False)

    def buyer():
        return {'role': 'buyer', 'name': 'Source regression buyer', 'buyer_id': BUYER, 'customer_id': CUSTOMER, 'actor_id': 'source-test-buyer', 'principal_id': 'access_code:buyer'}

    procurement.register_routes(app, store, buyer, buyer, buyer, lambda *args: None)
    client = TestClient(app)
    delivery = (date.today() + timedelta(days=2)).isoformat()
    for pid in long_ids:
        selected = client.post(procurement.PREFIX + '/from-product', json={
            'product_id': pid, 'quantity': '2', 'unit': 'packages',
            'date': delivery, 'budget': '200.00', 'mode': 'fixture',
        })
        assert selected.status_code == 200, 'Direct selection failed for a long source name'
        original = selected.json()
        assert len(original['lines']) == 1 and len(original['lines'][0]['requested_label']) > 120
        changed = client.post(procurement.PREFIX + '/' + original['id'] + '/actions', json={
            'version': original['version'], 'action': 'message', 'message': 'Budget €150',
        })
        assert changed.status_code == 200, 'A conversational follow-up rejected a valid source name'
        updated = changed.json()
        assert len(updated['lines']) == 1
        assert updated['lines'][0]['id'] == original['lines'][0]['id']
        assert updated['lines'][0]['selected_product_id'] == pid
        assert updated['lines'][0]['requested_label'] == original['lines'][0]['requested_label']
        assert Decimal(updated['lines'][0]['quantity']) == 2 and updated['lines'][0]['unit'] == 'packages'
        assert updated['constraints']['delivery_date'] == delivery
        assert Decimal(updated['constraints']['budget']) == 150
        assert not updated['ambiguities'] and updated['receipt'] is None
        assert store.get('procurement', original['id'], BUYER)['version'] == updated['version']
    with store.tx() as connection:
        orders = connection.execute('SELECT COUNT(*) FROM aimo_orders').fetchone()[0]
    assert orders == 0 and store.spent() == 0
