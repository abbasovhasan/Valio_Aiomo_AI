"""History metadata stays personal while original order evidence survives."""

import copy
from datetime import date, timedelta

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from backend import history, procurement, preferences
from backend.config import BUYER, CUSTOMER
from backend.store import Store


@pytest.fixture
def env(tmp_path, monkeypatch):
    product = {
        "id": "history-pasta", "baseUnit": "ST", "salesUnit": "BAG", "allowedLotSize": 1,
        "units": [{"unitId": "BAG", "sizeInBaseUnits": 1}],
        "synkkaData": {"names": [{"language": "en", "value": "Spaghetti"}],
                       "classifications": [],
                       "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "netWeight": {"unit": "KGM", "value": 5}}]},
    }
    monkeypatch.setattr(procurement.catalog, "load_catalog", lambda: {product["id"]: product})
    store = Store(tmp_path / "history.sqlite", postgres=False)
    app = FastAPI()

    def buyer(x_buyer: str = Header(default=BUYER), x_role: str = Header(default="buyer")):
        if x_role != "buyer":
            raise HTTPException(403)
        return {"role": "buyer", "name": "History test", "buyer_id": x_buyer,
                "customer_id": CUSTOMER if x_buyer == BUYER else "customer-" + x_buyer}

    procurement.register_routes(app, store, buyer, buyer, buyer, lambda *args: None)
    history.register_routes(app, store, buyer, lambda *args: None)
    preferences.register_routes(app, store, buyer, lambda *args: None)
    client = TestClient(app)
    delivery = (date.today() + timedelta(days=2)).isoformat()

    def create():
        response = client.post(procurement.PREFIX, json={"message": "6 kg spaghetti. Cheapest.", "date": delivery})
        assert response.status_code == 200, response.text
        return response.json()

    return client, store, create, app, delivery


def test_history_lists_scoped_requests_and_archive_persists(env):
    client, store, create, _, _ = env
    first, second = create(), create()
    result = client.get(history.PREFIX + "?limit=1").json()
    assert result['total'] == 2 and len(result['items']) == 1 and result['offset'] == 0
    assert result['items'][0]['id'] == second['id']
    assert client.get(history.PREFIX + '?offset=1').json()['items'][0]['id'] == first['id']
    assert client.get(history.PREFIX, headers={'X-Buyer': 'other'}).json()['items'] == []
    assert client.get(history.PREFIX + '/' + first['id'], headers={'X-Buyer': 'other'}).status_code == 404
    assert client.patch(history.PREFIX + '/' + first['id'], json={'archived': True}, headers={'X-Buyer': 'other'}).status_code == 404
    archived = client.patch(history.PREFIX + '/' + first['id'], json={'archived': True})
    assert archived.status_code == 200 and archived.json()['archived']
    assert client.get(history.PREFIX).json()['total'] == 1
    assert client.get(history.PREFIX + '?archived=true').json()['items'][0]['id'] == first['id']
    reopened = Store(store.path, postgres=False)
    assert reopened.get('history_state', 'history-state-' + first['id'], BUYER)['archived']
    assert client.patch(history.PREFIX + '/' + first['id'], json={'archived': False}).status_code == 200
    assert client.get(history.PREFIX).json()['total'] == 2


def test_history_detail_is_typed_and_does_not_expose_raw_product_or_evidence(env):
    client, store, create, _, _ = env
    session = create()
    detail = client.get(history.PREFIX + '/' + session['id'])
    assert detail.status_code == 200, detail.text
    assert detail.json() == client.get(procurement.PREFIX + '/' + session['id']).json()
    candidate = detail.json()['lines'][0]['candidates'][0]
    assert 'product' not in candidate and 'commercial' not in candidate
    assert candidate['product_details']['id'] == 'history-pasta'
    paths = client.get('/openapi.json').json()['paths']
    schema = paths[history.PREFIX + '/{id}']['get']['responses']['200']['content']['application/json']['schema']
    assert schema['$ref'].endswith('/ProcurementSessionResponse')


def test_removing_history_preserves_receipt_ledger_and_immutable_audit(env):
    client, store, create, _, _ = env
    session = create()
    response = client.post(procurement.PREFIX + '/' + session['id'] + '/confirm',
                           json={'fingerprint': session['offer']['fingerprint']},
                           headers={'Idempotency-Key': 'history-test-confirm'})
    assert response.status_code == 200, response.text
    confirmed = response.json()
    saved = store.get('procurement', session['id'], BUYER)
    spent = store.spent()
    with store.tx() as c:
        before = c.execute('SELECT id,kind,body FROM aimo_audit WHERE buyer_id=? ORDER BY id', (BUYER,)).fetchall()
    assert client.delete(history.PREFIX + '/' + session['id']).json()['removed']
    assert client.delete(history.PREFIX + '/' + session['id']).status_code == 200
    assert client.get(history.PREFIX).json()['total'] == 0
    assert client.get(history.PREFIX + '/' + session['id']).status_code == 404
    assert client.patch(history.PREFIX + '/' + session['id'], json={'archived': False}).status_code == 404
    assert client.post(history.PREFIX + '/' + session['id'] + '/reuse', json={}).status_code == 404
    assert store.get('procurement', session['id'], BUYER) == saved
    assert store.order(confirmed['receipt']['id'], BUYER) == confirmed['receipt']
    assert store.spent() == spent
    with store.tx() as c:
        assert c.execute('SELECT id,kind,body FROM aimo_audit WHERE buyer_id=? ORDER BY id', (BUYER,)).fetchall() == before
    assert client.get(procurement.PREFIX + '/' + session['id'] + '/verify').json()['integrity_valid']


def test_reuse_quotes_a_new_request_without_transferring_authority(env):
    client, store, create, _, delivery = env
    original = create()
    confirmed = client.post(procurement.PREFIX + '/' + original['id'] + '/confirm',
                            json={'fingerprint': original['offer']['fingerprint']},
                            headers={'Idempotency-Key': 'history-reuse-confirm'})
    assert confirmed.status_code == 200, confirmed.text
    client.patch(history.PREFIX + '/' + original['id'], json={'archived': True})
    saved = copy.deepcopy(store.get('procurement', original['id'], BUYER))
    response = client.post(history.PREFIX + '/' + original['id'] + '/reuse', json={'date': delivery, 'budget': '20.00', 'mode': 'fixture'})
    assert response.status_code == 200, response.text
    reused = response.json()
    assert reused['id'] != original['id'] and reused['version'] == 1
    assert reused['constraints']['delivery_date'] == delivery and reused['constraints']['budget'] == '20.00'
    assert reused['receipt'] is None and not reused['checkout_pending']
    assert not reused['offer']['approved']
    assert reused['lines'][0]['quantity'] == original['lines'][0]['quantity']
    assert reused['lines'][0]['selected_product_id'] == original['lines'][0]['selected_product_id']
    assert reused['offer']['id'] != original['offer']['id']
    assert store.get('procurement', original['id'], BUYER) == saved


def test_reuse_applies_new_hard_preferences_and_does_not_promise_old_delivery(env):
    client, store, create, _, delivery = env
    original = create()
    assert original['can_confirm']
    saved = copy.deepcopy(store.get('procurement', original['id'], BUYER))
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': ['peanut_free']}).status_code == 200
    response = client.post(history.PREFIX + '/' + original['id'] + '/reuse', json={'date': delivery})
    assert response.status_code == 200, response.text
    reused = response.json()
    assert 'peanut_free' in reused['lines'][0]['dietary']
    assert not reused['can_confirm'] and reused['offer'] is None
    assert any('peanut' in issue for candidate in reused['lines'][0]['candidates'] for issue in candidate['issues'])
    assert store.get('procurement', original['id'], BUYER) == saved
    without_date = client.post(history.PREFIX + '/' + original['id'] + '/reuse', json={})
    assert without_date.status_code == 200, without_date.text
    assert without_date.json()['constraints']['delivery_date'] is None
    assert not without_date.json()['can_confirm']


def test_reuse_preserves_unanswered_product_requirements(env):
    client, store, _, _, delivery = env
    response = client.post(procurement.PREFIX, json={'message': '6 kg spaghetti and some butter', 'date': delivery})
    assert response.status_code == 200, response.text
    original = response.json()
    assert original['ambiguities'] and not original['can_confirm']
    reused = client.post(history.PREFIX + '/' + original['id'] + '/reuse', json={'date': delivery})
    assert reused.status_code == 200, reused.text
    assert reused.json()['ambiguities'] == original['ambiguities']
    assert not reused.json()['can_confirm']


def test_reuse_new_date_clears_only_stale_delivery_explanation(env):
    client, store, _, _, _ = env
    response = client.post(procurement.PREFIX, json={
        'message': '6 kg spaghetti and some butter by Monday. Prefer quality.',
    })
    assert response.status_code == 200, response.text
    original = response.json()
    old_date = original['constraints']['delivery_date']
    old_notes = original['interpretation_notes']
    assert any(note.startswith('Interpreted the delivery deadline as ') for note in old_notes)
    assert original['ambiguities'] and not original['can_confirm']
    other_notes = [note for note in old_notes if not note.startswith('Interpreted the delivery deadline as ')]
    assert other_notes
    new_date = (date.fromisoformat(old_date) + timedelta(days=1)).isoformat()
    response = client.post(history.PREFIX + '/' + original['id'] + '/reuse', json={'date': new_date})
    assert response.status_code == 200, response.text
    reused = response.json()
    assert reused['constraints']['delivery_date'] == new_date
    assert reused['interpretation_notes'] == other_notes
    assert reused['ambiguities'] == original['ambiguities'] and not reused['can_confirm']
    saved = store.get('procurement', reused['id'], BUYER)
    assert saved['constraints']['delivery_date'] == new_date
    assert store.get('procurement', original['id'], BUYER)['interpretation_notes'] == old_notes


def test_history_unselected_request_has_no_price_but_verified_zero_is_retained(env, monkeypatch):
    client, _, create, _, _ = env
    response = client.post(procurement.PREFIX, json={'message': 'I need some butter'})
    assert response.status_code == 200, response.text
    unresolved = response.json()
    assert not unresolved['cart']['items'] and not unresolved['can_confirm']
    entries = client.get(history.PREFIX).json()['items']
    assert next(entry for entry in entries if entry['id'] == unresolved['id'])['total'] is None
    lookup = procurement.fixture_lookup

    def zero_price(*args):
        evidence = lookup(*args)
        for row in evidence['price']['products']:
            row['catalogPrice']['valueWithTax'] = 0
        return evidence

    monkeypatch.setattr(procurement, 'fixture_lookup', zero_price)
    quoted = create()
    assert quoted['cart']['items'] and quoted['cart']['subtotal'] == '0.00'
    entries = client.get(history.PREFIX).json()['items']
    assert next(entry for entry in entries if entry['id'] == quoted['id'])['total'] == '0.00'


def test_history_validates_controls_and_never_accepts_a_caller_scope(env):
    client, _, create, _, _ = env
    session = create()
    url = history.PREFIX + '/' + session['id']
    assert client.get(history.PREFIX + '?limit=101').status_code == 422
    assert client.get(history.PREFIX + '?offset=-1').status_code == 422
    assert client.patch(url, json={'archived': True, 'buyer_id': 'other'}).status_code == 422
    assert client.post(url + '/reuse', json={'date': '2026-99-99'}).status_code == 422
    assert client.post(url + '/reuse', json={'budget': '-1'}).status_code == 422
    assert client.get(history.PREFIX, headers={'X-Role': 'approver'}).status_code == 403
