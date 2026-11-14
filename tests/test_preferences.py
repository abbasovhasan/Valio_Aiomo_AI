import copy

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from backend import preferences
from backend.store import Store


@pytest.fixture
def env(tmp_path):
    db = Store(tmp_path / "preferences.sqlite", postgres=False)
    app = FastAPI()
    def buyer(x_buyer: str = Header(default="alice"), x_role: str = Header(default="buyer")):
        if x_role != "buyer":
            raise HTTPException(403)
        return {"buyer_id": x_buyer, "customer_id": "customer-" + x_buyer}
    preferences.register_routes(app, db, buyer, lambda *args: None)
    return TestClient(app), db


def test_saved_preferences_are_customer_scoped_and_cannot_change_authority(env):
    c, db = env
    saved = c.put('/api/v1/preferences', json={"preferred_brand":"Valio", "preferred_origin":"finland", "preferred_organic":True, "priority":"origin"})
    assert saved.status_code == 200 and saved.json()['updated_at']
    assert c.get('/api/v1/preferences',headers={'X-Buyer':'bob'}).json()['preferred_brand'] is None
    assert c.get('/api/v1/preferences').json()['preferred_brand']=='Valio'
    assert c.put('/api/v1/preferences',json={'autonomous_limit':'1000000'}).status_code==422
    assert c.put('/api/v1/preferences',json={},headers={'X-Role':'approver'}).status_code==403


def test_new_request_defaults_do_not_override_explicit_requirements(env):
    c, db = env
    c.put('/api/v1/preferences',json={'preferred_brand':'Valio','preferred_origin':'finland','preferred_organic':True,'priority':'delivery'})
    scope={'buyer_id':'alice','customer_id':'customer-alice'}
    original={'constraints':{'preferences':'balanced'},'lines':[{'required_brand':'Arla','origin':'eu','require_organic':True},{'preferred_brand':'Other','preferred_origin':'eu'}]}
    session=copy.deepcopy(original)
    preferences.apply_saved(session,db,scope,'20 litres milk by Monday')
    assert session['constraints']['preferences']=='delivery'
    assert session['lines'][0]['required_brand']=='Arla' and session['lines'][0].get('preferred_brand') is None
    assert session['lines'][0].get('preferred_origin') is None
    assert session['lines'][1]['preferred_brand']=='Other' and session['lines'][1]['preferred_origin']=='eu'
    explicit=copy.deepcopy(original)
    explicit['constraints']['preferences']='cheapest'
    preferences.apply_saved(explicit,db,scope,'Choose cheapest')
    assert explicit['constraints']['preferences']=='cheapest'
    # Saving defaults has no access to or mutation of an existing cart record.
    assert original['constraints']['preferences']=='balanced'
