import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Check, LoaderCircle, RefreshCw, SlidersHorizontal } from "lucide-react";
import "./preferences.css";

type Preferences = {
  preferred_brand: string | null;
  preferred_origin: "finland" | "eu" | null;
  preferred_organic: boolean;
  priority: "balanced" | "cheapest" | "quality" | "origin" | "delivery";
  updated_at?: string;
};
const defaults: Preferences = { preferred_brand: null, preferred_origin: null, preferred_organic: false, priority: "balanced" };
const priorities: Record<Preferences["priority"], string> = {
  balanced: "Balanced · let me compare",
  cheapest: "Lowest rounded item cost",
  quality: "Review quality specifications myself",
  origin: "Preferred origin first",
  delivery: "Earliest verified availability",
};
function payload(preferences: Preferences) {
  return {
    preferred_brand: preferences.preferred_brand?.trim() || null,
    preferred_origin: preferences.preferred_origin || null,
    preferred_organic: preferences.preferred_organic === true,
    priority: preferences.priority,
  };
}

export function PreferencesPanel({ api, role, onSignIn, disabled, applyToNewRequest, onApplyChange, hasCart }: {
  api: (path: string, options?: RequestInit) => Promise<any>;
  role: string | null;
  onSignIn: () => void;
  disabled: boolean;
  applyToNewRequest: boolean;
  onApplyChange: (apply: boolean) => void;
  hasCart: boolean;
}) {
  const [preferences, setPreferences] = useState<Preferences>({ ...defaults });
  const [saved, setSaved] = useState<Preferences>({ ...defaults });
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    setPreferences({ ...defaults }); setSaved({ ...defaults }); setLoaded(false); setError(""); setNotice("");
    if (role !== "buyer") return;
    let cancelled = false;
    setLoading(true);
    api("/preferences")
      .then((data: Preferences) => { if (!cancelled) { setPreferences(data); setSaved(data); setLoaded(true); } })
      .catch((e: Error) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [api, role]);
  async function reload() {
    setLoading(true); setError("");
    try { const data = await api("/preferences"); setPreferences(data); setSaved(data); setLoaded(true); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  async function save(next: Preferences) {
    if (role !== "buyer") { onSignIn(); return; }
    setSaving(true); setError(""); setNotice("");
    try {
      const data: Preferences = await api("/preferences", { method: "PUT", body: JSON.stringify(payload(next)) });
      setPreferences(data); setSaved(data); setLoaded(true);
      setNotice(hasCart ? "Saved for your next request. Your current cart is unchanged." : "Saved for future requests. Explicit instructions in your request take priority.");
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(false); }
  }
  function submit(e: FormEvent) { e.preventDefault(); save(preferences); }
  const dirty = JSON.stringify(payload(preferences)) !== JSON.stringify(payload(saved));
  const locked = disabled || loading || saving || !loaded;
  return <details className="proc-preferences">
    <summary><SlidersHorizontal size={15} /><span>Buying preferences</span><small>{role === "buyer" && loaded ? priorities[saved.priority] : "Save your usual choices"}</small></summary>
    {role !== "buyer" ? <div className="proc-preferences-body"><p>Buyer preferences are saved privately to the signed-in buyer account. They guide future suggestions and do not change hard requirements.</p><button type="button" onClick={onSignIn}>Sign in as buyer to manage preferences</button></div> : <div className="proc-preferences-body">
      <p>Set your usual choices for new requests. These are preferences, not requirements. Your explicit request and all hard dietary, origin, brand and budget constraints take priority.</p>
      {loading && <p role="status"><LoaderCircle className="spin" size={14} />Loading your saved preferences…</p>}
      {error && <div className="proc-preferences-error" role="alert"><p>{error}</p>{!loaded && <button type="button" onClick={reload} disabled={loading}>Retry loading preferences</button>}</div>}
      <form onSubmit={submit}>
        <div className="proc-preferences-fields">
          <label>Purchasing priority<select value={preferences.priority} onChange={(e) => setPreferences((current) => ({ ...current, priority: e.target.value as Preferences["priority"] }))} disabled={locked}>{Object.entries(priorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Preferred brand<input type="text" maxLength={80} placeholder="No brand preference" value={preferences.preferred_brand || ""} onChange={(e) => setPreferences((current) => ({ ...current, preferred_brand: e.target.value || null }))} disabled={locked} /></label>
          <label>Preferred origin<select value={preferences.preferred_origin || ""} onChange={(e) => setPreferences((current) => ({ ...current, preferred_origin: (e.target.value || null) as Preferences["preferred_origin"] }))} disabled={locked}><option value="">No origin preference</option><option value="finland">Finland</option><option value="eu">European Union</option></select></label>
          <label className="proc-preference-check"><input type="checkbox" checked={preferences.preferred_organic === true} onChange={(e) => setPreferences((current) => ({ ...current, preferred_organic: e.target.checked }))} disabled={locked} />Prefer verified organic products</label>
        </div>
        <div className="proc-preferences-actions"><button type="submit" disabled={locked || !dirty}>{saving ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}{saving ? "Saving preferences…" : "Save preferences"}</button><button type="button" className="proc-clear-preferences" disabled={locked} onClick={() => save({ ...defaults })}><RefreshCw size={13} />Clear saved preferences</button></div>
      </form>
      {!hasCart && <label className="proc-apply-preferences"><input type="checkbox" checked={applyToNewRequest} onChange={(e) => onApplyChange(e.target.checked)} disabled={disabled || saving} />Use saved preferences for this new request</label>}
      <p className="proc-preferences-note">Saving does not change an existing cart. Quality has no invented score; that priority keeps product comparison in your hands. Delivery means verified available date, not a delivery guarantee.</p>
      {notice && <p className="proc-preferences-saved" role="status"><Check size={14} />{notice}</p>}
    </div>}
  </details>;
}
