import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Check, LoaderCircle, RefreshCw, SlidersHorizontal } from "lucide-react";
import "./preferences.css";

type Preferences = {
  preferred_brand: string | null;
  preferred_origin: "finland" | "eu" | null;
  preferred_organic: boolean;
  priority: "balanced" | "cheapest" | "quality" | "origin" | "delivery";
  dietary_restrictions: string[]; excluded_ingredients: string[]; custom_preferences: string;
  updated_at?: string;
};
const defaults: Preferences = { preferred_brand: null, preferred_origin: null, preferred_organic: false, priority: "balanced", dietary_restrictions: [], excluded_ingredients: [], custom_preferences: "" };
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
    dietary_restrictions: preferences.dietary_restrictions || [],
    excluded_ingredients: (preferences.excluded_ingredients || []).map((item) => item.trim()).filter(Boolean),
    custom_preferences: preferences.custom_preferences || "",
  };
}

export function PreferencesPanel({ api, role, onSignIn, disabled, applyToNewRequest, onApplyChange, hasCart, onSaved }: {
  api: (path: string, options?: RequestInit) => Promise<any>;
  role: string | null;
  onSignIn: () => void;
  disabled: boolean;
  applyToNewRequest: boolean;
  onApplyChange: (apply: boolean) => void;
  hasCart: boolean;
  onSaved?: (hardChanged: boolean) => void | Promise<void>;
}) {
  const [preferences, setPreferences] = useState<Preferences>({ ...defaults });
  const [saved, setSaved] = useState<Preferences>({ ...defaults });
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [restrictionSearch, setRestrictionSearch] = useState("");
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
    if ((next.excluded_ingredients || []).filter((item) => item.trim()).length > 8) { setError("Use up to eight excluded ingredients; none were saved."); return; }
    setSaving(true); setError(""); setNotice("");
    try {
      const data: Preferences = await api("/preferences", { method: "PUT", body: JSON.stringify(payload(next)) });
      const hardChanged = JSON.stringify([saved.dietary_restrictions || [], saved.excluded_ingredients || []]) !== JSON.stringify([data.dietary_restrictions || [], data.excluded_ingredients || []]);
      setPreferences(data); setSaved(data); setLoaded(true);
      await onSaved?.(hardChanged);
      setNotice(hardChanged ? "Requirements saved. Search and cart checks will enforce them." : "Preferences saved for new requests.");
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(false); }
  }
  function submit(e: FormEvent) { e.preventDefault(); save(preferences); }
  const dirty = JSON.stringify(payload(preferences)) !== JSON.stringify(payload(saved));
  const locked = disabled || loading || saving || !loaded;
  return <details className="proc-preferences">
    <summary><SlidersHorizontal size={15} /><span>Buying preferences</span><small>{role === "buyer" && loaded ? priorities[saved.priority] : "Save your usual choices"}</small></summary>
    {role !== "buyer" ? <div className="proc-preferences-body"><p>Buyer preferences are saved privately to the signed-in buyer account. They guide future suggestions and do not change hard requirements.</p><button type="button" onClick={onSignIn}>Sign in as buyer to manage preferences</button></div> : <div className="proc-preferences-body">
      <p>Mandatory food restrictions are always checked. Optional buying preferences guide new requests.</p>
      {loading && <p role="status"><LoaderCircle className="spin" size={14} />Loading your saved preferences…</p>}
      {error && <div className="proc-preferences-error" role="alert"><p>{error}</p>{!loaded && <button type="button" onClick={reload} disabled={loading}>Retry loading preferences</button>}</div>}
      <form onSubmit={submit}>
        <details className="preference-restrictions"><summary>Mandatory food requirements <span>{preferences.dietary_restrictions?.length || 0}</span></summary><label>Find a requirement<input type="search" value={restrictionSearch} onChange={(e) => setRestrictionSearch(e.target.value)} placeholder="Allergy, diet or ingredient" /></label><div className="preference-restriction-options">{[
          ["lactose_free", "Lactose-free"], ["milk_free", "Milk / dairy allergy exclusion"], ["gluten_free", "Gluten-free"], ["peanut_free", "Peanut allergy exclusion"], ["nut_free", "Tree nut allergy exclusion"], ["vegetarian", "Vegetarian"], ["vegan", "Vegan"], ["no_pork", "No pork"], ["halal", "Verified halal"], ["kosher", "Verified kosher"], ["egg_free", "Egg exclusion"], ["soy_free", "Soy exclusion"], ["fish_free", "Fish exclusion"], ["crustacean_free", "Crustacean exclusion"], ["mollusc_free", "Mollusc exclusion"], ["celery_free", "Celery exclusion"], ["mustard_free", "Mustard exclusion"], ["sesame_free", "Sesame exclusion"], ["sulphite_free", "Sulphite exclusion"], ["lupin_free", "Lupin exclusion"]
        ].filter(([, label]) => label.toLowerCase().includes(restrictionSearch.toLowerCase())).map(([value, label]) => <label key={value}><input type="checkbox" checked={preferences.dietary_restrictions?.includes(value) || false} disabled={locked} onChange={(e) => setPreferences((current) => ({ ...current, dietary_restrictions: e.target.checked ? [...(current.dietary_restrictions || []), value] : (current.dietary_restrictions || []).filter((item) => item !== value) }))} />{label}</label>)}</div><label>Other excluded ingredients<textarea rows={2} value={(preferences.excluded_ingredients || []).join("\n")} placeholder="One ingredient per line, up to 8" disabled={locked} onChange={(e) => setPreferences((current) => ({ ...current, excluded_ingredients: e.target.value.split("\n") }))} /></label><p>Missing allergen, ingredient or certification evidence is not verified safe. Lactose-free does not mean milk-allergy safe.</p></details>

        <div className="proc-preferences-fields">
          <label>Purchasing priority<select value={preferences.priority} onChange={(e) => setPreferences((current) => ({ ...current, priority: e.target.value as Preferences["priority"] }))} disabled={locked}>{Object.entries(priorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Preferred brand<input type="text" maxLength={80} placeholder="No brand preference" value={preferences.preferred_brand || ""} onChange={(e) => setPreferences((current) => ({ ...current, preferred_brand: e.target.value || null }))} disabled={locked} /></label>
          <label>Preferred origin<select value={preferences.preferred_origin || ""} onChange={(e) => setPreferences((current) => ({ ...current, preferred_origin: (e.target.value || null) as Preferences["preferred_origin"] }))} disabled={locked}><option value="">No origin preference</option><option value="finland">Finland</option><option value="eu">European Union</option></select></label>
          <label className="proc-preference-check"><input type="checkbox" checked={preferences.preferred_organic === true} onChange={(e) => setPreferences((current) => ({ ...current, preferred_organic: e.target.checked }))} disabled={locked} />Prefer verified organic products</label>
        </div>
        <div className="proc-preferences-actions"><button type="submit" disabled={locked || !dirty}>{saving ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}{saving ? "Saving preferences…" : "Save preferences"}</button><button type="button" className="proc-clear-preferences" disabled={locked} onClick={() => save({ ...defaults })}><RefreshCw size={13} />Clear saved preferences</button></div>
      </form>
      {!hasCart && <label className="proc-apply-preferences"><input type="checkbox" checked={applyToNewRequest} onChange={(e) => onApplyChange(e.target.checked)} disabled={disabled || saving} />Use saved optional preferences for this new request</label>}
      <p className="proc-preferences-note">Mandatory restrictions cannot be bypassed by turning optional preferences off. Quality and delivery estimates are not guarantees.</p>
      {notice && <p className="proc-preferences-saved" role="status"><Check size={14} />{notice}</p>}
    </div>}
  </details>;
}
