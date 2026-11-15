import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ArrowLeft, ArrowRight, KeyRound, LoaderCircle, LogOut, ShieldCheck, ShoppingBasket, X } from "lucide-react";
import "./auth.css";

export type WorkspaceSession = {
  role: string | null; name?: string; buyer_id?: string; customer_id?: string;
  workspace_id?: string; workspace_name?: string; username?: string | null;
  demo_workspace?: boolean; remember_me?: boolean; auth_method?: string;
  session_expires_at?: string;
  quick_demo?: boolean;
};
type Props = {
  api: (path: string, options?: RequestInit) => Promise<any>;
  session: WorkspaceSession;
  onClose: () => void;
  onSignedIn: (session: WorkspaceSession) => void | Promise<void>;
  onLogout: () => void | Promise<void>;
  onSessionChanging: () => void;
  onSessionSettled: () => void;
};

export function AuthDialog({ api, session, onClose, onSignedIn, onLogout, onSessionChanging, onSessionSettled }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [method, setMethod] = useState<"demo" | "code" | "login" | "register">("demo");
  const [demoEnabled, setDemoEnabled] = useState<boolean | null>(null);
  const [demoError, setDemoError] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(Boolean(session.remember_me));
  const [workspaceId, setWorkspaceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { dialog.current?.showModal(); }, []);
  useEffect(() => {
    let active = true;
    api("/auth/demo").then((config) => {
      if (!active) return;
      setDemoEnabled(config.enabled === true);
      if (!config.enabled) setMethod((current) => current === "demo" ? "login" : current);
    }).catch(() => { if (active) setDemoError("Demo roles could not be loaded. Use an account or reopen sign-in to retry."); });
    return () => { active = false; };
  }, [api]);

  async function enterDemo(role: "buyer" | "approver") {
    if (!demoEnabled || busy) return;
    setError(""); setBusy(true); onSessionChanging();
    try {
      const next = await api("/auth/demo", { method: "POST", body: JSON.stringify({ role, remember_me: remember }) });
      await onSignedIn(next);
      onClose();
    } catch (err) { setError(err instanceof Error ? err.message : "Demo sign-in could not be completed. Try again."); }
    finally { setBusy(false); onSessionSettled(); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true); onSessionChanging();
    const path = method === "code" ? "/session" : `/auth/${method}`;
    const body = method === "code"
      ? { access_code: code, remember_me: remember, ...(workspaceId.trim() ? { workspace_id: workspaceId.trim() } : {}) }
      : method === "register"
        ? { name, username, password, invite_code: code, remember_me: remember }
        : { username, password, remember_me: remember };
    try {
      const next = await api(path, { method: "POST", body: JSON.stringify(body) });
      setPassword(""); setCode("");
      await onSignedIn(next);
      onClose();
    } catch (err) { setError(err instanceof Error ? err.message : "Sign-in could not be completed. Try again."); }
    finally { setBusy(false); onSessionSettled(); }
  }

  return <dialog ref={dialog} className="auth-modal auth-dialog" aria-labelledby="auth-title" onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
    <button className="modal-close icon-button" type="button" onClick={onClose} disabled={busy} aria-label="Close sign-in"><X size={20} /></button>
    <span className="modal-icon"><KeyRound size={25} /></span>
    <h2 id="auth-title">Sign in</h2>
    {session.role && <div className="current-session"><div><strong>{session.name}</strong><small>{session.quick_demo ? `${session.role} · shared demonstration` : session.workspace_name || session.role}</small>{!session.quick_demo && session.demo_workspace === false && <button className="text-button" type="button" disabled={busy} onClick={() => { setMethod("code"); setWorkspaceId(session.workspace_id || ""); }}>Approve this workspace</button>}</div><button className="text-button" type="button" disabled={busy} onClick={async () => { setBusy(true); setSigningOut(true); setError(""); try { await onLogout(); onClose(); } catch { setError("Sign-out could not be completed. Check the connection and try again."); } finally { setBusy(false); setSigningOut(false); } }}><LogOut size={15} />Sign out</button></div>}
    {method === "demo" ? <>
      <p className="auth-demo-label">Shared demonstration</p>
      {demoError ? <p role="alert" className="form-error">{demoError}</p> : demoEnabled === null ? <p role="status" className="auth-loading"><LoaderCircle size={16} className="spin" />Loading demo roles…</p> : <div className="auth-role-cards" role="group" aria-label="Choose demonstration role">
        <button type="button" disabled={busy || !demoEnabled} onClick={() => enterDemo("buyer")} aria-pressed={Boolean(session.quick_demo && session.role === "buyer")}><ShoppingBasket aria-hidden="true" size={28} /><strong>Buyer</strong></button>
        <button type="button" disabled={busy || !demoEnabled} onClick={() => enterDemo("approver")} aria-pressed={Boolean(session.quick_demo && session.role === "approver")}><ShieldCheck aria-hidden="true" size={28} /><strong>Approver</strong></button>
      </div>}
      <label className="auth-remember"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} disabled={busy} /><span>Remember me for 30 days on this device</span></label>
      {error && <div className="form-error" role="alert">{error}</div>}
      {busy && <p role="status" className="auth-loading"><LoaderCircle size={16} className="spin" />{signingOut ? "Signing out…" : "Opening workspace…"}</p>}
      <button type="button" className="auth-secondary text-button" disabled={busy} onClick={() => { setMethod("login"); setError(""); }}><KeyRound size={15} />Use an account</button>
      <p className="auth-demo-scope">Demo records are shared. Use nonconfidential examples only.</p>
    </> : <>
    {demoEnabled && <button type="button" className="auth-secondary text-button" disabled={busy} onClick={() => { setMethod("demo"); setError(""); setPassword(""); setCode(""); }}><ArrowLeft size={15} />Demo roles</button>}
    <nav className="auth-methods" aria-label="Sign-in method">
      {([['login','Account sign-in'],['register','Create workspace'],['code','Access code']] as const).map(([value,label]) => <button type="button" key={value} aria-pressed={method === value} disabled={busy} onClick={() => { setMethod(value); setError(""); setPassword(""); setCode(""); }}>{label}</button>)}
    </nav>
    <form onSubmit={submit}>
      {method === "register" && <><label htmlFor="auth-name">Your name</label><input id="auth-name" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} maxLength={80} required disabled={busy} /></>}
      {method !== "code" && <><label htmlFor="auth-username">Username</label><input id="auth-username" autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={(event) => setUsername(event.target.value)} minLength={method === "register" ? 3 : 1} maxLength={40} pattern={method === "register" ? "[A-Za-z0-9][A-Za-z0-9_.-]*" : undefined} required disabled={busy} />{method === "register" && <small className="auth-field-help">3–40 characters: letters, numbers, dots, underscores or hyphens.</small>}<label htmlFor="auth-password">Password</label><input id="auth-password" type="password" autoComplete={method === "register" ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} minLength={method === "register" ? 12 : undefined} maxLength={128} required disabled={busy} />{method === "register" && <small className="auth-field-help">Use 12–128 characters. No email address is required.</small>}</>}
      {method !== "login" && <><label htmlFor="access-code">{method === "register" ? "Buyer invitation code" : "ACCESS CODE"}</label><input id="access-code" type="password" autoComplete="off" value={code} onChange={(event) => setCode(event.target.value)} placeholder={method === "register" ? "Use this installation’s private buyer code" : "Enter your buyer or approver code"} required disabled={busy} /></>}
      {method === "code" && <details className="auth-workspace" open={Boolean(workspaceId)}><summary>Approve a private workspace</summary><label htmlFor="manager-workspace">Manager workspace ID (optional)</label><input id="manager-workspace" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} autoComplete="off" maxLength={100} disabled={busy} /><small>Leave blank for the shared demonstration. Use a separate manager code to approve this workspace.</small>{workspaceId && <button type="button" className="text-button" onClick={() => setWorkspaceId("")}>Use the shared demonstration instead</button>}</details>}
      {method === "register" && <p className="auth-field-help">Your invitation creates a separate demonstration workspace. It does not create a Valio Aimo customer contract or enable real purchases.</p>}
      <label className="auth-remember"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} disabled={busy} /><span>Remember me for 30 days on this device</span></label>
      {error && <div className="form-error" role="alert">{error}</div>}
      <button className="primary-button" type="submit" disabled={busy}>{busy ? <><LoaderCircle size={17} className="spin" />{signingOut ? "Signing out…" : method === "register" ? "Creating workspace…" : "Signing in…"}</> : method === "register" ? "Create my workspace" : method === "login" ? "Sign in" : "Open this session"}<ArrowRight size={17} /></button>
    </form>
    <div className="auth-help"><p>{method === "code" ? "Buyer and approver codes have separate permissions. A workspace ID alone grants no access." : "Preferences and carts are saved in your workspace. Sign out to revoke this browser’s session."}</p></div>
    </>}
  </dialog>;
}
