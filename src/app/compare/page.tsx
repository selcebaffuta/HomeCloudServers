import Link from "next/link";

import { ArrowLink } from "@/components/ui/ArrowLink";
import { JsonLd } from "@/components/ui/JsonLd";
import { brand } from "@/config/brand";
import { comparisonRows } from "@/data/features";
import { getProductHref, products } from "@/data/products";
import { createMetadata } from "@/lib/metadata";

import styles from "./page.module.css";

export const metadata = createMetadata({
  title: "Compare models",
  description: `Compare the ${brand.name} Base, Plus and Pro product families without invented specifications or pricing.`,
  path: "/compare",
});

export default function ComparePage() {
  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "ItemList",
          name: `Compare ${brand.name} models`,
          numberOfItems: products.length,
          itemListElement: products.map((product, index) => ({
            "@type": "ListItem",
            position: index + 1,
            name: product.displayName,
          })),
        }}
      />
      <section className={styles.hero}>
        <p className="eyebrow">Find your fit</p>
        <h1>Same cloud.<br />Different presence.</h1>
        <p>Every model starts with the same core personal cloud experience. The difference is how much of that experience lives on the hardware itself.</p>
      </section>

      <section className={styles.comparison} aria-labelledby="comparison-heading">
        <h2 className="sr-only" id="comparison-heading">Product comparison</h2>
        <div className={styles.desktopTable}>
          <table>
            <thead>
              <tr>
                <th scope="col">Capability</th>
                {products.map((product) => (
                  <th key={product.id} scope="col">
                    <span>{product.eyebrow}</span>
                    <strong>{product.shortName}</strong>
                    <Link href={getProductHref(product)}>Explore <span aria-hidden="true">↗</span></Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row) => (
                <tr key={row.label}>
                  <th scope="row">{row.label}</th>
                  {products.map((product) => <td key={product.id}>{row.value(product)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.mobileComparison}>
          {products.map((product) => (
            <article key={product.id}>
              <div className={styles.mobileProductHeader}>
                <div><span>{product.eyebrow}</span><h2>{product.displayName}</h2></div>
                <Link href={getProductHref(product)} aria-label={`Explore ${product.displayName}`}>↗</Link>
              </div>
              <dl>
                {comparisonRows.map((row) => (
                  <div key={row.label}><dt>{row.label}</dt><dd>{row.value(product)}</dd></div>
                ))}
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.note}>
        <div><p className="eyebrow">Specifications with restraint</p><h2>We’ll publish the numbers when they are real.</h2></div>
        <div><p>Storage configurations, memory, processor specifications, availability and pricing are intentionally not listed yet.</p><p>Final combinations may vary by configuration. No purchase is available in this milestone.</p></div>
      </section>

      <section className={styles.closing}>
        <p className="eyebrow">A clear starting point</p>
        <h2>Begin with the essentials.</h2>
        <p>Base contains the complete core experience, without a front display.</p>
        <ArrowLink href={getProductHref(products[0])}>Explore Base</ArrowLink>
      </section>
    </>
  );
}
