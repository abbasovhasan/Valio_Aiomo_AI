"""Complete catalog discovery, explicit filters and bounded quotation of one page.

Discovery never depends on stock, price or a delivery date. Supplier quotation
adds nullable commercial facts; its failure cannot turn a catalog hit into no hit.
"""
from datetime import date as Date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from . import catalog, product_facts as facts, upstream, procurement
from .preferences import DietaryRestriction, read as preferences
from .procurement import commercial, item_facts, suitability
from .procurement_contract import ProductDetailsResponse, MoneyText, PositiveText, NonnegativeText, Unit, DateText


class CatalogProductResponse(ProductDetailsResponse):
    id: str
    name: str
    claims: list[str]
    origin_codes: list[str]
    attributes: dict
    product_details: ProductDetailsResponse
    eligibility_issues: list[str]
    quote_issues: list[str]
    issues: list[str]
    selectable: bool
    unit_price: MoneyText | None
    line_total: MoneyText | None
    pack_quantity: PositiveText | None
    pack_unit: Unit
    requested_quantity: PositiveText
    quantity_sales_units: PositiveText | None
    effective_quantity: PositiveText | None
    surplus_quantity: NonnegativeText | None
    available_sales_units: NonnegativeText | None = None
    price_per_kg: NonnegativeText | None = None
    price_per_litre: NonnegativeText | None = None
    availability: Literal['available', 'unknown', 'insufficient', 'not_queried']
    delivery_date: DateText | None
    source: str


class Facet(BaseModel):
    value: str
    label: str
    count: int = Field(ge=0)


class SearchResponse(BaseModel):
    products: list[CatalogProductResponse]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    has_more: bool
    facets: dict[str, list[Facet]]
    applied_filters: dict
    source: str
    quote_error: str | None
    sort_scope: Literal['full_filtered_catalog', 'quoted_page']
    sort_basis: str


SearchSort = Literal['relevance', 'name_asc', 'name_desc', 'price_asc', 'price_desc',
                     'price_kg_asc', 'price_kg_desc', 'price_l_asc', 'price_l_desc', 'delivery_asc']


def sort_quoted_page(products, sort):
    """Order only bounded supplier evidence; unknowns stay last in either order.

    The source dataset contains no prices. Sorting a quoted page must never be
    presented as a lowest/highest price search over the complete catalog.
    """
    field = {'price_asc': 'unit_price', 'price_desc': 'unit_price',
             'price_kg_asc': 'price_per_kg', 'price_kg_desc': 'price_per_kg',
             'price_l_asc': 'price_per_litre', 'price_l_desc': 'price_per_litre',
             'delivery_asc': 'delivery_date'}.get(sort)
    if not field:
        return products
    known = [p for p in products if p.get(field) is not None]
    unknown = [p for p in products if p.get(field) is None]
    key = (lambda p: (p[field], p['id'])) if field == 'delivery_date' else (lambda p: (Decimal(p[field]), p['id']))
    return sorted(known, key=key, reverse=sort.endswith('_desc')) + unknown


def register_routes(app, db, identity, limit):
    rate_limit = limit
    @app.get('/api/v1/products', response_model=SearchResponse)
    @app.get('/api/v1/products/search', response_model=SearchResponse)
    def search_inventory(
        q: str = Query(default='', max_length=500),
        offset: int = Query(default=0, ge=0, le=100000),
        limit: int = Query(default=20, ge=1, le=50),
        category: str | None = Query(default=None, max_length=80),
        brand: str | None = Query(default=None, max_length=80),
        origin: str | None = Query(default=None, max_length=80),
        dietary: list[DietaryRestriction] = Query(default=[]),
        organic: bool = False,
        apply_preferences: bool = True,
        sort: SearchSort = 'relevance',
        date: Date | None = None,
        quantity: Decimal = Query(default=Decimal(1), gt=0, le=1000000, decimal_places=3),
        unit: Unit = 'packages',
        mode: Literal['fixture', 'live'] = 'live',
        scope=Depends(identity),
    ):
        if not catalog.load_catalog():
            raise HTTPException(503, detail={'code': 'catalog_missing', 'message': 'The authorized catalog is unavailable. Try again after it is restored.'})
        if len(dietary) > 20:
            raise HTTPException(422, detail={'code': 'filter_bounds', 'message': 'Use at most 20 dietary filters.'})
        if date:
            today = datetime.now(ZoneInfo('Europe/Helsinki')).date()
            if not today <= date <= today + timedelta(days=30):
                raise HTTPException(422, detail={'code': 'invalid_delivery_date', 'message': 'Choose a delivery date within the next 30 days.'})
        saved = preferences(db, scope)
        restrictions = list(dict.fromkeys(list(dietary) + saved['dietary_restrictions']))
        exclusions = saved['excluded_ingredients']
        result = facts.search_page(q, limit, offset, category=category, brand=brand,
            dietary=restrictions, origin=origin, require_organic=organic,
            preferred_brand=saved['preferred_brand'] if apply_preferences else None,
            preferred_origin=saved['preferred_origin'] if apply_preferences else None,
            preferred_organic=saved['preferred_organic'] if apply_preferences else False,
            excluded_ingredients=exclusions, sort=sort)
        day = date.isoformat() if date else None
        evidence, quote_error = None, None
        if day and result['products']:
            if mode == 'live':
                rate_limit('catalog-live-' + scope['buyer_id'], 60)
            try:
                lookup = upstream.sponsor_lookup if mode == 'live' else procurement.fixture_lookup
                evidence = lookup(scope.get('commercial_customer_id', scope['customer_id']), day, [p['id'] for p in result['products']])
            except upstream.UpstreamError as exc:
                quote_error = str(exc)
        products = []
        for p in result['products']:
            units, capacity = item_facts(p, quantity, unit)
            eligibility = facts.suitability(p, restrictions, origin, brand, organic, exclusions)
            quote = commercial(p, units, evidence, day) if evidence else {
                'unit_price': None, 'line_total': None, 'availability': 'not_queried', 'delivery_date': None,
                'issues': [quote_error or 'Choose a delivery date for prices and availability.']}
            safe = ProductDetailsResponse.model_validate(p).model_dump()
            products.append({**p, 'product_details': safe,
                'attributes': {'brand': p.get('brand'), 'claims': p['claims'], 'origin_codes': p['origin_codes'], 'organic': p.get('organic')},
                'eligibility_issues': eligibility, 'quote_issues': quote['issues'], 'issues': eligibility + quote['issues'],
                'selectable': not eligibility, 'unit_price': quote['unit_price'], 'line_total': quote['line_total'],
                'pack_quantity': format(capacity, 'f') if capacity is not None else None, 'pack_unit': unit,
                'requested_quantity': format(quantity, 'f'), 'quantity_sales_units': format(units, 'f') if units is not None else None,
                'effective_quantity': format(units * capacity, 'f') if units is not None and capacity is not None else None,
                'surplus_quantity': format(units * capacity - quantity, 'f') if units is not None and capacity is not None else None,
                'available_sales_units': quote.get('available_sales_units'),
                **facts.comparable_prices(p, quote.get('price_decimal')),
                'availability': quote['availability'], 'delivery_date': quote['delivery_date'],
                'source': evidence['source'] if evidence else 'local_challenge_catalog',
                'lactose_free': True if 'FREE_FROM_LACTOSE' in p['claims'] else None,
                'contains_milk': True if any(v.get('id') == 'AM' and v.get('unit') == 'CONTAINS' for v in p['allergens']) else None})
        page_sort = sort not in {'relevance', 'name_asc', 'name_desc'}
        basis = ('Estimated available date' if sort == 'delivery_asc' else
                 'EUR per verified kg' if sort.startswith('price_kg_') else
                 'EUR per verified litre' if sort.startswith('price_l_') else
                 'EUR per supplier sales unit (package or kg)' if page_sort else
                 'Product name' if sort.startswith('name_') else 'Catalog match and explicit saved preferences')
        return {**result, 'products': sort_quoted_page(products, sort), 'source': 'local restricted challenge catalog',
            'sort_scope': 'quoted_page' if page_sort else 'full_filtered_catalog', 'sort_basis': basis,
            'applied_filters': {'q': q, 'category': category, 'brand': brand, 'origin': origin, 'organic': organic,
                'dietary': restrictions, 'excluded_ingredients': exclusions, 'soft_preferences': apply_preferences, 'sort': sort},
            'quote_error': quote_error}
