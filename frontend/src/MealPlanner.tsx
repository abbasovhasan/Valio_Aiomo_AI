import { useState } from "react";
import { ArrowRight, Check, ChefHat, LoaderCircle, Plus, Trash2 } from "lucide-react";
import { formatQuantity, salesQuantity } from "./productPresentation";
import { sessionInterrupted } from "./api";
import "./meal-planner.css";

type Ingredient = {
  id: string; label: string; query: string; grams_per_serving: string;
  applies_to: "all" | "meat" | "vegetarian"; split_gluten_free: boolean;
  dietary: string[]; origin: string | null;
};
type Candidate = {
  product_id: string; name: string; sales_unit: string; kg_per_sales_unit: string | null;
  quantity_sales_units: string | null; effective_kg: string | null; issues: string[];
};
type Line = {
  id: string; ingredient_id: string; ingredient: string; search_query: string;
  required_kg: string; grams_per_serving: string; servings: number;
  dietary: string[]; candidates: Candidate[];
};
type Plan = {
  id: string; dish: string; cohorts: Record<string, number>; lines: Line[];
  ingredients: Ingredient[]; recipe_note: string; verified_recipe: false;
  recipe_provenance: string; preference_note: string; dietary_restrictions: string[];
};
type Props = {
  api: (path: string, options?: RequestInit) => Promise<any>;
  role: string | null; onSignIn: () => void;
  onQuoteSession?: (sessionId: string) => void;
  onBeforeQuote?: () => boolean | Promise<boolean>;
};
function example(id: string, label: string, query: string, grams: string, applies_to: Ingredient["applies_to"] = "all", split_gluten_free = false): Ingredient {
  return { id, label, query, grams_per_serving: grams, applies_to, split_gluten_free, dietary: [], origin: null };
}
const exampleIngredients: Ingredient[] = [
  example("pasta", "Dry spaghetti", "spaghetti", "100", "all", true),
  example("beef", "Raw minced beef", "minced beef", "120", "meat", true),
  example("lentils", "Dry lentils", "red lentils", "70", "vegetarian", true),
  example("tomatoes", "Crushed tomatoes", "crushed tomatoes", "150"),
  example("onion", "Onions", "onion", "30"), example("oil", "Oil", "olive oil", "10"),
  example("salt", "Salt", "salt", "1"), example("oregano", "Oregano", "oregano", "0.5"),
];
const wholeMealDiets = [["vegetarian", "Vegetarian"], ["vegan", "Vegan"], ["gluten_free", "Gluten-free"], ["lactose_free", "Lactose-free"]] as const;
const groupLabels: Record<string, string> = { meat_standard: "Standard", meat_gluten_free: "Gluten-free", vegetarian_standard: "Vegetarian", vegetarian_gluten_free: "Vegetarian & gluten-free" };
const exampleName = (name: string) => /bolognese|bolognaise/i.test(name);

export function MealPlanner({ api, role, onSignIn, onQuoteSession, onBeforeQuote }: Props) {
  const [form, setForm] = useState({ meal_name: "Spaghetti bolognese", servings: "50", vegetarian: "0", gluten_free: "0", vegetarian_gluten_free: "0", meat_origin: "any", priority: "balanced", preferred_brand: "", preferred_origin: "" });
  const [dietary, setDietary] = useState<string[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>(exampleIngredients);
  const [source, setSource] = useState<"proposed" | "customer">("proposed");
  const [started, setStarted] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [quoting, setQuoting] = useState(false);
  const [quoteError, setQuoteError] = useState("");
  const [quoteDate, setQuoteDate] = useState("");
  const [quoteBudget, setQuoteBudget] = useState("");
  const [quoteMode, setQuoteMode] = useState("fixture");
  const pending = busy || quoting;
  const allVegetarian = dietary.includes("vegetarian") || dietary.includes("vegan");
  const allGlutenFree = dietary.includes("gluten_free");
  const groupValues = { vegetarian: allVegetarian ? form.servings : form.vegetarian,
    gluten_free: allGlutenFree ? form.servings : form.gluten_free,
    vegetarian_gluten_free: allVegetarian ? (allGlutenFree ? form.servings : form.gluten_free) : allGlutenFree ? form.vegetarian : form.vegetarian_gluten_free };

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value })); setDirty(true);
    if (key === "meal_name" && !started) {
      setIngredients(exampleName(value) ? exampleIngredients : []);
      setSource(exampleName(value) ? "proposed" : "customer");
    } else if (key === "meal_name" && !exampleName(value)) setSource("customer");
  }
  function editIngredient(id: string, changes: Partial<Ingredient>) {
    setIngredients((current) => current.map((item) => item.id === id ? { ...item, ...changes } : item));
    setSource("customer"); setDirty(true);
  }
  function addIngredient() {
    setIngredients((current) => [...current, { id: `ingredient-${crypto.randomUUID().slice(0, 12)}`, label: "", query: "", grams_per_serving: "", applies_to: "all", split_gluten_free: false, dietary: [], origin: null }]);
    setStarted(true); setSource("customer"); setDirty(true);
  }
  async function generate() {
    if (!role) { onSignIn(); return; }
    if (pending) return;
    setStarted(true); setError("");
    if (!ingredients.length) { if (started) setError("Add at least one ingredient and its grams per serving."); return; }
    if (!form.meal_name.trim() || !ingredients.every((item) => item.query.trim() && item.grams_per_serving.trim() && Number(item.grams_per_serving) > 0)) {
      setError("Enter a meal name, ingredient names and positive grams per serving."); return;
    }
    setBusy(true);
    try {
      const next: Plan = await api("/meal-plans", { method: "POST", body: JSON.stringify({
        ...form, servings: Number(form.servings), vegetarian: Number(form.vegetarian), gluten_free: Number(form.gluten_free), vegetarian_gluten_free: Number(form.vegetarian_gluten_free),
        template: source === "proposed" && exampleName(form.meal_name) ? "bolognese" : "custom", recipe_source: source,
        ingredients, dietary_restrictions: dietary, preferred_brand: form.preferred_brand.trim() || null, preferred_origin: form.preferred_origin || null,
      }) });
      setChoices((prior) => Object.fromEntries(next.lines.flatMap((line) => prior[line.id] && line.candidates.some((candidate) => candidate.product_id === prior[line.id]) ? [[line.id, prior[line.id]]] : [])));
      setPlan(next); setIngredients(next.ingredients); setDirty(false);
    } catch (cause) { if (!sessionInterrupted(cause)) setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  async function quotePlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!plan || dirty || pending) return;
    if (!role) { onSignIn(); return; }
    const returnFocus = event.currentTarget?.querySelector<HTMLButtonElement>(".meal-primary");
    let cancelled = false;
    setQuoting(true); setQuoteError("");
    try {
      if (onBeforeQuote && !await onBeforeQuote()) { cancelled = true; return; }
      const selections = Object.fromEntries(plan.lines.flatMap((line, index) => choices[line.id] ? [[index, choices[line.id]]] : []));
      const session = await api("/procurement/sessions/from-meal-plan", { method: "POST", body: JSON.stringify({ plan_id: plan.id, selections, mode: quoteMode, ...(quoteDate ? { date: quoteDate } : {}), ...(quoteBudget ? { budget: quoteBudget } : {}) }) });
      onQuoteSession?.(session.id);
    } catch (cause) { if (!sessionInterrupted(cause)) setQuoteError((cause as Error).message); }
    finally {
      setQuoting(false);
      if (cancelled && returnFocus) window.requestAnimationFrame(() => { if (returnFocus.isConnected) returnFocus.focus({ preventScroll: true }); });
    }
  }
  function download() {
    if (!plan || dirty) return;
    const blob = new Blob([JSON.stringify({ ...plan, selections: choices, can_commit: false }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = `${plan.id}-shopping-plan.json`; link.click(); URL.revokeObjectURL(url);
  }

  return <section className="meal-studio" aria-labelledby="meal-title">
    <header className="meal-heading"><span className="meal-eyebrow"><ChefHat size={17} />From kitchen to cart</span><h2 id="meal-title">Plan a meal</h2><p>Set your servings. Review the ingredients. Choose products for a shopping draft.</p></header>
    <div className="meal-layout">
      <form className="paper meal-config" onSubmit={(event) => { event.preventDefault(); void generate(); }}>
        <label>Meal name<input aria-label="Meal name" value={form.meal_name} onChange={(event) => update("meal_name", event.target.value)} maxLength={120} required disabled={pending} /></label>
        <label>Servings<input aria-label="Number of servings" type="number" min="1" max="10000" step="1" required value={form.servings} onChange={(event) => update("servings", event.target.value)} disabled={pending} /></label>
        {!started && <p className="meal-hint">{exampleName(form.meal_name) ? "Starts with an illustrative bolognese recipe for you to edit." : "Add your kitchen’s ingredients and grams per serving in the next step."}</p>}
        <details className="meal-settings"><summary>Dietary requirements <span>Optional</span></summary>
          <fieldset className="meal-diets"><legend>For every serving</legend>{wholeMealDiets.map(([value, label]) => <label key={value}><input type="checkbox" checked={dietary.includes(value)} disabled={pending} onChange={(event) => { setDietary((current) => event.target.checked ? [...current, value] : current.filter((item) => item !== value)); setDirty(true); }} />{label}</label>)}</fieldset>
          <p className="meal-hint">Vegetarian or vegan uses the lentil option in the example recipe. Missing dietary evidence remains a blocker.</p>
          <fieldset className="meal-groups"><legend>Different dietary groups</legend><p className="meal-hint">Totals include diners who need both. Enter the overlap so each diner is counted once.</p>{([["vegetarian", "Vegetarian servings"], ["gluten_free", "Gluten-free servings"], ["vegetarian_gluten_free", "Both vegetarian & gluten-free"]] as const).map(([key, label]) => <label key={key}>{label}<input type="number" min="0" max={form.servings || "10000"} step="1" value={groupValues[key]} onChange={(event) => update(key, event.target.value)} disabled={pending || (key === "vegetarian" ? allVegetarian : key === "gluten_free" ? allGlutenFree : allGlutenFree || allVegetarian)} /></label>)}</fieldset>
        </details>
        <details className="meal-settings"><summary>Ingredient preferences <span>Optional</span></summary>
          <label>Purchasing priority<select value={form.priority} onChange={(event) => update("priority", event.target.value)} disabled={pending}><option value="balanced">Price and specifications</option><option value="price">Lowest basket cost</option><option value="quality">Review specifications first</option></select></label>
          <label>Preferred brand<input value={form.preferred_brand} maxLength={80} placeholder="Any brand" onChange={(event) => update("preferred_brand", event.target.value)} disabled={pending} /></label>
          <label>Preferred origin<select value={form.preferred_origin} onChange={(event) => update("preferred_origin", event.target.value)} disabled={pending}><option value="">Any origin</option><option value="finland">Prefer Finland</option><option value="eu">Prefer EU</option></select></label>
          <label>Required meat origin<select value={form.meat_origin} onChange={(event) => update("meat_origin", event.target.value)} disabled={pending}><option value="any">Any origin</option><option value="finland">Finland only</option><option value="eu">EU only</option></select></label>
          <p className="meal-hint">Saved hard dietary restrictions also apply. Brand and preferred origin help rank suitable products.</p>
        </details>
        {error && <p className="meal-error" role="alert">{error}</p>}
        <button className="primary-button meal-primary" disabled={pending || role === "approver"}>{busy ? <><LoaderCircle size={16} className="spin" />Calculating ingredients…</> : plan ? "Recalculate plan" : started ? "Calculate ingredients" : "Plan a meal"}<ArrowRight size={16} /></button>
      </form>
      <div className="meal-workspace">
        {!started ? <div className="paper meal-welcome"><ChefHat size={28} /><h3>Your recipe, scaled for service</h3><p>Use the bolognese example or enter any meal with your own ingredients. Prices and stock are checked when you create a shopping draft.</p><ol><li>Set meal and servings</li><li>Adjust ingredients and dietary groups</li><li>Choose products and create a cart draft</li></ol></div> : <>
          <section className="paper meal-editor" aria-labelledby="meal-ingredients-title">
            <div className="meal-section-heading"><div><h3 id="meal-ingredients-title">Your ingredients</h3><p>{source === "proposed" ? "Illustrative bolognese · unverified recipe" : "Your kitchen’s quantities · unverified recipe"}</p></div><span className="meal-small-tag">g per serving</span></div>
            <p className="meal-hint">Raw or dry weight, before cooking. Edit an ingredient name to search for a replacement.</p>
            <div className="meal-ingredient-list">{ingredients.map((ingredient) => <div className="meal-ingredient-edit" key={ingredient.id}>
              <label>Ingredient<input aria-label={`Ingredient ${ingredient.label || "name"}`} value={ingredient.query} maxLength={200} placeholder="e.g. carrot" disabled={pending} onChange={(event) => editIngredient(ingredient.id, { query: event.target.value, label: event.target.value })} /></label>
              <label>Grams / serving<input aria-label={`Grams per serving for ${ingredient.label || "new ingredient"}`} type="number" min="0.01" max="5000" step="0.01" placeholder="150" value={ingredient.grams_per_serving} disabled={pending} onChange={(event) => editIngredient(ingredient.id, { grams_per_serving: event.target.value })} /></label>
              <label>Use for<select aria-label={`Serving group for ${ingredient.label || "new ingredient"}`} value={ingredient.applies_to} disabled={pending} onChange={(event) => editIngredient(ingredient.id, { applies_to: event.target.value as Ingredient["applies_to"] })}><option value="all">All servings</option><option value="meat">Meat servings</option><option value="vegetarian">Vegetarian servings</option></select></label>
              <button className="meal-remove" type="button" aria-label={`Remove ${ingredient.label || "ingredient"}`} disabled={pending} onClick={() => { setIngredients((current) => current.filter((item) => item.id !== ingredient.id)); setSource("customer"); setDirty(true); }}><Trash2 size={16} /></button>
            </div>)}</div>
            {!ingredients.length && <p className="meal-hint">No recipe is supplied for this dish. Add your first ingredient to begin.</p>}
            <div className="meal-editor-actions"><button type="button" className="text-button" onClick={addIngredient} disabled={pending || ingredients.length >= 12}><Plus size={16} />Add ingredient</button><button className="secondary-button" type="button" onClick={() => void generate()} disabled={pending || !ingredients.length}>{busy ? "Calculating…" : "Recalculate quantities"}</button></div>
            <p className="meal-hint">Up to 12 ingredients. Shared ingredients must satisfy every group using them. Your chef checks yield and separate preparation.</p>
          </section>
          {plan && <>
            <section className="paper meal-plan-summary" aria-live="polite"><div className="meal-section-heading"><div><span className="meal-eyebrow">Shopping plan</span><h3>{plan.dish}</h3></div><span className="meal-small-tag">Chef review required</span></div><div className="meal-cohorts">{Object.entries(plan.cohorts).filter(([, count]) => count > 0).map(([key, count]) => <div key={key}><strong>{count}</strong><span>{groupLabels[key] || key}</span></div>)}</div><p>{plan.recipe_note}</p>{dirty && <p role="status" className="meal-unsaved">You changed the plan. Recalculate before adding ingredients to cart.</p>}<button className="text-button" type="button" disabled={dirty || pending} onClick={download}>Export ingredient plan</button></section>
            <section className="meal-matches" aria-label="Ingredient products">{plan.lines.map((line) => <article className="paper meal-match" key={line.id}>
              <div className="meal-section-heading"><div><h3>{line.ingredient}</h3><p>{line.servings} servings × {formatQuantity(line.grams_per_serving)} g</p></div><strong className="meal-required">{formatQuantity(line.required_kg)} kg</strong></div>
              {!!line.dietary.length && <p className="meal-hint">Required: {line.dietary.map((value) => value.replaceAll("_", " ")).join(", ")}</p>}
              {!line.candidates.length ? <p className="meal-error">No catalog match. Edit this ingredient above to find an alternative.</p> : <details className="meal-options" open={!!choices[line.id]}><summary>{choices[line.id] ? <><Check size={15} />Selected product</> : `${line.candidates.length} catalog ${line.candidates.length === 1 ? "option" : "options"}`}<span>{line.candidates.every((candidate) => candidate.issues.length > 0) ? "Evidence review needed" : "Choose a product"}</span></summary>{line.candidates.map((candidate) => <label className="meal-candidate" key={candidate.product_id}><input type="radio" name={`meal-${line.id}`} checked={choices[line.id] === candidate.product_id} disabled={dirty || pending} onChange={() => setChoices((current) => ({ ...current, [line.id]: candidate.product_id }))} /><span><strong>{candidate.name}</strong><small>SKU {candidate.product_id} · {candidate.quantity_sales_units ? salesQuantity(candidate.quantity_sales_units, candidate.sales_unit) : "Package quantity unknown"}{candidate.effective_kg ? ` · ${formatQuantity(candidate.effective_kg)} kg after rounding` : " · Net mass unknown"}</small>{candidate.issues.map((issue) => <small className="meal-error" key={issue}>{issue}</small>)}</span></label>)}</details>}
            </article>)}</section>
            {onQuoteSession && <form className="paper meal-transfer" onSubmit={quotePlan}><span className="meal-eyebrow">Next: Smart Order</span><h3>Add ingredients to cart</h3><p>Exact quantities and selected products carry into a new draft. Shared products are combined before package rounding and pricing.</p><details className="meal-settings"><summary>Delivery, budget & pricing <span>Optional</span></summary><div className="meal-transfer-fields"><label>Delivery deadline<input aria-label="Meal plan delivery date" type="date" value={quoteDate} onInput={(event) => setQuoteDate(event.currentTarget.value)} onChange={(event) => setQuoteDate(event.target.value)} disabled={dirty || pending} /></label><label>Maximum item budget (€)<input aria-label="Meal plan maximum budget" type="number" min="0" step="0.01" placeholder="No budget set" value={quoteBudget} onChange={(event) => setQuoteBudget(event.target.value)} disabled={dirty || pending} /></label><label>Pricing<select value={quoteMode} onChange={(event) => setQuoteMode(event.target.value)} disabled={dirty || pending}><option value="fixture">Sample prices & stock</option><option value="live">Live supplier sandbox</option></select></label></div></details><p className="meal-hint">{quoteDate ? `Requested delivery: ${quoteDate}. ` : "No delivery deadline yet. "}{quoteBudget ? `Item budget: €${quoteBudget}. ` : ""}Pricing and availability are checked in Smart Order. Recipe review and all hard restrictions remain required.</p>{quoteError && <p role="alert" className="meal-error">{quoteError}</p>}<button className="primary-button meal-primary" disabled={dirty || pending || role === "approver"}>{quoting ? <><LoaderCircle size={16} className="spin" />Preparing draft…</> : <>Add ingredients to cart<ArrowRight size={16} /></>}</button><small>Creates a separate simulated shopping draft. Nothing is ordered or reserved.</small></form>}
          </>}
        </>}
      </div>
    </div>
  </section>;
}
