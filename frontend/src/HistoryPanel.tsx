import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Archive, ArchiveRestore, LoaderCircle, Trash2 } from "lucide-react";
import "./workspace.css";

type Entry = { id: string; title: string; created_at: string; updated_at?: string; archived: boolean; order_status: string; line_count: number; total: string | null; currency?: string; receipt_id?: string | null };
type History = { items: Entry[]; total: number; limit: number; offset: number };
const money = (value: string | null) => value == null ? "Unquoted" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR" }).format(Number(value));
export function HistoryPanel({ api, role, onSignIn, onOpen, onRemoved, date, budget, mode }: {
  api: (path: string, options?: RequestInit) => Promise<any>; role: string | null; onSignIn: () => void;
  onOpen: (session: any) => void; onRemoved: (id: string) => void; date: string; budget: string; mode: string;
}) {
  const [archived, setArchived] = useState(false);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<History | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [remove, setRemove] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (role !== "buyer") return;
    let cancelled = false;
    setBusy("load"); setError("");
    api(`/history?archived=${archived}&limit=20&offset=${offset}`).then((value) => { if (!cancelled) setData(value); }).catch((e) => { if (!cancelled) setError((e as Error).message); }).finally(() => { if (!cancelled) setBusy(""); });
    return () => { cancelled = true; };
  }, [api, role, archived, offset, refresh]);
  async function perform(id: string, operation: () => Promise<any>) {
    setBusy(id); setError("");
    try { await operation(); setRefresh((value) => value + 1); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(""); }
  }
  if (role !== "buyer") return <button className="workspace-signin" onClick={onSignIn}>Sign in as buyer to open History</button>;
  return <section className="history-workspace" aria-label="Request history"><div className="history-toolbar"><label><input type="checkbox" checked={archived} onChange={(e) => { setArchived(e.target.checked); setOffset(0); }} />Show archived requests</label><span>{data?.total ?? ""} requests</span></div>{error && <p role="alert" className="workspace-error">{error}</p>}{busy === "load" && <p role="status"><LoaderCircle className="spin" size={16} />Loading history…</p>}{data?.items.map((entry) => <article className="history-entry" key={entry.id}><div><button className="history-open" disabled={Boolean(busy)} onClick={() => perform(entry.id, async () => onOpen(await api(`/history/${entry.id}`)))}>{entry.title || "Purchasing request"}</button><p>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "Europe/Helsinki" }).format(new Date(entry.created_at))} · {entry.line_count} items · {entry.receipt_id ? "Simulated order" : "Draft"} · {money(entry.total)}</p></div><div className="history-actions"><button disabled={Boolean(busy)} onClick={() => perform(entry.id, async () => onOpen(await api(`/history/${entry.id}/reuse`, { method: "POST", body: JSON.stringify({ ...(date ? { date } : {}), ...(budget ? { budget } : {}), mode }) })))}>Reuse</button><button disabled={Boolean(busy)} onClick={() => perform(entry.id, () => api(`/history/${entry.id}`, { method: "PATCH", body: JSON.stringify({ archived: !entry.archived }) }))}>{entry.archived ? <ArchiveRestore size={15} /> : <Archive size={15} />}{entry.archived ? "Restore" : "Archive"}</button>{remove === entry.id ? <><button className="history-remove" disabled={Boolean(busy)} onClick={() => perform(entry.id, async () => { await api(`/history/${entry.id}`, { method: "DELETE" }); onRemoved(entry.id); setRemove(null); })}>Remove from history</button><button onClick={() => setRemove(null)}>Cancel</button></> : <button aria-label={`Remove ${entry.title || "request"} from history`} disabled={Boolean(busy)} onClick={() => setRemove(entry.id)}><Trash2 size={15} /></button>}</div></article>)}{data && !data.items.length && <p className="workspace-empty">{archived ? "No archived requests." : "Your saved requests and simulated orders appear here."}</p>}{data && data.total > data.limit && <div className="workspace-pagination"><button disabled={!offset || Boolean(busy)} onClick={() => setOffset(Math.max(0, offset - data.limit))}><ArrowLeft size={15} />Previous</button><button disabled={offset + data.items.length >= data.total || Boolean(busy)} onClick={() => setOffset(offset + data.limit)}>Next<ArrowRight size={15} /></button></div>}<p className="history-retention">Removing a history entry hides it from this list. Recorded orders and required audit evidence are retained.</p></section>;
}
