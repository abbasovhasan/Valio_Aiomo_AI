import type { ProductCandidate } from "./productPresentation";
export type ComparisonEntry = { key: string; product: ProductCandidate; requestedQuantity?: string; requestedUnit?: string; lineId?: string; contextLabel?: string };
export type ComparisonState = { entries: ComparisonEntry[]; replacement: ComparisonEntry | null };
export const emptyComparison: ComparisonState = { entries: [], replacement: null };
export type ComparisonAction = { type: "toggle"; entry: ComparisonEntry } | { type: "remove"; key: string } | { type: "replace"; key: string } | { type: "cancel" } | { type: "clear" } | { type: "update"; entries: ComparisonEntry[] };
export function comparisonReducer(state: ComparisonState, action: ComparisonAction): ComparisonState {
  if (action.type === "clear") return emptyComparison;
  if (action.type === "cancel") return { ...state, replacement: null };
  if (action.type === "remove") return { ...state, entries: state.entries.filter((entry) => entry.key !== action.key), replacement: null };
  if (action.type === "toggle") {
    if (state.entries.some((entry) => entry.key === action.entry.key)) return { ...state, entries: state.entries.filter((entry) => entry.key !== action.entry.key), replacement: null };
    return state.entries.length < 3 ? { entries: [...state.entries, action.entry], replacement: null } : { ...state, replacement: action.entry };
  }
  if (action.type === "replace") return state.replacement ? { entries: state.entries.map((entry) => entry.key === action.key ? state.replacement! : entry), replacement: null } : state;
  if (action.type === "update") return { ...state, entries: state.entries.map((entry) => action.entries.find((next) => next.key === entry.key) || entry) };
  return state;
}
export function staleComparisonEntry(entry: ComparisonEntry, reason = "Refresh this product's quote before choosing."): ComparisonEntry {
  return { ...entry, product: { ...entry.product, unit_price: null, line_total: null, price_per_requested_unit: null, price_per_kg: null, price_per_litre: null, available_sales_units: null, availability: "unknown", delivery_date: null, quote_issues: [reason] } };
}
