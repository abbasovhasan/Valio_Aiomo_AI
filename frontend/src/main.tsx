import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  ShieldX,
  Fingerprint,
  Play,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  X,
  RefreshCw,
  CircleHelp,
  ExternalLink,
  LockKeyhole,
  Leaf,
  Milk,
  Clock3,
  AlertTriangle,
  ReceiptText,
  Radio,
  Braces,
  Zap,
  LogOut,
  Copy,
  LoaderCircle,
  Search,
  Circle,
  KeyRound,
  Package,
  History,
  Menu,
  Eye,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import "./style.css";
import { MealPlanner } from "./MealPlanner";
import { ProcurementDesk } from "./ProcurementDesk";

type CheckItem = {
  code: string;
  label: string;
  status: string;
  detail: string;
};
type Product = {
  id: string;
  name: string;
  sales_unit: string;
  liters_per_sales_unit: string;
  diet_evidence?: any;
};
type Offer = {
  id: string;
  product: Product;
  quantity_sales_units: string;
  effective_liters: string;
  requested_date: string;
  total: string;
  unit_price: string;
  tax_rate: string;
  status: string;
  checks: CheckItem[];
  reasons: string[];
  repair: any;
  expires_at: string;
  version: any;
  fingerprint: string;
  approved: boolean;
  mode: string;
  evidence: any;
};
type Event = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  status: string;
  evidence: any;
};
type Run = {
  id: string;
  mode: string;
  scenario: string;
  request: any;
  created_at: string;
  events: Event[];
  offers: Offer[];
  recommended_offer_id: string | null;
  agent: {
    provider: string;
    status: string;
    summary: string;
    tool_calls: any[];
  };
};
type Session = {
  role: string | null;
  name?: string;
  buyer_id?: string;
  customer_id?: string;
};
const money = (v: any) =>
  v === null || v === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-FI", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 2,
      }).format(Number(v || 0));
const number = (v: any) =>
  new Intl.NumberFormat("en-FI", { maximumFractionDigits: 2 }).format(
    Number(v || 0),
  );
const statusLabel = (s: string) =>
  s === "within_mandate"
    ? "Within mandate"
    : s === "approval_required"
      ? "Needs approval"
      : "Blocked";
const scenarios = [
  {
    id: "baseline",
    name: "Clear runway",
    caption: "An ordinary order, inside its mandate.",
    icon: ShieldCheck,
  },
  {
    id: "shortage",
    name: "The milk runs out",
    caption: "A controlled shortage. Find a safe way forward.",
    icon: Milk,
  },
  {
    id: "injection",
    name: "An untrusted instruction",
    caption: "Supplier text tries to change the rules.",
    icon: ShieldX,
  },
  {
    id: "stale",
    name: "The offer changes",
    caption: "An old decision cannot approve a new basket.",
    icon: Clock3,
  },
  {
    id: "diet",
    name: "A tempting shortcut",
    caption: "A cheaper option fails the dietary rule.",
    icon: AlertTriangle,
  },
  {
    id: "unknown",
    name: "Quantity unknown",
    caption: "A supplier sentinel is not verified stock.",
    icon: CircleHelp,
  },
];
async function api(path: string, options: RequestInit = {}) {
  let r = await fetch("/api/v1" + path, {
    ...options,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  let data = await r.json().catch(() => ({}));
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message ||
          JSON.stringify(
            data.detail ||
              data.error ||
              "The gateway could not complete this request.",
          ),
    );
  return data;
}
function Icon({
  icon: IconName,
  size = 18,
  ...rest
}: {
  icon: LucideIcon;
  size?: number;
  className?: string;
}) {
  return <IconName size={size} strokeWidth={1.65} {...rest} />;
}
function MilkPack({
  alternate = false,
  small = false,
}: {
  alternate?: boolean;
  small?: boolean;
}) {
  return (
    <div
      className={
        "milk-art " + (alternate ? "alternate " : "") + (small ? "small" : "")
      }
      aria-hidden="true"
    >
      <svg viewBox="0 0 114 154">
        <path
          d="M24 37 45 15h40l13 22v102L24 151Z"
          fill={alternate ? "#e9ba7c" : "#edf0dd"}
          stroke="#c4cbbd"
        />
        <path
          d="M24 37h57l17 0v102l-17 10-57 2Z"
          fill={alternate ? "#f5dcb6" : "#f9faf0"}
        />
        <path
          d="m81 37 17 0v102l-17 10Z"
          fill={alternate ? "#d3a370" : "#d9ddcc"}
        />
        <path
          d="M24 37h57L65 15H45Z"
          fill={alternate ? "#efd0a6" : "#f4f5e7"}
        />
        <path
          d="M81 37 65 15h20l13 22Z"
          fill={alternate ? "#d3a370" : "#d4dbca"}
        />
        <rect
          x="24"
          y="67"
          width="57"
          height="54"
          fill={alternate ? "#ae563d" : "#32624b"}
        />
        <path
          d="M25 107q15-17 29-3t27-6v23H25Z"
          fill={alternate ? "#e6b991" : "#aac7a4"}
        />
        <text
          x="52"
          y="86"
          textAnchor="middle"
          fill="white"
          fontFamily="Georgia"
          fontSize="14"
        >
          milk
        </text>
        <text
          x="52"
          y="98"
          textAnchor="middle"
          fill="white"
          fontFamily="sans-serif"
          fontSize="5"
        >
          LACTOSE-FREE
        </text>
        <text x="51" y="137" textAnchor="middle" fill="#315043" fontSize="10">
          1 L
        </text>
        <ellipse
          cx="52"
          cy="27"
          rx="8"
          ry="4"
          fill="#e6e7dc"
          stroke="#b9c3b2"
        />
      </svg>
      <span>Illustration</span>
    </div>
  );
}
function App() {
  const [session, setSession] = useState<Session>({ role: null }),
    [workspace, setWorkspace] = useState<any>(null),
    [authOpen, setAuthOpen] = useState(false),
    [code, setCode] = useState(""),
    [authError, setAuthError] = useState(""),
    [authBusy, setAuthBusy] = useState(false);
  const [tab, setTab] = useState("purchase"),
    [mode, setMode] = useState("fixture"),
    [scenario, setScenario] = useState("baseline"),
    [quantity, setQuantity] = useState("1000"),
    [date, setDate] = useState("2026-11-16"),
    [brief, setBrief] = useState(
      "Breakfast for the whole hotel. At least 1,000 litres of lactose-free milk, delivered by Monday. Keep the dietary rule.",
    );
  const [quoteSessionId, setQuoteSessionId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null),
    [busy, setBusy] = useState(false),
    [actionBusy, setActionBusy] = useState(""),
    [error, setError] = useState(""),
    [receipt, setReceipt] = useState<any>(null),
    [selected, setSelected] = useState<string | null>(null),
    [expanded, setExpanded] = useState<string | null>(null),
    [evidence, setEvidence] = useState<any>(null),
    [useModel, setUseModel] = useState(true),
    [toast, setToast] = useState(""),
    [elapsed, setElapsed] = useState(0),
    [about, setAbout] = useState(false),
    [mobileMenu, setMobileMenu] = useState(false);
  const [comparison, setComparison] = useState<{
    from: Offer;
    to: Offer;
  } | null>(null);
  const keys = useRef<Record<string, string>>({});
  const resultRef = useRef<HTMLDivElement>(null);
  async function loadWorkspace() {
    try {
      const w = await api("/workspace");
      setWorkspace(w);
    } catch {
      /* Session may have expired; do not invent workspace data. */
    }
  }
  useEffect(() => {
    api("/session")
      .then((s) => {
        setSession(s);
        if (s.role) loadWorkspace();
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!busy) return;
    setElapsed(0);
    const t = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [busy]);
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(""), 3800);
    return () => clearTimeout(t);
  }, [toast]);
  async function login(e: React.FormEvent) {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const s = await api("/session", {
        method: "POST",
        body: JSON.stringify({ access_code: code }),
      });
      setSession(s);
      setCode("");
      setAuthOpen(false);
      await loadWorkspace();
      setToast(`Signed in as ${s.name || s.role}`);
    } catch (e) {
      setAuthError((e as Error).message);
    } finally {
      setAuthBusy(false);
    }
  }
  async function logout() {
    await api("/session", { method: "DELETE" });
    setSession({ role: null });
    setWorkspace(null);
    setToast("Session closed.");
  }
  async function startRun(s = scenario, q = quantity) {
    if (!session.role) {
      setAuthOpen(true);
      return;
    }
    setBusy(true);
    setError("");
    setReceipt(null);
    setSelected(null);
    setComparison(null);
    setTab("desk");
    try {
      const r = await api("/runs", {
        method: "POST",
        body: JSON.stringify({
          quantity_liters: Number(q),
          date,
          scenario: s,
          mode,
          brief,
          use_model: mode === "live" && useModel,
        }),
      });
      setRun(r);
      setSelected(r.recommended_offer_id || r.offers[0]?.id);
      await loadWorkspace();
      window.setTimeout(
        () =>
          resultRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          }),
        150,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function commit(offer: Offer) {
    setError("");
    setActionBusy(offer.id);
    try {
      keys.current[offer.id] ||= crypto.randomUUID();
      const r = await api(`/offers/${offer.id}/commit`, {
        method: "POST",
        headers: { "Idempotency-Key": keys.current[offer.id] },
        body: JSON.stringify({}),
      });
      setReceipt(r);
      setRun((previous) =>
        previous
          ? {
              ...previous,
              events: [
                ...previous.events,
                {
                  id: crypto.randomUUID(),
                  kind: r.idempotent_replay
                    ? "idempotent_replay"
                    : "simulated_commitment",
                  title: r.idempotent_replay
                    ? "Same request. Same receipt."
                    : "Simulated commitment recorded",
                  detail: r.idempotent_replay
                    ? "The gateway returned the existing order without spending again."
                    : "The gateway refreshed supplier evidence, enforced shared spending atomically, and recorded one simulated order.",
                  status: "pass",
                  evidence: {
                    receipt_id: r.id,
                    total: r.total,
                    created_at: r.created_at,
                    idempotent_replay: r.idempotent_replay,
                  },
                },
              ],
            }
          : previous,
      );
      await loadWorkspace();
      setToast(
        r.idempotent_replay
          ? "Retry verified: the same receipt."
          : "One simulated order. Recorded.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionBusy("");
    }
  }
  async function approve(offer: Offer) {
    if (session.role !== "approver") {
      setAuthOpen(true);
      return;
    }
    setActionBusy(offer.id);
    setError("");
    try {
      const o = await api(`/offers/${offer.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ fingerprint: offer.fingerprint }),
      });
      setRun((r) =>
        r
          ? {
              ...r,
              offers: r.offers.map((a) => (a.id === o.id ? o : a)),
              events: [
                ...r.events,
                {
                  id: crypto.randomUUID(),
                  kind: "human_approval",
                  title: "Exact offer approved by a separate identity",
                  detail: `${session.name} approved this fingerprint; changes require revalidation and renewed approval.`,
                  status: "pass",
                  evidence: o.approval || { fingerprint: o.fingerprint },
                },
              ],
            }
          : r,
      );
      setToast(
        "Approval bound to this exact offer. Sign back in as buyer to commit.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionBusy("");
    }
  }
  async function repair(offer: Offer) {
    if (offer.repair?.action === "revalidate") {
      setActionBusy(offer.id);
      setError("");
      try {
        const r = await api(`/offers/${offer.id}/revalidate`, {
          method: "POST",
        });
        const next =
          r.offers.find((o: Offer) => o.product.id === offer.product.id) ||
          r.offers[0];
        setComparison({ from: offer, to: next });
        setRun(r);
        setSelected(r.recommended_offer_id || next.id);
        setExpanded(next.id);
        setReceipt(null);
        setToast("Fresh evidence. A new fingerprint. No inherited approval.");
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setActionBusy("");
      }
    } else if (
      run?.recommended_offer_id &&
      run.recommended_offer_id !== offer.id
    ) {
      setSelected(run.recommended_offer_id);
      setExpanded(run.recommended_offer_id);
      setToast("A compliant alternative. The hard rule stays fixed.");
    } else {
      setScenario("baseline");
      await startRun("baseline");
    }
  }
  const displayMode = run && !busy ? run.mode : mode;
  const mandate = workspace?.mandate;
  const currentOffer =
    run?.offers.find((o) => o.id === selected) || run?.offers[0];
  const activeScenario = scenarios.find((s) => s.id === scenario)!;
  const required = run?.offers.filter(
    (o) => o.status === "approval_required",
  ).length;
  const invalid = run?.offers.filter((o) => o.status === "invalid").length;
  const progress = busy ? Math.min(90, 12 + elapsed * 2.2) : run ? 100 : 0;
  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          href="#"
          className="brand"
          aria-label="A4TB Valio Aimo home"
          onClick={(e) => {
            e.preventDefault();
            setTab("purchase");
          }}
        >
          <span className="brand-mark">
            a<span>i</span>mo<span className="brand-dot">↗</span>
          </span>
          <span className="brand-divider" />
          <span className="brand-sub">
            A4TB
            <br />
            VALIO AIMO
          </span>
        </a>
        <nav
          aria-label="Main navigation"
          className={mobileMenu ? "mobile-open" : ""}
        >
          {[
            ["purchase", "Smart order"],
            ["desk", "Trust scenarios"],
            ["meals", "Meal planner"],
            ["recorder", "Decision recorder"],
            ["gateway", "Gateway API"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => {
                setTab(id);
                setMobileMenu(false);
              }}
              className={tab === id ? "active" : ""}
            >
              {label}
              {id === "recorder" && run && (
                <span className="nav-count">{run.events.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="topbar-right">
          <span className="simulation">
            <span /> SIMULATED ORDERS ONLY
          </span>
          <button className="profile-button" onClick={() => setAuthOpen(true)}>
            <span className="avatar">
              {session.role === "approver" ? "LK" : session.role ? "AB" : "↗"}
            </span>
            <span>
              {session.name || "Open your desk"}
              <small>
                {session.role
                  ? `${session.role} · example identity`
                  : "Private demo access"}
              </small>
            </span>
            <ChevronDown size={14} />
          </button>
          <button
            className="mobile-toggle icon-button"
            onClick={() => setMobileMenu(!mobileMenu)}
            aria-label="Toggle navigation"
          >
            <Menu size={22} />
          </button>
        </div>
      </header>
      <main>
        <section className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="tiny-square" /> THE BUYER AGENT'S WORKBENCH
            </div>
            <h1>
              Good judgment.
              <br className="mobile-br" /> <em>On the record.</em>
            </h1>
            <p>
              Your kitchen sets the boundaries. The agent finds a way through.
            </p>
          </div>
          <button className="explain-link" onClick={() => setAbout(true)}>
            <span className="play-ring">
              <Play size={13} fill="currentColor" />
            </span>{" "}
            What makes it trustworthy? <ArrowUpRight size={17} />
          </button>
        </section>
        <div className="context-strip">
          <div>
            <span className="hotel-symbol">A</span>
            <strong>Aurora Hotel</strong>
            <span className="context-dot">·</span>
            <span>Example purchasing mandate</span>
          </div>
          <div
            className={
              "source-pill " +
              (tab !== "meals" && displayMode === "live" ? "live" : "")
            }
          >
            <Radio size={13} />
            {tab === "purchase"
              ? "CUSTOMER-REVIEWED BASKET · SIMULATION"
              : tab === "meals"
              ? "LOCAL CATALOG · PLANNING ONLY"
              : displayMode === "live"
                ? "LIVE VALIO SANDBOX"
                : "LABELLED REHEARSAL FIXTURE"}
          </div>
        </div>
        {error && (
          <div className="error-banner" role="alert">
            <ShieldX size={20} />
            <div>
              <strong>The gateway stopped this action.</strong>
              <span>{error}</span>
            </div>
            <button
              className="icon-button"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              <X size={17} />
            </button>
          </div>
        )}
        <div hidden={tab !== "purchase"}>
          <ProcurementDesk api={api} role={session.role} onSignIn={() => setAuthOpen(true)} onUpdated={loadWorkspace} initialSessionId={quoteSessionId} />
        </div>
        <div hidden={tab !== "meals"}>
          <MealPlanner
            onQuoteSession={(id) => { setQuoteSessionId(id); setTab("purchase"); }}
            api={api}
            role={session.role}
            onSignIn={() => setAuthOpen(true)}
          />
        </div>
        {tab === "desk" && (
          <div className="desk-grid">
            <aside className="brief-column">
              <section className="paper brief-paper">
                <div className="section-label">
                  <span>01 / THE BRIEF</span>
                  <Milk size={18} />
                </div>
                <h2>
                  Breakfast is
                  <br /> counting on you.
                </h2>
                <label className="field-label" htmlFor="brief">
                  THE KITCHEN'S REQUEST
                </label>
                <textarea
                  id="brief"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  rows={4}
                />
                <div className="brief-fields">
                  <label>
                    AT LEAST
                    <div className="number-field">
                      <input
                        aria-label="Quantity in litres"
                        type="number"
                        min="1"
                        max="10000"
                        step="1"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                      />
                      <span>litres</span>
                    </div>
                  </label>
                  <label>
                    DELIVER BY
                    <input
                      aria-label="Delivery date"
                      type="date"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                    />
                  </label>
                </div>
                <div className="diet-rule">
                  <LockKeyhole size={15} />
                  <span>
                    Lactose-free milk<strong>Hard rule. No exceptions.</strong>
                  </span>
                  <Check size={17} />
                </div>
                <p className="brief-note">
                  Typed quantity and date are authoritative. This is an authored
                  hotel scenario, not a real customer order.
                </p>
                <button
                  className="primary-button run-button"
                  onClick={() => startRun()}
                  disabled={busy || !quantity || !date}
                >
                  {busy ? (
                    <>
                      <LoaderCircle size={17} className="spin" /> Checking the
                      path…
                    </>
                  ) : (
                    <>
                      <span>Send to buyer agent</span>
                      <ArrowUpRight size={19} />
                    </>
                  )}
                </button>
                <div className="mode-setting">
                  <label htmlFor="evidence-mode">Evidence source</label>
                  <select
                    id="evidence-mode"
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                    disabled={busy}
                  >
                    <option value="fixture">Rehearsal fixture</option>
                    <option value="live">Live sponsor sandbox</option>
                  </select>
                </div>
                {run && run.mode !== mode && (
                  <p className="next-mode-note">
                    New selection applies to the next run. Displayed offers:{" "}
                    {run.mode === "live" ? "live sandbox" : "fixture"}.
                  </p>
                )}
                {mode === "live" && (
                  <label className="model-check">
                    <input
                      type="checkbox"
                      checked={useModel}
                      onChange={(e) => setUseModel(e.target.checked)}
                    />
                    <Zap size={13} /> Use NVIDIA Nemotron agent
                  </label>
                )}
              </section>
              <section className="rehearsal">
                <div className="section-label">
                  <span>THE REHEARSAL LAB</span>
                  <span className="mini-tag">CONTROLLED</span>
                </div>
                <p>
                  Trust is what happens
                  <br />
                  when something goes wrong.
                </p>
                <div className="scenario-list">
                  {scenarios.map((s) => (
                    <button
                      key={s.id}
                      disabled={busy}
                      onClick={() => setScenario(s.id)}
                      className={scenario === s.id ? "chosen" : ""}
                    >
                      <Icon icon={s.icon} size={16} />
                      <span>{s.name}</span>
                      {scenario === s.id ? (
                        <span className="selection-dot" />
                      ) : (
                        <ChevronRight size={14} />
                      )}
                    </button>
                  ))}
                </div>
                <span className="scenario-caption">
                  {activeScenario.caption}
                </span>
                {mode === "live" && scenario !== "baseline" && (
                  <p className="injection-note">
                    Live evidence + an explicitly controlled failure overlay.
                  </p>
                )}
              </section>
            </aside>
            <section className="results-column" ref={resultRef}>
              <div className="results-title">
                <div className="section-label">02 / THE DECISION</div>
                <span className="small-muted">
                  {busy
                    ? `${elapsed}s elapsed`
                    : run
                      ? `${run.offers.length} offers inspected`
                      : "Ready when you are"}
                </span>
              </div>
              {!run && !busy && (
                <div className="empty-stage">
                  <div className="orbit-graphic">
                    <div className="orbit o1" />
                    <div className="orbit o2" />
                    <span className="orbit-label ol1">
                      <Search size={14} /> Find
                    </span>
                    <span className="orbit-label ol2">
                      <ShieldCheck size={14} /> Validate
                    </span>
                    <span className="orbit-label ol3">
                      <ReceiptText size={14} /> Record
                    </span>
                    <div className="orbit-core">
                      <Milk size={38} strokeWidth={1} />
                      <span>1,000 L</span>
                    </div>
                  </div>
                  <div className="eyebrow">
                    A PURCHASE IS A CHAIN OF DECISIONS
                  </div>
                  <h2>
                    Make every link
                    <br />
                    <em>worth trusting.</em>
                  </h2>
                  <p>
                    Find the right milk. Check the real units.
                    <br />
                    Know where the agent must stop.
                  </p>
                  <div className="empty-footer">
                    <span>
                      <ShieldCheck size={15} /> Policy enforced on the server
                    </span>
                    <span>
                      <Braces size={15} /> Any agent. One gateway.
                    </span>
                  </div>
                </div>
              )}
              {busy && (
                <div className="working-stage" role="status" aria-live="polite">
                  <div className="working-symbol">
                    <LoaderCircle className="spin" size={36} strokeWidth={1} />
                  </div>
                  <div className="eyebrow">EVIDENCE BEFORE EXECUTION</div>
                  <h2>
                    Finding a path
                    <br />
                    <em>inside the mandate.</em>
                  </h2>
                  <p>
                    {elapsed < 3
                      ? "Reading the brief and searching the catalogue."
                      : elapsed < 8
                        ? "Checking sales packs, dietary evidence, price and availability."
                        : mode === "live" && useModel
                          ? "Waiting for the grounded agent and sponsor evidence."
                          : "Applying policy to every candidate."}
                  </p>
                  <div className="progress-track">
                    <i style={{ width: progress + "%" }} />
                  </div>
                  <span className="small-muted">
                    {mode === "live"
                      ? "Live upstream calls can take a moment."
                      : "Controlled fixture; no upstream calls."}
                  </span>
                </div>
              )}
              {run && !busy && (
                <>
                  <div
                    className={
                      "decision-summary " + (required ? "attention" : "")
                    }
                  >
                    <div className="summary-icon">
                      {required ? (
                        <Icon icon={AlertTriangle} size={22} />
                      ) : (
                        <Icon icon={ShieldCheck} size={23} />
                      )}
                    </div>
                    <div>
                      <span className="eyebrow">
                        {run.scenario === "baseline"
                          ? "THE PATH IS VISIBLE"
                          : "REWIND & REPAIR"}
                      </span>
                      <h2>
                        {required
                          ? "A safe alternative. A human decision."
                          : run.offers.every((o) => o.status === "invalid")
                            ? "This is where the agent stops."
                            : "A way forward, within the rules."}
                      </h2>
                      <p>
                        {run.agent?.summary ||
                          "Every offer has been checked by the gateway."}
                      </p>
                    </div>
                  </div>
                  <div className="agent-provenance">
                    <span>
                      <span className="status-dot" />
                      {run.agent?.provider || "Deterministic planner"}
                    </span>
                    <span>
                      {run.mode === "live"
                        ? "Live sandbox evidence"
                        : "Fixture evidence"}{" "}
                      · {run.agent?.status || "complete"}
                    </span>
                  </div>
                  <div className="offer-list">
                    {run.offers.map((offer, i) => (
                      <article
                        className={
                          "offer-card " +
                          (selected === offer.id ? "selected " : "") +
                          (offer.status === "invalid" ? "is-blocked" : "")
                        }
                        key={offer.id}
                      >
                        <button
                          className="offer-main"
                          onClick={() => {
                            setSelected(offer.id);
                            setExpanded(
                              expanded === offer.id ? null : offer.id,
                            );
                          }}
                          aria-expanded={expanded === offer.id}
                        >
                          <div className="offer-art">
                            {i < 2 ? (
                              <MilkPack alternate={i === 1} small />
                            ) : (
                              <Package size={36} strokeWidth={1} />
                            )}
                          </div>
                          <div className="offer-info">
                            <div className="offer-meta">
                              <span className={"status-tag " + offer.status}>
                                {offer.status === "invalid" ? (
                                  <ShieldX size={12} />
                                ) : offer.status === "approval_required" ? (
                                  <KeyRound size={12} />
                                ) : (
                                  <Check size={12} />
                                )}{" "}
                                {offer.approved
                                  ? "Human approved"
                                  : statusLabel(offer.status)}
                              </span>
                              {run.recommended_offer_id === offer.id && (
                                <span className="recommended">
                                  AGENT'S PICK
                                </span>
                              )}
                            </div>
                            <h3>{offer.product.name}</h3>
                            <p>
                              SKU {offer.product.id}
                              <span>·</span>
                              {number(offer.quantity_sales_units)}{" "}
                              {offer.product.sales_unit}
                              <span>→</span>
                              {number(offer.effective_liters)} L
                            </p>
                          </div>
                          <div className="offer-cost">
                            <strong>{money(offer.total)}</strong>
                            <span>incl. tax</span>
                            <ChevronDown
                              size={16}
                              className={expanded === offer.id ? "flipped" : ""}
                            />
                          </div>
                        </button>
                        {expanded === offer.id && (
                          <div className="offer-detail">
                            <div className="checks">
                              {offer.checks.map((c, j) => (
                                <div
                                  className={"check-row " + c.status}
                                  key={c.code + j}
                                >
                                  <span className="check-icon">
                                    {c.status === "pass" ? (
                                      <Check size={13} />
                                    ) : c.status === "blocked" ||
                                      c.status === "fail" ? (
                                      <X size={13} />
                                    ) : (
                                      <AlertTriangle size={13} />
                                    )}
                                  </span>
                                  <div>
                                    <strong>{c.label}</strong>
                                    <p>{c.detail}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                            <div className="evidence-link-row">
                              <span>
                                Offer v{offer.version} · exact basket bound
                              </span>
                              <button
                                className="text-button"
                                onClick={() =>
                                  setEvidence({
                                    offer_id: offer.id,
                                    fingerprint: offer.fingerprint,
                                    expires_at: offer.expires_at,
                                    evidence: offer.evidence,
                                  })
                                }
                              >
                                <Braces size={13} /> Inspect evidence
                              </button>
                            </div>
                          </div>
                        )}
                        {offer.status === "invalid" && (
                          <div className="blocked-reason">
                            <ShieldX size={14} />
                            <span>
                              {offer.reasons?.[0] ||
                                "A hard rule failed. This cannot be approved."}
                            </span>
                          </div>
                        )}
                      </article>
                    ))}
                  </div>
                  {comparison && (
                    <div className="comparison-slip">
                      <div className="eyebrow">
                        <History size={14} /> WHAT REVALIDATION CHANGED
                      </div>
                      <div>
                        <span>Offer state</span>
                        <del>Expired</del>
                        <ArrowRight size={12} />
                        <strong>{statusLabel(comparison.to.status)}</strong>
                      </div>
                      <div>
                        <span>Price</span>
                        <del>{money(comparison.from.total)}</del>
                        <ArrowRight size={12} />
                        <strong>{money(comparison.to.total)}</strong>
                      </div>
                      <div>
                        <span>Approval</span>
                        <span className="approval-reset">
                          Cleared · exact new fingerprint
                        </span>
                      </div>
                      <p>
                        The dietary rule and requested date remain enforced. New
                        evidence creates a new offer.
                      </p>
                    </div>
                  )}
                  {currentOffer && (
                    <div className="action-slip">
                      <div className="slip-notch" />
                      <div className="section-label">
                        <span>THE NEXT PERMITTED ACTION</span>
                        <ArrowDownLine />
                      </div>
                      {currentOffer.status === "invalid" ? (
                        <>
                          <h3>A hard boundary stays hard.</h3>
                          <p>
                            {currentOffer.repair?.detail ||
                              "This offer cannot be approved. Search for compliant stock or change the requested date and revalidate."}
                          </p>
                          <button
                            className="secondary-button"
                            onClick={() => repair(currentOffer)}
                            disabled={!!actionBusy}
                          >
                            {actionBusy ? (
                              <LoaderCircle size={15} className="spin" />
                            ) : (
                              <RefreshCw size={15} />
                            )}{" "}
                            {currentOffer.repair?.action === "revalidate"
                              ? "Refresh this exact offer"
                              : run.recommended_offer_id &&
                                  run.recommended_offer_id !== currentOffer.id
                                ? "Inspect the permitted alternative"
                                : "Recheck a compliant path"}
                          </button>
                        </>
                      ) : currentOffer.status === "approval_required" &&
                        !currentOffer.approved ? (
                        <>
                          <h3>{money(currentOffer.total)} needs a person.</h3>
                          <p>
                            The offer exceeds the agent's{" "}
                            {money(mandate?.autonomous_limit || 1400)}{" "}
                            authority.{" "}
                            {mandate?.approver || "The named approver"} can
                            approve this exact basket. Dietary rules still
                            apply.
                          </p>
                          <div className="action-buttons">
                            <button
                              className="primary-button"
                              onClick={() => approve(currentOffer)}
                              disabled={!!actionBusy}
                            >
                              {actionBusy ? (
                                <LoaderCircle size={16} className="spin" />
                              ) : (
                                <Fingerprint size={17} />
                              )}{" "}
                              {session.role === "approver"
                                ? "Approve this exact offer"
                                : "Open approver sign-in"}
                              <ArrowUpRight size={16} />
                            </button>
                            <button
                              className="text-button"
                              onClick={() => {
                                setScenario("baseline");
                                startRun("baseline");
                              }}
                            >
                              Rewind to clear runway <History size={14} />
                            </button>
                          </div>
                          <div className="authority-note">
                            <LockKeyhole size={12} /> The buyer agent cannot
                            approve itself.
                          </div>
                        </>
                      ) : (
                        <>
                          <h3>
                            {currentOffer.approved
                              ? "A human approved this exact offer."
                              : "Ready to commit. On your terms."}
                          </h3>
                          <p>
                            {number(currentOffer.effective_liters)} L ·{" "}
                            {currentOffer.requested_date} ·{" "}
                            {money(currentOffer.total)} incl. tax. The gateway
                            rechecks freshness and cumulative spend atomically.
                          </p>
                          <button
                            className="primary-button"
                            onClick={() => commit(currentOffer)}
                            disabled={!!actionBusy || session.role !== "buyer"}
                          >
                            {actionBusy ? (
                              <LoaderCircle size={17} className="spin" />
                            ) : (
                              <ReceiptText size={17} />
                            )}{" "}
                            {receipt
                              ? "Retry same request"
                              : session.role !== "buyer"
                                ? "Sign in as buyer to commit"
                                : "Commit simulated order"}
                            <ArrowRight size={17} />
                          </button>
                          {session.role !== "buyer" && (
                            <button
                              className="text-button buyer-signin"
                              onClick={() => setAuthOpen(true)}
                            >
                              Open buyer sign-in <ArrowUpRight size={14} />
                            </button>
                          )}
                          <div className="authority-note">
                            <LockKeyhole size={12} /> No real order. No payment.
                            One idempotent receipt.
                          </div>
                        </>
                      )}
                    </div>
                  )}
                  {receipt && (
                    <Receipt
                      receipt={receipt}
                      onInspect={() => setEvidence(receipt)}
                    />
                  )}
                  <div className="run-footer">
                    <span>RUN {run.id.slice(0, 8).toUpperCase()}</span>
                    <button
                      className="text-button"
                      onClick={() => setTab("recorder")}
                    >
                      Open the decision recorder <ArrowRight size={14} />
                    </button>
                  </div>
                </>
              )}
            </section>
            <aside className="mandate-column">
              <section className="mandate-card">
                <div className="section-label">
                  <span>03 / THE AUTHORITY</span>
                  <ShieldCheck size={17} />
                </div>
                <h2>
                  Room to act.
                  <br /> <em>A line to respect.</em>
                </h2>
                <div className="envelope-visual">
                  <div className="envelope-circle">
                    <div>
                      <span>AUTONOMOUS UP TO</span>
                      <strong>
                        {money(mandate?.autonomous_limit || 1400)}
                      </strong>
                      <small>per simulated order</small>
                    </div>
                    <span className="circle-dot" />
                  </div>
                </div>
                <div className="authority-level">
                  <span className="level-dot green" />
                  <div>
                    <strong>Inside the mandate</strong>
                    <span>The agent may commit.</span>
                  </div>
                  <Check size={15} />
                </div>
                <div className="authority-level">
                  <span className="level-dot amber" />
                  <div>
                    <strong>
                      Up to {money(mandate?.exception_limit || 2500)}
                    </strong>
                    <span>A named human must approve.</span>
                  </div>
                  <Fingerprint size={15} />
                </div>
                <div className="authority-level">
                  <span className="level-dot red" />
                  <div>
                    <strong>Hard rule fails</strong>
                    <span>Blocked. Approval won't fix it.</span>
                  </div>
                  <LockKeyhole size={15} />
                </div>
                <div className="spend-summary">
                  <div>
                    <span>CUMULATIVE COMMITMENTS</span>
                    <strong>
                      {money(mandate?.spent || 0)}{" "}
                      <small>
                        / {money(mandate?.cumulative_limit || 6000)}
                      </small>
                    </strong>
                  </div>
                  <div className="spend-track">
                    <i
                      style={{
                        width:
                          Math.min(
                            100,
                            (Number(mandate?.spent || 0) /
                              Number(mandate?.cumulative_limit || 6000)) *
                              100,
                          ) + "%",
                      }}
                    />
                  </div>
                  <span>Shared cap · checked inside one transaction</span>
                </div>
                <p className="brief-note">
                  Customer spend limits are configured by the server operator.
                  Changes require refreshed offers and renewed approval.
                </p>
                <div className="mandate-footer">
                  <LockKeyhole size={12} />
                  {session.role
                    ? `Server-issued mandate · ${workspace?.storage === "postgres" ? "Aiven PostgreSQL" : "local SQLite"}`
                    : "Example mandate · sign in to load current state"}
                </div>
              </section>
              <section className="margin-note">
                <span className="hand-arrow">↙</span>
                <p>
                  The useful part isn't
                  <br />
                  that it can buy.
                  <br />
                  <em>
                    It's knowing when
                    <br />
                    it shouldn't.
                  </em>
                </p>
              </section>
              <div className="evidence-footnote">
                <Leaf size={15} />
                <p>
                  Product data is synthetic challenge data. Prices and
                  availability never reserve stock. Every receipt is simulated.
                </p>
              </div>
            </aside>
          </div>
        )}
        {tab === "recorder" && (
          <section className="recorder-page">
            <div className="recorder-header">
              <div>
                <div className="eyebrow">THE FLIGHT RECORDER</div>
                <h2>Decisions leave fingerprints.</h2>
                <p>
                  A factual record of tool calls, evidence and enforced
                  boundaries. No hidden reasoning.
                </p>
              </div>
              <button
                className="secondary-button"
                onClick={() => setTab("desk")}
              >
                <ArrowLeft size={16} /> Back to the desk
              </button>
            </div>
            {run ? (
              <>
                <div className="recorder-run-meta">
                  <span>RUN {run.id.slice(0, 12)}</span>
                  <span className="mini-tag">
                    {run.mode === "live" ? "LIVE SANDBOX" : "FIXTURE"}
                  </span>
                  <span>
                    {new Date(run.created_at).toLocaleString("en-GB")}
                  </span>
                </div>
                <div className="event-timeline">
                  {run.events.map((event, i) => (
                    <article
                      key={event.id || i}
                      className={"timeline-event " + event.status}
                    >
                      <div className="timeline-number">
                        {String(i + 1).padStart(2, "0")}
                      </div>
                      <div className="timeline-content">
                        <div className="event-kind">
                          {event.kind.replaceAll("_", " ")}
                        </div>
                        <h3>{event.title}</h3>
                        <p>{event.detail}</p>
                        {event.evidence &&
                          Object.keys(event.evidence).length > 0 && (
                            <button
                              className="text-button"
                              onClick={() => setEvidence(event.evidence)}
                            >
                              <Braces size={14} /> Examine evidence
                            </button>
                          )}
                      </div>
                      <span className={"event-status " + event.status}>
                        {event.status === "pass" ? (
                          <Check size={15} />
                        ) : event.status === "blocked" ? (
                          <ShieldX size={15} />
                        ) : (
                          <Circle size={13} />
                        )}{" "}
                        {event.status}
                      </span>
                    </article>
                  ))}
                </div>
                {run.agent?.tool_calls?.length > 0 && (
                  <div className="tool-calls">
                    <h3>Agent tool interface</h3>
                    <p>Inputs and factual tool results crossing the gateway.</p>
                    <button
                      className="secondary-button"
                      onClick={() => setEvidence(run.agent.tool_calls)}
                    >
                      <Braces size={16} /> Inspect {run.agent.tool_calls.length}{" "}
                      tool calls
                    </button>
                  </div>
                )}
                <div className="recorder-repair">
                  <History size={28} />
                  <div>
                    <h3>Rewind the brief. Revalidate the decision.</h3>
                    <p>
                      Changing quantity or date creates a new offer. A previous
                      approval never carries over.
                    </p>
                  </div>
                  <button
                    className="primary-button"
                    onClick={() => setTab("desk")}
                  >
                    Return to the brief <ArrowRight size={16} />
                  </button>
                </div>
              </>
            ) : (
              <div className="recorder-empty">
                <History size={42} strokeWidth={1} />
                <h3>The first decision starts at the desk.</h3>
                <p>Run a scenario to inspect its factual evidence trail.</p>
                <button
                  className="primary-button"
                  onClick={() => setTab("desk")}
                >
                  Open the order desk <ArrowRight size={16} />
                </button>
              </div>
            )}
          </section>
        )}
        {tab === "gateway" && (
          <section className="gateway-page">
            <div>
              <div className="eyebrow">
                AN OPEN INTERFACE. AN ENFORCED BOUNDARY.
              </div>
              <h2>Bring your own agent.</h2>
              <p className="gateway-lede">
                The outside buyer calls a documented gateway. The gateway owns
                policy, approvals and simulated commitment. The browser has no
                special authority.
              </p>
              <div className="architecture-flow">
                {[
                  ["External buyer", "NVIDIA Nemotron"],
                  ["Trust gateway", "FastAPI · typed tools"],
                  ["Evidence", "Valio sandbox"],
                  ["Commitment", "Aiven / local SQLite"],
                ].map(([title, sub], i) => (
                  <React.Fragment key={title}>
                    {i > 0 && <ArrowRight size={20} />}
                    <div>
                      <Icon
                        icon={[Zap, ShieldCheck, Search, ReceiptText][i]}
                        size={24}
                      />
                      <strong>{title}</strong>
                      <span>{sub}</span>
                    </div>
                  </React.Fragment>
                ))}
              </div>
            </div>
            <div className="api-columns">
              <div className="api-endpoints">
                <h3>One contract for every client.</h3>
                {[
                  [
                    "POST",
                    "/api/v1/session",
                    "Exchange a server-issued access code.",
                  ],
                  ["GET", "/api/v1/products", "Search the static catalogue."],
                  [
                    "POST",
                    "/api/v1/meal-plans",
                    "Scale a meal into a review-only ingredient plan.",
                  ],
                  [
                    "GET",
                    "/api/v1/meal-plans/{id}",
                    "Review a saved plan in your buyer scope.",
                  ],
                  ["POST", "/api/v1/runs", "Create a grounded purchasing run."],
                  [
                    "POST",
                    "/api/v1/offers/{id}/approve",
                    "Approve an exact fingerprint as approver.",
                  ],
                  [
                    "POST",
                    "/api/v1/offers/{id}/commit",
                    "Commit once, with an idempotency key.",
                  ],
                  [
                    "GET",
                    "/api/v1/receipts/{id}",
                    "Inspect a scoped simulated receipt.",
                  ],
                ].map(([method, path, desc]) => (
                  <div className="endpoint" key={path}>
                    <span>{method}</span>
                    <div>
                      <code>{path}</code>
                      <p>{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="api-proof">
                <Braces size={27} />
                <h3>Trust it by testing it.</h3>
                <p>
                  Use the independent Python client. An unauthorised role,
                  changed fingerprint, stale offer or duplicate request meets
                  the same server checks.
                </p>
                <pre>
                  <code>
                    ./start.sh{`\n\n`}python scripts/agent_client.py --help
                  </code>
                </pre>
                <a
                  className="primary-button"
                  href="/docs"
                  target="_blank"
                  rel="noreferrer"
                >
                  Explore the OpenAPI contract <ExternalLink size={16} />
                </a>
                <p className="small-muted">
                  No sponsor-provided order endpoint exists. Our order service
                  is explicitly simulated.
                </p>
              </div>
            </div>
            <div className="integration-row">
              {[
                ["Valio Aimo", "Product / price / availability"],
                ["NVIDIA", "Nemotron grounded planning"],
                ["Aiven", "Transactional order ledger"],
                ["Codex", "Implementation & verification"],
              ].map(([name, desc]) => (
                <div key={name}>
                  <strong>{name}</strong>
                  <span>{desc}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
      <footer className="page-footer">
        <span>
          A4TB · VALIO AIMO <span>·</span> Built for the moments that need
          judgment.
        </span>
        <div>
          <span className="footer-lock">
            <LockKeyhole size={12} /> Private prototype
          </span>
          <span>
            Junction 2026 <ArrowUpRight size={12} />
          </span>
        </div>
      </footer>
      {authOpen && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setAuthOpen(false);
          }}
        >
          <section
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-title"
          >
            <button
              className="modal-close icon-button"
              onClick={() => setAuthOpen(false)}
              aria-label="Close sign-in"
            >
              <X size={20} />
            </button>
            <span className="modal-icon">
              <KeyRound size={25} />
            </span>
            <div className="eyebrow">AUTHORITY STARTS WITH IDENTITY</div>
            <h2 id="auth-title">Your place at the desk.</h2>
            <p>
              Use a buyer or approver access code from this installation. Each
              code maps to an identity on the server.
            </p>
            {session.role && (
              <div className="current-session">
                <span className="avatar">
                  {session.role === "approver" ? "LK" : "AB"}
                </span>
                <div>
                  <strong>{session.name}</strong>
                  <small>{session.role} · example identity</small>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    logout();
                    setAuthOpen(false);
                  }}
                >
                  <LogOut size={15} /> Sign out
                </button>
              </div>
            )}
            <form onSubmit={login}>
              <label htmlFor="access-code">ACCESS CODE</label>
              <input
                autoFocus
                id="access-code"
                type="password"
                autoComplete="off"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Enter your private demo code"
                required
              />
              {authError && (
                <div className="form-error" role="alert">
                  {authError}
                </div>
              )}
              <button
                className="primary-button"
                type="submit"
                disabled={authBusy || !code}
              >
                {authBusy ? (
                  <LoaderCircle size={17} className="spin" />
                ) : (
                  "Open this session"
                )}
                <ArrowRight size={17} />
              </button>
            </form>
            <div className="auth-help">
              <LockKeyhole size={14} />
              <p>
                Local setup stores generated codes in{" "}
                <code>.local/access.json</code>. Switching a UI control never
                grants approval rights.
              </p>
            </div>
          </section>
        </div>
      )}
      {evidence && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setEvidence(null);
          }}
        >
          <section
            className="evidence-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-title"
          >
            <div className="evidence-modal-header">
              <div>
                <div className="eyebrow">INSPECT THE RECORD</div>
                <h2 id="evidence-title">Evidence, without embellishment.</h2>
              </div>
              <button
                className="icon-button"
                onClick={() => setEvidence(null)}
                aria-label="Close evidence"
              >
                <X size={22} />
              </button>
            </div>
            <p>
              Source data and recorded decisions. A fingerprint binds an offer;
              it does not guarantee future stock or delivery.
            </p>
            <pre>{JSON.stringify(evidence, null, 2)}</pre>
            <button
              className="secondary-button"
              onClick={() => {
                navigator.clipboard
                  .writeText(JSON.stringify(evidence, null, 2))
                  .then(() => setToast("Evidence copied."))
                  .catch(() =>
                    setToast("Copy unavailable. Select the evidence text."),
                  );
              }}
            >
              <Copy size={15} /> Copy evidence
            </button>
          </section>
        </div>
      )}
      {about && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setAbout(false);
          }}
        >
          <section
            className="about-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
          >
            <button
              className="modal-close icon-button"
              onClick={() => setAbout(false)}
              aria-label="Close explanation"
            >
              <X size={22} />
            </button>
            <div className="eyebrow">TWENTY SECONDS TO TRUST</div>
            <h2 id="about-title">
              An agent can suggest.
              <br />
              <em>Only the gateway can commit.</em>
            </h2>
            <div className="about-steps">
              {[
                [
                  Search,
                  "Find a grounded offer",
                  "Real catalogue IDs, dimensional quantities, price and delivery evidence.",
                ],
                [
                  ShieldCheck,
                  "Respect the mandate",
                  "Autonomous, approvable or invalid. A hard dietary rule cannot be bought off.",
                ],
                [
                  ReceiptText,
                  "Leave a verifiable record",
                  "Exact-offer approval, atomic spend enforcement and an idempotent simulated receipt.",
                ],
              ].map(([I, title, desc], i) => (
                <div key={i}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>{title as string}</h3>
                    <p>{desc as string}</p>
                  </div>
                  <Icon icon={I as LucideIcon} size={22} />
                </div>
              ))}
            </div>
            <button
              className="primary-button"
              onClick={() => {
                setAbout(false);
                setScenario("shortage");
              }}
            >
              Try the shortage rehearsal <ArrowRight size={17} />
            </button>
            <p className="small-muted">
              The hotel and mandate are authored examples. All orders are
              simulated.
            </p>
          </section>
        </div>
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCheck size={17} />
          {toast}
        </div>
      )}
    </div>
  );
}
function ArrowDownLine() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path d="M8 2v12m-4-4 4 4 4-4" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
function Receipt({
  receipt,
  onInspect,
}: {
  receipt: any;
  onInspect: () => void;
}) {
  return (
    <section className="receipt-card" aria-live="polite">
      <div className="receipt-top">
        <span className="receipt-stamp">
          <CheckCheck size={26} />
        </span>
        <span>
          SIMULATED
          <br />
          ORDER RECORDED
        </span>
        <ReceiptText size={24} />
      </div>
      <h3>One order. A clear trail.</h3>
      <div className="receipt-number">
        {receipt.order_id || receipt.id || "SIMULATED RECEIPT"}
      </div>
      <div className="receipt-facts">
        <div>
          <span>Committed total</span>
          <strong>{money(receipt.total || receipt.offer?.total)}</strong>
        </div>
        <div>
          <span>Customer</span>
          <strong>{receipt.customer_id || "Aurora Hotel"}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{receipt.status || "simulated"}</strong>
        </div>
      </div>
      <p>
        Retries return this same order. This is our simulator, not a Valio
        purchase or stock reservation.
      </p>
      <p>
        B2B purchases require a customer contract and are usually invoiced after
        delivery. This simulated receipt is not an invoice; no payment is taken.
      </p>
      <button className="text-button" onClick={onInspect}>
        Inspect the decision receipt <ArrowUpRight size={15} />
      </button>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
