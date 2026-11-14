"""Independent safety boundaries through real discovery and purchasing routes.

Catalog/commercial examples are authored; all persistence is isolated. No live
providers or shared/private customer ledgers are modified by these tests.
"""

from datetime import date, timedelta

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from backend import catalog, preferences, procurement, product_facts, product_search, upstream
from backend.config import BUYER, CUSTOMER
from backend.store import Store


def product(pid, name, *, claims=(), allergens=(), ingredients=None, volume=None):
    conversion = {'synkkaPackagingType': 'BASE_UNIT_OR_EACH', 'netWeight': {'unit': 'KGM', 'value': 2}}
    if volume is not None:
        conversion['volume'] = {'unit': 'LTR', 'value': volume}
    return {
        'id': pid, 'category': 'authored-safety', 'baseUnit': 'ST', 'salesUnit': 'KI',
        'allowedLotSize': 1, 'deleted': False, 'deposits': [],
        'units': [{'unitId': 'KI', 'sizeInBaseUnits': 1}],
        'synkkaData': {
            'brand': 'Safety test', 'names': [{'language': 'en', 'value': name}],
            'unitConversions': [conversion], 'countriesOfOrigin': ['246'],
            'keyIngredients': [{'language': 'en', 'value': ingredients}] if ingredients else [],
            'classifications': [
                {'name': 'nutritionalClaim', 'values': [{'id': c} for c in claims]},
                {'name': 'allergen', 'values': list(allergens)},
            ],
        },
    }


@pytest.fixture
def env(tmp_path, monkeypatch):
    rows = {
        'plain-milk': product('plain-milk', 'Plain milk 1 L', volume=1),
        'vanilla': product('vanilla', 'Vanilla milk drink 1 L', volume=1),
        'beef': product('beef', 'Minced beef'),
        'meatballs': product('meatballs', 'Cooked minced beef meatballs'),
        'lentils': product('lentils', 'Lentils', claims=['VEGAN']),
        'pork': product('pork', 'Bacon', ingredients='Pork, salt', claims=['VEGAN']),
        'unknown': product('unknown', 'Chicken breast'),
        'chocolate': product('chocolate', 'Chocolate'),
    }
    rows.update({f'cheese-{i:02d}': product(f'cheese-{i:02d}', f'Cheddar cheese variant {i:02d}') for i in range(24)})
    monkeypatch.setattr(catalog, 'load_catalog', lambda: rows)
    monkeypatch.setattr(catalog, 'supplemental', lambda: {})
    store = Store(tmp_path / 'search-safety.sqlite', postgres=False)
    app = FastAPI()

    def identity(x_role: str = Header(default='buyer')):
        return {'role': x_role, 'name': 'Authored safety ' + x_role, 'buyer_id': BUYER, 'customer_id': CUSTOMER}

    def buyer(scope=Depends(identity)):
        if scope['role'] != 'buyer':
            raise HTTPException(403)
        return scope

    def approver(scope=Depends(identity)):
        if scope['role'] != 'approver':
            raise HTTPException(403)
        return scope

    procurement.register_routes(app, store, buyer, approver, identity, lambda *args: None)
    preferences.register_routes(app, store, buyer, lambda *args: None)
    app.state.search_rate_calls = []
    product_search.register_routes(app, store, identity, lambda *args: app.state.search_rate_calls.append(args))
    return TestClient(app), store, rows, (date.today() + timedelta(days=2)).isoformat()


def create(env, message='2 kg lentils. Choose cheapest.', **fields):
    response = env[0].post(procurement.PREFIX, json={'message': message, 'date': env[3], 'mode': 'fixture', 'use_model': False, **fields})
    assert response.status_code == 200, response.text
    return response.json()


def action(env, session, name, **fields):
    return env[0].post(procurement.PREFIX + '/' + session['id'] + '/actions', json={'version': session['version'], 'action': name, **fields})


@pytest.mark.parametrize('query,unit,plain,prepared', [('milk', 'L', 'plain-milk', 'vanilla'), ('minced beef', 'kg', 'beef', 'meatballs')])
def test_generic_ingredient_never_silently_chooses_a_cheaper_prepared_variant(env, monkeypatch, query, unit, plain, prepared):
    original_lookup = procurement.fixture_lookup

    def prices(*args):
        evidence = original_lookup(*args)
        for row in evidence['price']['products']:
            row['catalogPrice']['valueWithTax'] = 10 if str(row['productId']) == plain else .10
        return evidence

    monkeypatch.setattr(procurement, 'fixture_lookup', prices)
    session = create(env, f'2 {unit} {query}. Choose cheapest.')
    line = session['lines'][0]
    assert line['selected_product_id'] == plain
    option = next(c for c in line['candidates'] if c['id'] == prepared)
    assert option['requires_explicit_choice']
    assert option['unit_price'] == '0.10' and session['can_confirm']
    chosen = action(env, session, 'select_product', line_id=line['id'], product_id=prepared)
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()['lines'][0]['selected_product_id'] == prepared


@pytest.mark.parametrize('pid,allowed', [('pork', False), ('unknown', False), ('lentils', True)])
def test_no_pork_filters_actual_search_and_direct_cart_even_when_soft_preferences_disabled(env, pid, allowed):
    client = env[0]
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': ['no_pork']}).status_code == 200
    response = client.get('/api/v1/products', params={'q': pid, 'date': env[3], 'mode': 'fixture', 'apply_preferences': 'false'})
    assert response.status_code == 200, response.text
    assert bool(response.json()['products']) is allowed
    added = client.post(procurement.PREFIX + '/from-product', json={'product_id': pid, 'date': env[3], 'mode': 'fixture', 'apply_preferences': False})
    assert added.status_code == (200 if allowed else 422), added.text
    if allowed:
        assert added.json()['lines'][0]['dietary'] == ['no_pork']
        assert added.json()['can_confirm']
    assert env[1].spent() == 0


@pytest.mark.parametrize('restriction,code', [('milk_free', 'AM'), ('peanut_free', 'AP'), ('nut_free', 'AN')])
@pytest.mark.parametrize('declaration,allowed', [('CONTAINS', False), ('MAY_CONTAIN', False), ('UNDECLARED', False), (None, False), ('FREE_FROM', True)])
def test_allergen_units_require_explicit_absence_and_never_infer_safety(env, restriction, code, declaration, allowed):
    # Official source meanings, not inferred labels from a product name:
    # https://ref.gs1.org/voc/AllergenTypeCode
    # https://ref.gs1.org/guidelines/gdm-implementation/1.8.0/ section 13.4.1
    client, store, rows, delivery = env
    values = [{'id': code, 'unit': declaration}] if declaration is not None else []
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = values
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': [restriction]}).status_code == 200
    found = client.get('/api/v1/products', params={'q': 'chocolate', 'date': delivery, 'mode': 'fixture'})
    assert found.status_code == 200, found.text
    assert bool(found.json()['products']) is allowed
    created = client.post(procurement.PREFIX + '/from-product', json={'product_id': 'chocolate', 'date': delivery, 'mode': 'fixture'})
    assert created.status_code == (200 if allowed else 422), created.text
    if allowed:
        assert created.json()['can_confirm']
    else:
        assert created.json()['detail']['code'] == 'product_ineligible'
    assert store.spent() == 0


def test_explicit_allergen_contradiction_overrides_positive_free_from_claim(env):
    _, _, rows, _ = env
    rows['chocolate']['synkkaData']['classifications'][0]['values'] = [{'id': 'FREE_FROM_MILK'}]
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [{'id': 'AM', 'unit': 'MAY_CONTAIN'}]
    assert product_facts.suitability(product_facts.normalize('chocolate'), ['milk_free'])


@pytest.mark.parametrize('restriction,code', [('milk_free', 'AM'), ('peanut_free', 'AP'), ('nut_free', 'AN')])
def test_source_non_allergen_free_from_evidence_is_used_and_conflicts_still_block(env, restriction, code):
    client, _, rows, delivery = env
    # The actual challenge dataset uses nonAllergen for explicit FREE_FROM
    # records. Keeping only the allergen group discards that verified source.
    rows['chocolate']['synkkaData']['classifications'].append({
        'name': 'nonAllergen', 'values': [{'id': code, 'unit': 'FREE_FROM'}],
    })
    assert not product_facts.suitability(product_facts.normalize('chocolate'), [restriction])
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': [restriction]}).status_code == 200
    response = client.post(procurement.PREFIX + '/from-product', json={'product_id': 'chocolate', 'date': delivery, 'mode': 'fixture'})
    assert response.status_code == 200 and response.json()['can_confirm'], response.text
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [{'id': code, 'unit': 'MAY_CONTAIN'}]
    assert product_facts.suitability(product_facts.normalize('chocolate'), [restriction])
    refused = client.post(procurement.PREFIX + '/from-product', json={'product_id': 'chocolate', 'date': delivery, 'mode': 'fixture'})
    assert refused.status_code == 422 and refused.json()['detail']['code'] == 'product_ineligible'


@pytest.mark.parametrize('diet,code', [('vegan', 'AM'), ('vegan', 'AE'), ('vegan', 'AF'), ('vegetarian', 'AF'), ('vegetarian', 'AC'), ('vegetarian', 'UM')])
def test_explicit_contained_animal_allergen_cannot_be_hidden_by_vegan_or_vegetarian_claim(env, diet, code):
    _, _, rows, _ = env
    rows['chocolate']['synkkaData']['classifications'][0]['values'] = [{'id': diet.upper()}]
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [{'id': code, 'unit': 'CONTAINS'}]
    assert product_facts.suitability(product_facts.normalize('chocolate'), [diet]), 'Contradictory supplier declarations need review, not verified compliance'


@pytest.mark.parametrize('declaration,allowed', [('CONTAINS', False), ('MAY_CONTAIN', False), ('UNDECLARED', False), ('FREE_FROM', True)])
def test_no_pork_uses_explicit_gs1_pork_code_even_without_a_pork_name(env, declaration, allowed):
    _, _, rows, _ = env
    # PO is pork according to the official GS1 AllergenTypeCode dictionary.
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [{'id': 'PO', 'unit': declaration}]
    issues = product_facts.suitability(product_facts.normalize('chocolate'), ['no_pork'])
    assert (not issues) is allowed
    if declaration in {'CONTAINS', 'MAY_CONTAIN'}:
        rows['chocolate']['synkkaData']['classifications'][0]['values'] = [{'id': 'VEGAN'}]
        assert product_facts.suitability(product_facts.normalize('chocolate'), ['no_pork'])


@pytest.mark.parametrize('subtype', ['ABD', 'ADQ'])
def test_fish_subtype_contradiction_cannot_be_hidden_by_generic_fish_absence(env, subtype):
    _, _, rows, _ = env
    # Actual source codes verified from GS1: ABD=tuna, ADQ=pollock.
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [
        {'id': 'AF', 'unit': 'FREE_FROM'}, {'id': subtype, 'unit': 'CONTAINS'},
    ]
    assert product_facts.suitability(product_facts.normalize('chocolate'), ['fish_free'])


@pytest.mark.parametrize('subtype', ['GK', 'GS'])
def test_wheat_subtype_contradiction_cannot_be_hidden_by_generic_gluten_absence(env, subtype):
    _, _, rows, _ = env
    # Actual source codes verified from GS1: GK=kamut, GS=spelt.
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [
        {'id': 'AW', 'unit': 'FREE_FROM'}, {'id': subtype, 'unit': 'CONTAINS'},
    ]
    assert product_facts.suitability(product_facts.normalize('chocolate'), ['gluten_free'])


@pytest.mark.parametrize('diet,code', [('vegan', 'BF'), ('vegan', 'CM'), ('vegetarian', 'BF'), ('vegetarian', 'CM')])
def test_contained_meat_codes_contradict_dietary_claims_without_name_inference(env, diet, code):
    _, _, rows, _ = env
    rows['chocolate']['synkkaData']['classifications'][0]['values'] = [{'id': diet.upper()}]
    rows['chocolate']['synkkaData']['classifications'][1]['values'] = [{'id': code, 'unit': 'CONTAINS'}]
    assert product_facts.suitability(product_facts.normalize('chocolate'), [diet])


def test_saved_restriction_change_blocks_old_quote_before_spending_and_refresh_applies_it(env):
    client, store, _, _ = env
    session = create(env)
    assert session['can_confirm']
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': ['peanut_free']}).status_code == 200
    response = client.post(procurement.PREFIX + '/' + session['id'] + '/confirm',
                           json={'fingerprint': session['offer']['fingerprint']},
                           headers={'Idempotency-Key': 'search-safety-stale-diet'})
    assert response.status_code == 409 and response.json()['detail']['code'] == 'preferences_changed'
    assert store.spent() == 0 and store.get('procurement', session['id'], BUYER)['receipt'] is None
    refreshed = action(env, session, 'quote')
    assert refreshed.status_code == 200, refreshed.text
    assert not refreshed.json()['can_confirm'] and refreshed.json()['offer'] is None
    assert 'peanut_free' in refreshed.json()['lines'][0]['dietary']


def test_failed_quote_preserves_selected_draft_and_same_session_can_retry(env, monkeypatch):
    client, store, _, delivery = env
    original_lookup = procurement.fixture_lookup

    def unavailable(*args):
        raise upstream.UpstreamError('Authored temporary supplier outage')

    monkeypatch.setattr(procurement, 'fixture_lookup', unavailable)
    response = client.post(procurement.PREFIX + '/from-product', json={'product_id': 'lentils', 'quantity': '3', 'unit': 'kg', 'date': delivery, 'mode': 'fixture'})
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['lines'][0]['selected_product_id'] == 'lentils'
    assert session['lines'][0]['quantity'] == '3'
    assert session['cart']['subtotal'] is None and not session['can_confirm']
    assert session['quotation_error'] and session['offer'] is None
    assert client.get(procurement.PREFIX + '/' + session['id']).json()['lines'][0]['selected_product_id'] == 'lentils'
    monkeypatch.setattr(procurement, 'fixture_lookup', original_lookup)
    retried = action(env, session, 'quote')
    assert retried.status_code == 200, retried.text
    assert retried.json()['id'] == session['id'] and retried.json()['version'] == session['version'] + 1
    assert retried.json()['lines'][0]['selected_product_id'] == 'lentils'
    assert retried.json()['can_confirm'] and retried.json()['cart']['subtotal'] is not None
    assert store.spent() == 0


def test_catalog_choice_outside_smart_shortlist_can_replace_current_product(env):
    session = create(env, '8 kg cheddar cheese. Choose cheapest.')
    line = session['lines'][0]
    assert len(line['candidates']) == 16
    shortlist = {candidate['id'] for candidate in line['candidates']}
    outside = next(pid for pid in env[2] if pid.startswith('cheese-') and pid not in shortlist)
    response = action(env, session, 'select_product', line_id=line['id'], product_id=outside)
    assert response.status_code == 200, response.text
    changed = response.json()
    assert changed['lines'][0]['selected_product_id'] == outside
    assert outside in {c['id'] for c in changed['lines'][0]['candidates']}
    assert len(changed['lines'][0]['candidates']) <= 16
    assert changed['cart']['items'][0]['id'] == outside and changed['can_confirm']
    assert env[1].spent() == 0


def test_camera_policy_allows_same_origin_photo_and_microphone_keeps_backend_audio(tmp_path):
    from backend.app import create_app

    client = TestClient(create_app(Store(tmp_path / 'camera-policy.sqlite', postgres=False)))
    response = client.get('/health')
    assert response.status_code == 200
    policy = response.headers['Permissions-Policy']
    assert 'camera=(self)' in policy and 'microphone=(self)' in policy
    assert 'geolocation=()' in policy
    paths = client.get('/openapi.json').json()['paths']
    assert '/api/v1/input/image' in paths and '/api/v1/input/audio' in paths


def test_live_catalog_quotation_is_rate_checked_before_provider_call(env, monkeypatch):
    client = env[0]
    called = []

    def supplier(*args):
        assert any(BUYER in str(call[0]) for call in client.app.state.search_rate_calls), 'Live supplier quotation must first consume a scoped rate-limit check'
        called.append(True)
        return procurement.fixture_lookup(*args)

    monkeypatch.setattr(upstream, 'sponsor_lookup', supplier)
    response = client.get('/api/v1/products', params={'q': 'lentils', 'date': env[3], 'mode': 'live'})
    assert response.status_code == 200, response.text
    assert called and response.json()['products']


def test_saved_hard_allergy_changes_actual_meal_plan_candidates_and_uses_verified_absence(env, tmp_path):
    from backend.app import create_app
    from backend.config import access_codes

    client = TestClient(create_app(Store(tmp_path / 'meal-plan-safety.sqlite', postgres=False)))
    assert client.post('/api/v1/session', json={'access_code': access_codes()['buyer']}).status_code == 200
    request = {'servings': 40, 'vegetarian': 0, 'gluten_free': 0, 'vegetarian_gluten_free': 0, 'meat_origin': 'any'}

    def beef_candidate():
        response = client.post('/api/v1/meal-plans', json=request)
        assert response.status_code == 200, response.text
        plan = response.json()
        candidate = next(c for line in plan['lines'] for c in line['candidates'] if c['product_id'] == 'beef')
        return plan, candidate

    original, before = beef_candidate()
    assert before['issues'] == [] and before['status'] == 'needs_chef_review'
    assert not original['can_commit']
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': ['peanut_free']}).status_code == 200
    restricted, blocked = beef_candidate()
    assert restricted['saved_restrictions_applied']['dietary_restrictions'] == ['peanut_free']
    assert blocked['status'] == 'evidence_gap' and any('peanut' in issue for issue in blocked['issues'])
    env[2]['beef']['synkkaData']['classifications'].append({'name': 'nonAllergen', 'values': [{'id': 'AP', 'unit': 'FREE_FROM'}]})
    _, verified = beef_candidate()
    assert verified['status'] == 'needs_chef_review' and not verified['issues']


def test_clearing_saved_only_restrictions_recovers_same_cart_after_fresh_quote(env):
    client = env[0]
    original = create(env, '2 kg chocolate. Choose cheapest.', apply_preferences=False)
    assert original['can_confirm']
    assert client.put('/api/v1/preferences', json={
        'dietary_restrictions': ['no_pork'], 'excluded_ingredients': ['coconut'],
    }).status_code == 200
    restricted = action(env, original, 'quote')
    assert restricted.status_code == 200, restricted.text
    restricted = restricted.json()
    assert not restricted['can_confirm']
    assert restricted['lines'][0]['dietary'] == ['no_pork']
    assert restricted['lines'][0]['excluded_ingredients'] == ['coconut']
    # A normal quantity follow-up must not convert saved defaults into intent.
    changed = action(env, restricted, 'message', message='Change chocolate to 3 kg')
    assert changed.status_code == 200, changed.text
    changed = changed.json()
    assert changed['lines'][0]['requested_dietary'] == []
    assert changed['lines'][0]['requested_excluded_ingredients'] == []
    assert client.put('/api/v1/preferences', json={}).status_code == 200
    recovered = action(env, changed, 'quote')
    assert recovered.status_code == 200, recovered.text
    recovered = recovered.json()
    assert recovered['id'] == original['id'] and recovered['can_confirm']
    assert recovered['lines'][0]['quantity'] == '3'
    assert recovered['lines'][0]['dietary'] == [] and recovered['lines'][0]['excluded_ingredients'] == []
    assert recovered['offer']['fingerprint'] != original['offer']['fingerprint']
    assert env[1].spent() == 0


def test_clearing_saved_overlap_cannot_relax_explicit_request_restriction(env):
    client = env[0]
    assert client.put('/api/v1/preferences', json={'dietary_restrictions': ['no_pork']}).status_code == 200
    original = create(env, '2 kg no pork lentils. Choose cheapest.', apply_preferences=False)
    assert original['can_confirm'] and original['lines'][0]['requested_dietary'] == ['no_pork']
    assert client.put('/api/v1/preferences', json={}).status_code == 200
    refreshed = action(env, original, 'quote')
    assert refreshed.status_code == 200, refreshed.text
    refreshed = refreshed.json()
    assert refreshed['lines'][0]['dietary'] == ['no_pork']
    assert refreshed['lines'][0]['requested_dietary'] == ['no_pork']
    rejected = action(env, refreshed, 'select_product', line_id=refreshed['lines'][0]['id'], product_id='pork')
    assert rejected.status_code == 422 and rejected.json()['detail']['code'] == 'product_ineligible'
    assert env[1].spent() == 0
