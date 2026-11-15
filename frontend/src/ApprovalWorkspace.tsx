import { useEffect, useReducer, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, LoaderCircle, RefreshCw, ShieldCheck, X } from "lucide-react";
import { ProductDetailsDialog } from "./ProductDetailsDialog";
import { ProductComparison } from "./ProductComparison";
import { comparisonReducer, emptyComparison } from "./comparisonSelection";
import { OrderReview, approvalReason, reviewDate } from "./OrderReview";
import type { ReviewSnapshot } from "./OrderReview";
import { formatMoney } from "./productPresentation";
import type { ProductCandidate } from "./productPresentation";
import "./approvals.css";

type API = (path: string, options?: RequestInit) => Promise<any>;
type Entry = {
  id: string; version: number; created_at: string; requested_date: string; subtotal: string; fingerprint: string; expires_at: string;
  status: "pending" | "expired"; can_approve: boolean; can_reject: boolean; can_request_changes?: boolean; decision_blockers?: string[]; line_count: number;
  buyer_name?: string; request_title?: string; submitted_at?: string | null; reasons?: string[]; requested_budget?: string | null; budget_excess?: string; explanation?: string | null; authority_limit?: string; cumulative_remaining?: string;
};
type Queue = { items: Entry[]; total: number; offset: number; limit: number };
type Order = ReviewSnapshot & {
  can_confirm: boolean; mode: string;
  offer: { fingerprint: string; expires_at: string; total: string; approved?: boolean } | null;
  rejection?: { reason: string; rejected_at: string; approver: string } | null;
};

export function ApprovalWorkspace({ api, onSwitchRole }: { api: API; onSwitchRole: () => void }) {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const [order, setOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState<{ candidate: ProductCandidate; quantity: string; unit: string } | null>(null);
  const [comparison, compareDispatch] = useReducer(comparisonReducer,emptyComparison);
  const [compareOpenRequest, setCompareOpenRequest] = useState(0);
  const review = useRef<HTMLDivElement>(null);
  const alive = useRef(true);
  const selectedId = useRef<string | null>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 15000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    const controller = new AbortController(); setLoadingQueue(true);
    api(`/approvals?limit=20&offset=${offset}`, { signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) setQueue(value);
    }).catch((e) => { if (!controller.signal.aborted) setError((e as Error).message); }).finally(()=>{if(!controller.signal.aborted)setLoadingQueue(false);});
    return () => controller.abort();
  }, [api, offset, refresh]);
  useEffect(()=>{if(order){review.current?.focus({preventScroll:true});review.current?.scrollIntoView({block:"start"});}},[order?.id]);
  async function open(entry: Entry) {
    if(busy) return;
    selectedId.current = entry.id;
    setBusy(entry.id); setError(""); setNotice(""); setReason(""); compareDispatch({type:"clear"});
    try {
      const next = await api(`/procurement/sessions/${encodeURIComponent(entry.id)}`);
      if (alive.current && selectedId.current === entry.id) setOrder(next);
    } catch (e) { if (alive.current) setError((e as Error).message); }
    finally { if (alive.current) setBusy(""); }
  }
  async function decide(decision: "approve" | "reject" | "request-changes") {
    if (!order?.offer || busy || order.approval?.can_decide === false || (decision === "request-changes" && !reason.trim())) return;
    if (decision === "approve" && order.approval?.blockers?.length) return;
    const id=order.id;
    setBusy(decision); setError(""); setNotice("");
    try {
      const next = await api(`/procurement/sessions/${id}/${decision}`, { method: "POST", body: JSON.stringify({ version:order.version, fingerprint: order.offer.fingerprint, ...(decision !== "approve" ? { reason: reason.trim() } : {}) }) });
      if (!alive.current || selectedId.current !== id) return;
      setOrder(next); compareDispatch({type:"clear"}); setRefresh((value) => value + 1);
      setNotice(decision === "approve" ? "Approved for this exact basket. The buyer must separately confirm the simulated order." : decision === "request-changes" ? "Changes requested. The buyer must revise and request a fresh decision." : "Declined. The buyer must revise and request a fresh decision.");
    } catch (e) {
      if (!alive.current) return;
      setError((e as Error).message);
      if(/version|changed|fingerprint|expired/i.test((e as Error).message)) {
        try { const next=await api(`/procurement/sessions/${id}`); if(alive.current && selectedId.current===id){setOrder(next);compareDispatch({type:"clear"});} } catch { /* Keep the decision error and allow an explicit retry. */ }
      }
    } finally { if (alive.current) setBusy(""); }
  }
  async function refreshReview() {
    if(busy) return;
    setError(""); setRefresh((value) => value + 1);
    if (!order) return;
    setBusy("refresh"); const id=order.id;
    try {
      const next = await api(`/procurement/sessions/${id}`);
      if (alive.current && selectedId.current===id) { setOrder(next); setDetails(null); compareDispatch({type:"clear"}); setClock(Date.now()); }
    } catch (e) { if (alive.current) setError((e as Error).message); }
    finally { if (alive.current) setBusy(""); }
  }
  const expired = Boolean(order?.offer && Date.parse(order.offer.expires_at) <= clock);
  const pending = order?.approval?.pending === true;
  const canDecide = pending && order?.approval?.can_decide !== false;
  const blockedDecision = order?.approval?.decision_blockers || [];
  return <section className="approval-workspace" aria-label="Approval workspace">
    <header className="approval-heading"><div><h1>{order ? "Review order" : "Approvals"}</h1><p>{order ? "Read-only basket. Your decision never submits an order." : "Requests explicitly submitted for your decision."}</p></div><button type="button" onClick={refreshReview} disabled={Boolean(busy) || loadingQueue}><RefreshCw size={16}/>{busy === "refresh" || loadingQueue ? "Refreshing…" : order ? "Refresh review" : "Refresh queue"}</button></header>
    {error && <p className="approval-error" role="alert">{error}</p>}
    {notice && <p className="approval-notice" role="status"><Check size={17}/>{notice}</p>}
    {order ? <>
      <button type="button" className="approval-back" disabled={Boolean(busy)} onClick={() => { selectedId.current = null; setOrder(null); setNotice(""); compareDispatch({type:"clear"}); }}><ArrowLeft size={16}/>All requests</button>
      <div ref={review} tabIndex={-1} className="approval-review-region">
        <OrderReview order={order} onDetails={(candidate,quantity,unit)=>setDetails({candidate,quantity,unit})} comparisonEntries={comparison.entries} onCompareToggle={(entry)=>compareDispatch({type:"toggle",entry})} onOpenCompare={()=>setCompareOpenRequest((value)=>value+1)} disabled={Boolean(busy)}>
          <section className="review-actions"><h3>Approval decision</h3>
            {!!blockedDecision.length && <div className="review-blockers">{blockedDecision.map((blocker)=><p key={blocker}>{blocker}</p>)}</div>}
            {pending && <>
              {expired && <p className="review-problem" role="status">This quote expired. The buyer must refresh it and request approval again.</p>}
              {!expired && <p>The decision applies only to this exact version and quote. Any relevant change requires fresh validation and approval.</p>}
              <label htmlFor="decision-reason">Decision note (required for changes)</label><textarea id="decision-reason" value={reason} onChange={(e)=>setReason(e.target.value)} maxLength={500} rows={3} disabled={Boolean(busy) || !canDecide}/>
              <div className="review-actions-buttons"><button type="button" className="primary-button" disabled={Boolean(busy) || !canDecide || expired || Boolean(order.approval?.blockers?.length) || !order.offer} onClick={()=>void decide("approve")}>{busy === "approve" ? <><LoaderCircle size={16} className="spin"/>Approving…</> : <><ShieldCheck size={16}/>Approve exact basket</>}</button><button type="button" disabled={Boolean(busy) || !canDecide || !order.offer} onClick={()=>void decide("reject")}>{busy === "reject" ? "Declining…" : <><X size={16}/>Decline basket</>}</button><button type="button" disabled={Boolean(busy) || !canDecide || !order.offer || !reason.trim()} onClick={()=>void decide("request-changes")}>{busy === "request-changes" ? "Sending changes…" : "Request changes"}</button></div>
            </>}
            {order.approval?.status === "approved" && <p className="approval-notice">Approved for the exact current basket. The buyer must separately submit the simulated order.</p>}
            {order.approval?.status === "rejected" && <p className="approval-error">Declined{order.rejection?.reason ? `: ${order.rejection.reason}` : "."}</p>}
            {order.review_state === "CHANGES_REQUESTED" && <p>Changes requested. Your note is saved in the decision history.</p>}
            {!pending && !["approved","rejected","changes_requested"].includes(order.approval?.status || "") && <p>This basket is not awaiting a decision. Ask the buyer to address its requirements and explicitly request approval.</p>}
          </section>
        </OrderReview>
        <ProductComparison state={comparison} dispatch={compareDispatch} api={api} date={order.constraints.delivery_date || ""} mode={order.mode} applyPreferences={false} readOnly openRequest={compareOpenRequest} disabled={Boolean(busy)} onChoose={()=>{}} onDetails={(entry)=>setDetails({candidate:entry.product,quantity:entry.requestedQuantity || "1",unit:entry.requestedUnit || "packages"})} chooseLabel=""/>
      </div>
      <button type="button" className="approval-switch" onClick={onSwitchRole}>Switch role<ArrowRight size={16}/></button>
    </> : <>
      {loadingQueue && <p role="status" className="approval-loading"><LoaderCircle size={17} className="spin"/>{queue ? "Refreshing approval requests…" : "Loading approval requests…"}</p>}
      {queue?.items.map((entry)=><article key={entry.id} className="approval-entry"><div><h2>{entry.request_title || `${entry.line_count} selected products`}</h2><p><strong>{entry.buyer_name || "Workspace buyer"}</strong> · {formatMoney(entry.subtotal)} in items</p><p>Delivery {reviewDate(entry.requested_date)} · submitted {reviewDate(entry.submitted_at || entry.created_at,true)}</p>{entry.reasons?.map((reason)=><p className="approval-reason" key={reason}>{approvalReason(reason)}{reason === "requested_budget" && entry.budget_excess != null && ` · excess ${formatMoney(entry.budget_excess)}`}</p>)}<p className="approval-entry-note">{entry.explanation || "No explanation provided."}</p><small>{Date.parse(entry.expires_at) <= clock ? "Quote expired" : "Awaiting decision"} · Request {entry.id.slice(-8)}</small>{entry.decision_blockers?.map((blocker)=><p className="approval-error" key={blocker}>{blocker}</p>)}</div><button type="button" disabled={Boolean(busy) || loadingQueue} onClick={()=>void open(entry)}>{busy === entry.id ? <><LoaderCircle size={16} className="spin"/>Opening review…</> : <>Review request<ArrowRight size={15}/></>}</button></article>)}
      {queue && !queue.items.length && !loadingQueue && <div className="approval-empty"><ShieldCheck size={28}/><h2>No pending requests</h2><p>Eligible buyer requests appear after the buyer chooses Request approval.</p><button type="button" onClick={onSwitchRole}>Switch role</button></div>}
      {queue && queue.total > queue.limit && <div className="approval-pagination"><button type="button" disabled={!offset || Boolean(busy) || loadingQueue} onClick={()=>setOffset(Math.max(0,offset-queue.limit))}>Previous</button><span>{offset+1}–{Math.min(offset+queue.limit,queue.total)} of {queue.total}</span><button type="button" disabled={offset+queue.limit>=queue.total || Boolean(busy) || loadingQueue} onClick={()=>setOffset(offset+queue.limit)}>Next</button></div>}
    </>}
    {details && <ProductDetailsDialog candidate={details.candidate} requestedQuantity={details.quantity} requestedUnit={details.unit} onClose={()=>setDetails(null)}/>}
  </section>;
}
