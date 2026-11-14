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


def test_saved_hard_restrictions_merge_with_prompt_and_persist_after_restart(env):
    c, db = env
    saved = c.put('/api/v1/preferences', json={
        'dietary_restrictions': ['no_pork', 'peanut_free', 'peanut_free'],
        'excluded_ingredients': ['  Coconut ', 'coconut'],
        'custom_preferences': 'Prefer whole grain when available.',
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()['dietary_restrictions'] == ['no_pork', 'peanut_free']
    assert saved.json()['excluded_ingredients'] == ['coconut']
    scope = {'buyer_id': 'alice', 'customer_id': 'customer-alice'}
    reopened = Store(db.path, postgres=False)
    session = {'constraints': {'preferences': 'cheapest'}, 'lines': [
        {'dietary': ['vegan'], 'excluded_ingredients': ['palm oil']},
        {'dietary': ['milk_free']},
    ]}
    preferences.enforce_hard(session, reopened, scope)
    assert session['lines'][0]['dietary'] == ['vegan', 'no_pork', 'peanut_free']
    assert session['lines'][1]['dietary'] == ['milk_free', 'no_pork', 'peanut_free']
    assert session['lines'][0]['excluded_ingredients'] == ['palm oil', 'coconut']
    assert session['constraints']['preferences'] == 'cheapest'
    assert preferences.read(reopened, {'buyer_id': 'bob'})['dietary_restrictions'] == []


def test_hard_only_application_cannot_apply_soft_brand_or_change_authority(env):
    c, db = env
    c.put('/api/v1/preferences', json={'dietary_restrictions': ['peanut_free'], 'preferred_brand': 'Valio', 'priority': 'quality'})
    session = {'constraints': {'preferences': 'balanced'}, 'lines': [{'dietary': []}]}
    preferences.apply_saved(session, db, {'buyer_id': 'alice'}, hard_only=True)
    assert session['lines'][0]['dietary'] == ['peanut_free']
    assert session['lines'][0].get('preferred_brand') is None
    assert session['constraints']['preferences'] == 'balanced'
    assert c.put('/api/v1/preferences', json={'dietary_restrictions': ['allergy_safe']}).status_code == 422
    assert c.put('/api/v1/preferences', json={'excluded_ingredients': ['x' * 81]}).status_code == 422


def test_clearing_saved_only_restrictions_updates_effective_cart_without_dropping_requested_rules(env):
    client, db = env
    scope = {'buyer_id': 'alice'}
    session = {'lines': [{'dietary': ['gluten_free'], 'excluded_ingredients': ['palm oil']}]}
    assert client.put('/api/v1/preferences', json={
        'dietary_restrictions': ['no_pork', 'peanut_free'], 'excluded_ingredients': ['coconut'],
    }).status_code == 200
    preferences.enforce_hard(session, db, scope)
    line = session['lines'][0]
    assert line['requested_dietary'] == ['gluten_free']
    assert line['requested_excluded_ingredients'] == ['palm oil']
    assert line['dietary'] == ['gluten_free', 'no_pork', 'peanut_free']
    assert line['excluded_ingredients'] == ['palm oil', 'coconut']
    assert client.put('/api/v1/preferences', json={}).status_code == 200
    preferences.enforce_hard(session, db, scope)
    assert line['dietary'] == ['gluten_free']
    assert line['excluded_ingredients'] == ['palm oil']
    assert session['saved_restrictions_applied'] == {'dietary_restrictions': [], 'excluded_ingredients': []}


def test_requested_overlap_is_preserved_when_same_saved_requirement_is_removed(env):
    client, db = env
    scope = {'buyer_id': 'alice'}
    session = {'lines': [{'dietary': ['no_pork', 'peanut_free'], 'excluded_ingredients': ['coconut']}]}
    assert client.put('/api/v1/preferences', json={
        'dietary_restrictions': ['no_pork', 'peanut_free'], 'excluded_ingredients': ['coconut'],
    }).status_code == 200
    preferences.enforce_hard(session, db, scope)
    assert client.put('/api/v1/preferences', json={}).status_code == 200
    preferences.enforce_hard(session, db, scope)
    assert session['lines'][0]['dietary'] == ['no_pork', 'peanut_free']
    assert session['lines'][0]['excluded_ingredients'] == ['coconut']


def test_empty_requested_provenance_allows_saved_toggle_and_soft_optout_cannot_bypass_active_hard_rules(env):
    client, db = env
    scope = {'buyer_id': 'alice'}
    session = {'constraints': {'preferences': 'balanced'}, 'lines': [{
        'requested_dietary': [], 'requested_excluded_ingredients': [],
        'dietary': [], 'excluded_ingredients': [],
    }]}
    for restriction, exclusions in [('no_pork', ['coconut']), ('milk_free', ['sesame oil'])]:
        assert client.put('/api/v1/preferences', json={
            'dietary_restrictions': [restriction], 'excluded_ingredients': exclusions, 'preferred_brand': 'Valio',
        }).status_code == 200
        preferences.apply_saved(session, db, scope, hard_only=True)
        assert session['lines'][0]['dietary'] == [restriction]
        assert session['lines'][0]['excluded_ingredients'] == exclusions
        assert session['lines'][0]['requested_dietary'] == []
        assert session['lines'][0]['requested_excluded_ingredients'] == []
        assert session['lines'][0].get('preferred_brand') is None
    assert client.put('/api/v1/preferences', json={}).status_code == 200
    preferences.enforce_hard(session, db, scope)
    assert session['lines'][0]['dietary'] == [] and session['lines'][0]['excluded_ingredients'] == []


@pytest.mark.parametrize('text,expected', [
    ('I need milk; peanut allergy.', ['peanut_free']),
    ('Nut and peanut allergies', ['nut_free', 'peanut_free']),
    ('allergic to milk and eggs', ['milk_free', 'egg_free']),
    ('no pork, halal and gluten-free', ['gluten_free', 'no_pork', 'halal']),
    ('milk chocolate and peanut butter', []),
    ('shellfish allergy', ['crustacean_free', 'mollusc_free']),
    ('wheat allergy', []),
])
def test_restriction_words_are_extracted_without_inventing_allergies(text, expected):
    assert set(preferences.dietary_from_text(text)) == set(expected)
