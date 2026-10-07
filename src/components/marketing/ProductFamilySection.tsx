import Link from "next/link";

import { ProductVisual } from "@/components/products/ProductVisual";
import { ArrowLink } from "@/components/ui/ArrowLink";
import { getProductHref, products } from "@/data/products";

import styles from "./ProductFamilySection.module.css";

export function ProductFamilySection() {
  return (
    <section className={styles.section} id="products">
      <div className={styles.heading}>
        <p className="eyebrow">One family, three levels of presence</p>
        <h2>Meet the family.</h2>
        <p>The same core personal cloud, with progressively richer ways to see and control it at home.</p>
      </div>
      <div className={styles.grid}>
        {products.map((product) => (
          <article className={styles.showcase} key={product.id}>
            <ProductVisual product={product} size="compact" />
            <div className={styles.copy}>
              <p className="eyebrow">{product.eyebrow}</p>
              <h3>{product.displayName}</h3>
              <strong>{product.familyLine}</strong>
              <p>{product.description}</p>
              <ul>{product.highlights.map((feature) => <li key={feature}>{feature}</li>)}</ul>
              <Link href={getProductHref(product)}>Explore {product.shortName} <span aria-hidden="true">↗</span></Link>
            </div>
          </article>
        ))}
      </div>
      <div className={styles.compare}><ArrowLink href="/compare" variant="secondary">Compare models</ArrowLink></div>
    </section>
  );
}
