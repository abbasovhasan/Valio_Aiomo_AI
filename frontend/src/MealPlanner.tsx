import { useState } from "react";

type Candidate = {
  product_id: string;
  name: string;
  sales_unit: string;
  quantity_sales_units: string | null;
  effective_kg: string | null;
  origin_codes: string[];
  gluten_free_claim: boolean;
  historical_reliability: number | null;
  issues: string[];
};
type Line = {
  ingredient: string;
  required_kg: string;
  grams_per_serving: string;
  servings: number;
  candidates: Candidate[];
};
type Plan = {
  id: string;
  cohorts: Record<string, number>;
  lines: Line[];
  recipe_note: string;
  preference_note: string;
  reliability_note: string;
  next_steps: string[];
  boundaries: string;
};
const defaults = {
  pasta_g: 100,
  beef_g: 120,
  dry_lentils_g: 70,
  tomatoes_g: 150,
  onion_g: 30,
  oil_g: 10,
  salt_g: 1,
  oregano_g: 0.5,
};
const labels: Record<string, string> = {
  pasta_g: "Dry pasta",
  beef_g: "Raw beef",
  dry_lentils_g: "Dry lentils",
  tomatoes_g: "Crushed tomatoes",
  onion_g: "Onion",
  oil_g: "Oil",
  salt_g: "Salt",
  oregano_g: "Oregano",
};

export function MealPlanner({
  api,
  role,
  onSignIn,
  onQuoteSession,
}: {
  api: (path: string, options?: RequestInit) => Promise<any>;
  role: string | null;
  onSignIn: () => void;
  onQuoteSession?: (sessionId: string) => void;
}) {
  const [form, setForm] = useState({
    servings: 500,
    vegetarian: 100,
    gluten_free: 50,
    vegetarian_gluten_free: 20,
    meat_origin: "finland",
    priority: "balanced",
    recipe_source: "proposed",
    include_carrot: false,
  });
  const [recipe, setRecipe] = useState(defaults);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [choices, setChoices] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [quoteError, setQuoteError] = useState("");
  const [quoteDate, setQuoteDate] = useState("");
  const [quoteBudget, setQuoteBudget] = useState("");
  const [quoteMode, setQuoteMode] = useState("fixture");
  function update(key: string, value: unknown) {
    setForm((f) => ({ ...f, [key]: value }));
    setDirty(true);
  }
  async function generate(e: React.FormEvent) {
    e.preventDefault();
    if (!role) {
      onSignIn();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const p = await api("/meal-plans", {
        method: "POST",
        body: JSON.stringify({ ...form, recipe }),
      });
      setPlan(p);
      setChoices({});
      setDirty(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function quotePlan(e: React.FormEvent) {
    e.preventDefault();
    if (!plan || dirty || quoting) return;
    if (!role) { onSignIn(); return; }
    setQuoting(true); setQuoteError("");
    try {
      const session = await api("/procurement/sessions/from-meal-plan", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id, selections: choices, mode: quoteMode, ...(quoteDate ? { date: quoteDate } : {}), ...(quoteBudget ? { budget: quoteBudget } : {}) }),
      });
      onQuoteSession?.(session.id);
    } catch (e) { setQuoteError((e as Error).message); }
    finally { setQuoting(false); }
  }
  function download() {
    if (!plan || dirty) return;
    const selected = plan.lines.map((line, i) => ({
      ingredient: line.ingredient,
      required_kg: line.required_kg,
      candidate:
        line.candidates.find((c) => c.product_id === choices[i]) || null,
    }));
    const blob = new Blob(
      [
        JSON.stringify(
          {
            ...plan,
            selections: selected,
            status: "draft_needs_chef_review",
            can_commit: false,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${plan.id}-shopping-plan.json`;
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="meal-planner">
      <div className="planner-intro">
        <div className="eyebrow">FROM KITCHEN NEED TO SHOPPING PLAN</div>
        <h2>Start with the meal.</h2>
        <p>
          Spaghetti bolognese for 500 people, with a lentil alternative. Set the
          portions, review the recipe, then compare ingredient candidates.
        </p>
      </div>
      <div className="planner-grid">
        <form className="paper planner-form" onSubmit={generate}>
          <h3>Who are we cooking for?</h3>
          <p>
            Vegetarian and gluten-free totals include diners who need both. Each
            diner is counted once.
          </p>
          <div className="planner-fields">
            {(
              [
                ["servings", "Total diners"],
                ["vegetarian", "Vegetarian diners"],
                ["gluten_free", "Gluten-free diners"],
                ["vegetarian_gluten_free", "Both vegetarian & gluten-free"],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  type="number"
                  min={key === "servings" ? 1 : 0}
                  max={10000}
                  required
                  value={form[key]}
                  onChange={(e) => update(key, Number(e.target.value))}
                />
              </label>
            ))}
          </div>
          <label>
            Meat sourcing
            <select
              value={form.meat_origin}
              onChange={(e) => update("meat_origin", e.target.value)}
            >
              <option value="finland">Finland only</option>
              <option value="eu">EU only</option>
              <option value="any">Any origin</option>
            </select>
          </label>
          <label>
            Purchasing priority
            <select
              value={form.priority}
              onChange={(e) => update("priority", e.target.value)}
            >
              <option value="balanced">Balance price and specifications</option>
              <option value="price">Price first</option>
              <option value="quality">Chef-reviewed quality first</option>
            </select>
          </label>
          <h3>Review the recipe</h3>
          <label>
            Recipe quantities
            <select
              value={form.recipe_source}
              onChange={(e) => update("recipe_source", e.target.value)}
            >
              <option value="proposed">Illustrative proposed recipe</option>
              <option value="customer">My kitchen's quantities</option>
            </select>
          </label>
          <p>
            Grams per diner, before cooking. Beef applies to meat portions; dry
            lentils to vegetarian portions. All other ingredients apply to
            everyone. Water and cooking yields need chef review.
          </p>
          <div className="planner-fields">
            {Object.entries(recipe).map(([key, value]) => (
              <label key={key}>
                {labels[key]} (g)
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  max={
                    key === "salt_g" || key === "oregano_g"
                      ? 10
                      : key === "oil_g"
                        ? 100
                        : 500
                  }
                  value={value}
                  onChange={(e) => {
                    setRecipe((r) => ({ ...r, [key]: Number(e.target.value) }));
                    update("recipe_source", "customer");
                  }}
                />
              </label>
            ))}
          </div>
          <label className="planner-checkbox">
            <input
              type="checkbox"
              checked={form.include_carrot}
              onChange={(e) => update("include_carrot", e.target.checked)}
            />{" "}
            Add carrot to the sauce (30 g per diner)
          </label>
          <p>
            Optional additions are opt-in and need the same dietary review as
            the core ingredients.
          </p>
          {error && (
            <p role="alert" className="planner-error">
              {error}
            </p>
          )}
          <button
            className="primary-button"
            disabled={busy || role === "approver"}
          >
            {busy ? "Planning ingredients…" : "Build shopping plan"}
          </button>
          {role === "approver" && <p>Sign in as buyer to create a plan.</p>}
        </form>
        <div className="planner-results">
          {!plan ? (
            <div className="paper planner-empty">
              <h3>A meal is more than one SKU.</h3>
              <p>
                Get scaled ingredient needs, separate dietary cohorts, and up to
                three catalog candidates per ingredient. The chef chooses
                products after checking purpose and dietary evidence.
              </p>
              <p>
                Planning uses the local challenge catalog. Prices and
                date-specific availability come later; no shared webshop basket
                is changed.
              </p>
            </div>
          ) : (
            <>
              <div className="paper planner-summary">
                <span className="eyebrow">
                  DRAFT SHOPPING PLAN · CHEF REVIEW REQUIRED
                </span>
                <h3>Every diner counted once.</h3>
                <div className="cohort-grid">
                  {Object.entries(plan.cohorts).map(([key, value]) => (
                    <div key={key}>
                      <strong>{value}</strong>
                      <span>{key.replaceAll("_", " ")}</span>
                    </div>
                  ))}
                </div>
                <p>{plan.recipe_note}</p>
                <p>{plan.preference_note}</p>
                {dirty && (
                  <p role="status" className="planner-error">
                    Inputs changed. Rebuild the plan before exporting.
                  </p>
                )}
                <button
                  className="text-button"
                  type="button"
                  disabled={dirty}
                  onClick={download}
                >
                  Export draft shopping plan (JSON) ↗
                </button>
              </div>
              {onQuoteSession && <form className="paper planner-summary planner-quote" onSubmit={quotePlan}>
                <span className="eyebrow">CONTINUE TO THE PURCHASING WORKSPACE</span>
                <h3>Turn this recipe into a quoted basket.</h3>
                <p>Keep your ingredient quantities, dietary groups and selected candidates. The purchasing workspace consolidates shared products, checks prices and availability, and highlights any requirements still unresolved.</p>
                <div className="planner-quote-fields">
                  <label>Requested delivery<input aria-label="Meal plan delivery date" type="date" required value={quoteDate} onChange={(e) => setQuoteDate(e.target.value)} disabled={quoting || dirty} /></label>
                  <label>Maximum budget (€)<input aria-label="Meal plan maximum budget" type="number" min="0" step="0.01" placeholder="Optional" value={quoteBudget} onChange={(e) => setQuoteBudget(e.target.value)} disabled={quoting || dirty} /></label>
                  <label>Quotation source<select value={quoteMode} onChange={(e) => setQuoteMode(e.target.value)} disabled={quoting || dirty}><option value="fixture">Rehearsal fixture · authored prices & stock</option><option value="live">Live Valio sponsor sandbox</option></select></label>
                </div>
                {quoteError && <p className="planner-error" role="alert">{quoteError}</p>}
                <button className="primary-button" type="submit" disabled={dirty || quoting || role === "approver"}>{quoting ? "Checking the shopping plan…" : "Quote this shopping plan"}</button>
                <p>Some or all candidates can remain unselected. You can refine each product search in the purchasing workspace. Recipe and dietary review is still required before simulated confirmation.</p>
              </form>}
              {plan.lines.map((line, i) => (
                <article
                  className="paper ingredient-card"
                  key={line.ingredient}
                >
                  <div className="ingredient-heading">
                    <h3>{line.ingredient}</h3>
                    <strong>
                      {Number(line.required_kg).toLocaleString("en-FI")} kg
                    </strong>
                  </div>
                  <p>
                    {line.servings} portions × {line.grams_per_serving} g.
                    Candidate pack counts are calculated separately; shared SKUs
                    must be consolidated before quoting.
                  </p>
                  {!line.candidates.length && (
                    <p className="planner-error">
                      No catalog match. Find a suitable product with the chef.
                    </p>
                  )}
                  {line.candidates.map((c) => (
                    <label className="candidate-option" key={c.product_id}>
                      <input
                        type="radio"
                        name={`ingredient-${i}`}
                        checked={choices[i] === c.product_id}
                        disabled={dirty || quoting}
                        onChange={() =>
                          setChoices((v) => ({ ...v, [i]: c.product_id }))
                        }
                      />
                      <span>
                        <strong>{c.name}</strong>
                        <small>
                          SKU {c.product_id} ·{" "}
                          {c.quantity_sales_units || "Unknown"} {c.sales_unit} ·{" "}
                          {c.effective_kg
                            ? `${Number(c.effective_kg).toLocaleString("en-FI")} kg after rounding`
                            : "Net mass unknown"}
                        </small>
                        <small>
                          Origin codes: {c.origin_codes.join(", ") || "unknown"}{" "}
                          · Gluten-free claim:{" "}
                          {c.gluten_free_claim ? "present" : "unknown"}
                        </small>
                        <small>
                          Historical delivered quantity:{" "}
                          {c.historical_reliability == null
                            ? "unknown"
                            : `${(c.historical_reliability * 100).toFixed(1)}%`}{" "}
                          · Price / stock: not queried
                        </small>
                        {c.issues.map((issue) => (
                          <small className="planner-error" key={issue}>
                            {issue}
                          </small>
                        ))}
                        <small>
                          Search match only; chef checks ingredient purpose,
                          vegetarian suitability and all dietary requirements.
                        </small>
                      </span>
                    </label>
                  ))}
                </article>
              ))}
              <div className="paper planner-summary">
                <h3>Before this becomes an order</h3>
                <ol>
                  {plan.next_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <p>{plan.reliability_note}</p>
                <p>{plan.boundaries}</p>
              </div>
            </>
          )}
          <div className="paper planner-summary">
            <h3>The B2B purchasing journey</h3>
            <p>
              An existing customer contract comes first. The worker described
              invoices usually being sent after delivery; the customer's actual
              contract determines payment terms.
            </p>
            <p>
              This demo uses a synthetic customer account and produces simulated
              receipts. It does not perform credit checks, create contracts,
              issue invoices or take payment.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
