import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import type { ProductCandidate } from "./productPresentation";
import { ProductImage } from "./ProductImage";
import { availabilityLabel, formatMoney, formatUnitPrice, formatQuantity, measurementLabel, nutritionLabel, nutritionName, packageEquation, packageLabel, salesQuantity } from "./productPresentation";
import "./product-details.css";

export function DetailsDialog({ title, subtitle, onClose, children, kind = "product", closeLabel }: { title: string; subtitle?: string; onClose: () => void; children: ReactNode; kind?: "product" | "details" | "cart" | "comparison"; closeLabel?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const root = document.documentElement;
    const previousOverflow = root.style.overflow;
    const previousGutter = root.style.scrollbarGutter;
    if (kind === "details") {
      // Keep the comparison's scroll position and width while its detail sheet is modal.
      if (window.innerWidth > root.clientWidth) root.style.scrollbarGutter = "stable";
      root.style.overflow = "hidden";
    }
    element?.showModal();
    return () => {
      element?.close();
      if (kind === "details") { root.style.overflow = previousOverflow; root.style.scrollbarGutter = previousGutter; }
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, [kind]);
  return <dialog ref={dialog} className={`product-dialog ${kind === "details" ? "product-details-sheet" : kind === "cart" ? "cart-dialog" : kind === "comparison" ? "comparison-dialog" : ""}`} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); onClose(); }} onClick={(event) => { if (event.target === event.currentTarget) { const r = event.currentTarget.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) onClose(); } }}>
    <header className="product-dialog-header"><div><h2 id={titleId}>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button type="button" autoFocus aria-label={closeLabel || (kind === "cart" ? "Close cart" : kind === "comparison" ? "Close comparison" : "Close product details")} onClick={onClose}><X size={20} /></button></header>
    <div className="product-dialog-content">{children}</div>
  </dialog>;
}
const regionCodes: Record<string, string> = { "040":"AT","056":"BE","100":"BG","191":"HR","196":"CY","203":"CZ","208":"DK","233":"EE","246":"FI","250":"FR","276":"DE","300":"GR","348":"HU","372":"IE","380":"IT","428":"LV","440":"LT","442":"LU","470":"MT","528":"NL","616":"PL","620":"PT","642":"RO","703":"SK","705":"SI","724":"ES","752":"SE" };
const allergens: Record<string, string> = { AM:"Milk", AP:"Peanuts", AN:"Tree nuts", AE:"Eggs", AY:"Soy", AF:"Fish", AC:"Crustaceans", UM:"Molluscs", BC:"Celery", BM:"Mustard", AS:"Sesame", AU:"Sulphites", NL:"Lupin", AW:"Gluten-containing cereals", PO:"Pork" };
const declarations: Record<string, string> = { CONTAINS: "Contains", MAY_CONTAIN: "May contain", FREE_FROM: "Declared free from", UNDECLARED: "Not declared" };
function text(value: unknown): string { return value == null || value === "" ? "Not supplied" : Array.isArray(value) ? value.length ? value.map(text).join(", ") : "Not supplied" : typeof value === "object" ? Object.entries(value).map(([key, v]) => `${key}: ${text(v)}`).join("; ") : String(value); }
export function formatProductOrigin(value: unknown) { return Array.isArray(value) && value.length ? value.map((code) => { const raw = String(code), iso = regionCodes[raw] || (/^[A-Z]{2}$/.test(raw) ? raw : null); try { return iso ? `${new Intl.DisplayNames(["en"],{type:"region"}).of(iso)} (${raw})` : `Supplier code ${raw}`; } catch { return `Supplier code ${raw}`; } }).join(", ") : "Not supplied"; }
function date(value?: string | null) { if (!value) return "Not verified"; const parsed = new Date(value.length === 10 ? value + "T12:00:00+02:00" : value); return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle:"medium", timeZone:"Europe/Helsinki", ...(value.length > 10 ? {timeStyle:"short" as const} : {}) }).format(parsed); }
export function allergenName(value: {name?:string;id?:string}) { return value.name || allergens[value.id || ""] || `Supplier allergen ${value.id || "unknown"}`; }
export function allergenDeclaration(value?:string) { return declarations[value || ""] || (value ? value.replaceAll("_"," ").toLowerCase() : "Relationship not supplied"); }
function Rows({ entries }: { entries: [string, ReactNode][] }) { return <dl className="product-detail-rows">{entries.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>; }
export function ProductEvidence({ candidate, requestedQuantity, requestedUnit }: { candidate: ProductCandidate; requestedQuantity?: string; requestedUnit?: string }) {
  const product = candidate.product_details || candidate.product || {};
  const attributes = candidate.attributes && !Array.isArray(candidate.attributes) ? candidate.attributes : {};
  const unit = requestedUnit || candidate.pack_unit;
  const equation = packageEquation(candidate, unit);
  const quantityUnit = unit === "packages" && candidate.sales_unit === "KG" ? "kg (sales unit)" : measurementLabel(unit);
  const priceUnit = candidate.sales_unit === "KG" ? "kg" : "sales package";
  const claims = product.claims || attributes.claims;
  const consumerCount = unit === "pieces" || (product.pieces_per_sales_unit != null && product.liters_per_sales_unit == null && product.kg_per_sales_unit == null);
  const issues = [...new Set([...(candidate.issues || []).map(text), ...(product.conversion_issues || [])])];
  return <div className="product-evidence">
    {issues.length > 0 && <div className="product-detail-warning"><strong>Review before choosing</strong><ul>{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></div>}
    <section><h3>Overview</h3><Rows entries={[["Brand", text(product.brand || attributes.brand)], [candidate.sales_unit === "KG" ? "Sold as" : "Per sales package", packageLabel(candidate, unit)], [`Price / ${priceUnit}`, formatMoney(candidate.unit_price)], ...(candidate.price_per_requested_unit != null && unit && !(candidate.sales_unit === "KG" && unit === "kg") ? [[`Price / ${measurementLabel(unit)}`,formatUnitPrice(candidate.price_per_requested_unit)] as [string,ReactNode]] : []), ["Item subtotal", formatMoney(candidate.line_total)]]} /></section>
    <section><h3>Purchasing</h3>{consumerCount && <p className="product-detail-note">Consumer units are the supplied base units, not individual contents inside a package.</p>}{equation && <p className="product-package-equation">{equation}</p>}<Rows entries={[["Requested", requestedQuantity || candidate.requested_quantity ? `${formatQuantity(requestedQuantity || candidate.requested_quantity)} ${quantityUnit}` : "Not specified"], ["Order quantity", candidate.quantity_sales_units == null ? "Conversion not established" : salesQuantity(candidate.quantity_sales_units,candidate.sales_unit)], ["Quantity after rounding", candidate.effective_quantity == null ? "Unknown" : `${formatQuantity(candidate.effective_quantity)} ${quantityUnit}`], ["Surplus", candidate.surplus_quantity == null ? "Unknown" : `${formatQuantity(candidate.surplus_quantity)} ${quantityUnit}`], ...(candidate.comparison_delta != null ? [["Basket change",formatMoney(candidate.comparison_delta)] as [string,ReactNode]] : []), ["Availability", availabilityLabel(candidate.availability)], ["Verified available quantity", candidate.available_sales_units == null || !["available", "insufficient", "out_of_stock"].includes(String(candidate.availability)) ? "Unknown" : salesQuantity(candidate.available_sales_units,candidate.sales_unit)], ["Estimated available date", date(candidate.delivery_date)]]} />{candidate.comparison_note && <p className="product-detail-note">{candidate.comparison_note}</p>}</section>
    <section><h3>Specifications</h3><Rows entries={[["Manufacturer",text(product.manufacturer)], ["Declared origin",formatProductOrigin(product.origin_codes || attributes.origin_codes)], ["Dietary claims",text(claims).replaceAll("_"," ").toLowerCase()], ...(product.certifications?.length ? [["Catalog certifications",product.certifications.map((value) => ({HALAL:"Halal",KOSHER:"Kosher",NO_PORK:"No pork claim"} as Record<string,string>)[value] || value).join(", ")] as [string,ReactNode]] : []), ["Organic",product.organic === true ? "Verified catalog classification" : "Not established"], ...(product.organic_evidence ? [["Organic evidence",text(product.organic_evidence)] as [string,ReactNode]] : []), ["Storage",text(product.storage)], ...(product.min_storage_temperature != null ? [["Minimum storage temperature",`${formatQuantity(product.min_storage_temperature)} °C`] as [string,ReactNode]] : []), ...(product.max_storage_temperature != null ? [["Maximum storage temperature",`${formatQuantity(product.max_storage_temperature)} °C`] as [string,ReactNode]] : []), ...(product.temperature_condition != null ? [["Temperature-condition code",text(product.temperature_condition)] as [string,ReactNode]] : []), ["Base units / sales unit", product.base_units_per_sales_unit == null ? "Unknown" : `${formatQuantity(product.base_units_per_sales_unit)} base units`], ["Historical delivered quantity",product.reliability == null ? "Unknown" : `${formatQuantity(product.reliability * 100)}% of ordered quantity`]]} /><p className="product-detail-note">Historical delivered quantity is not an on-time probability or a delivery guarantee. Follow supplied storage instructions; a supplier temperature code alone is not a temperature requirement.</p></section>
    <section><h3>Ingredients & allergens</h3><p className="product-ingredients">{product.ingredients || "Ingredient information was not supplied."}</p>{product.allergens?.length ? <ul className="product-allergen-list">{product.allergens.map((allergen,index) => <li key={`${allergen.id}-${allergen.unit}-${index}`} data-declaration={allergen.unit}><strong>{allergen.name || allergens[allergen.id || ""] || "Supplier allergen"}{allergen.id && <small> ({allergen.id})</small>}</strong><span>{declarations[allergen.unit || ""] || (allergen.unit ? allergen.unit.replaceAll("_"," ").toLowerCase() : "Relationship not supplied")}</span></li>)}</ul> : <p className="product-detail-note">No allergen classification supplied. This does not establish allergen absence.</p>}<p className="product-food-warning">Lactose-free does not mean milk-allergy safe. Unlisted or undeclared allergens remain unknown. Check ingredients and kitchen preparation needs.</p></section>
    {product.nutrition?.length ? <section><h3>Nutritional information</h3><Rows entries={product.nutrition.map((item) => [nutritionName(item.id),nutritionLabel(item)])} /></section> : null}
    <section><h3>Sources & package evidence</h3><Rows entries={[["Product catalog",product.source || "Supplied challenge catalog"], ["Supplier category code",text(product.category)], ["Supplier order increment",product.allowed_lot_size == null ? "Unknown" : `${formatQuantity(product.allowed_lot_size)} supplier sales units`], ["Catalog updated",date(product.updated_at)], ...(product.origin_evidence ? [["Origin evidence",product.origin_evidence] as [string,ReactNode]] : []), ["Price & stock",candidate.source === "authored_fixture" ? "Authored rehearsal prices and stock" : candidate.source === "live_valio_sandbox" ? "Live Valio challenge sandbox" : candidate.source || "Not queried"], ["Supplier sales-unit code",text(product.sales_unit || candidate.sales_unit)], ["Supplier base-unit code",text(product.base_unit)]]} />{product.conversion_evidence && Object.entries(product.conversion_evidence).map(([dimension,evidence]) => <p className="product-conversion-evidence" key={dimension}><strong>{measurementLabel(dimension)}</strong><span>{evidence}</span></p>)}{product.carbon_group_estimate != null && <p className="product-detail-note">Category-average carbon estimate: {formatQuantity(product.carbon_group_estimate)} kg CO₂-eq / kg. This is not a product-specific measurement or a measured saving.</p>}</section>
  </div>;
}
export function ProductDetailsDialog({ candidate, requestedQuantity, requestedUnit, onClose }: { candidate: ProductCandidate; requestedQuantity?: string; requestedUnit?: string; onClose: () => void }) {
  const [failedImage, setFailedImage] = useState<string | null>(null);
  const facts = candidate.product_details || candidate.product;
  const imageUrl = facts?.image_status === "verified" && facts.image_url?.startsWith("https://") ? facts.image_url : null;
  return <DetailsDialog kind="details" title="Product details" subtitle={`SKU ${candidate.id}`} onClose={onClose}><p className="product-details-name">{candidate.name}</p>{imageUrl && imageUrl !== failedImage && <div className="product-details-photo" onErrorCapture={() => setFailedImage(imageUrl)}><ProductImage product={candidate} /></div>}<ProductEvidence candidate={candidate} requestedQuantity={requestedQuantity} requestedUnit={requestedUnit} /></DetailsDialog>;
}
