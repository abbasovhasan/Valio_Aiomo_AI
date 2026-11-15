import { useState } from "react";
import { Package } from "lucide-react";
import type { ProductCandidate } from "./productPresentation";
export function ProductImage({ product, small = false }: { product: ProductCandidate; small?: boolean }) {
  const [failed, setFailed] = useState(false);
  const facts = product.product_details || product.product;
  const url = facts?.image_status === "verified" && facts.image_url?.startsWith("https://") ? facts.image_url : null;
  return <span className={`product-image ${small ? "is-small" : ""}`}>{url && !failed ? <img src={url} alt={product.name} loading="lazy" onError={() => setFailed(true)} /> : <span role="img" aria-label="No verified product image"><Package size={small ? 23 : 35} aria-hidden="true" /></span>}</span>;
}
