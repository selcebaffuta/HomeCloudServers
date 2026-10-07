import Link from "next/link";

import type { Product } from "@/data/products";
import { products } from "@/data/products";
import { ArrowLink } from "@/components/ui/ArrowLink";
import { HomeCloudInterfacePreview } from "./HomeCloudInterfacePreview";
import { ProductVisual } from "./ProductVisual";

import styles from "./ProductPage.module.css";

interface ProductPageProps {
  readonly product: Product;
}

export function ProductPage({ product }: ProductPageProps) {
  const siblingProducts = products.filter((item) => item.id !== product.id);

  return (
    <>
      <section className={styles.hero} data-family={product.family}>
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

      <section className={styles.positioning} data-family={product.family}>
        <p className="eyebrow">{product.story.eyebrow}</p>
        <h2>{product.story.headline}</h2>
        <p>{product.story.description}</p>
      </section>

      <section className={styles.capabilities} id="capabilities" data-family={product.family}>
        <div className={styles.capabilitiesHeading}>
          <p className="eyebrow">Core capabilities</p>
          <h2>{product.story.capabilityHeading}</h2>
        </div>
        <ol>
          {product.features.map((feature, index) => (
            <li key={feature}><span>{String(index + 1).padStart(2, "0")}</span><strong>{feature}</strong></li>
          ))}
        </ol>
      </section>

      <section className={styles.detailVisual} data-family={product.family}>
        <div className={styles.detailPanel}>
          <p className="eyebrow">{product.story.interfaceEyebrow}</p>
          <h2>{product.story.interfaceHeading}</h2>
          <p>{product.story.interfaceDescription}</p>
          <HomeCloudInterfacePreview family={product.family} />
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
