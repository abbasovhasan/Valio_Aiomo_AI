import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowRight, ArrowUpRight, Check, CheckCheck, ChevronDown, Clock3,
  LoaderCircle, MessageSquare, Package, Plus, RefreshCw, ShieldCheck,
  ShoppingBasket, SlidersHorizontal, Sparkles, Trash2, X, Search,
} from "lucide-react";
import "./procurement.css";

type API = (path: string, options?: RequestInit) => Promise<any>;
type Candidate = {
  id: string; name: string; sales_unit?: string; pack_quantity?: string | null;
  pack_unit?: string; quantity_sales_units?: string | null;
  effective_quantity?: string | null; requested_quantity?: string | null; surplus_quantity?: string | null; unit_price?: string | null;
  line_total?: string | null; availability?: unknown; delivery_date?: string | null;
  attributes?: Record<string, unknown> | string[]; issues?: unknown[]; source?: string;
};
type Line = {
  id: string; requested_label: string; quantity: string; unit: string; status: string;
  selected_product_id?: string | null; candidates: Candidate[]; issues?: unknown[];
  selection_reason?: string; dietary?: string[]; origin?: string | null; max_unit_price?: string | null;
};
type CartItem = {
  id: string; name: string; quantity_sales_units: string; effective_quantity?: string;
  unit?: string; unit_price?: string | null; line_total?: string | null; sales_unit?: string;
  quantity_breakdown?: { unit: string; requested_quantity: string; effective_quantity: string; surplus_quantity: string; includes_converted_requirements?: boolean }[];
};
type ProcurementSession = {
  id: string; version: number; order_status: string; assistant_message: string;
  messages: { role: string; text?: string; content?: string }[];
  constraints: { budget?: string | null; currency?: string; delivery_date?: string | null; preferences?: unknown };
  lines: Line[];
  cart: { items: CartItem[]; subtotal?: string | null; total?: string | null; unknown_charges?: unknown; budget_remaining?: string | null };
  clarification_questions?: { id: string; line_id?: string; prompt: string; options?: { id: string; label: string; action: string; payload?: Record<string, unknown> }[] }[];
  approval?: { status?: string; threshold?: string; approved?: boolean };
  can_confirm: boolean; mode: string;
  offer?: { id: string; fingerprint: string; expires_at: string; total: string; status: string } | null;
  receipt?: { id?: string; order_id?: string; total?: string; status?: string; created_at?: string } | null;
  model?: { status?: string; message?: string; provider?: string };
  recipe_review_required?: boolean; recipe_notes?: string[];
  use_model?: boolean; interpretation_source?: string; interpretation_notes?: string[];
};
const savedSessionKey = "aimo-procurement-session";
const examples = [
  { label: "Stock the breakfast kitchen", text: "I need 200 litres of lactose-free milk, 10 kg of butter and 5 kg of cheese delivered by Monday. Choose the cheapest suitable products." },
  { label: "A simple milk order", text: "I need 1,000 litres of lactose-free milk delivered by Monday. Choose the most affordable suitable option." },
  { label: "Bolognese for 500 diners", text: "I need ingredients for spaghetti bolognese for 500 people. 20% vegetarian and 10% gluten-free, with an overlap: 20 diners. Delivered by Monday. Prefer Finnish ingredients." },
];
const money = (value: unknown) => value == null ? "Not quoted" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR" }).format(Number(value));
const amount = (value: unknown) => value == null ? "Unknown" : new Intl.NumberFormat("en-FI", { maximumFractionDigits: 3 }).format(Number(value));
function readable(value: unknown): string {
  if (value == null) return "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "Unknown";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(readable).join(", ");
  const obj = value as Record<string, unknown>;
  return String(obj.message || obj.detail || obj.label || obj.status || "Needs review");
}
function dateLabel(value: string | null | undefined) {
  if (!value) return "Date not set";
  const date = new Date(value.length === 10 ? value + "T12:00:00+02:00" : value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Helsinki" }).format(date);
}
function remember(id: string | null) {
  try { id ? localStorage.setItem(savedSessionKey, id) : localStorage.removeItem(savedSessionKey); } catch { /* The server remains the source of truth when storage is unavailable. */ }
}
function recall() {
  try { return localStorage.getItem(savedSessionKey); } catch { return null; }
}

export function ProcurementDesk({ api, role, onSignIn, onUpdated, initialSessionId }: {
  api: API; role: string | null; onSignIn: () => void; onUpdated?: () => void | Promise<void>; initialSessionId?: string | null;
}) {
  const [session, setSession] = useState<ProcurementSession | null>(null);
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState("fixture");
  const [useModel, setUseModel] = useState(true);
  const [deliveryDate, setDeliveryDate] = useState("");
  const [budget, setBudget] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState<string | null>(null);
  const [reviewConfirm, setReviewConfirm] = useState(false);
  const [confirmedReceipt, setConfirmedReceipt] = useState<any>(null);
  const [verification, setVerification] = useState<{ integrity_valid: boolean; scope_valid: boolean; receipt_id?: string } | null>(null);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [clock, setClock] = useState(Date.now());
  const requestKeys = useRef<Record<string, string>>({});
  const composer = useRef<HTMLTextAreaElement>(null);
  const result = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<ProcurementSession | null>(null);
  const importedSession = useRef<string | null>(null);
  sessionRef.current = session;
  function accept(next: ProcurementSession) {
    setSession(next);
    remember(next.id);
    setMode(next.mode);
    if (next.use_model !== undefined) setUseModel(next.use_model);
    setBudget(next.constraints?.budget ?? "");
    setDeliveryDate(next.constraints?.delivery_date || "");
    setReviewConfirm(false);
    setVerification(null);
    setConfirmedReceipt(next.receipt || null);
  }
  useEffect(() => {
    if (!role) { setSession(null); setConfirmedReceipt(null); setVerification(null); return; }
    const incoming = initialSessionId && initialSessionId !== importedSession.current ? initialSessionId : null;
    const id = incoming || recall();
    if (!id) return;
    if (incoming) { importedSession.current = incoming; setSession(null); setConfirmedReceipt(null); setVerification(null); }
    let cancelled = false;
    setBusy("restore");
    api(`/procurement/sessions/${encodeURIComponent(id)}`)
      .then((data) => { if (!cancelled) accept(data); })
      .catch(() => { if (!cancelled) setNotice("Your saved cart could not be reopened. Check the connection and reload, or begin a new purchasing request."); })
      .finally(() => { if (!cancelled) setBusy(""); });
    return () => { cancelled = true; };
  }, [role, api, initialSessionId]);
  useEffect(() => {
    if (!session?.offer || session.receipt) return;
    setClock(Date.now());
    const interval = window.setInterval(() => setClock(Date.now()), 15000);
    return () => window.clearInterval(interval);
  }, [session?.offer?.fingerprint, session?.receipt]);
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
      await onUpdated?.();
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
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    if (session) { await action("message", { message: message.trim() }); return; }
    const data = await perform("understand", () => api("/procurement/sessions", {
      method: "POST", body: JSON.stringify({ message: message.trim(), mode, ...(deliveryDate ? { date: deliveryDate } : {}), ...(budget ? { budget } : {}), use_model: mode === "live" && useModel }),
    }), true);
    if (data) result.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function updateConstraints(e: FormEvent) {
    e.preventDefault();
    if (!session) return;
    // Each server action recalculates the whole cart and advances its version.
    setBusy("constraints"); setError(""); setNotice("");
    try {
      let current = session;
      if ((current.constraints.delivery_date || "") !== deliveryDate) current = await api(`/procurement/sessions/${current.id}/actions`, { method: "POST", body: JSON.stringify({ version: current.version, action: "set_date", date: deliveryDate }) });
      if (String(current.constraints.budget ?? "") !== budget) current = await api(`/procurement/sessions/${current.id}/actions`, { method: "POST", body: JSON.stringify({ version: current.version, action: "set_budget", budget: budget || null }) });
      accept(current); setNotice("Budget and delivery requirements updated. All affected products were checked again.");
    } catch (e) {
      setError((e as Error).message);
      try { accept(await api(`/procurement/sessions/${session.id}`)); } catch { /* Keep the current cart available. */ }
    } finally { setBusy(""); }
  }
  async function approve() {
    if (!session?.offer) return;
    await perform("approve", () => api(`/procurement/sessions/${session.id}/approve`, { method: "POST", body: JSON.stringify({ fingerprint: session.offer!.fingerprint }) }));
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
    setSession(null); remember(null); setMessage(""); setConfirmedReceipt(null);
    setError(""); setNotice(""); setReviewConfirm(false); setVerification(null); composer.current?.focus();
  }
  const receipt = confirmedReceipt || session?.receipt;
  const canEdit = role !== "approver" && !receipt;
  const approvalNeeded = session?.approval?.status === "required" || session?.offer?.status === "approval_required";
  const approved = session?.approval?.approved || session?.approval?.status === "approved";
  const offerExpired = Boolean(session?.offer && Date.parse(session.offer.expires_at) <= clock);
  const ready = session?.order_status === "READY_TO_ORDER";
  const questions = session?.clarification_questions || [];
  const unresolvedCount = session?.lines.filter((line) => !line.selected_product_id || Boolean(line.issues?.length)).length || 0;
  const hasUnknownCharges = Boolean(session?.cart.unknown_charges && (!Array.isArray(session.cart.unknown_charges) || session.cart.unknown_charges.length));
  const displayedTotal = session?.cart.total ?? session?.cart.subtotal;
  const negativeBudget = session?.cart.budget_remaining != null && Number(session.cart.budget_remaining) < 0;
  const isWorking = Boolean(busy);
  return (
    <section className="procurement" aria-label="AI purchasing assistant">
      <div className="procurement-heading">
        <div><span className="eyebrow">YOUR KITCHEN. ONE CLEAR CART.</span><h2>Tell us what <em>you need.</em></h2><p>Describe the order. Compare real catalog products. Review every quantity before confirming.</p></div>
        {session && <button className="proc-new" onClick={startNew} disabled={isWorking}><Plus size={16} /> New request</button>}
      </div>
      <div className="procurement-grid">
        <div className="proc-main">
          <form className="proc-composer" onSubmit={submit} aria-busy={busy === "understand" || busy === "message"}>
            <div className="proc-composer-label"><label htmlFor="procurement-request"><Sparkles size={16} />{session ? "Make a change or ask for another product" : "What does your kitchen need?"}</label><span>PLAIN LANGUAGE WELCOME</span></div>
            <textarea id="procurement-request" ref={composer} value={message} onChange={(e) => setMessage(e.target.value)} placeholder={session ? "For example: reduce the butter to 5 kg, or choose the cheaper milk." : "For example: 200 litres of lactose-free milk, 10 kg of butter and 5 kg of cheese delivered by Monday. Choose the cheapest suitable products."} rows={session ? 2 : 3} maxLength={3000} disabled={isWorking || !canEdit} />
            {!session && <div className="proc-examples" aria-label="Example purchasing requests">{examples.map((example) => <button type="button" key={example.label} onClick={() => { setMessage(example.text); composer.current?.focus(); }} disabled={isWorking}><span>{example.label}</span><ArrowUpRight size={13} /></button>)}</div>}
            <div className="proc-composer-bottom"><button className="proc-settings-toggle" type="button" onClick={() => setShowSettings(!showSettings)} aria-expanded={showSettings}><SlidersHorizontal size={14} />{mode === "live" ? "Live sandbox" : "Rehearsal fixture"}<ChevronDown size={13} /></button><button className="proc-submit" type="submit" disabled={isWorking || !canEdit || !message.trim()}>{busy === "understand" || busy === "message" ? <><LoaderCircle className="spin" size={16} /> Checking your request…</> : <>{session ? "Update my cart" : "Build my cart"}<ArrowRight size={16} /></>}</button></div>
            {showSettings && <div className="proc-settings"><label>Product price & stock source<select value={mode} onChange={(e) => setMode(e.target.value)} disabled={Boolean(session) || isWorking}><option value="fixture">Rehearsal fixture · authored prices & stock</option><option value="live">Live Valio sponsor sandbox</option></select></label>{!session && <div className="proc-field-pair"><label>Deliver by (optional)<input aria-label="Initial delivery date" type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} /></label><label>Maximum budget (€)<input aria-label="Initial maximum budget" type="number" min="0.01" step="0.01" placeholder="Optional" value={budget} onChange={(e) => setBudget(e.target.value)} /></label></div>}<label className="proc-model"><input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} disabled={mode !== "live" || isWorking || Boolean(session)} />Use NVIDIA to interpret the request in live mode</label><p>{mode === "fixture" ? "Catalog identities are supplied challenge data. Prices and stock are authored rehearsal values." : "Live price and availability reads use the Valio challenge sandbox. No real supplier order is placed."}{session && " Start a new request to change the evidence source."}</p></div>}
          </form>
          {role === "approver" && <div className="proc-notice"><ShieldCheck size={18} /><p>You are signed in as the purchasing approver. Review the saved cart below; sign in as buyer to edit or confirm it.</p></div>}
          {error && <div className="proc-error" role="alert"><div><strong>We could not complete that step.</strong><p>{error}</p></div><button aria-label="Dismiss purchasing error" onClick={() => setError("")}><X size={17} /></button></div>}
          {notice && <div className="proc-notice" role="status"><MessageSquare size={17} /><p>{notice}</p></div>}
          <div ref={result} className="proc-results" aria-live="polite">
            {busy === "restore" && <div className="proc-loading"><LoaderCircle className="spin" size={20} />Reopening your saved cart…</div>}
            {!session && busy !== "restore" && <div className="proc-empty"><div className="proc-empty-art" aria-hidden="true"><div className="proc-art-orbit" /><div className="proc-art-basket"><ShoppingBasket size={54} strokeWidth={1.1} /><span><Check size={14} /></span></div><span className="proc-art-note note-a">A little less searching.</span><span className="proc-art-note note-b">A lot more clarity.</span></div><div><span className="eyebrow">FROM REQUEST TO READY FOR REVIEW</span><h3>Make room for <em>better buying.</em></h3><p>Package sizes, suitable alternatives, price and availability belong in one place. Your assistant prepares the details; you make the final call.</p></div><div className="proc-empty-steps"><span><b>01</b> Describe the need</span><span><b>02</b> Resolve the choices</span><span><b>03</b> Confirm the cart</span></div></div>}
            {session && <>
              <div className={`proc-response ${ready ? "is-ready" : ""}`}><div className="proc-response-icon">{ready ? <CheckCheck size={20} /> : <MessageSquare size={20} />}</div><div><span className="eyebrow">{receipt ? "SIMULATED ORDER RECORDED" : ready ? "YOUR CART IS READY TO REVIEW" : session.order_status === "CANNOT_FULFILL" ? "LET’S RESOLVE THE REMAINING REQUIREMENTS" : "A FEW DETAILS TO GET RIGHT"}</span><p>{session.assistant_message}</p>{session.interpretation_notes?.filter((note) => !/recipe|illustrative/i.test(note)).map((note, i) => <small key={i}>{note}</small>)}{session.interpretation_source && <small>{session.interpretation_source}</small>}{session.model?.message && <small>{session.model.message}</small>}</div></div>
              {session.messages?.length > 0 && <div className="proc-conversation"><button onClick={() => setConversationOpen(!conversationOpen)} aria-expanded={conversationOpen}><MessageSquare size={14} /> Request history <span>{session.messages.length}</span><ChevronDown size={14} /></button>{conversationOpen && <ol>{session.messages.map((entry, i) => <li className={entry.role === "user" ? "from-user" : ""} key={i}><strong>{entry.role === "user" ? "You" : "Purchasing assistant"}</strong><p>{entry.text || entry.content}</p></li>)}</ol>}</div>}
              {session.recipe_review_required && <div className="proc-question proc-recipe-review"><span className="eyebrow">CHEF REVIEW</span><h3>Review the proposed recipe before buying.</h3>{session.recipe_notes?.map((note, i) => <p key={i}>{note}</p>)}<p>Check ingredient quantities, dietary groups and your kitchen’s preparation needs. Acknowledgement records your review; it does not certify a recipe or product.</p><button disabled={isWorking || !canEdit} onClick={() => action("acknowledge_recipe")}>I have reviewed the proposed recipe<Check size={14} /></button></div>}
              {questions.filter((q) => !q.line_id && !(session.recipe_review_required && /review and acknowledge.*recipe/i.test(q.prompt))).map((q) => <div className="proc-question" key={q.id}><h3>{q.prompt}</h3><div>{q.options?.map((o) => <button key={o.id} disabled={isWorking || !canEdit} onClick={() => action(o.action, o.payload || {})}>{o.label}<ArrowRight size={14} /></button>)}</div></div>)}
              <div className="proc-section-title"><div><span className="eyebrow">THE PRODUCT WORKSPACE</span><h3>{session.lines.length} {session.lines.length === 1 ? "request" : "requests"}, every detail visible.</h3></div><span className="proc-source-tag">{session.mode === "live" ? "LIVE SANDBOX" : "REHEARSAL FIXTURE"}</span></div>
              {canEdit && session.lines.length > 0 && <p className="proc-workspace-note">Refine a product search to find other candidates. Its quantity, dietary and origin requirements stay in place.</p>}
              {session.lines.map((line, index) => <article className="proc-line" key={line.id} aria-label={line.requested_label}>
                <div className="proc-line-heading"><span className="proc-line-number">{String(index + 1).padStart(2, "0")}</span><div><h3>{line.requested_label}</h3><p>{amount(line.quantity)} {line.unit} requested <span>·</span> {line.selected_product_id ? "Product selected" : line.status.replaceAll("_", " ").toLowerCase()}</p></div>{canEdit && <button className="proc-icon-button" title="Remove this request" aria-label={`Remove ${line.requested_label}`} disabled={isWorking} onClick={() => action("remove_line", { line_id: line.id })}><Trash2 size={16} /></button>}</div>
                {(line.dietary?.length || line.origin || line.max_unit_price != null) && <div className="proc-line-constraints" aria-label="Product requirements">{line.dietary?.map((diet) => <span key={diet}>{diet.replaceAll("_", " ")}</span>)}{line.origin && <span>Origin: {line.origin}</span>}{line.max_unit_price != null && <span>Price limit: {money(line.max_unit_price)} / {line.unit}</span>}</div>}
                {line.selection_reason && <p className="proc-selection-reason"><Check size={13} />{line.selection_reason}</p>}
                {canEdit && <form className="proc-query" key={`${line.id}-${line.requested_label}`} onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); action("set_query", { line_id: line.id, query: form.get("query") }); }}><label htmlFor={`query-${line.id}`}>Product search</label><div><input id={`query-${line.id}`} name="query" aria-label={`Search products for ${line.requested_label}`} type="text" maxLength={120} required defaultValue={line.requested_label} disabled={isWorking} /><button type="submit" disabled={isWorking}><Search size={13} />Find products</button></div></form>}
                <form className="proc-quantity" key={`${line.id}-${line.quantity}`} onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); action("set_quantity", { line_id: line.id, quantity: form.get("quantity"), unit: line.unit }); }}><label htmlFor={`quantity-${line.id}`}>Required quantity</label><div><input id={`quantity-${line.id}`} name="quantity" type="number" min="0.001" max="100000" step="0.001" required defaultValue={line.quantity} disabled={isWorking || !canEdit} /><span>{line.unit}</span><button type="submit" disabled={isWorking || !canEdit}>Update</button></div></form>
                {!!line.issues?.length && <ul className="proc-issues">{line.issues.map((issue, i) => <li key={i}>{readable(issue)}</li>)}</ul>}
                {questions.filter((q) => q.line_id === line.id).map((q) => <div className="proc-line-question" key={q.id}><strong>{q.prompt}</strong><div>{q.options?.filter((o) => o.action !== "select_product").map((o) => <button key={o.id} disabled={isWorking || !canEdit} onClick={() => action(o.action, { line_id: line.id, ...(o.payload || {}) })}>{o.label}<ArrowRight size={13} /></button>)}</div></div>)}
                {!line.candidates.length ? <div className="proc-no-match"><Package size={22} /><p>No suitable catalog candidates were found. Try a different product description, change the requirement, or remove this item.</p></div> : <div className="proc-candidates">{line.candidates.map((candidate) => {
                  const selected = line.selected_product_id === candidate.id;
                  const candidateDetails = candidate.attributes ? (Array.isArray(candidate.attributes) ? candidate.attributes.map((v) => ["Attribute", v]) : Object.entries(candidate.attributes)) : [];
                  return <div className={`proc-candidate ${selected ? "selected" : ""}`} key={candidate.id}>
                    <div className="proc-product-top"><span className="proc-product-icon"><Package size={23} strokeWidth={1.2} /></span><span className={`proc-selection ${selected ? "selected" : ""}`}>{selected && <Check size={12} />}{selected ? "Selected" : "Alternative"}</span></div>
                    <h4>{candidate.name}</h4><p className="proc-sku">SKU {candidate.id}</p>
                    <div className="proc-product-facts"><div><span>Sales package</span><strong>{candidate.pack_quantity != null ? `${amount(candidate.pack_quantity)} ${candidate.pack_unit || line.unit}` : candidate.sales_unit || "Unknown"}</strong></div><div><span>Order quantity</span><strong>{candidate.quantity_sales_units == null ? "Conversion needed" : `${amount(candidate.quantity_sales_units)} ${candidate.sales_unit || "packs"}`}</strong></div><div><span>Quantity after rounding</span><strong>{candidate.effective_quantity == null ? "Unknown" : `${amount(candidate.effective_quantity)} ${line.unit}`}</strong></div><div><span>Price / sales unit</span><strong>{money(candidate.unit_price)}</strong></div></div>
                    {candidate.issues?.length ? <p className="proc-candidate-warning">{readable(candidate.issues[0])}</p> : <p className="proc-product-available"><Check size={13} />{candidate.availability == null ? "Stock not verified" : readable(candidate.availability)}{candidate.delivery_date && ` · ${dateLabel(candidate.delivery_date)}`}</p>}
                    {candidate.surplus_quantity != null && Number(candidate.surplus_quantity) > 0 && <p className="proc-pack-surplus"><Package size={13} /><span><strong>{amount(candidate.surplus_quantity)} {line.unit} extra</strong> from whole packs</span></p>}
                    <div className="proc-product-bottom"><strong>{money(candidate.line_total)}<small>line total</small></strong><button className={selected ? "selected" : ""} disabled={isWorking || !canEdit || selected || Boolean(candidate.issues?.length)} onClick={() => action("select_product", { line_id: line.id, product_id: candidate.id })}>{selected ? <Check size={15} /> : <Plus size={15} />}{selected ? "Selected" : candidate.issues?.length ? "Blocked" : "Choose"}</button></div>
                    <button className="proc-details-toggle" onClick={() => setDetails(details === `${line.id}-${candidate.id}` ? null : `${line.id}-${candidate.id}`)} aria-expanded={details === `${line.id}-${candidate.id}`}>Product evidence<ChevronDown size={12} /></button>
                    {details === `${line.id}-${candidate.id}` && <div className="proc-product-details">{candidateDetails.map(([key, value], i) => <p key={i}><strong>{String(key).replaceAll("_", " ")}</strong><span>{readable(value).replaceAll("_", " ")}</span></p>)}<p><strong>Source</strong><span>{candidate.source || "Challenge catalog"}</span></p>{candidate.issues?.map((issue, i) => <p className="proc-candidate-warning" key={i}>{readable(issue)}</p>)}<small>Supplier evidence supports product selection. Check all dietary requirements and kitchen preparation needs.</small></div>}
                  </div>;
                })}</div>}
              </article>)}
              {session.lines.length === 0 && <div className="proc-no-match"><p>Your cart is empty. Describe the products you need in the request box above.</p></div>}
            </>}
          </div>
        </div>
        <aside className="proc-sidebar" aria-label="Shopping cart and order review">
          <div className="proc-cart"><div className="proc-cart-heading"><ShoppingBasket size={20} /><h3>Your shopping cart</h3><span>{session?.cart.items.length || 0}</span></div>
            {!session ? <div className="proc-cart-empty"><Package size={32} strokeWidth={1.1} /><p>Good things start<br />with a clear request.</p><small>Your selected products will appear here.</small></div> : <>
              <div className="proc-cart-source"><span className={session.mode === "live" ? "live" : ""} />{session.mode === "live" ? "Live sandbox quotation" : "Authored rehearsal quotation"}</div>
              <div className="proc-cart-items">{session.cart.items.length ? session.cart.items.map((item, i) => <div className="proc-cart-item" key={`${item.id}-${i}`}><div><strong>{item.name}</strong><span>{amount(item.quantity_sales_units)} {item.sales_unit || "packs"}</span>{item.quantity_breakdown?.length ? item.quantity_breakdown.map((quantity, j) => <div className="proc-cart-quantity-breakdown" key={j}><span>{amount(quantity.requested_quantity)} {quantity.unit} requested → {amount(quantity.effective_quantity)} {quantity.unit} ordered</span>{Number(quantity.surplus_quantity) > 0 && <em>{amount(quantity.surplus_quantity)} {quantity.unit} extra from whole packs</em>}{quantity.includes_converted_requirements && <small>Includes shared product requirements converted before rounding.</small>}</div>) : item.effective_quantity != null && <span>{amount(item.effective_quantity)} {item.unit || ""} ordered</span>}</div><b>{money(item.line_total)}</b></div>) : <p className="proc-cart-no-items">Choose suitable products to build your cart.</p>}</div>
              <form className="proc-cart-requirements" onSubmit={updateConstraints}><label>Requested delivery<input type="date" aria-label="Cart delivery date" required value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} disabled={isWorking || !canEdit} /></label><label>Maximum budget (€)<input type="number" aria-label="Cart maximum budget" min="0.01" step="0.01" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="No budget set" disabled={isWorking || !canEdit} /></label>{canEdit && <button type="submit" disabled={isWorking}>Apply requirements<ArrowRight size={13} /></button>}</form>
              <div className="proc-totals">{unresolvedCount > 0 && <p className="proc-cart-partial">Partial cart · {unresolvedCount} {unresolvedCount === 1 ? "request still needs" : "requests still need"} attention.</p>}<div><span>{session.cart.total == null ? "Item subtotal" : "Cart total"}</span><strong>{money(displayedTotal)}</strong></div>{session.constraints.budget != null && <div><span>Budget</span><b>{money(session.constraints.budget)}</b></div>}{session.cart.budget_remaining != null && <div className={negativeBudget ? "over-budget" : "under-budget"}><span>{negativeBudget ? "Budget balance (over)" : "Budget remaining"}</span><b>{money(session.cart.budget_remaining)}</b></div>}{hasUnknownCharges && <p className="proc-candidate-warning">Delivery and service charges are excluded. This simulation confirms the quoted item subtotal only.</p>}<small>Quoted item prices include tax. Availability is an estimate, never a reservation.</small></div>
              {receipt ? <div className="proc-success" role="status"><span><CheckCheck size={24} /></span><h4>Simulated order recorded.</h4><p>{receipt.order_id || receipt.id}</p><strong>{money(receipt.total ?? displayedTotal)}</strong><small>This is a prototype receipt. No real supplier order, invoice or payment was created.</small><button onClick={verifyReceipt} disabled={isWorking}>{busy === "verify" ? "Checking receipt…" : verification ? "Verify receipt again" : "Verify receipt"}<RefreshCw size={13} /></button>{verification && <p className="proc-receipt-verified"><ShieldCheck size={14} />The saved receipt matches this recorded order. This verifies our simulator record.</p>}<button onClick={startNew}>Start another request<ArrowRight size={13} /></button></div> : <div className="proc-checkout">
                {approvalNeeded && !approved && <div className="proc-approval"><ShieldCheck size={18} /><div><strong>Purchasing approval needed</strong><p>This exact cart exceeds the buyer's authority. A separate approver must review it.{session.approval?.threshold != null && ` Autonomous limit: ${money(session.approval.threshold)}.`}</p>{role === "approver" ? <button onClick={approve} disabled={isWorking || !session.offer || offerExpired}>{busy === "approve" ? "Approving…" : "Approve this exact cart"}<Check size={14} /></button> : <button onClick={onSignIn}>Sign in as approver<ArrowUpRight size={13} /></button>}</div></div>}
                {approved && <p className="proc-approved"><ShieldCheck size={15} />This exact cart has manager approval.</p>}
                {session.offer && <div className={`proc-offer-expiry ${offerExpired ? "expired" : ""}`}><Clock3 size={13} /><span>{offerExpired ? "Quote expired. Refresh prices and availability." : <>Quote valid until {new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Helsinki" }).format(new Date(session.offer.expires_at))} Helsinki</>}</span></div>}
                {reviewConfirm ? <div className="proc-confirm-review"><h4>Confirm this simulated order?</h4><p>{session.cart.items.length} selected products · {money(displayedTotal)} in items · requested {dateLabel(session.constraints.delivery_date)}.</p><button className="proc-confirm" onClick={confirm} disabled={isWorking || offerExpired}>{busy === "confirm" ? <LoaderCircle className="spin" size={15} /> : <CheckCheck size={16} />}Confirm simulated order</button><button className="proc-cancel" disabled={isWorking} onClick={() => setReviewConfirm(false)}>Keep reviewing</button></div> : <button className="proc-confirm" disabled={isWorking || !session.can_confirm || role !== "buyer" || offerExpired} onClick={() => setReviewConfirm(true)}>Review & confirm<ArrowRight size={16} /></button>}
                {!session.can_confirm && !approvalNeeded && <p className="proc-blocked-note">Resolve all product and constraint questions before confirming the full cart.</p>}
                {role === "approver" && session.can_confirm && <p className="proc-blocked-note">Sign in as buyer to confirm the approved cart.</p>}
                <button className="proc-refresh" disabled={isWorking || !canEdit || !session.lines.length} onClick={() => action("quote")}>{busy === "quote" ? <LoaderCircle className="spin" size={13} /> : <RefreshCw size={13} />}Refresh prices & availability</button>
              </div>}
            </>}
          </div>
          <div className="proc-trust"><ShieldCheck size={19} /><div><strong>You stay in control.</strong><p>Only a complete, validated item basket can be confirmed. Important changes require a fresh quote and any necessary approval.</p><p>All orders in this prototype are simulated.</p></div></div>
          {!role && <button className="proc-access" onClick={onSignIn}>Open your buyer workspace<ArrowUpRight size={16} /></button>}
        </aside>
      </div>
    </section>
  );
}
