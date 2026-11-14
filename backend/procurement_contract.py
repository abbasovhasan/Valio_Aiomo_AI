"""Public purchasing responses: validated facts, nullable unknowns and EUR strings.

The gateway retains private working records separately. These models describe
the customer-facing contract and reject malformed amounts or impossible ready
claims before a successful response can reach a client. Additional explanatory
fields remain extensible; numeric purchasing facts never use JSON floats.
"""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)


def _nonnegative(value: str) -> str:
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise ValueError("Expected a finite nonnegative decimal string.")
    return value


def _positive(value: str) -> str:
    if Decimal(value) <= 0:
        raise ValueError("Expected a positive decimal string.")
    return value


def _date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp must include its timezone.")
    return value


def _plain_decimal(value):
    """Keep exact historical Decimal strings readable without changing records.

    Whole-pack arithmetic can legitimately produce 2E+1. Bound the exponent
    before formatting so malformed persisted text cannot expand without limit.
    JSON numbers and non-finite strings remain invalid contract inputs.
    """
    if isinstance(value, str) and len(value) <= 80 and re.fullmatch(r"-?\d+(?:\.\d+)?[eE][+-]?\d{1,2}", value):
        return format(Decimal(value), "f")
    return value


DecimalText = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^-?\d+(?:\.\d+)?$", max_length=80),
    BeforeValidator(_plain_decimal),
]
NonnegativeText = Annotated[DecimalText, AfterValidator(_nonnegative)]
PositiveText = Annotated[NonnegativeText, AfterValidator(_positive)]
MoneyText = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^\d+(?:\.\d{1,2})?$", max_length=30),
]
SignedMoneyText = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^-?\d+(?:\.\d{1,2})?$", max_length=30),
]
DateText = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    AfterValidator(_date),
]
TimestampText = Annotated[str, AfterValidator(_timestamp)]
FingerprintText = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Unit = Literal["L", "kg", "pieces", "packages"]
Origin = Literal["finland", "eu"]
Diet = Literal["lactose_free", "gluten_free", "vegetarian", "vegan"]
LineStatus = Literal[
    "EXACT_MATCH", "AMBIGUOUS_MATCH", "CONSTRAINT_CONFLICT", "OUT_OF_STOCK", "NOT_FOUND"
]
OrderStatus = Literal[
    "READY_TO_ORDER", "NEEDS_CLARIFICATION", "CANNOT_FULFILL", "SIMULATED_ORDER_CONFIRMED"
]


class ResponseModel(BaseModel):
    # Extend factual explanations without silently deleting newly added fields.
    # strict=True rejects JSON numbers where the API promises exact strings.
    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)


class MessageResponse(ResponseModel):
    role: Literal["user", "assistant"]
    text: str


class ConstraintsResponse(ResponseModel):
    budget: MoneyText | None
    currency: Literal["EUR"]
    delivery_date: DateText | None
    preferences: Literal["balanced", "cheapest", "quality", "origin", "delivery"]


class ProductDetailsResponse(ResponseModel):
    id: str | None = None
    name: str | None = None
    brand: str | None = None
    manufacturer: list[str] | None = None
    vendor: str | None = None
    category: str | None = None
    ingredients: str | None = None
    allergens: list[dict[str, JsonValue]] | None = None
    storage: str | None = None
    # Supplier storage-condition identifiers are codes, never inferred degrees.
    temperature_condition: str | int | None = Field(
        default=None, description="Supplier storage-condition identifier; not a temperature in degrees."
    )
    source: str | None = None
    updated_at: str | None = None
    sales_unit: str | None = None
    base_unit: str | None = None
    base_units_per_sales_unit: PositiveText | None = None
    allowed_lot_size: PositiveText | None = None
    kg_per_sales_unit: PositiveText | None = None
    liters_per_sales_unit: PositiveText | None = None
    pieces_per_sales_unit: PositiveText | None = None
    conversion_evidence: dict[str, str] | None = None
    conversion_issues: list[str] | None = None
    reliability: float | None = Field(
        default=None, description="Historical delivered/ordered quantity ratio; not on-time probability."
    )
    carbon_group_estimate: float | None = Field(
        default=None, description="Product-group average kg CO2-equivalent per kg; not an individual SKU measurement."
    )
    organic: bool | None = None
    organic_evidence: str | list[str] | None = None


class CandidateAttributesResponse(ResponseModel):
    brand: str | None
    claims: list[str]
    origin_codes: list[str]
    organic: bool | None = None


class CandidateResponse(ResponseModel):
    id: str
    name: str
    sales_unit: str | None
    pack_quantity: PositiveText | None
    pack_unit: Unit
    quantity_sales_units: PositiveText | None
    effective_quantity: PositiveText | None
    requested_quantity: PositiveText
    surplus_quantity: NonnegativeText | None
    unit_price: MoneyText | None
    line_total: MoneyText | None
    availability: Literal["available", "unknown", "insufficient", "not_queried"]
    available_sales_units: NonnegativeText | None = None
    delivery_date: DateText | None
    attributes: CandidateAttributesResponse
    issues: list[str]
    issue_codes: list[str] | None = None
    source: str
    product_details: ProductDetailsResponse | None = None
    match_method: Literal[
        "exact_sku", "lexical", "category", "semantic_expansion", "supplier_substitution"
    ] | None = None
    match_reason: str | None = None
    requires_explicit_choice: bool | None = None
    price_per_requested_unit: NonnegativeText | None = Field(
        default=None, description="EUR sales-pack price divided by verified capacity in the requested unit."
    )
    comparison_delta: SignedMoneyText | None = Field(
        default=None,
        description="Signed EUR item-subtotal change for this choice, including shared-SKU rounding; null when a complete comparison cannot be established.",
    )
    comparison_note: str | None = None
    next_available_date: DateText | None = None
    preference_matches: list[str] | None = None


class RequestedLineResponse(ResponseModel):
    id: str
    requested_label: str
    quantity: PositiveText
    unit: Unit
    dietary: list[Diet]
    origin: Origin | None
    max_unit_price: NonnegativeText | None
    required_brand: str | None = None
    preferred_brand: str | None = None
    preferred_origin: Origin | None = None
    require_organic: bool | None = None
    preferred_organic: bool | None = None
    retrieval_queries: list[str] | None = None
    selected_product_id: str | None
    selection_reason: str | None = None
    candidates: list[CandidateResponse]
    issues: list[str]
    issue_codes: list[str] | None = None
    status: LineStatus
    classifications: list[LineStatus] | None = None
    meal_plan_line: dict[str, JsonValue] | None = None


class QuantityBreakdownResponse(ResponseModel):
    unit: Unit
    requested_quantity: PositiveText
    effective_quantity: PositiveText
    surplus_quantity: NonnegativeText
    includes_converted_requirements: bool


class CartItemResponse(ResponseModel):
    id: str
    name: str
    sales_unit: str | None
    quantity_sales_units: PositiveText | None
    effective_quantity: PositiveText | None
    unit: Literal["packages"]
    quantity_breakdown: list[QuantityBreakdownResponse]
    unit_price: MoneyText | None
    line_total: MoneyText | None
    availability: Literal["available", "unknown", "insufficient", "not_queried"]
    delivery_date: DateText | None
    line_ids: list[str]
    issues: list[str]
    evidence: dict[str, JsonValue] | None


class CartResponse(ResponseModel):
    items: list[CartItemResponse]
    subtotal: MoneyText | None = Field(
        description="Tax-inclusive item subtotal for selected products; never a complete commercial charge."
    )
    total: MoneyText | None = Field(
        description="Final commercial total, null while delivery/service or other required charges are unknown."
    )
    unknown_charges: list[str] = Field(
        description="Charges outside the quoted item-price simulation. No omitted fee is treated as zero."
    )
    budget_remaining: SignedMoneyText | None
    currency: Literal["EUR"]
    price_scope: str


class ClarificationOptionResponse(ResponseModel):
    id: str
    label: str
    action: str
    payload: dict[str, JsonValue]


class ClarificationResponse(ResponseModel):
    id: str
    line_id: str | None
    prompt: str
    options: list[ClarificationOptionResponse]


class AuthorityResponse(ResponseModel):
    id: str
    assortment: str
    autonomous_limit: MoneyText
    exception_limit: MoneyText
    cumulative_limit: MoneyText
    expires_at: TimestampText
    confirmation_required: bool
    orders: Literal["simulated_only"]


class ApprovalStateResponse(ResponseModel):
    status: Literal["required", "not_required", "blocked", "approved"]
    threshold: MoneyText
    approved: bool
    policy: AuthorityResponse


class OfferResponse(ResponseModel):
    id: str
    fingerprint: FingerprintText
    expires_at: TimestampText
    total: MoneyText
    status: Literal["within_mandate", "approval_required"]
    approved: bool


class ExactApprovalResponse(ResponseModel):
    approver: str
    approver_role: Literal["approver"]
    fingerprint: FingerprintText
    approved_at: TimestampText
    expires_at: TimestampText


class SimulatedReceiptResponse(ResponseModel):
    id: str
    offer_id: str
    buyer_id: str
    customer_id: str
    status: Literal["simulated"]
    simulated: Literal[True]
    items: list[CartItemResponse]
    total: MoneyText
    currency: Literal["EUR"]
    price_scope: str
    requested_date: DateText
    mode: Literal["fixture", "live"]
    fingerprint: FingerprintText
    approval: ExactApprovalResponse | None
    idempotent_replay: bool
    notice: str
    created_at: TimestampText

    @field_validator("simulated", mode="before")
    @classmethod
    def simulation_is_explicit(cls, value):
        if value is not True:
            raise ValueError("The purchasing service issues simulated receipts only.")
        return value


class ProcurementSessionResponse(ResponseModel):
    id: str
    version: int = Field(ge=1)
    buyer_id: str
    customer_id: str
    mode: Literal["fixture", "live"]
    use_model: bool
    created_at: TimestampText
    messages: list[MessageResponse]
    lines: list[RequestedLineResponse]
    constraints: ConstraintsResponse
    receipt: SimulatedReceiptResponse | None
    checkout_pending: bool
    offer: OfferResponse | None
    can_confirm: bool
    cart: CartResponse
    clarification_questions: list[ClarificationResponse]
    approval: ApprovalStateResponse
    order_status: OrderStatus
    assistant_message: str
    interpretation_source: str | None = None
    interpretation_notes: list[str] | None = None
    ambiguities: list[str] | None = None
    recipe_notes: list[str] | None = None
    recipe_request: str | None = None
    recipe_review_required: bool | None = None
    recipe_acknowledged_at: TimestampText | None = None
    source_meal_plan: dict[str, JsonValue] | None = None
    source_recipe: dict[str, JsonValue] | None = None
    last_selected_line_id: str | None = None

    @model_validator(mode="after")
    def ready_claim_has_complete_records(self):
        if self.order_status == "READY_TO_ORDER":
            if (
                not self.lines
                or not self.cart.items
                or self.cart.subtotal is None
                or self.offer is None
                or self.recipe_review_required
                or self.clarification_questions
            ):
                raise ValueError("A ready basket needs all selected, priced, resolved records.")
            if Decimal(self.offer.total) != Decimal(self.cart.subtotal):
                raise ValueError("Offer total must equal the disclosed item subtotal.")
            for line in self.lines:
                selected = next((c for c in line.candidates if c.id == line.selected_product_id), None)
                if line.status != "EXACT_MATCH" or selected is None or selected.issues:
                    raise ValueError("A ready basket cannot contain an unresolved product.")
        if self.order_status == "SIMULATED_ORDER_CONFIRMED" and (
            self.receipt is None or self.can_confirm or self.checkout_pending
        ):
            raise ValueError("A confirmed simulation needs a saved receipt and a closed cart.")
        return self


class ReceiptVerificationResponse(ResponseModel):
    receipt_id: str
    integrity_valid: bool
    scope_valid: bool
    simulated: Literal[True]
    verification_scope: str

    @field_validator("simulated", mode="before")
    @classmethod
    def simulation_is_explicit(cls, value):
        if value is not True:
            raise ValueError("Receipt verification covers simulated records only.")
        return value
