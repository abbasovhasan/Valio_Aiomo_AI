export type Nutrient = { id: string; value: string; unit: string; basis_quantity: string; basis_unit: string; precision?: string | null; serving_size?: string | null; serving_unit?: string | null; daily_intake_percent?: string | null };
export type ProductFacts = {
  id?: string; name?: string; brand?: string | null; manufacturer?: string[]; vendor?: string | null;
  category?: string | null; ingredients?: string | null; allergens?: { id?: string; unit?: string; name?: string }[];
  nutrition?: Nutrient[] | null; image_url?: string | null; image_status?: "not_supplied" | "verified" | null; min_storage_temperature?: string | null; max_storage_temperature?: string | null;
  storage?: string | null; temperature_condition?: string | number | null; source?: string; updated_at?: string | null;
  sales_unit?: string; base_unit?: string; base_units_per_sales_unit?: string | null; allowed_lot_size?: string;
  kg_per_sales_unit?: string | null; liters_per_sales_unit?: string | null; pieces_per_sales_unit?: string | null;
  conversion_evidence?: Record<string, string>; conversion_issues?: string[]; reliability?: number | null;
  carbon_group_estimate?: number | null; organic?: boolean | null; organic_evidence?: unknown;
  origin_codes?: string[]; origin_evidence?: string | null; claims?: string[]; certifications?: string[];
};
export type ProductCandidate = {
  id: string; name: string; sales_unit?: string; pack_quantity?: string | null; pack_unit?: string;
  quantity_sales_units?: string | null; effective_quantity?: string | null; requested_quantity?: string | null;
  surplus_quantity?: string | null; unit_price?: string | null; line_total?: string | null; availability?: unknown;
  delivery_date?: string | null; attributes?: Record<string, unknown> | string[]; issues?: unknown[]; source?: string;
  product_details?: ProductFacts; product?: ProductFacts; match_method?: string; match_reason?: string;
  requires_explicit_choice?: boolean; price_per_kg?: string | null; price_per_litre?: string | null; price_per_requested_unit?: string | null; comparison_delta?: string | null;
  comparison_note?: string; available_sales_units?: string | null; issue_codes?: string[];
  eligibility_issues?: string[]; quote_issues?: string[]; selectable?: boolean;
};
export const formatQuantity = (value: unknown) => value == null || value === "" || !Number.isFinite(Number(value)) ? "Unknown" : new Intl.NumberFormat("en-FI", { maximumFractionDigits: 6 }).format(Number(value));
export const formatMoney = (value: unknown) => value == null || value === "" || !Number.isFinite(Number(value)) ? "Requires quote" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR" }).format(Number(value));
export const formatUnitPrice = (value: unknown) => value == null || value === "" || !Number.isFinite(Number(value)) ? "Requires quote" : new Intl.NumberFormat("en-FI", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(Number(value));
export function measurementLabel(unit: string | undefined) {
  return ({ packages: "sales packages", package: "sales package", sales_units: "sales packages", sales_unit: "sales package", kg: "kg", KG: "kg", KGM: "kg", L: "L", LTR: "L", g: "g", GRM: "g", ml: "ml", MLT: "ml", MGM: "mg", E14: "kcal", KJO: "kJ", MC: "MC (unit not verified)", pieces: "consumer units" } as Record<string, string>)[unit || ""] || unit || "units";
}
// Unverified supplier unit codes are retained in Sources, never guessed to mean a package size.
export function salesQuantity(quantity: unknown, unit?: string) {
  const known = ({ KG: "kg", KGM: "kg", L: "L", LTR: "L" } as Record<string, string>)[unit || ""];
  return `${formatQuantity(quantity)} ${known || "sales packages"}`;
}
export function packageLabel(candidate: ProductCandidate, requestedUnit?: string) {
  const p = candidate.product_details || candidate.product || {};
  const dimensions = [
    { value: p.liters_per_sales_unit, unit: "L" },
    { value: p.kg_per_sales_unit, unit: "kg" },
    { value: p.pieces_per_sales_unit, unit: "pieces" },
  ];
  const exact = dimensions.find((entry) => entry.unit === requestedUnit && entry.value != null);
  const value = exact || dimensions.find((entry) => entry.value != null);
  if (value) {
    if (candidate.sales_unit === "KG" && value.unit === "kg" && Number(value.value) === 1) return "Sold by weight (kg)";
    return `${formatQuantity(value.value)} ${measurementLabel(value.unit)} / ${candidate.sales_unit === "KG" ? "kg" : "sales package"}`;
  }
  if (candidate.pack_quantity != null && candidate.pack_unit && !/^(packages?|sales_units?)$/.test(candidate.pack_unit)) return `${formatQuantity(candidate.pack_quantity)} ${measurementLabel(candidate.pack_unit)} / sales package`;
  return "Package conversion not supplied";
}
export function packageEquation(candidate: ProductCandidate, unit?: string): string | null {
  const dimension = unit || candidate.pack_unit;
  if (!dimension || /^(packages?|sales_units?)$/.test(dimension) || candidate.pack_unit !== dimension) return null;
  if (candidate.sales_unit === "KG" && dimension === "kg" && Number(candidate.pack_quantity) === 1) return null;
  if ((candidate.product_details || candidate.product)?.conversion_issues?.length) return null;
  if ([candidate.quantity_sales_units, candidate.pack_quantity, candidate.effective_quantity].some((value) => value == null || value === "" || !Number.isFinite(Number(value)) || Number(value) <= 0)) return null;
  return `${formatQuantity(candidate.quantity_sales_units)} × ${formatQuantity(candidate.pack_quantity)} ${measurementLabel(dimension)} = ${formatQuantity(candidate.effective_quantity)} ${measurementLabel(dimension)}`;
}
export function availabilityLabel(value: unknown) {
  return value === "available" ? "Available" : value === "insufficient" ? "Limited stock" : value === "out_of_stock" ? "Out of stock" : "Stock not verified";
}
export function usefulMatchReason(candidate: ProductCandidate) {
  if (!candidate.match_reason || (!["semantic_expansion", "supplier_substitution"].includes(candidate.match_method || "") && !candidate.requires_explicit_choice)) return null;
  return candidate.match_reason;
}

export function nutritionLabel(item: Nutrient) {
  return `${item.value} ${measurementLabel(item.unit)} / ${item.basis_quantity} ${measurementLabel(item.basis_unit)}${item.precision ? ` (${item.precision.toLowerCase().replaceAll("_"," ")})` : ""}${item.serving_size ? `; serving ${item.serving_size} ${measurementLabel(item.serving_unit || "")}` : ""}${item.daily_intake_percent != null ? `; daily intake ${item.daily_intake_percent}%` : ""}`;
}
export function nutritionName(id: string) {
  return ({"ENER-KJO":"Energy (kJ)","ENER-E14":"Energy (kcal)",FAT:"Fat",FASAT:"Saturated fat",CHOAVL:"Carbohydrate","SUGAR-":"Sugars",FIBTG:"Fibre","PRO-":"Protein",SALTEQ:"Salt",CA:"Calcium",FAMSCIS:"Monounsaturated fat",FAPUCIS:"Polyunsaturated fat",LACS:"Lactose",ID:"Iodine",NA:"Sodium",RIBF:"Riboflavin",VITB12:"Vitamin B12","VITD-":"Vitamin D"} as Record<string,string>)[id] || `Supplier nutrient ${id}`;
}
