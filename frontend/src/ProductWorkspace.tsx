import { useEffect, useReducer, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ArrowLeft, ArrowRight, LoaderCircle, Search, X } from "lucide-react";
import "./workspace.css";
import { ProductComparison, CompareControl } from "./ProductComparison";
import { ProductImage } from "./ProductImage";
import { comparisonReducer, emptyComparison, staleComparisonEntry } from "./comparisonSelection";
import type { ProductCandidate, ProductFacts } from "./productPresentation";
import { availabilityLabel, measurementLabel, packageEquation, packageLabel, salesQuantity } from "./productPresentation";

type API = (path: string, options?: RequestInit) => Promise<any>;
export type CatalogProduct = ProductCandidate & ProductFacts;
type Results = { products: CatalogProduct[]; total: number; offset: number; limit: number; has_more: boolean; sort_scope?: "full_filtered_catalog" | "quoted_page"; sort_basis?: string; quote_error?: string | null; applied_filters?: { dietary?: string[]; excluded_ingredients?: string[] }; facets?: { brands?: { value: string; label: string; count: number }[]; categories?: { value: string; label: string; count: number }[] } };
const dietaryLabels: Record<string, string> = { lactose_free: "Lactose-free", milk_free: "Milk / dairy allergy exclusion", gluten_free: "Gluten-free", peanut_free: "Peanut allergy exclusion", nut_free: "Tree nut allergy exclusion", egg_free: "Egg exclusion", soy_free: "Soy exclusion", fish_free: "Fish exclusion", crustacean_free: "Crustacean exclusion", mollusc_free: "Mollusc exclusion", celery_free: "Celery exclusion", mustard_free: "Mustard exclusion", sesame_free: "Sesame exclusion", sulphite_free: "Sulphite exclusion", lupin_free: "Lupin exclusion", vegetarian: "Vegetarian", vegan: "Vegan", no_pork: "No pork", halal: "Verified halal", kosher: "Verified kosher" };
const money = (value: unknown) => value == null ? "Requires quote" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR" }).format(Number(value));
const amount = (value: unknown) => new Intl.NumberFormat("en-FI", { maximumFractionDigits: 3 }).format(Number(value));
export function ProductWorkspace({ api, role, onSignIn, date, mode, disabled, getRequirements, onAdd, onInspect, preferencesVersion = 0, active = true }: {
  api: API; role: string | null; onSignIn: () => void; date: string; mode: string; disabled: boolean;
  getRequirements: () => { date: string; budget: string }; preferencesVersion?: number; active?: boolean;
  onAdd: (id: string, quantity: string, unit: string, applyPreferences?: boolean) => Promise<boolean>;
  onInspect: (product: CatalogProduct, quantity?: string, unit?: string) => void;
}) {
  const [comparison, compareDispatch] = useReducer(comparisonReducer,emptyComparison);
  const [applyPreferences,setApplyPreferences] = useState(false);
  const [sort,setSort] = useState("relevance");
  const [availableOnly,setAvailableOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [brand, setBrand] = useState("");
  const [category, setCategory] = useState("");
  const [origin, setOrigin] = useState("");
  const [dietary, setDietary] = useState("");
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<CatalogProduct | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("packages");
  const [quoted, setQuoted] = useState<CatalogProduct | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [quoteError, setQuoteError] = useState("");
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const selectionRef = useRef<HTMLDivElement>(null);
  function params(q: string, start: number, count = 20, desired = "1", dimension = "packages") {
    const requirements = getRequirements();
    const p = new URLSearchParams({ q, offset: String(start), limit: String(count), mode, quantity: desired, unit: dimension, apply_preferences: String(applyPreferences), sort });
    if (requirements.date) p.set("date", requirements.date);
    return p;
  }
  useEffect(() => {
    if (!role || !active) return;
    const controller = new AbortController();
    const p = params(search, offset);
    if (brand) p.set("brand", brand);
    if (category) p.set("category", category);
    if (origin) p.set("origin", origin);
    if (dietary) p.append("dietary", dietary);
    setLoading(true); setError("");
    api(`/products/search?${p}`, { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) setResults(data); }).catch((e) => { if (!controller.signal.aborted) setError((e as Error).message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, role, search, offset, brand, category, origin, dietary, date, mode, applyPreferences, sort, refresh, preferencesVersion, active]);
  useEffect(() => {
    if (!active) return;
    if (!selected || !quantity || Number(quantity) <= 0) { setQuoted(null); return; }
    const controller = new AbortController();
    setQuoting(true); setQuoted(null); setQuoteError("");
    const timer = window.setTimeout(() => {
      api(`/products/search?${params(selected.id, 0, 1, quantity, unit)}`, { signal: controller.signal })
        .then((data: Results) => { if (controller.signal.aborted) return; const current = data.products.find((product) => product.id === selected.id); setQuoted(current || { ...selected, selectable: false, unit_price: null, line_total: null, quantity_sales_units: null, effective_quantity: null, surplus_quantity: null, available_sales_units: null, availability: "not_queried", delivery_date: null, eligibility_issues: ["This product is not in the current eligible results. Review mandatory restrictions or choose another product."], quote_issues: [], issues: [] }); setQuoteError(data.quote_error || ""); })
        .catch((e) => { if (!controller.signal.aborted) setQuoteError((e as Error).message); })
        .finally(() => { if (!controller.signal.aborted) setQuoting(false); });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [selected?.id, quantity, unit, date, mode, applyPreferences, sort, refresh, preferencesVersion, active]);
  useEffect(() => { compareDispatch({type:"update",entries:comparison.entries.map((entry)=>staleComparisonEntry(entry))}); }, [date,mode,preferencesVersion]);
  function submitSearch(e: FormEvent) { e.preventDefault(); setSearch(query.trim()); setOffset(0); setRefresh((value) => value + 1); }
  function resetFilters() { setBrand(""); setCategory(""); setOrigin(""); setDietary(""); setAvailableOnly(false); setOffset(0); }
  function choose(product: CatalogProduct) { setSelected(product); setQuantity("1"); setUnit("packages"); setNotice(""); window.setTimeout(() => selectionRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0); }
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selected) return;
    const form = new FormData(e.currentTarget);
    setAdding(true); setNotice("");
    try { if (await onAdd(selected.id, String(form.get("quantity")), String(form.get("unit")),applyPreferences)) setNotice(`${selected.name} added to your cart.`); }
    finally { setAdding(false); }
  }
  const product = quoted || selected;
  const blocked = product?.selectable === false;
  const equation = product ? packageEquation(product, unit) : null;
  const filters = [
    { value: category, label: `Category: ${category}`, clear: () => setCategory("") },
    { value: brand, label: `Brand: ${brand}`, clear: () => setBrand("") },
    { value: origin, label: `Origin: ${origin === "finland" ? "Finland" : "EU"}`, clear: () => setOrigin("") },
    { value: dietary, label: dietaryLabels[dietary] || dietary, clear: () => setDietary("") },
    { value: availableOnly ? "available" : "", label: "Available on this page", clear: () => setAvailableOnly(false) },
  ].filter((filter) => filter.value);
  const visibleProducts = results?.products.filter((row)=>!availableOnly || row.availability === "available") || [];
  const appliedDietary = results?.applied_filters?.dietary || [];
  const appliedExclusions = results?.applied_filters?.excluded_ingredients || [];
  return <section className="catalog-workspace" aria-label="Product catalog">
    <form className="catalog-search" onSubmit={submitSearch}><label htmlFor="catalog-query">Search products</label><div><Search size={18} /><input id="catalog-query" type="search" maxLength={500} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Product, brand, category or SKU" /><button type="submit" disabled={loading}>{loading ? <><LoaderCircle className="spin" size={16} />Searching…</> : "Search"}</button></div></form>
    <div className="catalog-view-options"><label>Sort<select value={sort} onChange={(e)=>setSort(e.target.value)}><option value="relevance">Best match</option><option value="name_asc">Name · A to Z</option><option value="name_desc">Name · Z to A</option><option value="price_asc">Sales-unit price · low to high (this page)</option><option value="price_desc">Sales-unit price · high to low (this page)</option><option value="price_kg_asc">Price / kg · low to high (this page)</option><option value="price_kg_desc">Price / kg · high to low (this page)</option><option value="price_l_asc">Price / L · low to high (this page)</option><option value="price_l_desc">Price / L · high to low (this page)</option><option value="delivery_asc">Earliest available date (this page)</option></select></label><label className="catalog-browse-preferences"><input type="checkbox" checked={applyPreferences} onChange={(e)=>{setApplyPreferences(e.target.checked);setOffset(0);}}/>Use saved optional preferences while browsing</label></div>
    <details className="catalog-filters"><summary>Filters{filters.length ? ` (${filters.length})` : ""}</summary><div><label>Category<select value={category} onChange={(e) => { setCategory(e.target.value); setOffset(0); }}><option value="">All categories</option>{results?.facets?.categories?.map((facet) => <option key={facet.value} value={facet.value}>{facet.label} ({facet.count})</option>)}</select></label><label>Brand<select value={brand} onChange={(e) => { setBrand(e.target.value); setOffset(0); }}><option value="">All brands</option>{results?.facets?.brands?.map((facet) => <option key={facet.value} value={facet.value}>{facet.label} ({facet.count})</option>)}</select></label><label>Required origin<select value={origin} onChange={(e) => { setOrigin(e.target.value); setOffset(0); }}><option value="">Any declared origin</option><option value="finland">Finland</option><option value="eu">EU</option></select></label><label>Verified dietary claim<select value={dietary} onChange={(e) => { setDietary(e.target.value); setOffset(0); }}><option value="">Any</option><option value="lactose_free">Lactose-free</option><option value="gluten_free">Gluten-free</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option></select></label><label className="catalog-page-availability"><input type="checkbox" checked={availableOnly} onChange={(e)=>setAvailableOnly(e.target.checked)} />Available on this quoted page</label></div></details>
    {!!filters.length && <div className="catalog-active-filters" aria-label="Active search filters">{filters.map((filter) => <button type="button" key={filter.label} aria-label={`Remove filter ${filter.label}`} onClick={() => { filter.clear(); setOffset(0); }}>{filter.label}<X size={12} aria-hidden="true" /></button>)}<button type="button" className="catalog-reset-filters" onClick={resetFilters}>Reset filters</button></div>}
    {!!(appliedDietary.length || appliedExclusions.length) && <div className="catalog-applied-requirements"><strong>Mandatory food requirements applied</strong><div>{appliedDietary.map((requirement) => <span key={requirement}>{dietaryLabels[requirement] || requirement.replaceAll("_", " ")}</span>)}{appliedExclusions.map((ingredient) => <span key={`ingredient-${ingredient}`}>Exclude {ingredient}</span>)}</div><p>Saved requirements remain active when search filters are reset. Manage them in Buying preferences.</p></div>}
    {!role && <button className="workspace-signin" onClick={onSignIn}>Sign in to search the catalog</button>}
    {loading && !results && <p role="status" className="catalog-loading">Searching products…</p>}
    {error && <p className="workspace-error" role="alert">{error}</p>}
    {results?.quote_error && <p className="workspace-warning" role="status">Prices need a quote: {results.quote_error}</p>}
    <ProductComparison state={comparison} dispatch={compareDispatch} api={api} date={date} mode={mode} applyPreferences={applyPreferences} active={active} disabled={disabled || adding || loading} chooseLabel="Add to cart" onChoose={(entry)=>onAdd(entry.product.id,entry.requestedQuantity || "1",entry.requestedUnit || "packages",applyPreferences)} onDetails={(entry)=>onInspect(entry.product,entry.requestedQuantity,entry.requestedUnit)} />
    {selected && <div ref={selectionRef} className="catalog-selection"><div className="catalog-selection-title"><div><strong>{selected.name}</strong><small>{packageLabel(selected)} · SKU {selected.id}</small></div><button type="button" aria-label="Close product selection" onClick={() => setSelected(null)}><X size={17} /></button></div><form onSubmit={add}><label>Quantity<input name="quantity" type="number" required min="0.001" max="100000" step="0.001" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label><label>Unit<select name="unit" value={unit} onChange={(e) => setUnit(e.target.value)}><option value="packages">{selected.sales_unit === "KG" ? "kg (sales unit)" : "Sales packages"}</option><option value="kg">kg required</option><option value="L">Litres required</option><option value="pieces">Consumer units</option></select></label><div className="catalog-selection-price">{quoting ? <span><LoaderCircle size={14} className="spin" />Checking price…</span> : <><strong>{money(quoted?.line_total)}</strong><small>{quoted?.quantity_sales_units != null ? equation || `${salesQuantity(quoted.quantity_sales_units,quoted.sales_unit)}${quoted.effective_quantity != null && unit !== "packages" ? ` · ${amount(quoted.effective_quantity)} ${measurementLabel(unit)}` : ""}` : "Quantity and price checked when added"}</small></>}</div><button className="catalog-add" type="submit" disabled={disabled || adding || quoting || blocked || role !== "buyer" || !quantity || Number(quantity) <= 0}>{adding ? "Adding…" : "Add to cart"}</button></form>{blocked && <p className="workspace-error">{product?.eligibility_issues?.join(" ") || "This product does not meet your mandatory requirements."}</p>}{!quoting && Boolean(quoteError || quoted?.quote_issues?.length) && <p className="workspace-warning">{quoteError || quoted?.quote_issues?.join(" ")} You can keep an eligible product in the draft; confirmation requires verified pricing and availability.</p>}{notice && <p className="workspace-success" role="status">{notice}</p>}<CompareControl checked={comparison.entries.some((entry)=>entry.key===selected.id)} disabled={disabled || quoting} onToggle={()=>compareDispatch({type:"toggle",entry:{key:selected.id,product:quoted || selected,requestedQuantity:quantity,requestedUnit:unit}})}/><button type="button" className="catalog-details-button" aria-haspopup="dialog" disabled={quoting} onClick={() => onInspect(quoted || selected,quantity,unit)}>Product details</button></div>}
    {results && <div className="catalog-result-summary" role="status">{results.total ? availableOnly ? `${visibleProducts.length} of ${results.products.length} products on this page; ${results.total} catalog matches` : `${offset + 1}–${Math.min(offset + results.products.length, results.total)} of ${results.total} products` : "No matching products"}{loading && <span>Updating…</span>}</div>}
    {results?.sort_scope === "quoted_page" && <p className="catalog-sort-scope">Sorted within this quoted page only · {results.sort_basis}. Unknown values stay last. Use Next to inspect more products.</p>}
    {!!visibleProducts.length && <table className="catalog-table"><thead><tr><th>Product</th><th>Package</th><th>Price / sales unit</th><th>Availability</th><th><span className="sr-only">Selection</span></th></tr></thead><tbody>{visibleProducts.map((row) => <tr className={selected?.id === row.id ? "selected" : ""} key={row.id}><th scope="row"><span className="catalog-product-identity"><ProductImage product={row} small/><span>{row.name}<small>{row.brand || "Brand not supplied"} · SKU {row.id}</small></span></span></th><td data-label="Package">{packageLabel(row)}</td><td data-label="Price">{money(row.unit_price)}<small>/ {row.sales_unit === "KG" ? "kg" : "sales package"}</small></td><td data-label="Availability">{availabilityLabel(row.availability)}{row.delivery_date && <small>{row.delivery_date}</small>}</td><td><CompareControl checked={comparison.entries.some((entry)=>entry.key===row.id)} disabled={disabled} onToggle={()=>compareDispatch({type:"toggle",entry:{key:row.id,product:row,requestedQuantity:row.requested_quantity || "1",requestedUnit:row.pack_unit || "packages"}})}/><button type="button" onClick={() => choose(row)}>{selected?.id === row.id ? "Selected" : "Select"}</button></td></tr>)}</tbody></table>}
    {results && results.total > results.limit && <div className="workspace-pagination"><button type="button" disabled={loading || !offset} onClick={() => setOffset(Math.max(0, offset - results.limit))}><ArrowLeft size={15} />Previous</button><span>Page {Math.floor(offset / results.limit) + 1}</span><button type="button" disabled={loading || !results.has_more} onClick={() => setOffset(offset + results.limit)}>Next<ArrowRight size={15} /></button></div>}
    {results && !visibleProducts.length && <p className="workspace-empty">Try a broader product name{filters.length ? " or reset the search filters" : ""}.{!!(appliedDietary.length || appliedExclusions.length) && " Mandatory requirements exclude products without sufficient evidence."}</p>}
  </section>;
}
