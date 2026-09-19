import Link from "next/link";

import type { Product } from "@/data/products";
import { products } from "@/data/products";
import { ArrowLink } from "@/components/ui/ArrowLink";
import { ProductVisual } from "./ProductVisual";

import styles from "./ProductPage.module.css";

interface ProductPageProps {
  readonly product: Product;
}

export function ProductPage({ product }: ProductPageProps) {
  const siblingProducts = products.filter((item) => item.id !== product.id);

  return (
    <>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className="eyebrow">{product.eyebrow}</p>
          <h1>{product.displayName}</h1>
          <p>{product.longDescription}</p>
          <div className={styles.actions}>
            <ArrowLink href="/compare">Compare models</ArrowLink>
            <ArrowLink href="#capabilities" variant="secondary">See capabilities</ArrowLink>
          </div>
        </div>
        <div>
          <ProductVisual product={product} />
          <p className={styles.conceptNote}>Conceptual product visual · final industrial design may change</p>
        </div>
      </section>

      <section className={styles.positioning}>
        <p className="eyebrow">Designed for real life</p>
        <h2>{product.description}</h2>
        <p>{product.idealFor}.</p>
      </section>

      <section className={styles.capabilities} id="capabilities">
        <div className={styles.capabilitiesHeading}>
          <p className="eyebrow">Core capabilities</p>
          <h2>Everything essential,<br />nothing in the way.</h2>
        </div>
        <ol>
          {product.features.map((feature, index) => (
            <li key={feature}><span>{String(index + 1).padStart(2, "0")}</span><strong>{feature}</strong></li>
          ))}
        </ol>
      </section>

      <section className={styles.detailVisual}>
        <div className={styles.detailPanel}>
          <p className="eyebrow">One unified interface</p>
          <h2>The device and the Web UI speak the same language.</h2>
          <p>System health, storage, apps, network and backup are organized around clear status—not server administration jargon.</p>
          <div className={styles.miniDashboard} aria-label="Conceptual Web UI status panel">
            <div className={styles.dashboardHeader}><span><i />All systems normal</span><small>Updated now</small></div>
            <div className={styles.dashboardBody}>
              <div><span>Storage</span><strong>42%</strong><i><b /></i></div>
              <div><span>Network</span><strong>Connected</strong><small>Remote access ready</small></div>
              <div><span>Backup</span><strong>Up to date</strong><small>No action needed</small></div>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.moreProducts}>
        <div><p className="eyebrow">The family</p><h2>Need a different fit?</h2></div>
        <div className={styles.siblingLinks}>
          {siblingProducts.map((item) => (
            <Link href={`/products/${item.slug}`} key={item.id}>
              <span>{item.eyebrow}</span><strong>{item.displayName}</strong><i aria-hidden="true">↗</i>
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.closing}>
        <p className="eyebrow">Choose with confidence</p>
        <h2>See how every model compares.</h2>
        <p>Pricing, final configurations and availability will be published when they are ready.</p>
        <ArrowLink href="/compare">Compare all models</ArrowLink>
      </section>
    </>
  );
}
