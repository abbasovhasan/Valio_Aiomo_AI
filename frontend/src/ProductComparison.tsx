import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Columns3, RefreshCw, X } from "lucide-react";
import { DetailsDialog, allergenName, allergenDeclaration, formatProductOrigin } from "./ProductDetailsDialog";
import { ProductImage } from "./ProductImage";
import type { ComparisonEntry, ComparisonState, ComparisonAction } from "./comparisonSelection";
import { staleComparisonEntry } from "./comparisonSelection";
import { availabilityLabel, formatMoney, formatQuantity, formatUnitPrice, measurementLabel, nutritionLabel, nutritionName, packageLabel, salesQuantity } from "./productPresentation";
import type { ProductCandidate } from "./productPresentation";
import "./comparison.css";

type Props = { state: ComparisonState; dispatch: (action: ComparisonAction) => void; api: (path: string, options?: RequestInit) => Promise<any>; date: string; mode: string; applyPreferences: boolean; disabled?: boolean; onChoose: (entry: ComparisonEntry) => void | Promise<unknown>; onDetails: (entry: ComparisonEntry) => void; chooseLabel: string; active?: boolean };
function attributes(product: ProductCandidate) { return product.attributes && !Array.isArray(product.attributes) ? product.attributes : {}; }
function valueText(value: unknown): string { return value == null || value === "" ? "Unknown" : Array.isArray(value) ? value.length ? value.map(valueText).join(", ") : "Not supplied" : typeof value === "object" ? Object.entries(value).map(([key,v]) => `${key}: ${valueText(v)}`).join("; ") : String(value); }
function facts(entry: ComparisonEntry) { return entry.product.product_details || entry.product.product || {}; }
function claimText(entry: ComparisonEntry) { return valueText(facts(entry).claims || attributes(entry.product).claims).replaceAll("_"," ").toLowerCase(); }
function allergenText(entry: ComparisonEntry) { const allergens = facts(entry).allergens; return allergens?.length ? allergens.map((allergen) => `${allergenName(allergen)}: ${allergenDeclaration(allergen.unit)}`).join("; ") : "Not supplied; absence not established"; }
export function CompareControl({ checked, onToggle, disabled }: { checked: boolean; onToggle: () => void; disabled?: boolean }) { return <label className="product-compare-control"><input type="checkbox" checked={checked} disabled={disabled} onChange={onToggle} />Compare</label>; }
export function ProductComparison({ state, dispatch, api, date, mode, applyPreferences, disabled, onChoose, onDetails, chooseLabel, active = true }: Props) {
  const [open,setOpen] = useState(false);
  const [refreshing,setRefreshing] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(()=>{if(!active){pending.current?.abort();setOpen(false);setRefreshing(false);}},[active]);
  async function refresh(entries = state.entries) {
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    setRefreshing(true);
    dispatch({type:"update",entries:entries.map((entry) => staleComparisonEntry(entry))});
    const next = await Promise.all(entries.map(async (entry) => {
      const params = new URLSearchParams({q:entry.product.id,limit:"1",mode,quantity:entry.requestedQuantity || "1",unit:entry.requestedUnit || "packages",apply_preferences:String(applyPreferences)});
      if (date) params.set("date",date);
      try {
        const response = await api(`/products/search?${params}`,{signal:controller.signal});
        const product = response.products.find((candidate: ProductCandidate) => candidate.id === entry.product.id);
        if (!product) return {...staleComparisonEntry(entry,"Product does not meet the current mandatory browsing requirements."),product:{...staleComparisonEntry(entry).product,selectable:false,eligibility_issues:["Product does not meet the current mandatory requirements."]}};
        const eligibility = entry.lineId ? entry.product.eligibility_issues || [] : [];
        const issues = [...new Set([...(product.eligibility_issues || []),...eligibility])];
        return {...entry,product:{...product,eligibility_issues:issues,selectable:product.selectable !== false && !issues.length}};
      } catch (error) { return staleComparisonEntry(entry,error instanceof Error ? error.message : "Quote unavailable."); }
    }));
    if (!controller.signal.aborted) { dispatch({type:"update",entries:next}); setRefreshing(false); }
  }
  function close() { pending.current?.abort(); setRefreshing(false); setOpen(false); }
  const rows: { label: string; render: (entry: ComparisonEntry) => ReactNode; comparable?: "price_per_kg" | "price_per_litre" }[] = [
    {label:"Brand",render:(entry)=>valueText(facts(entry).brand || attributes(entry.product).brand)},
    {label:"Package",render:(entry)=>packageLabel(entry.product,entry.requestedUnit)},
    {label:"Price / sales unit",render:(entry)=><>{formatMoney(entry.product.unit_price)}<small>{entry.product.sales_unit === "KG" ? "per kg" : "per sales package"}</small></>},
    {label:"Price / kg",render:(entry)=>entry.product.price_per_kg == null ? "Not established" : formatUnitPrice(entry.product.price_per_kg),comparable:"price_per_kg"},
    {label:"Price / L",render:(entry)=>entry.product.price_per_litre == null ? "Not established" : formatUnitPrice(entry.product.price_per_litre),comparable:"price_per_litre"},
    {label:"Requested quantity",render:(entry)=>`${formatQuantity(entry.requestedQuantity || "1")} ${(!entry.requestedUnit || entry.requestedUnit === "packages") && entry.product.sales_unit === "KG" ? "kg (sales unit)" : measurementLabel(entry.requestedUnit || "packages")}`},
    {label:"Order quantity",render:(entry)=>entry.product.quantity_sales_units == null ? "Unknown" : salesQuantity(entry.product.quantity_sales_units,entry.product.sales_unit)},
    {label:"Item subtotal",render:(entry)=>formatMoney(entry.product.line_total)},
    {label:"Price & stock source",render:(entry)=>entry.product.source === "authored_fixture" ? "Sample prices & stock" : entry.product.source === "live_valio_sandbox" ? "Live Valio challenge sandbox" : "Not quoted"},
    {label:"Availability",render:(entry)=>availabilityLabel(entry.product.availability)},
    {label:"Available quantity",render:(entry)=>entry.product.available_sales_units == null || !["available","insufficient","out_of_stock"].includes(String(entry.product.availability)) ? "Unknown" : salesQuantity(entry.product.available_sales_units,entry.product.sales_unit)},
    {label:"Estimated date",render:(entry)=>entry.product.delivery_date || "Not verified"},
    {label:"Declared origin",render:(entry)=>formatProductOrigin(facts(entry).origin_codes || attributes(entry.product).origin_codes)},
    {label:"Dietary claims",render:claimText},
    {label:"Ingredients",render:(entry)=>valueText(facts(entry).ingredients)},
    {label:"Allergen evidence",render:allergenText},
    {label:"Nutrition",render:(entry)=>facts(entry).nutrition?.length ? <dl className="comparison-nutrition">{facts(entry).nutrition!.map((item,index)=><div key={`${item.id}-${index}`}><dt>{nutritionName(item.id)}</dt><dd>{nutritionLabel(item)}</dd></div>)}</dl> : "Not supplied"},
  ];
  return <div className="comparison-workspace">
    {state.entries.length > 0 && <div className="comparison-tray"><div>{state.entries.map((entry)=><span key={entry.key}><span className="comparison-chip-name" title={entry.product.name}>{entry.product.name}</span><button type="button" aria-label={`Remove ${entry.product.name} from comparison`} onClick={()=>dispatch({type:"remove",key:entry.key})}><X size={13}/></button></span>)}</div><button type="button" className="comparison-open" disabled={disabled || state.entries.length < 2} onClick={()=>{setOpen(true);void refresh();}}><Columns3 size={16}/>Compare ({state.entries.length})</button><button type="button" disabled={disabled} onClick={()=>dispatch({type:"clear"})}>Clear comparison</button></div>}
    {state.replacement && <div className="comparison-replace" role="status"><strong>Replace a compared product with {state.replacement.product.name}</strong><div>{state.entries.map((entry)=><button type="button" key={entry.key} onClick={()=>dispatch({type:"replace",key:entry.key})}>Replace {entry.product.name}</button>)}<button type="button" onClick={()=>dispatch({type:"cancel"})}>Cancel</button></div></div>}
    {open && <DetailsDialog kind="comparison" title={`Compare ${state.entries.length} products`} onClose={close}><div className="comparison-toolbar"><p>Compare supplied facts. Different products and order quantities may not be substitutes. Unknown values are not equivalent.</p><button type="button" disabled={refreshing || disabled || !state.entries.length} onClick={()=>void refresh()}><RefreshCw size={15}/>{refreshing ? "Checking quotes…" : "Refresh quotes"}</button></div>{state.entries.length < 2 && <p className="comparison-note">{state.entries.length ? "Keep this product and select another from the results to compare." : "Select products from the results to compare."}</p>}<div className="comparison-scroll" tabIndex={0} aria-label="Product comparison, scroll horizontally"><table className="comparison-table" style={{"--columns":Math.max(1,state.entries.length)} as CSSProperties}><thead><tr><th scope="col">Product</th>{state.entries.map((entry)=><th scope="col" key={entry.key}><ProductImage product={entry.product}/><strong>{entry.product.name}</strong><small>SKU {entry.product.id}{entry.contextLabel && ` · ${entry.contextLabel}`}</small><div><button type="button" aria-label={`Remove ${entry.product.name} from comparison`} onClick={()=>dispatch({type:"remove",key:entry.key})}>Remove</button><button type="button" aria-label={`Change ${entry.product.name} in comparison`} onClick={()=>{close();dispatch({type:"remove",key:entry.key});}}>Change</button><button type="button" onClick={()=>{close();onDetails(entry);}}>Details</button></div></th>)}</tr></thead><tbody>{rows.map((row)=>{
      const comparable = row.comparable;
      const prices = comparable ? state.entries.map((entry)=>entry.product[comparable]) : [];
      const complete = prices.length >= 2 && prices.every((value)=>value != null && Number.isFinite(Number(value)));
      const lowest = complete ? Math.min(...prices.map(Number)) : null;
      return <tr key={row.label}><th scope="row">{row.label}</th>{state.entries.map((entry)=><td className={lowest != null && comparable && Number(entry.product[comparable]) === lowest ? "comparison-lowest" : ""} key={entry.key}>{row.render(entry)}</td>)}</tr>;
    })}<tr><th scope="row">Choose</th>{state.entries.map((entry)=><td key={entry.key}>{entry.product.eligibility_issues?.length ? <p>{entry.product.eligibility_issues.join(" ")}</p> : entry.product.quote_issues?.length ? <p>{entry.product.quote_issues.join(" ")}</p> : null}<button className="comparison-choose" type="button" disabled={disabled || refreshing || entry.product.selectable === false} onClick={()=>{close();void onChoose(entry);}}>{chooseLabel}</button></td>)}</tr></tbody></table></div><p className="comparison-note">Tax included; delivery and service charges excluded. Highlights require a supplied common measurement basis. Unlisted allergens remain unknown; lactose-free is not milk-allergy safe. Choosing rechecks the cart.</p></DetailsDialog>}
  </div>;
}
