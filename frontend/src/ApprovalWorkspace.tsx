import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, LoaderCircle, RefreshCw, ShieldCheck, X } from "lucide-react";
import { ProductDetailsDialog } from "./ProductDetailsDialog";
import { formatMoney, formatQuantity, measurementLabel, salesQuantity } from "./productPresentation";
import type { ProductCandidate } from "./productPresentation";
import "./approvals.css";

type API = (path: string, options?: RequestInit) => Promise<any>;
type Entry = { id: string; version: number; created_at: string; requested_date: string; subtotal: string; fingerprint: string; expires_at: string; status: "pending" | "expired"; can_approve: boolean; can_reject: boolean; line_count: number };
type Queue = { items: Entry[]; total: number; offset: number; limit: number };
type Order = {
  id: string; version: number; order_status: string; can_confirm: boolean;
  offer: { fingerprint: string; expires_at: string; total: string; approved?: boolean } | null;
  constraints: { delivery_date?: string; budget?: string | null };
  approval: { status: string; threshold: string };
  rejection?: { reason: string; rejected_at: string; approver: string } | null;
  lines: { id: string; requested_label: string; quantity: string; unit: string; selected_product_id: string | null; dietary: string[]; candidates: ProductCandidate[]; issues: string[] }[];
  cart: { subtotal: string | null; total: string | null; budget_remaining?: string | null; items: { id: string; name: string; quantity_sales_units: string; sales_unit?: string; line_total: string }[] };
  recipe_review_required?: boolean; recipe_notes?: string[];
};
const date = (value?: string) => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Europe/Helsinki" }).format(new Date(value.length === 10 ? value + "T12:00:00+02:00" : value)) : "Not specified";

export function ApprovalWorkspace({ api, onSwitchRole }: { api: API; onSwitchRole: () => void }) {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const [order, setOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState<{ candidate: ProductCandidate; quantity: string; unit: string } | null>(null);
  const alive = useRef(true);
  const selectedId = useRef<string | null>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 15000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    const controller = new AbortController();
    api(`/approvals?limit=20&offset=${offset}`, { signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) setQueue(value);
    }).catch((e) => { if (!controller.signal.aborted) setError((e as Error).message); });
    return () => controller.abort();
  }, [api, offset, refresh]);
  async function open(entry: Entry) {
    selectedId.current = entry.id;
    setBusy(entry.id); setError(""); setNotice(""); setReason("");
    try {
      const next = await api(`/procurement/sessions/${encodeURIComponent(entry.id)}`);
      if (alive.current && selectedId.current === entry.id) setOrder(next);
    } catch (e) { if (alive.current) setError((e as Error).message); }
    finally { if (alive.current) setBusy(""); }
  }
  async function decide(decision: "approve" | "reject") {
    if (!order?.offer || busy) return;
    setBusy(decision); setError("");
    try {
      const next = await api(`/procurement/sessions/${order.id}/${decision}`, { method: "POST", body: JSON.stringify({ fingerprint: order.offer.fingerprint, ...(decision === "reject" ? { reason: reason.trim() } : {}) }) });
      if (!alive.current) return;
      setOrder(next); setRefresh((value) => value + 1);
      setNotice(decision === "approve" ? "Approved. The buyer can review and confirm the simulated order." : "Declined. The buyer must revise and requote this basket.");
    } catch (e) { if (alive.current) setError((e as Error).message); }
    finally { if (alive.current) setBusy(""); }
  }
  async function refreshReview() {
    setError(""); setRefresh((value) => value + 1);
    if (!order) return;
    setBusy("refresh");
    try {
      const next = await api(`/procurement/sessions/${order.id}`);
      if (alive.current) { setOrder(next); setDetails(null); setClock(Date.now()); }
    } catch (e) { if (alive.current) setError((e as Error).message); }
    finally { if (alive.current) setBusy(""); }
  }
  const expired = Boolean(order?.offer && Date.parse(order.offer.expires_at) <= clock);
  const pending = order?.approval.status === "required";
  return <section className="approval-workspace" aria-label="Approval workspace">
    <header className="approval-heading"><div><h1>Approvals</h1><p>{order ? "Review the exact basket before deciding." : "Purchasing requests awaiting your decision."}</p></div><button type="button" onClick={refreshReview} disabled={Boolean(busy)}><RefreshCw size={16} />{order ? "Refresh review" : "Refresh queue"}</button></header>
    {error && <p className="approval-error" role="alert">{error}</p>}
    {notice && <p className="approval-notice" role="status"><Check size={17} />{notice}</p>}
    {order ? <>
      <button type="button" className="approval-back" disabled={Boolean(busy)} onClick={() => { selectedId.current = null; setOrder(null); setNotice(""); }}><ArrowLeft size={16} />All requests</button>
      <div className="approval-review">
        <div className="approval-summary"><div><span>Item subtotal</span><strong>{formatMoney(order.cart.total ?? order.cart.subtotal)}</strong></div><div><span>Requested delivery</span><strong>{date(order.constraints.delivery_date)}</strong></div><div><span>Buyer budget</span><strong>{order.constraints.budget == null ? "Not set" : formatMoney(order.constraints.budget)}</strong></div><div><span>Buyer authority</span><strong>{formatMoney(order.approval.threshold)}</strong></div></div>
        <p className="approval-scope">Tax included. Delivery and service charges excluded. This decision does not place an order.</p>
        <div className="approval-items">{order.lines.map((line) => {
          const candidate = line.candidates.find((item) => item.id === line.selected_product_id);
          return <article key={line.id}><div><h2>{candidate?.name || line.requested_label}</h2><p>{formatQuantity(line.quantity)} {measurementLabel(line.unit)} requested</p>{candidate && <p>{salesQuantity(candidate.quantity_sales_units,candidate.sales_unit)} · {formatMoney(candidate.line_total)}</p>}{line.dietary.length > 0 && <p className="approval-requirements">{line.dietary.map((value) => value.replaceAll("_"," ")).join(" · ")}</p>}{line.issues.map((issue) => <p className="approval-error" key={issue}>{issue}</p>)}</div>{candidate && <button type="button" onClick={() => setDetails({ candidate, quantity: line.quantity, unit: line.unit })}>Product details</button>}</article>;
        })}</div>
        {order.recipe_review_required && <p className="approval-error">The buyer must review the recipe before this basket can proceed.</p>}
        {pending && <div className="approval-decision">{expired && <p role="status">This quote expired. Ask the buyer to refresh it before approving.</p>}<label htmlFor="decline-reason">Reason for declining (optional)</label><textarea id="decline-reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} rows={2} disabled={Boolean(busy)} /><div><button type="button" className="primary-button" disabled={Boolean(busy) || expired || !order.offer} onClick={() => decide("approve")}>{busy === "approve" ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}Approve basket</button><button type="button" disabled={Boolean(busy) || !order.offer} onClick={() => decide("reject")}><X size={16} />Decline basket</button></div></div>}
        {order.approval.status === "approved" && <p className="approval-notice">Approved for the exact current basket.</p>}
        {order.approval.status === "rejected" && <p className="approval-error">Declined{order.rejection?.reason ? `: ${order.rejection.reason}` : "."}</p>}
      </div>
      <button type="button" className="approval-switch" onClick={onSwitchRole}>Switch role<ArrowRight size={16} /></button>
    </> : <>
      {!queue && !error && <p role="status" className="approval-loading"><LoaderCircle size={17} className="spin" />Loading approval requests…</p>}
      {queue?.items.map((entry) => <article key={entry.id} className="approval-entry"><div><h2>{entry.line_count} {entry.line_count === 1 ? "product" : "products"} · {formatMoney(entry.subtotal)}</h2><p>Delivery {date(entry.requested_date)} · {Date.parse(entry.expires_at) <= clock ? "Quote expired" : "Awaiting decision"}</p><small>Request {entry.id.slice(-8)}</small></div><button type="button" disabled={Boolean(busy)} onClick={() => open(entry)}>{busy === entry.id ? <LoaderCircle size={16} className="spin" /> : <>Review request<ArrowRight size={15} /></>}</button></article>)}
      {queue && !queue.items.length && <div className="approval-empty"><ShieldCheck size={28} /><h2>No pending requests</h2><p>Buyer baskets that require approval appear here.</p><button type="button" onClick={onSwitchRole}>Switch role</button></div>}
      {queue && queue.total > queue.limit && <div className="approval-pagination"><button type="button" disabled={!offset || Boolean(busy)} onClick={() => setOffset(Math.max(0,offset - queue.limit))}>Previous</button><span>{offset + 1}–{Math.min(offset + queue.limit,queue.total)} of {queue.total}</span><button type="button" disabled={offset + queue.limit >= queue.total || Boolean(busy)} onClick={() => setOffset(offset + queue.limit)}>Next</button></div>}
    </>}
    {details && <ProductDetailsDialog candidate={details.candidate} requestedQuantity={details.quantity} requestedUnit={details.unit} onClose={() => setDetails(null)} />}
  </section>;
}
