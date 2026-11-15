import { useEffect, useReducer, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowLeft, ArrowRight, ArrowUpRight, Check, Columns3, CheckCheck, Clock3,
  LoaderCircle, MessageSquare, Package, Plus, RefreshCw, ShieldCheck,
  ShoppingBasket, SlidersHorizontal, Trash2, X, Search,
} from "lucide-react";
import "./procurement.css";
import { OrderReview, approvalReason, reviewStateLabel } from "./OrderReview";
import type { ApprovalInfo, BudgetException, ReviewSnapshot } from "./OrderReview";
import { PreferencesPanel } from "./PreferencesPanel";
import { MultimodalInput } from "./MultimodalInput";
import { ProductWorkspace } from "./ProductWorkspace";
import { HistoryPanel } from "./HistoryPanel";
import { ProductComparison, CompareControl } from "./ProductComparison";
import { comparisonReducer, emptyComparison, staleComparisonEntry } from "./comparisonSelection";
import type { ComparisonEntry } from "./comparisonSelection";
import { ProductImage } from "./ProductImage";
import { DetailsDialog, ProductDetailsDialog } from "./ProductDetailsDialog";
import type { ProductCandidate as Candidate } from "./productPresentation";
import { availabilityLabel, formatUnitPrice, measurementLabel, packageEquation, packageLabel, salesQuantity, usefulMatchReason } from "./productPresentation";

type API = (path: string, options?: RequestInit) => Promise<any>;
type Line = {
  id: string; requested_label: string; quantity: string; unit: string; status: string;
  selected_product_id?: string | null; candidates: Candidate[]; issues?: unknown[];
  selection_reason?: string; dietary?: string[]; origin?: string | null; max_unit_price?: string | null;
  required_brand?: string | null; preferred_brand?: string | null; preferred_origin?: string | null;
  require_organic?: boolean; preferred_organic?: boolean;
};
type CartItem = {
  line_ids?: string[];
  id: string; name: string; quantity_sales_units: string; effective_quantity?: string;
  unit?: string; unit_price?: string | null; line_total?: string | null; sales_unit?: string;
  quantity_breakdown?: { unit: string; requested_quantity: string; effective_quantity: string; surplus_quantity: string; includes_converted_requirements?: boolean }[];
};
type SimulatedReceipt = {
  id?: string; order_id?: string; total?: string; status?: string; created_at?: string;
  items?: CartItem[]; requested_date?: string; customer_id?: string; mode?: string;
  price_scope?: string; notice?: string;
  approval?: { approver?: string; approved_at?: string; fingerprint?: string; covered_reasons?: string[] } | null;
  budget_exception?: BudgetException | null;
};
type ProcurementSession = {
  id: string; buyer_id?: string; version: number; order_status: string; assistant_message: string;
  messages: { role: string; text?: string; content?: string }[];
  constraints: { budget?: string | null; currency?: string; delivery_date?: string | null; preferences?: unknown };
  lines: Line[];
  cart: { items: CartItem[]; subtotal?: string | null; total?: string | null; unknown_charges?: unknown; budget_remaining?: string | null };
  clarification_questions?: { id: string; line_id?: string; prompt: string; options?: { id: string; label: string; action: string; payload?: Record<string, unknown> }[] }[];
  approval?: ApprovalInfo;
  review_state?: string; buyer_name?: string; workspace_name?: string | null; customer_id?: string; request_title?: string; submitted_at?: string | null; original_request?: string; budget_exception?: BudgetException | null; decision_history?: ReviewSnapshot["decision_history"];
  rejection?: { reason?: string | null; approver?: string; rejected_at?: string } | null;
  can_confirm: boolean; mode: string;
  offer?: { id: string; fingerprint: string; expires_at: string; total: string; status: string } | null;
  receipt?: SimulatedReceipt | null;
  model?: { status?: string; message?: string; provider?: string };
  recipe_review_required?: boolean; recipe_notes?: string[];
  use_model?: boolean; interpretation_source?: string; interpretation_notes?: string[]; commercial_context?: string;
};
const savedSessionKey = "aimo-procurement-session";
const examples = [
  { label: "Stock the breakfast kitchen", text: "I need 200 litres of lactose-free milk, 10 kg of butter and 5 kg of cheese delivered by Monday. Show me suitable options." },
  { label: "A simple milk order", text: "I need 1,000 litres of lactose-free milk delivered by Monday. Choose the most affordable suitable option." },
  { label: "Bolognese for 500 diners", text: "I need ingredients for spaghetti bolognese for 500 people. 20% vegetarian and 10% gluten-free, with an overlap: 20 diners. Delivered by Monday. Prefer Finnish ingredients." },
];
const money = (value: unknown) => value == null ? "Requires quote" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR" }).format(Number(value));
const amount = (value: unknown) => value == null ? "Unknown" : new Intl.NumberFormat("en-FI", { maximumFractionDigits: 3 }).format(Number(value));
function readable(value: unknown): string {
  if (value == null) return "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "Unknown";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.length ? value.map(readable).join(", ") : "Not supplied";
  const obj = value as Record<string, unknown>;
  return String(obj.message || obj.detail || obj.label || obj.status || "Needs review");
}
function dateLabel(value: string | null | undefined) {
  if (!value) return "Date not set";
  const date = new Date(value.length === 10 ? value + "T12:00:00+02:00" : value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Helsinki" }).format(date);
}
function remember(id: string | null, buyerId: string | undefined) {
  if (!buyerId) return;
  try {
    const scopedKey = `${savedSessionKey}:${buyerId}`;
    id ? localStorage.setItem(scopedKey, id) : localStorage.removeItem(scopedKey);
    if (buyerId === "buyer-hotel-aurora") localStorage.removeItem(savedSessionKey);
  } catch { /* The server remains the source of truth when storage is unavailable. */ }
}
function recall(buyerId: string | undefined) {
  if (!buyerId) return null;
  try {
    return localStorage.getItem(`${savedSessionKey}:${buyerId}`)
      || (buyerId === "buyer-hotel-aurora" ? localStorage.getItem(savedSessionKey) : null);
  } catch { return null; }
}

const regionCodes: Record<string, string> = {
  "040": "AT", "056": "BE", "100": "BG", "191": "HR", "196": "CY", "203": "CZ", "208": "DK", "233": "EE", "246": "FI", "250": "FR", "276": "DE", "300": "GR", "348": "HU", "372": "IE", "380": "IT", "428": "LV", "440": "LT", "442": "LU", "470": "MT", "528": "NL", "616": "PL", "620": "PT", "642": "RO", "703": "SK", "705": "SI", "724": "ES", "752": "SE",
};
function originLabel(values: unknown) {
  if (!Array.isArray(values) || !values.length) return "Not supplied";
  return values.map((code) => {
    const value = String(code);
    const region = regionCodes[value] || (/^[A-Z]{2}$/.test(value) ? value : null);
    try { return region ? `${new Intl.DisplayNames(["en"], { type: "region" }).of(region)} (${value})` : `Supplier code ${value}`; }
    catch { return `Supplier code ${value}`; }
  }).join(", ");
}
function timestampLabel(value: string | null | undefined) {
  if (!value) return "Not supplied";
  const date = new Date(value.replace(/([+-]\d{2})(\d{2})$/, "$1:$2"));
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Helsinki" }).format(date) + " Helsinki";
}
type CandidateSort = "recommended" | "total" | "total_desc" | "per_unit" | "per_unit_desc" | "name" | "name_desc" | "brand" | "origin" | "delivery";
function candidateAttributes(candidate: Candidate): Record<string, unknown> {
  return candidate.attributes && !Array.isArray(candidate.attributes) ? candidate.attributes : {};
}
function candidateBrand(candidate: Candidate): string | null {
  const value = (candidate.product_details || candidate.product)?.brand || candidateAttributes(candidate).brand;
  return typeof value === "string" && value.trim() && !/^(unknown|n\/a|not supplied|-)$/i.test(value.trim()) ? value.trim() : null;
}
function candidateOrigins(candidate: Candidate): string[] {
  const value = (candidate.product_details || candidate.product)?.origin_codes || candidateAttributes(candidate).origin_codes;
  return Array.isArray(value) ? value.filter((code): code is string => typeof code === "string").map((code) => regionCodes[code] || code.toUpperCase()) : [];
}
function candidateClaims(candidate: Candidate): string[] {
  const value = (candidate.product_details || candidate.product)?.claims || candidateAttributes(candidate).claims;
  return Array.isArray(value) ? value.filter((claim): claim is string => typeof claim === "string") : [];
}
function declaredDietMatches(candidate: Candidate, filter: string): boolean {
  if (!filter) return true;
  if (filter === "organic") return (candidate.product_details || candidate.product)?.organic === true;
  const supported: Record<string, string[]> = { lactose_free: ["FREE_FROM_LACTOSE"], gluten_free: ["FREE_FROM_GLUTEN"], vegetarian: ["VEGETARIAN", "VEGAN"], vegan: ["VEGAN"] };
  return (supported[filter] || []).some((claim) => candidateClaims(candidate).includes(claim));
}
function comparePresent<T extends string | number>(a: T | null, b: T | null, descending = false): number {
  if (a === null) return b === null ? 0 : 1;
  if (b === null) return -1;
  const order = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "en", { sensitivity: "base", numeric: true });
  return descending ? -order : order;
}
function numericValue(value: string | null | undefined): number | null {
  if (value == null || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
function CandidateChoices({ line, renderCandidate, compareCount, onCompare, disabled }: { line: Line; renderCandidate: (candidate: Candidate) => React.ReactNode; compareCount: number; onCompare: () => void; disabled: boolean }) {
  const [sort, setSort] = useState<CandidateSort>("recommended");
  const [validOnly, setValidOnly] = useState(false);
  const [brand, setBrand] = useState("");
  const [origin, setOrigin] = useState("");
  const [diet, setDiet] = useState("");
  const brands = [...new Set(line.candidates.map(candidateBrand).filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b));
  const origins = [...new Set(line.candidates.flatMap(candidateOrigins))].sort((a, b) => originLabel([a]).localeCompare(originLabel([b])));
  const selected = line.candidates.find((candidate) => candidate.id === line.selected_product_id);
  const isCompliant = (candidate: Candidate) => Array.isArray(candidate.issues) && candidate.issues.length === 0;
  const matches = (candidate: Candidate) => (!validOnly || isCompliant(candidate)) && (!brand || candidateBrand(candidate) === brand) && (!origin || candidateOrigins(candidate).includes(origin)) && declaredDietMatches(candidate, diet);
  const filtered = line.candidates.map((candidate, index) => ({ candidate, index })).filter(({ candidate }) => matches(candidate) || candidate.id === line.selected_product_id);
  const matchingCount = line.candidates.filter(matches).length;
  const selectedOutsideFilter = Boolean(selected && !matches(selected));
  const activeFilters = validOnly || Boolean(brand || origin || diet);
  filtered.sort((a, b) => {
    const pinned = Number(b.candidate.id === line.selected_product_id) - Number(a.candidate.id === line.selected_product_id);
    if (pinned) return pinned;
    let compared = 0;
    if (sort === "recommended") compared = Number(!isCompliant(a.candidate)) - Number(!isCompliant(b.candidate));
    if (sort === "total" || sort === "total_desc") compared = comparePresent(numericValue(a.candidate.line_total), numericValue(b.candidate.line_total),sort === "total_desc");
    if (sort === "per_unit" || sort === "per_unit_desc") compared = comparePresent(numericValue(a.candidate.price_per_requested_unit), numericValue(b.candidate.price_per_requested_unit),sort === "per_unit_desc");
    if (sort === "name" || sort === "name_desc") compared = comparePresent(a.candidate.name,b.candidate.name,sort === "name_desc");
    if (sort === "brand") compared = comparePresent(candidateBrand(a.candidate), candidateBrand(b.candidate));
    if (sort === "origin") compared = comparePresent(candidateOrigins(a.candidate).length ? originLabel(candidateOrigins(a.candidate)) : null, candidateOrigins(b.candidate).length ? originLabel(candidateOrigins(b.candidate)) : null);
    if (sort === "delivery") compared = comparePresent(a.candidate.delivery_date || null, b.candidate.delivery_date || null);
    return compared || a.index - b.index;
  });
  const visible = filtered.map(({ candidate }) => candidate);
  function reset() { setSort("recommended"); setValidOnly(false); setBrand(""); setOrigin(""); setDiet(""); }
  return <div className="proc-candidate-workspace">
    <details className="proc-product-controls" open={activeFilters || undefined}>
      <summary><SlidersHorizontal size={14} />Sort & filter products<span>{activeFilters ? "Filters on" : "Customize your view"}</span></summary>
      <div className="proc-product-control-fields">
        <label>Sort by<select aria-label={`Sort ${line.requested_label} products`} value={sort} onChange={(e) => setSort(e.target.value as CandidateSort)}><option value="recommended">Suggested order</option><option value="total">Item subtotal · lowest first</option><option value="total_desc">Item subtotal · highest first</option><option value="name">Name · A to Z</option><option value="name_desc">Name · Z to A</option><option value="per_unit">Price per {measurementLabel(line.unit)} · lowest first</option><option value="per_unit_desc">Price per {measurementLabel(line.unit)} · highest first</option><option value="brand">Brand · A to Z</option><option value="origin">Declared origin · A to Z</option><option value="delivery">Available date · earliest first</option></select></label>
        <label>Brand<select aria-label={`Filter ${line.requested_label} by brand`} value={brand} onChange={(e) => setBrand(e.target.value)}><option value="">All brands · including unknown</option>{brand && !brands.includes(brand) && <option value={brand}>{brand} · not in current results</option>}{brands.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>Origin includes<select aria-label={`Filter ${line.requested_label} by declared origin`} value={origin} onChange={(e) => setOrigin(e.target.value)}><option value="">All origins · including unknown</option>{origin && !origins.includes(origin) && <option value={origin}>{originLabel([origin])} · not in current results</option>}{origins.map((value) => <option key={value} value={value}>{originLabel([value])}</option>)}</select></label>
        <label>Declared attributes<select aria-label={`Filter ${line.requested_label} by declared attribute`} value={diet} onChange={(e) => setDiet(e.target.value)}><option value="">All attributes</option><option value="lactose_free">Explicit lactose-free claim</option><option value="gluten_free">Explicit gluten-free claim</option><option value="vegetarian">Explicit vegetarian / vegan claim</option><option value="vegan">Explicit vegan claim</option><option value="organic">Verified organic classification</option></select></label>
        <label className="proc-valid-filter"><input type="checkbox" checked={validOnly} onChange={(e) => setValidOnly(e.target.checked)} />Compliant choices only</label>
        <button type="button" className="proc-reset-filters" onClick={reset} disabled={!activeFilters && sort === "recommended"}><RefreshCw size={13} />Reset view</button>
      </div>
      <p>Filters change the view, not your order requirements. Unknown attributes do not count as a match. The selected product always stays visible.</p>
    </details>
    <div className="proc-filter-count"><span role="status">{matchingCount} of {line.candidates.length} products match{activeFilters ? " your filters" : ""}.</span>{selectedOutsideFilter && <strong>Selected product kept visible outside the filter.</strong>}<button type="button" className="proc-compare-items" disabled={disabled || compareCount < 2} onClick={onCompare}><Columns3 size={14}/>Compare items{compareCount ? ` (${compareCount})` : ""}</button></div><p className="proc-compare-hint">Select Compare on any two or three products. Comparison is optional and does not change your cart.</p>
    {visible.length ? <><div className="proc-candidates">{visible.slice(0, 4).map(renderCandidate)}</div>{visible.length > 4 && <details className="proc-more-candidates"><summary>Show {visible.length - 4} more alternatives</summary><div className="proc-candidates">{visible.slice(4).map(renderCandidate)}</div></details>}</> : <div className="proc-no-match"><p>No returned products match these filters. Reset the view or refine the product search.</p><button type="button" onClick={reset}>Reset view</button></div>}
    <p className="proc-comparison-scope">Basket change compares the server-quoted total with your selected product after rounding. Prices and sorting cover these retrieved products, not the entire catalog.</p>
  </div>;
}

function OrderReceiptSummary({ receipt }: { receipt: SimulatedReceipt }) {
  return <section className="proc-order-summary" aria-label="Recorded simulated order details">
    <div className="proc-order-summary-heading"><CheckCheck size={22} /><div><span className="eyebrow">SIMULATED ORDER · SAVED RECORD</span><h3>Your order, on the record.</h3></div></div>
    <p className="proc-order-reference">Reference: <strong>{receipt.order_id || receipt.id}</strong></p>
    <dl className="proc-order-facts">
      <div><dt>Requested delivery</dt><dd>{dateLabel(receipt.requested_date)}</dd></div>
      <div><dt>Item subtotal</dt><dd>{money(receipt.total)}</dd></div>
      <div><dt>Price & stock source</dt><dd>{receipt.mode === "fixture" ? "Authored rehearsal fixture" : receipt.mode === "live" ? "Live challenge sandbox" : "See recorded quotation"}</dd></div>
      <div><dt>Manager approval</dt><dd>{receipt.approval ? `Approved${receipt.approval.approver ? ` by ${receipt.approval.approver}` : ""}` : "No separate manager approval recorded"}{receipt.approval?.approved_at && <small>{timestampLabel(receipt.approval.approved_at)}</small>}</dd></div>
    </dl>
    {receipt.budget_exception && <div className="proc-receipt-exception"><h4>Approved budget exception</h4><p>Original requested budget: {money(receipt.budget_exception.original_budget)} · quoted items: {money(receipt.budget_exception.total)} · approved excess: {money(receipt.budget_exception.excess)}.</p>{receipt.budget_exception.explanation && <p>Buyer explanation: {receipt.budget_exception.explanation}</p>}</div>}
    {receipt.items?.length ? <table className="proc-receipt-items"><caption>Confirmed items and exact sales-package quantities</caption><thead><tr><th scope="col">Product</th><th scope="col">Ordered quantity</th><th scope="col">Item subtotal</th></tr></thead><tbody>{receipt.items.map((item, i) => <tr key={`${item.id}-${i}`}><th scope="row">{item.name}<small>SKU {item.id}</small></th><td data-label="Ordered quantity">{salesQuantity(item.quantity_sales_units,item.sales_unit)}{item.quantity_breakdown?.map((quantity, j) => <small key={j}>{amount(quantity.effective_quantity)} {measurementLabel(quantity.unit)} planned{Number(quantity.surplus_quantity) > 0 && ` · ${amount(quantity.surplus_quantity)} ${measurementLabel(quantity.unit)} surplus`}</small>)}</td><td data-label="Item subtotal">{money(item.line_total)}</td></tr>)}</tbody></table> : <p>The item list is available in the recorded cart.</p>}
    <div className="proc-order-next"><h4>What happens next?</h4><p>This simulation stops here. No supplier delivery has been scheduled and no invoice or payment has been created. Use “Verify receipt” to check this saved simulator record.</p><p>For an actual purchase, use your authorized supplier ordering channel. Your customer contract governs any real invoice and payment terms.</p></div>
    <p className="proc-order-scope">Quoted item prices include tax. Delivery and service charges are excluded. This receipt is not a Valio Aimo order confirmation.</p>
  </section>;
}

export function ProcurementDesk({ api, role, onSignIn, onUpdated, initialSessionId, buyerId, active = true, view = "order", onNavigate, demoTools = false, onActiveCartChange }: {
  api: API; role: string | null; onSignIn: () => void; onUpdated?: () => void | Promise<void>; initialSessionId?: string | null; buyerId?: string; active?: boolean; view?: "order" | "products" | "history"; onNavigate?: (view: "order" | "products" | "history") => void; demoTools?: boolean; onActiveCartChange?: (state: {id: string; hasItems: boolean} | null) => void;
}) {
  const [smartComparison, compareDispatch] = useReducer(comparisonReducer,emptyComparison);
  const [session, setSession] = useState<ProcurementSession | null>(null);
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState("live");
  const [useModel, setUseModel] = useState(false);
  const [applyPreferences, setApplyPreferences] = useState(true);
  const [preferencesVersion, setPreferencesVersion] = useState(0);
  const [deliveryDate, setDeliveryDate] = useState("");
  const [budget, setBudget] = useState("");
  const [mediaBusy, setMediaBusy] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState<{ candidate: Candidate; quantity?: string; unit?: string } | null>(null);
  const [compactCart, setCompactCart] = useState(() => typeof window !== "undefined" && window.matchMedia("(max-width: 1000px)").matches);
  const [cartOpen, setCartOpen] = useState(false);
  const [reviewConfirm, setReviewConfirm] = useState(false);
  const [approvalExplanation, setApprovalExplanation] = useState("");
  const [compareOpenRequest, setCompareOpenRequest] = useState(0);
  const [confirmedReceipt, setConfirmedReceipt] = useState<SimulatedReceipt | null>(null);
  const [verification, setVerification] = useState<{ integrity_valid: boolean; scope_valid: boolean; receipt_id?: string } | null>(null);
  const [clock, setClock] = useState(Date.now());
  const requestKeys = useRef<Record<string, string>>({});
  const composer = useRef<HTMLTextAreaElement>(null);
  const entryDate = useRef<HTMLInputElement>(null);
  const entryBudget = useRef<HTMLInputElement>(null);
  const result = useRef<HTMLDivElement>(null);
  const reviewRegion = useRef<HTMLDivElement>(null);
  useEffect(()=>{if(reviewConfirm){reviewRegion.current?.focus({preventScroll:true});reviewRegion.current?.scrollIntoView({block:"start"});}},[reviewConfirm]);
  const sessionRef = useRef<ProcurementSession | null>(null);
  const importedSession = useRef<string | null>(null);
  const activeCartCallback = useRef(onActiveCartChange); activeCartCallback.current = onActiveCartChange;
  useEffect(() => { activeCartCallback.current?.(session ? {id:session.id,hasItems:session.lines.length > 0 && !session.receipt} : null); }, [session?.id,session?.lines.length,Boolean(session?.receipt)]);
  useEffect(() => () => activeCartCallback.current?.(null), []);
  sessionRef.current = session;
  function accept(next: ProcurementSession) {
    if (sessionRef.current && sessionRef.current.id !== next.id) { compareDispatch({type:"clear"}); setApprovalExplanation(""); }
    else compareDispatch({type:"update",entries:smartComparison.entries.map((entry) => {
      const line = next.lines.find((candidate)=>candidate.id===entry.lineId);
      const product = line?.candidates.find((candidate)=>candidate.id===entry.product.id);
      return product && line ? {...entry,product,requestedQuantity:line.quantity,requestedUnit:line.unit} : {...staleComparisonEntry(entry,"This product is outside the current quoted options."),product:{...staleComparisonEntry(entry).product,selectable:false,eligibility_issues:["Find this product in the current request before choosing."]}};
    })});
    setSession(next);
    remember(next.id, buyerId || next.buyer_id);
    setMode(next.mode);
    if (next.use_model !== undefined) setUseModel(next.use_model);
    setBudget(next.constraints?.budget ?? "");
    setDeliveryDate(next.constraints?.delivery_date || "");
    if (next.receipt || (sessionRef.current && sessionRef.current.id !== next.id)) setReviewConfirm(false);
    setVerification(null);
    setConfirmedReceipt(next.receipt || null);
  }
  useEffect(() => {
    if (!role) { setSession(null); setConfirmedReceipt(null); setVerification(null); return; }
    const incoming = initialSessionId && initialSessionId !== importedSession.current ? initialSessionId : null;
    const id = incoming || recall(buyerId);
    if (!id) return;
    if (incoming) { setApprovalExplanation(""); importedSession.current = incoming; compareDispatch({type:"clear"}); setSession(null); setConfirmedReceipt(null); setVerification(null); }
    let cancelled = false;
    setBusy("restore");
    api(`/procurement/sessions/${encodeURIComponent(id)}`)
      .then((data) => { if (!cancelled) accept(data); })
      .catch(() => { if (!cancelled) setNotice("Your saved cart could not be reopened. Check the connection and reload, or begin a new purchasing request."); })
      .finally(() => { if (!cancelled) setBusy(""); });
    return () => { cancelled = true; };
  }, [role, api, initialSessionId, buyerId]);
  useEffect(() => {
    if (!session?.offer || session.receipt) return;
    setClock(Date.now());
    const interval = window.setInterval(() => setClock(Date.now()), 15000);
    return () => window.clearInterval(interval);
  }, [session?.offer?.fingerprint, session?.receipt]);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1000px)");
    const update = () => { setCompactCart(media.matches); if (!media.matches) setCartOpen(false); };
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => { setDetails(null); setCartOpen(false); setReviewConfirm(false); }, [view, active]);
  async function perform(label: string, operation: () => Promise<any>, clearMessage = false) {
    if (!role) { onSignIn(); return; }
    setBusy(label); setError(""); setNotice("");
    try {
      const data = await operation();
      if (data?.lines && data?.constraints) accept(data);
      else if (data?.session) accept(data.session);
      else if (data?.receipt) setConfirmedReceipt(data.receipt);
      else if (label === "confirm") setConfirmedReceipt(data);
      if (clearMessage) setMessage("");
      if (label !== "review" && label !== "status") await onUpdated?.();
      return data;
    } catch (e) {
      const text = (e as Error).message;
      setError(text);
      if (/version|concurrent|cart changed|session changed/i.test(text) && sessionRef.current) {
        try {
          accept(await api(`/procurement/sessions/${sessionRef.current.id}`));
          setNotice("This cart changed in another request. The latest saved version is shown; review it before trying again.");
        } catch { /* Preserve the original useful error. */ }
      }
    } finally { setBusy(""); }
  }
  async function action(actionName: string, payload: Record<string, unknown> = {}, label = actionName) {
    if (!session) return;
    return perform(label, () => api(`/procurement/sessions/${session.id}/actions`, {
      method: "POST", body: JSON.stringify({ version: session.version, action: actionName, ...payload }),
    }), actionName === "message");
  }
  function currentRequirements() {
    return { date: entryDate.current?.value ?? deliveryDate, budget: entryBudget.current?.value ?? budget };
  }
  async function applyRequirements(current: ProcurementSession, date: string, desiredBudget: string) {
    let next = current;
    if ((next.constraints.delivery_date || "") !== date) next = await api(`/procurement/sessions/${next.id}/actions`, { method: "POST", body: JSON.stringify({ version: next.version, action: "set_date", date: date || null }) });
    if (String(next.constraints.budget ?? "") !== desiredBudget) next = await api(`/procurement/sessions/${next.id}/actions`, { method: "POST", body: JSON.stringify({ version: next.version, action: "set_budget", budget: desiredBudget || null }) });
    return next;
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (mediaBusy || !message.trim()) return;
    const requirements = currentRequirements();
    const data = await perform("understand", async () => {
      if (session) {
        const next = await applyRequirements(session, requirements.date, requirements.budget);
        return api(`/procurement/sessions/${next.id}/actions`, { method: "POST", body: JSON.stringify({ version: next.version, action: "message", message: message.trim() }) });
      }
      return api("/procurement/sessions", { method: "POST", body: JSON.stringify({ message: message.trim(), mode, ...(requirements.date ? { date: requirements.date } : {}), ...(requirements.budget ? { budget: requirements.budget } : {}), use_model: useModel, apply_preferences: applyPreferences }) });
    }, true);
    if (data) result.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function updateConstraints(e: FormEvent) {
    e.preventDefault();
    const fields = new FormData(e.currentTarget as HTMLFormElement);
    const chosenDate = String(fields.get("delivery_date") ?? deliveryDate);
    const chosenBudget = String(fields.get("budget") ?? budget);
    setDeliveryDate(chosenDate); setBudget(chosenBudget);
    if (!session || session.receipt) return;
    await perform("constraints", () => applyRequirements(session, chosenDate, chosenBudget));
  }
  async function addCatalogProduct(productId: string, quantity: string, unit: string, browsePreferences = false) {
    if (role !== "buyer") { onSignIn(); return false; }
    const requirements = currentRequirements();
    const data = await perform("add_product", async () => {
      if (session && !session.receipt) {
        const next = await applyRequirements(session, requirements.date, requirements.budget);
        return api(`/procurement/sessions/${next.id}/actions`, { method: "POST", body: JSON.stringify({ version: next.version, action: "add_product", product_id: productId, quantity, unit }) });
      }
      return api("/procurement/sessions/from-product", { method: "POST", body: JSON.stringify({ product_id: productId, quantity, unit, ...(requirements.date ? { date: requirements.date } : {}), ...(requirements.budget ? { budget: requirements.budget } : {}), mode: demoTools ? mode : "live", apply_preferences: browsePreferences }) });
    });
    return Boolean(data);
  }
  async function openReview() {
    if (!session || isWorking || mediaBusy) return;
    const draft = currentRequirements();
    if (draft.date !== (session.constraints.delivery_date || "") || draft.budget !== String(session.constraints.budget ?? "")) {
      setNotice("Apply your delivery date and budget changes before reviewing the order."); editRequirements(); return;
    }
    const current = await perform("review", () => api(`/procurement/sessions/${session.id}`));
    if (current) { setCartOpen(false); setReviewConfirm(true); result.current?.scrollIntoView({block:"start"}); }
  }
  async function requestApproval() {
    if (!session?.offer || !session.approval?.can_request) return;
    await perform("request-approval", () => api(`/procurement/sessions/${session.id}/request-approval`, {method:"POST",body:JSON.stringify({version:session.version,fingerprint:session.offer!.fingerprint,explanation:approvalExplanation.trim() || null})}));
  }
  async function cancelRequest() {
    if (!session) return;
    await perform("cancel", () => api(`/procurement/sessions/${session.id}/cancel`, {method:"POST",body:JSON.stringify({version:session.version})}));
  }
  async function refreshStatus() {
    if (!session) return;
    const draft = currentRequirements();
    const dateChanged = draft.date !== (session.constraints.delivery_date || "");
    const budgetChanged = draft.budget !== String(session.constraints.budget ?? "");
    const updated = await perform("status", () => api(`/procurement/sessions/${session.id}`));
    if (updated) {
      if (dateChanged) setDeliveryDate(draft.date);
      if (budgetChanged) setBudget(draft.budget);
    }
  }
  async function confirm() {
    if (!session?.offer) return;
    const fingerprint = session.offer.fingerprint;
    const cacheKey = `${session.id}-${fingerprint}`;
    if (!requestKeys.current[cacheKey]) {
      let stored: string | null = null;
      try { stored = sessionStorage.getItem(`aimo-confirmation-${cacheKey}`); } catch { /* In-memory retry protection remains available. */ }
      requestKeys.current[cacheKey] = stored || crypto.randomUUID();
      try { sessionStorage.setItem(`aimo-confirmation-${cacheKey}`, requestKeys.current[cacheKey]); } catch { /* Storage can be unavailable in private browser contexts. */ }
    }
    await perform("confirm", () => api(`/procurement/sessions/${session.id}/confirm`, {
      method: "POST", headers: { "Idempotency-Key": requestKeys.current[cacheKey] }, body: JSON.stringify({ fingerprint }),
    }));
  }
  async function verifyReceipt() {
    if (!session?.receipt) return;
    await perform("verify", async () => {
      const data = await api(`/procurement/sessions/${session.id}/verify`);
      if (!data.integrity_valid || !data.scope_valid) throw new Error("The saved receipt could not be verified against this purchasing record.");
      setVerification(data);
      return data;
    });
  }
  function startNew() {
    compareDispatch({type:"clear"});
    setSession(null); remember(null, buyerId || session?.buyer_id); setMessage(""); setConfirmedReceipt(null);
    setBudget(""); setDeliveryDate(""); setUseModel(false); setDetails(null); if (!demoTools) setMode("live");
    setError(""); setNotice(""); setApprovalExplanation(""); setReviewConfirm(false); setVerification(null); setCartOpen(false); composer.current?.focus();
  }
  const receipt = confirmedReceipt || session?.receipt;
  const cancelled = session?.review_state === "CANCELLED";
  const canEdit = role !== "approver" && !receipt && !cancelled;
  const approvalDeclined = session?.approval?.status === "rejected";
  const changesRequested = session?.review_state === "CHANGES_REQUESTED" || session?.approval?.status === "changes_requested";
  const approvalPending = session?.approval?.pending === true;
  const approvalNeeded = !approvalDeclined && !changesRequested && !cancelled && (session?.approval?.status === "required" || session?.offer?.status === "approval_required");
  const approved = !approvalDeclined && (session?.approval?.approved || session?.approval?.status === "approved");
  const offerExpired = Boolean(session?.offer && Date.parse(session.offer.expires_at) <= clock);
  const ready = !approvalDeclined && !changesRequested && !cancelled && session?.order_status === "READY_TO_ORDER";
  const questions = session?.clarification_questions || [];
  const unresolvedCount = session?.lines.filter((line) => !line.selected_product_id || Boolean(line.issues?.length)).length || 0;
  const hasUnknownCharges = Boolean(session?.cart.unknown_charges && (!Array.isArray(session.cart.unknown_charges) || session.cart.unknown_charges.length));
  const displayedTotal = session?.cart.total ?? session?.cart.subtotal;
  const negativeBudget = session?.cart.budget_remaining != null && Number(session.cart.budget_remaining) < 0;
  const isWorking = Boolean(busy);
  function renderCandidate(line: Line, candidate: Candidate) {
    const selected = line.selected_product_id === candidate.id;
    const blocked = candidate.selectable === false || Boolean(candidate.eligibility_issues?.length) || (candidate.selectable === undefined && !candidate.eligibility_issues && Boolean(candidate.issues?.length));
    const equation = packageEquation(candidate, line.unit);
    const reason = usefulMatchReason(candidate);
    const brand = candidateBrand(candidate);
    const claims = candidateClaims(candidate);
    const priceUnit = candidate.sales_unit === "KG" ? "kg" : "sales package";
    return <div className={`proc-candidate ${selected ? "selected" : ""}`} key={candidate.id}>
      <div className="proc-product-top"><ProductImage product={candidate} small /><span className={`proc-selection ${selected ? "selected" : ""}`}>{selected && <Check size={12} />}{selected ? "Selected" : "Alternative"}</span><span className="proc-card-brand">{brand}</span></div>
      <CompareControl checked={smartComparison.entries.some((entry)=>entry.key===candidate.id)} disabled={mediaBusy || isWorking} onToggle={()=>compareDispatch({type:"toggle",entry:{key:candidate.id,product:candidate,requestedQuantity:line.quantity,requestedUnit:line.unit,lineId:line.id,contextLabel:line.requested_label}})} />
      <h4>{candidate.name}</h4><p className="proc-sku">SKU {candidate.id}</p>
      {(claims.includes("FREE_FROM_LACTOSE") || claims.includes("FREE_FROM_GLUTEN") || claims.includes("VEGAN") || claims.includes("VEGETARIAN")) && <div className="proc-card-claims">{claims.includes("FREE_FROM_LACTOSE") && <span>Lactose-free</span>}{claims.includes("FREE_FROM_GLUTEN") && <span>Gluten-free</span>}{claims.includes("VEGAN") ? <span>Vegan claim</span> : claims.includes("VEGETARIAN") && <span>Vegetarian claim</span>}</div>}
      {reason && <p className="proc-match-reason">{reason}</p>}{candidate.requires_explicit_choice && !selected && <p className="proc-explicit-choice">Related option · your choice required</p>}
      <div className="proc-product-facts"><div><span>{candidate.sales_unit === "KG" ? "Sold as" : "Per sales package"}</span><strong>{packageLabel(candidate,line.unit).replace(" / sales package", "")}</strong></div><div><span>Requested</span><strong>{amount(line.quantity)} {measurementLabel(line.unit)}</strong></div><div><span>Order quantity</span><strong>{candidate.quantity_sales_units == null ? "Conversion needed" : salesQuantity(candidate.quantity_sales_units,candidate.sales_unit)}</strong></div><div><span>Price / {priceUnit}</span><strong>{money(candidate.unit_price)}</strong></div>{candidate.price_per_requested_unit != null && !(candidate.sales_unit === "KG" && line.unit === "kg") && <div><span>Price / {measurementLabel(line.unit)}</span><strong>{formatUnitPrice(candidate.price_per_requested_unit)}</strong></div>}</div>
      {equation ? <p className="proc-card-equation">{equation}</p> : candidate.effective_quantity != null && <p className="proc-card-equation">{amount(candidate.effective_quantity)} {measurementLabel(line.unit)} after rounding</p>}
      {candidate.issues?.length ? <p className="proc-candidate-warning">{readable(candidate.issues[0])}</p> : <p className="proc-product-available"><Check size={13} />{availabilityLabel(candidate.availability)}{candidate.delivery_date && ` · ${dateLabel(candidate.delivery_date)}`}</p>}
      {candidate.surplus_quantity != null && Number(candidate.surplus_quantity) > 0 && <p className="proc-pack-surplus"><span><strong>{amount(candidate.surplus_quantity)} {measurementLabel(line.unit)} extra</strong> {candidate.sales_unit === "KG" ? "after order-lot rounding" : "from whole packages"}</span></p>}
      {candidate.comparison_delta != null && !selected && <p className={`proc-price-comparison ${Number(candidate.comparison_delta) < 0 ? "saves" : ""}`}><strong>Basket change: {money(candidate.comparison_delta)}</strong></p>}
      <div className="proc-product-bottom"><strong>{money(candidate.line_total)}<small>item subtotal</small></strong><button className={selected ? "selected" : ""} disabled={isWorking || !canEdit || selected || blocked} onClick={() => action("select_product", { line_id: line.id, product_id: candidate.id })}>{selected ? <Check size={15} /> : <Plus size={15} />}{selected ? "Selected" : blocked ? "Unavailable" : "Choose"}</button></div>
      <button type="button" className="proc-details-toggle" disabled={mediaBusy || isWorking} aria-haspopup="dialog" onClick={() => setDetails({candidate,quantity:line.quantity,unit:line.unit})}>Product details<ArrowUpRight size={13} /></button>
    </div>;
  }
  function editRequirements() {
    setCartOpen(false);
    window.requestAnimationFrame(() => { entryDate.current?.scrollIntoView({block:"center",behavior:"smooth"}); entryDate.current?.focus({preventScroll:true}); });
  }
  const cartContent = <>

          <div className="proc-cart">{!compactCart && <div className="proc-cart-heading"><ShoppingBasket size={20} /><h3>Cart</h3><span>{session?.cart.items.length || 0}</span></div>}
            {!session ? <div className="proc-cart-empty"><Package size={32} strokeWidth={1.1} /><p>No products yet.</p></div> : <>
              <div className="proc-cart-source"><span className={session.mode === "live" ? "live" : ""} />{session.mode === "live" ? "Live quotation" : "Demo prices"}</div>{session.commercial_context && <details className="proc-commercial-details"><summary>Quotation account</summary><p>{session.commercial_context}</p></details>}
              <div className="proc-cart-items">{session.cart.items.length ? session.cart.items.map((item, i) => <div className="proc-cart-item" key={`${item.id}-${i}`}><div><strong>{item.name}</strong><span>{salesQuantity(item.quantity_sales_units,item.sales_unit)}</span>{item.quantity_breakdown?.length ? item.quantity_breakdown.map((quantity, j) => <div className="proc-cart-quantity-breakdown" key={j}><span>{amount(quantity.requested_quantity)} {measurementLabel(quantity.unit)} requested → {amount(quantity.effective_quantity)} {measurementLabel(quantity.unit)} ordered</span>{Number(quantity.surplus_quantity) > 0 && <em>{amount(quantity.surplus_quantity)} {measurementLabel(quantity.unit)} extra {item.sales_unit === "KG" ? "after order-lot rounding" : "from whole packs"}</em>}{quantity.includes_converted_requirements && <small>Includes shared product requirements converted before rounding.</small>}</div>) : item.effective_quantity != null && <span>{amount(item.effective_quantity)} {measurementLabel(item.unit)} ordered</span>}</div><b>{money(item.line_total)}</b>{canEdit && item.line_ids?.length === 1 && (() => { const line = session.lines.find((candidate) => candidate.id === item.line_ids![0]); return line ? <form className="proc-cart-quantity" key={`cart-quantity-${line.id}-${line.quantity}`} onSubmit={(e) => { e.preventDefault(); const values = new FormData(e.currentTarget); action("set_quantity", { line_id: line.id, quantity: values.get("quantity"), unit: line.unit }); }}><label className="sr-only" htmlFor={`cart-quantity-${line.id}`}>Required quantity for {item.name}</label><input id={`cart-quantity-${line.id}`} name="quantity" type="number" required min="0.001" step="0.001" defaultValue={line.quantity} disabled={isWorking} /><span>{measurementLabel(line.unit)}</span><button type="submit" disabled={isWorking}>Update</button><button type="button" aria-label={`Remove ${line.requested_label} request from cart`} disabled={isWorking} onClick={() => action("remove_line", { line_id: line.id })}><Trash2 size={14} /></button></form> : null; })()}</div>) : <p className="proc-cart-no-items">Choose suitable products to build your cart.</p>}</div>
              <div className="proc-cart-requirements proc-cart-requirements-summary"><dl><div><dt>Requested delivery</dt><dd>{dateLabel(session.constraints.delivery_date)}</dd></div><div><dt>Maximum budget</dt><dd>{session.constraints.budget == null ? "Not set" : money(session.constraints.budget)}</dd></div></dl>{canEdit && <button type="button" onClick={editRequirements}>Edit requirements<ArrowUpRight size={13}/></button>}</div>
              <div className="proc-totals">{unresolvedCount > 0 && <p className="proc-cart-partial">Partial cart · {unresolvedCount} {unresolvedCount === 1 ? "request still needs" : "requests still need"} attention.</p>}<div><span>{session.cart.total == null ? "Item subtotal" : "Cart total"}</span><strong>{money(displayedTotal)}</strong></div>{session.cart.budget_remaining != null && <div className={negativeBudget ? "over-budget" : "under-budget"}><span>{negativeBudget ? "Budget balance (over)" : "Budget remaining"}</span><b>{money(session.cart.budget_remaining)}</b></div>}{hasUnknownCharges && <p className="proc-candidate-warning">Delivery and service charges excluded.</p>}<small>Tax included. Availability is not a reservation.</small></div>
              {receipt ? <div className="proc-success" role="status"><span><CheckCheck size={24} /></span><h4>Simulated order recorded.</h4><p>{receipt.order_id || receipt.id}</p><strong>{money(receipt.total ?? displayedTotal)}</strong><small>This is a prototype receipt. No real supplier order, invoice or payment was created.</small><button onClick={verifyReceipt} disabled={isWorking}>{busy === "verify" ? "Checking receipt…" : verification ? "Verify receipt again" : "Verify receipt"}<RefreshCw size={13} /></button>{verification && <p className="proc-receipt-verified"><ShieldCheck size={14} />The saved receipt matches this recorded order. This verifies our simulator record.</p>}<button onClick={startNew}>Start another request<ArrowRight size={13} /></button></div> : <div className="proc-checkout">
                {approvalDeclined && <div className="proc-approval proc-approval-declined"><ShieldCheck size={18} /><div><strong>Approval declined</strong>{session.rejection?.reason && <p>{session.rejection.reason}</p>}{session.rejection?.approver && <p>Decision by {session.rejection.approver}{session.rejection.rejected_at && ` · ${timestampLabel(session.rejection.rejected_at)}`}</p>}<p>Revise this cart or refresh prices and availability before requesting a new decision.</p></div></div>}
                {changesRequested && <div className="proc-approval proc-approval-declined"><ShieldCheck size={18}/><div><strong>Changes requested</strong><p>{session.decision_history?.slice().reverse().find((decision)=>decision.action === "request_changes" || decision.action === "changes_requested")?.reason || session.assistant_message}</p><p>Revise the cart and request a fresh decision.</p></div></div>}
                {approvalNeeded && !approved && <div className="proc-approval"><ShieldCheck size={18}/><div><strong>{approvalPending ? "Approval requested" : "Approval required"}</strong>{session.approval?.reasons?.map((reason)=><p key={reason}>{approvalReason(reason)}</p>)}<p>{approvalPending ? "A separate manager must review this exact basket. Use a different browser session for the manager decision." : session.approval?.can_request ? "Review the order, then request approval for this exact basket." : "Resolve the remaining requirements before requesting approval."}</p><button type="button" onClick={refreshStatus} disabled={isWorking}>{busy === "status" ? "Checking status…" : "Refresh status"}<RefreshCw size={13}/></button></div></div>}
                {cancelled && <p className="proc-blocked-note">This request was cancelled. Start a new request to continue.</p>}
                {approved && <p className="proc-approved"><ShieldCheck size={15} />This exact cart has manager approval.</p>}
                {session.offer && <div className={`proc-offer-expiry ${offerExpired ? "expired" : ""}`}><Clock3 size={13} /><span>{offerExpired ? "Quote expired. Refresh prices and availability." : <>Quote valid until {new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Helsinki" }).format(new Date(session.offer.expires_at))} Helsinki</>}</span></div>}
                <button className="proc-confirm" disabled={isWorking || mediaBusy || !session.lines.length} onClick={openReview}>{busy === "review" ? <><LoaderCircle className="spin" size={15}/>Opening review…</> : <>Review order<ArrowRight size={16}/></>}</button>
                {!session.can_confirm && !approvalNeeded && !approvalDeclined && !cancelled && <p className="proc-blocked-note">Resolve all product and constraint questions before confirming the full cart.</p>}
                {role === "approver" && session.can_confirm && <p className="proc-blocked-note">Sign in as buyer to confirm the approved cart.</p>}
                <button className="proc-refresh" disabled={isWorking || !canEdit || !session.lines.length} onClick={() => action("quote")}>{busy === "quote" ? <LoaderCircle className="spin" size={13} /> : <RefreshCw size={13} />}Refresh prices & availability</button>
              </div>}
            </>}
          </div>

          {view === "products" && session && <button className="proc-review-cart" onClick={() => onNavigate?.("order")}>Review cart<ArrowRight size={15} /></button>}
          {!role && <button className="proc-access" onClick={onSignIn}>Open your buyer workspace<ArrowUpRight size={16} /></button>}

  </>;
  return (
    <section className="procurement" aria-label="AI purchasing assistant">
      <div hidden={reviewConfirm}>
      <div className="procurement-heading"><h1>{view === "products" ? "Products" : view === "history" ? "History" : "Smart order"}</h1>{session && view !== "history" && <button className="proc-new" onClick={startNew} disabled={isWorking}><Plus size={16} />New request</button>}</div>
      {compactCart && view !== "history" && <button type="button" className="proc-mobile-cart-entry" aria-haspopup="dialog" disabled={mediaBusy || isWorking} onClick={() => setCartOpen(true)}><span><ShoppingBasket size={18} /><span><b>Cart · {session?.cart.items.length || 0} products</b><small>{receipt ? "Recorded" : approvalDeclined ? "Approval declined" : approvalNeeded && !approved ? "Approval needed" : ready ? "Ready to review" : session ? "Needs review" : "No products yet"}</small></span></span><strong>{session ? money(displayedTotal) : "Empty"}<ArrowRight size={16} /></strong></button>}
      <div className={`procurement-grid ${view === "history" ? "is-history" : ""}`}>
        <div className="proc-main">
          {view !== "history" && <form className="proc-entry-constraints" onSubmit={updateConstraints}><label>Delivery date<input ref={entryDate} name="delivery_date" aria-label="Delivery date before ordering" type="date" value={deliveryDate} onInput={(e) => setDeliveryDate(e.currentTarget.value)} onChange={(e) => setDeliveryDate(e.target.value)} disabled={isWorking || role === "approver" || (view === "order" && !canEdit)} /></label><label>Maximum budget (€)<input ref={entryBudget} name="budget" aria-label="Budget before ordering" type="number" min="0" step="0.01" placeholder="Optional" value={budget} onChange={(e) => setBudget(e.target.value)} disabled={isWorking || role === "approver" || (view === "order" && !canEdit)} /></label>{session && !session.receipt && <button type="submit" disabled={isWorking || role !== "buyer"}>Apply</button>}</form>}
          {demoTools && view !== "history" && <details className="proc-demo-tools"><summary>Demo settings</summary><label>Quotation source<select value={mode} onChange={(e) => setMode(e.target.value)} disabled={Boolean(session) || isWorking}><option value="live">Live sponsor sandbox</option><option value="fixture">Authored fixture prices & stock</option></select></label><label className="proc-model"><input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} disabled={Boolean(session) || isWorking} />Use NVIDIA for nonconfidential demo requests</label>{useModel && <p>This request and prior product requirements are sent to NVIDIA's trial service. Nonconfidential demonstration content only.</p>}</details>}
          <div hidden={view !== "products"}><ProductWorkspace active={view === "products"} api={api} role={role} onSignIn={onSignIn} date={deliveryDate} mode={mode} disabled={isWorking} getRequirements={currentRequirements} onAdd={addCatalogProduct} preferencesVersion={preferencesVersion} onInspect={(product,quantity,unit) => setDetails({candidate:product as Candidate,quantity,unit})} /></div>
          {view === "history" && <HistoryPanel api={api} role={role} onSignIn={onSignIn} date={deliveryDate} budget={budget} mode={mode} onOpen={(next) => { accept(next); onNavigate?.("order"); }} onRemoved={(id) => { if (session?.id === id) startNew(); }} />}
          {view === "order" && <>
          <form className="proc-composer" onSubmit={submit} aria-busy={busy === "understand" || busy === "message"}>
            <div className="proc-composer-label"><label htmlFor="procurement-request">{session ? "Make a change or ask for another product" : "What do you need?"}</label></div>
            <textarea id="procurement-request" ref={composer} value={message} onChange={(e) => setMessage(e.target.value)} placeholder={session ? "For example: reduce the butter to 5 kg, or choose the cheaper milk." : "For example: 200 litres of lactose-free milk, 10 kg of butter and 5 kg of cheese delivered by Monday. Show me suitable options."} rows={session ? 2 : 3} maxLength={3000} disabled={isWorking || !canEdit} />
            <MultimodalInput key={session?.id || "new-request"} api={api} onText={(text) => setMessage((current) => current ? current + "\n" + text : text)} onBusyChange={setMediaBusy} disabled={isWorking || role !== "buyer" || !canEdit} requiresSignIn={role !== "buyer"} active={active} onSignIn={onSignIn} onType={() => composer.current?.focus()} />
            {!session && <div className="proc-examples" aria-label="Example purchasing requests">{examples.map((example) => <button type="button" key={example.label} onClick={() => { setMessage(example.text); composer.current?.focus(); }} disabled={isWorking}><span>{example.label}</span><ArrowUpRight size={13} /></button>)}</div>}
            <div className="proc-composer-bottom"><button className="proc-submit" type="submit" disabled={isWorking || mediaBusy || !canEdit || !message.trim()}>{busy === "understand" || busy === "message" ? <><LoaderCircle className="spin" size={16} />Checking…</> : <>{session ? "Update cart" : "Build cart"}<ArrowRight size={16} /></>}</button></div>
          </form>

          </>}
          {view !== "history" && <PreferencesPanel api={api} role={role} onSignIn={onSignIn} disabled={isWorking} applyToNewRequest={applyPreferences} onApplyChange={setApplyPreferences} hasCart={Boolean(session)} onSaved={async (hardChanged) => { setPreferencesVersion((value) => value + 1); if (hardChanged && session && !session.receipt) await action("quote"); }} />}
          {role === "approver" && <div className="proc-notice"><ShieldCheck size={18} /><p>You are signed in as the purchasing approver. Review the saved cart below; sign in as buyer to edit or confirm it.</p></div>}
          {error && <div className="proc-error" role="alert"><div><strong>We could not complete that step.</strong><p>{error}</p></div><button aria-label="Dismiss purchasing error" onClick={() => setError("")}><X size={17} /></button></div>}
          {notice && <div className="proc-notice" role="status"><MessageSquare size={17} /><p>{notice}</p></div>}
          <div hidden={view !== "order"} ref={result} className="proc-results" aria-live="polite">
            {busy === "restore" && <div className="proc-loading"><LoaderCircle className="spin" size={20} />Reopening your saved cart…</div>}

            {session && <>
              <div className={`proc-response ${approvalDeclined ? "is-declined" : ready ? "is-ready" : ""}`}><div className="proc-response-icon">{ready ? <CheckCheck size={20} /> : <MessageSquare size={20} />}</div><div><span className="proc-response-title">{receipt ? "Simulated order recorded" : approvalDeclined ? "Approval declined" : ready ? "Ready to review" : "Review requirements"}</span><p>{session.assistant_message}</p>{session.interpretation_notes?.filter((note) => !/recipe|illustrative/i.test(note)).map((note, i) => <small key={i}>{note}</small>)}{session.model?.message && <small>{session.model.message}</small>}</div></div>
              {receipt && <OrderReceiptSummary receipt={receipt} />}

              {session.recipe_review_required && <div className="proc-question proc-recipe-review"><span className="eyebrow">CHEF REVIEW</span><h3>Review the proposed recipe before buying.</h3>{session.recipe_notes?.map((note, i) => <p key={i}>{note}</p>)}<p>Check ingredient quantities, dietary groups and your kitchen’s preparation needs. Acknowledgement records your review; it does not certify a recipe or product.</p><button disabled={isWorking || !canEdit} onClick={() => action("acknowledge_recipe")}>I have reviewed the proposed recipe<Check size={14} /></button></div>}
              {questions.filter((q) => !q.line_id && !(session.recipe_review_required && /review and acknowledge.*recipe/i.test(q.prompt))).map((q) => <div className="proc-question" key={q.id}><h3>{q.prompt}</h3>{/how many.*(?:both|overlap)|need both vegetarian/i.test(q.prompt) && <form className="proc-overlap-form" onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); action("message", { message: `${form.get("overlap")} overlap` }); }}><label htmlFor={`overlap-${q.id}`}>Diners who need both diets</label><div><input id={`overlap-${q.id}`} name="overlap" type="number" min="0" max="10000" step="1" required defaultValue="0" disabled={isWorking || !canEdit} /><button type="submit" disabled={isWorking || !canEdit}>Apply overlap<Check size={14} /></button></div><small>Enter 0 if the dietary groups do not overlap.</small></form>}<div>{q.options?.map((o) => <button key={o.id} disabled={isWorking || !canEdit} onClick={() => action(o.action, o.payload || {})}>{o.label}<ArrowRight size={14} /></button>)}</div></div>)}
              {view === "order" && <ProductComparison state={smartComparison} dispatch={compareDispatch} api={api} date={deliveryDate} mode={mode} applyPreferences={false} disabled={isWorking || mediaBusy} openRequest={compareOpenRequest} chooseLabel="Choose for this request" onChoose={(entry)=>entry.lineId ? action("select_product",{line_id:entry.lineId,product_id:entry.product.id}) : undefined} onDetails={(entry)=>setDetails({candidate:entry.product,quantity:entry.requestedQuantity,unit:entry.requestedUnit})} />}
              <div className="proc-section-title"><h2>Products <span>{session.lines.length}</span></h2><span className="proc-source-tag">{session.mode === "live" ? "Live quotation" : "Demo prices"}</span></div>
              {session.lines.map((line, index) => <article className="proc-line" key={line.id} aria-label={line.requested_label}>
                <div className="proc-line-heading"><span className="proc-line-number">{String(index + 1).padStart(2, "0")}</span><div><h3>{line.requested_label}</h3><p>{amount(line.quantity)} {measurementLabel(line.unit)} requested <span>·</span> {line.issues?.length || line.status === "CONSTRAINT_CONFLICT" ? "Needs review" : line.selected_product_id ? "Product selected" : line.status.replaceAll("_", " ").toLowerCase()}</p></div>{canEdit && <button className="proc-icon-button" title="Remove this request" aria-label={`Remove ${line.requested_label}`} disabled={isWorking} onClick={() => action("remove_line", { line_id: line.id })}><Trash2 size={16} /></button>}</div>
                {(line.dietary?.length || line.origin || line.max_unit_price != null || line.required_brand || line.preferred_brand || line.preferred_origin || line.require_organic || line.preferred_organic) && <div className="proc-line-constraints" aria-label="Product requirements">{line.dietary?.map((diet) => <span key={diet}>{diet.replaceAll("_", " ")}</span>)}{line.origin && <span>Required origin: {line.origin}</span>}{line.required_brand && <span>Required brand: {line.required_brand}</span>}{line.require_organic && <span>Organic required</span>}{line.preferred_brand && <span className="is-preference">Prefer brand: {line.preferred_brand}</span>}{line.preferred_origin && <span className="is-preference">Prefer origin: {line.preferred_origin}</span>}{line.preferred_organic && <span className="is-preference">Prefer organic</span>}{line.max_unit_price != null && <span>Price limit: {money(line.max_unit_price)} / {measurementLabel(line.unit)}</span>}</div>}
                {line.selection_reason && <p className="proc-selection-reason"><Check size={13} />{line.selection_reason}</p>}
                {canEdit && <form className="proc-query" key={`query-${line.id}-${line.requested_label}`} onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); action("set_query", { line_id: line.id, query: form.get("query") }); }}><label htmlFor={`query-${line.id}`}>Product search</label><div><input id={`query-${line.id}`} name="query" aria-label={`Search products for ${line.requested_label}`} type="text" maxLength={200} required defaultValue={line.requested_label} disabled={isWorking} /><button type="submit" disabled={isWorking}><Search size={13} />Find products</button></div></form>}
                <form className="proc-quantity" key={`quantity-${line.id}-${line.quantity}`} onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); action("set_quantity", { line_id: line.id, quantity: form.get("quantity"), unit: line.unit }); }}><label htmlFor={`quantity-${line.id}`}>Required quantity</label><div><input id={`quantity-${line.id}`} name="quantity" type="number" min="0.001" max="100000" step="0.001" required defaultValue={line.quantity} disabled={isWorking || !canEdit} /><span>{measurementLabel(line.unit)}</span><button type="submit" disabled={isWorking || !canEdit}>Update</button></div></form>
                {!!line.issues?.length && <ul className="proc-issues">{line.issues.map((issue, i) => <li key={i}>{readable(issue)}</li>)}</ul>}
                {questions.filter((q) => q.line_id === line.id).map((q) => <div className="proc-line-question" key={q.id}><strong>{q.prompt}</strong><div>{q.options?.filter((o) => o.action !== "select_product").map((o) => <button key={o.id} disabled={isWorking || !canEdit} onClick={() => action(o.action, { line_id: line.id, ...(o.payload || {}) })}>{o.label}<ArrowRight size={13} /></button>)}</div></div>)}
                {!line.candidates.length ? <div className="proc-no-match"><Package size={22} /><p>No suitable catalog candidates were found. Try a different product description, change the requirement, or remove this item.</p></div> : <CandidateChoices key={`candidates-${line.id}-${line.requested_label}`} line={line} compareCount={smartComparison.entries.length} onCompare={()=>setCompareOpenRequest((value)=>value+1)} disabled={isWorking || mediaBusy} renderCandidate={(candidate) => renderCandidate(line, candidate)} />}
              </article>)}
              {session.lines.length === 0 && <div className="proc-no-match"><p>Your cart is empty. Describe the products you need in the request box above.</p></div>}
            </>}
          </div>
        </div>
        {!compactCart && <aside hidden={view === "history"} className="proc-sidebar" tabIndex={0} aria-label="Shopping cart and order review">{cartContent}</aside>}

      </div>
      </div>
      {reviewConfirm && session && <div className="proc-review-page" ref={reviewRegion} tabIndex={-1}>
        <h1>Review order</h1>
        <button type="button" className="review-page-back" disabled={isWorking} onClick={()=>setReviewConfirm(false)}><ArrowLeft size={16}/>Back to cart</button>
        {error && <p className="proc-error" role="alert">{error}</p>}
        {notice && <p className="proc-notice" role="status">{notice}</p>}
        <OrderReview order={session} onDetails={(candidate,quantity,unit)=>setDetails({candidate,quantity,unit})} disabled={isWorking}>
          <section className="review-actions" aria-label="Order next step"><h3>{reviewStateLabel(session)}</h3>
            {approvalPending && <p>Approval requested for this exact basket. A separate manager browser session can review it in Approvals. Refresh status after their decision.</p>}
            {approved && <p>This exact basket has approval. Only the buyer can submit the simulated order.</p>}
            {approvalDeclined && <p>Approval declined{session.rejection?.reason ? `: ${session.rejection.reason}` : "."} Return to the cart to revise and requote.</p>}
            {changesRequested && <p>Return to the cart to make the requested changes, then request a fresh decision.</p>}
            {session.approval?.can_request && role === "buyer" && !offerExpired && !cancelled && <form onSubmit={(event)=>{event.preventDefault();void requestApproval();}}><label htmlFor="approval-explanation">Explanation for approver (optional)</label><textarea id="approval-explanation" value={approvalExplanation} onChange={(event)=>setApprovalExplanation(event.target.value)} maxLength={500} rows={3} disabled={isWorking}/><p className="review-note">The original requested budget stays {session.constraints.budget == null ? "unset" : money(session.constraints.budget)}. The request covers only this exact quoted basket.</p><button type="submit" className="primary-button" disabled={isWorking}>{busy === "request-approval" ? <><LoaderCircle size={15} className="spin"/>Requesting approval…</> : "Request approval"}</button></form>}
            {offerExpired && <p className="review-problem">Quote expired. Refresh prices and availability before continuing; this creates a fresh decision snapshot.</p>}
            {cancelled && <p>This request is cancelled. Start a new request from the cart.</p>}
            <div className="review-actions-buttons">
              {session.can_confirm && !offerExpired && role === "buyer" && !cancelled && <button type="button" className="primary-button" onClick={confirm} disabled={isWorking}>{busy === "confirm" ? <><LoaderCircle className="spin" size={15}/>Confirming…</> : "Confirm simulated order"}</button>}
              <button type="button" onClick={refreshStatus} disabled={isWorking}>{busy === "status" ? "Checking status…" : "Refresh status"}</button>
              {canEdit && <button type="button" onClick={()=>action("quote")} disabled={isWorking}>{busy === "quote" ? "Refreshing quote…" : "Refresh prices & availability"}</button>}
              <button type="button" onClick={()=>setReviewConfirm(false)} disabled={isWorking}>Edit cart & requirements</button>
              {!cancelled && !receipt && role === "buyer" && <button type="button" onClick={cancelRequest} disabled={isWorking}>{busy === "cancel" ? "Cancelling…" : "Cancel request"}</button>}
            </div><p className="review-note">All orders are simulated. No supplier order, invoice, payment or reservation is created.</p>
          </section>
        </OrderReview>
      </div>}
      {details && <ProductDetailsDialog candidate={details.candidate} requestedQuantity={details.quantity} requestedUnit={details.unit} onClose={() => setDetails(null)} />}
      {compactCart && cartOpen && view !== "history" && !reviewConfirm && <DetailsDialog title="Cart" kind="cart" onClose={() => setCartOpen(false)}>{cartContent}</DetailsDialog>}
    </section>
  );
}
