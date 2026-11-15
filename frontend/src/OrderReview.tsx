import { useState } from "react";
import type { ReactNode } from "react";
import { Check, Columns3, ShieldCheck } from "lucide-react";
import { CompareControl } from "./ProductComparison";
import { ProductImage } from "./ProductImage";
import type { ComparisonEntry } from "./comparisonSelection";
import type { ProductCandidate } from "./productPresentation";
import { availabilityLabel, formatMoney, formatQuantity, formatUnitPrice, measurementLabel, packageEquation, packageLabel, salesQuantity } from "./productPresentation";
import "./order-review.css";

export type ApprovalInfo = {
  status?: string; threshold?: string; approved?: boolean; pending?: boolean; can_request?: boolean;
  reasons?: string[]; requested_budget?: string | null; budget_excess?: string | null; explanation?: string | null;
  blockers?: string[]; decision_blockers?: string[]; can_decide?: boolean; cumulative_spent?: string; cumulative_remaining?: string; scope_note?: string;
  policy?: { exception_limit?: string; cumulative_limit?: string; [key: string]: unknown };
};
export type BudgetException = { status: string; original_budget: string; total: string; excess: string; explanation: string | null; fingerprint: string; version: number; requested_at?: string };
export type ReviewSnapshot = {
  id: string; buyer_id?: string; customer_id?: string; workspace_name?: string | null; version: number; order_status: string; review_state?: string; buyer_name?: string; request_title?: string; submitted_at?: string | null; original_request?: string;
  messages?: { role: string; text?: string; content?: string }[];
  constraints: { delivery_date?: string | null; budget?: string | null; preferences?: unknown };
  approval?: ApprovalInfo; budget_exception?: BudgetException | null;
  lines: { id: string; requested_label: string; quantity: string; unit: string; selected_product_id?: string | null; candidates: ProductCandidate[]; dietary?: string[]; origin?: string | null; required_brand?: string | null; require_organic?: boolean; max_unit_price?: string | null; issues?: unknown[] }[];
  cart: { subtotal?: string | null; total?: string | null; budget_remaining?: string | null; items: { id: string; name: string; quantity_sales_units: string; sales_unit?: string; line_total?: string | null; unit_price?: string | null; quantity_breakdown?: { unit: string; requested_quantity: string; effective_quantity: string; surplus_quantity: string; includes_converted_requirements?: boolean }[] }[] };
  decision_history?: { action: string; actor: string; at: string; reason?: string | null; fingerprint?: string; version?: number }[];
  recipe_review_required?: boolean; recipe_notes?: string[];
};
export function reviewDate(value?: string | null, time = false) {
  if (!value) return "Not specified";
  const parsed = new Date(value.length === 10 ? `${value}T12:00:00+02:00` : value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", ...(time ? { timeStyle: "short" as const } : {}), timeZone: "Europe/Helsinki" }).format(parsed) + (time ? " Helsinki" : "");
}
export function approvalReason(reason: string) {
  return ({ requested_budget: "Above the buyer’s requested budget", spending_authority: "Above the buyer’s purchasing authority" } as Record<string, string>)[reason] || reason.replaceAll("_", " ");
}
export function reviewStateLabel(order: ReviewSnapshot) {
  if (order.approval?.can_request) return "Approval required";
  return ({ DRAFT: "Draft", BLOCKED: "Requirements need attention", PENDING_APPROVAL: "Approval requested", CHANGES_REQUESTED: "Changes requested", REJECTED: "Approval declined", APPROVED: "Approved exact basket", READY: "Ready for simulated confirmation", SIMULATED_ORDER_SUBMITTED: "Simulated order recorded", CANCELLED: "Request cancelled" } as Record<string,string>)[order.review_state || ""] || (order.approval?.status === "rejected" ? "Approval declined" : "Review order");
}
function issueText(value: unknown) { return typeof value === "string" ? value : value && typeof value === "object" && "message" in value ? String(value.message) : "Requirement needs attention"; }
function ReviewProductPhoto({ candidate }: { candidate: ProductCandidate }) {
  const [failedImage,setFailedImage] = useState("");
  const facts = candidate.product_details || candidate.product;
  const url = facts?.image_status === "verified" && facts.image_url?.startsWith("https://") ? facts.image_url : null;
  return url && url !== failedImage ? <div className="review-product-photo" onErrorCapture={()=>setFailedImage(url)}><ProductImage product={candidate}/></div> : null;
}
export function FinancialSummary({ order }: { order: ReviewSnapshot }) {
  const approval = order.approval;
  return <section className="review-finances" aria-label="Budget and purchasing policy"><h3>Budget & purchasing policy</h3><dl>
    <div><dt>Requested maximum budget</dt><dd>{order.constraints.budget == null ? "Not set" : formatMoney(order.constraints.budget)}</dd><small>Your editable requirement; changing it grants no authority.</small></div>
    <div><dt>Buyer purchasing authority</dt><dd>{approval?.threshold == null ? "Not supplied" : formatMoney(approval.threshold)}</dd><small>Trusted autonomous limit set by the workspace policy.</small></div>
    <div><dt>Amount above requested budget</dt><dd>{order.budget_exception?.excess == null && approval?.budget_excess == null ? "Not supplied" : formatMoney(order.budget_exception?.excess ?? approval?.budget_excess)}</dd><small>The original requested budget is retained for any exception.</small></div>
  </dl><details className="review-policy"><summary>Workspace policy & allowance</summary><dl>
    <div><dt>Workspace per-order ceiling</dt><dd>{approval?.policy?.exception_limit == null ? "Not supplied" : formatMoney(approval.policy.exception_limit)}</dd><small>Hard limit; approval cannot override it.</small></div>
    <div><dt>Committed workspace spend</dt><dd>{approval?.cumulative_spent == null ? "Not supplied" : formatMoney(approval.cumulative_spent)}</dd><small>Simulated committed orders only; quotes reserve no funds.</small></div>
    <div><dt>Remaining simulated allowance</dt><dd>{approval?.cumulative_remaining == null ? "Not supplied" : formatMoney(approval.cumulative_remaining)}</dd><small>{approval?.policy?.cumulative_limit != null ? `Of a ${formatMoney(approval.policy.cumulative_limit)} workspace lifetime limit.` : "Lifetime workspace limit; current server check applies."}</small></div>
  </dl>{approval?.scope_note && <p className="review-note">{approval.scope_note}</p>}</details></section>;
}
export function OrderReview({ order, onDetails, comparisonEntries = [], onCompareToggle, onOpenCompare, disabled, children }: {
  order: ReviewSnapshot; onDetails: (candidate: ProductCandidate, quantity: string, unit: string) => void;
  comparisonEntries?: ComparisonEntry[]; onCompareToggle?: (entry: ComparisonEntry) => void; onOpenCompare?: () => void; disabled?: boolean; children?: ReactNode;
}) {
  const original = order.original_request || order.messages?.find((message) => message.role === "user")?.text || order.messages?.find((message) => message.role === "user")?.content;
  return <article className="order-review" aria-label="Review order">
    <header className="order-review-title"><div><p className="review-state"><ShieldCheck size={15}/>{reviewStateLabel(order)}</p><h2>{order.request_title || "Review order"}</h2></div><span>Request {order.id.slice(-8)} · version {order.version}</span></header>
    <dl className="review-overview"><div><dt>Buyer</dt><dd>{order.buyer_name || "Current workspace buyer"}</dd></div><div><dt>Workspace</dt><dd>{order.workspace_name || (order.customer_id ? `Customer ID: ${order.customer_id}` : order.buyer_id ? `Buyer account ID: ${order.buyer_id}` : "Not supplied")}</dd></div><div><dt>Requested delivery</dt><dd>{reviewDate(order.constraints.delivery_date)}</dd></div><div><dt>Item subtotal</dt><dd>{formatMoney(order.cart.total ?? order.cart.subtotal)}</dd></div><div><dt>Approval submitted</dt><dd>{reviewDate(order.submitted_at,true)}</dd></div></dl>
    <p className="review-note">Tax included. Delivery and service charges are excluded. Reviewing does not submit an order.</p>
    {original && <section className="review-original"><h3>Original request</h3><p>{original}</p></section>}
    <FinancialSummary order={order}/>
    {!!order.approval?.reasons?.length && <section className="review-reasons"><h3>Approval reason</h3><ul>{order.approval.reasons.map((reason)=><li key={reason}>{approvalReason(reason)}</li>)}</ul>{(order.budget_exception?.explanation || order.approval.explanation) && <p><strong>Buyer explanation:</strong> {order.budget_exception?.explanation || order.approval.explanation}</p>}</section>}
    {!!order.approval?.blockers?.length && <section className="review-blockers"><h3>Resolve before proceeding</h3><ul>{order.approval.blockers.map((blocker)=><li key={blocker}>{blocker}</li>)}</ul><p>Financial approval cannot override these requirements. Return to the cart to change products or requirements, or refresh an expired quote.</p></section>}
    <section className="review-products"><h3>Products & quantities</h3>{order.lines.map((line)=>{
      const selected = line.candidates.find((candidate)=>candidate.id===line.selected_product_id);
      const comparablePrices = line.unit === "kg" ? [{value:selected?.price_per_kg,unit:"kg"},{value:selected?.price_per_litre,unit:"L"}] : [{value:selected?.price_per_litre,unit:"L"},{value:selected?.price_per_kg,unit:"kg"}];
      const comparablePrice = comparablePrices.find((price)=>price.value != null);
      const suitabilityUnresolved = Boolean(selected && (selected.selectable === false || selected.eligibility_issues?.length));
      const issues = [...new Set([...(line.issues || []).map(issueText), ...(selected?.eligibility_issues || [])])];
      const entry = (candidate: ProductCandidate): ComparisonEntry => ({key:candidate.id,product:candidate,lineId:line.id,requestedQuantity:line.quantity,requestedUnit:line.unit,contextLabel:line.requested_label});
      return <article className="review-product" key={line.id}><div className="review-product-heading"><div className="review-product-identity">{selected && <ReviewProductPhoto candidate={selected}/>}<div><h4>{selected?.name || line.requested_label}</h4><p>{formatQuantity(line.quantity)} {measurementLabel(line.unit)} requested · {line.requested_label}</p></div></div>{selected && <button type="button" disabled={disabled} onClick={()=>onDetails(selected,line.quantity,line.unit)}>Product details</button>}</div>
        {!selected ? <p className="review-problem">No verified suitable product selected.</p> : <><p className="review-sku">SKU {selected.id}</p>{suitabilityUnresolved && <p className="review-problem"><strong>Suitability unresolved · this selected product is not verified for the request.</strong></p>}<dl className="review-product-facts"><div><dt>Order quantity</dt><dd>{salesQuantity(selected.quantity_sales_units,selected.sales_unit)}</dd></div><div><dt>Package size</dt><dd>{packageLabel(selected,line.unit)}</dd></div><div><dt>Price / {selected.sales_unit === "KG" ? "kg" : "sales package"}</dt><dd>{formatMoney(selected.unit_price)}</dd></div><div><dt>Comparable price</dt><dd>{comparablePrice ? `${formatUnitPrice(comparablePrice.value)} / ${comparablePrice.unit}` : "Basis not supplied"}</dd></div><div><dt>Item subtotal</dt><dd>{formatMoney(selected.line_total)}</dd></div></dl>{packageEquation(selected,line.unit) && <p>{packageEquation(selected,line.unit)}</p>}{selected.surplus_quantity != null && Number(selected.surplus_quantity)>0 && <p>{formatQuantity(selected.surplus_quantity)} {measurementLabel(line.unit)} surplus after package rounding.</p>}<p>{availabilityLabel(selected.availability)} · estimated delivery {reviewDate(selected.delivery_date)}</p><p className="review-note">Price & stock source: {selected.source === "authored_fixture" ? "Sample prices & stock" : selected.source === "live_valio_sandbox" ? "Live supplier challenge sandbox" : "Not quoted"}.</p></>}
        <div className="review-requirements">{line.dietary?.map((diet)=><span key={diet}>{diet.replaceAll("_"," ")}</span>)}{line.origin && <span>Required origin: {line.origin}</span>}{line.required_brand && <span>Required brand: {line.required_brand}</span>}{line.require_organic && <span>Organic required</span>}{line.max_unit_price != null && <span>Maximum {formatMoney(line.max_unit_price)} / {measurementLabel(line.unit)}</span>}</div>
        {issues.length > 0 && <ul className="review-problem">{issues.map((issue,index)=><li key={index}>{issue}</li>)}</ul>}
        {onCompareToggle && line.candidates.length > 1 && <details className="review-alternatives"><summary>Compare items · {line.candidates.length} quoted options</summary><p className="review-note">Choose two or three for a read-only comparison. These choices do not change the basket.</p>{line.candidates.map((candidate)=><div key={candidate.id}><CompareControl checked={comparisonEntries.some((item)=>item.key===candidate.id)} disabled={disabled} onToggle={()=>onCompareToggle(entry(candidate))}/><span>{candidate.name}<small>{formatMoney(candidate.line_total)} · {salesQuantity(candidate.quantity_sales_units,candidate.sales_unit)}</small></span><button type="button" disabled={disabled} onClick={()=>onDetails(candidate,line.quantity,line.unit)}>Details</button></div>)}{onOpenCompare && <button type="button" disabled={disabled || comparisonEntries.length<2} onClick={onOpenCompare}><Columns3 size={15}/>Compare items ({comparisonEntries.length})</button>}</details>}
      </article>;
    })}</section>
    {order.cart.items.some((item)=>(item.quantity_breakdown?.length || 0)>1 || item.quantity_breakdown?.some((quantity)=>quantity.includes_converted_requirements)) && <section className="review-aggregates"><h3>Combined product quantities</h3>{order.cart.items.map((item)=><div key={item.id}><strong>{item.name}</strong><p>{salesQuantity(item.quantity_sales_units,item.sales_unit)} · {formatMoney(item.line_total)}</p>{item.quantity_breakdown?.map((quantity,index)=><p key={index}>{formatQuantity(quantity.requested_quantity)} {measurementLabel(quantity.unit)} requested → {formatQuantity(quantity.effective_quantity)} {measurementLabel(quantity.unit)} ordered{Number(quantity.surplus_quantity)>0 && ` · ${formatQuantity(quantity.surplus_quantity)} ${measurementLabel(quantity.unit)} surplus`}</p>)}</div>)}<p className="review-note">Shared SKU requirements are combined by the server before package rounding.</p></section>}
    {order.recipe_review_required && <section className="review-blockers"><h3>Chef review required</h3>{order.recipe_notes?.map((note,index)=><p key={index}>{note}</p>)}<p>Return to the cart to acknowledge the proposed recipe. Dietary evidence still applies.</p></section>}
    {!!order.decision_history?.length && <details className="review-decisions"><summary>Decision history ({order.decision_history.length})</summary><ol>{order.decision_history.map((decision,index)=><li key={`${decision.at}-${index}`}><Check size={14}/><div><strong>{decision.action.replaceAll("_"," ")}</strong><span>{decision.actor} · {reviewDate(decision.at,true)}{decision.version != null && ` · version ${decision.version}`}</span>{decision.reason && <p>{decision.reason}</p>}</div></li>)}</ol></details>}
    {children}
  </article>;
}
