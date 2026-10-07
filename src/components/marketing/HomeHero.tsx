import { ArrowLink } from "@/components/ui/ArrowLink";
import { ProductVisual } from "@/components/products/ProductVisual";
import { brand } from "@/config/brand";
import { products } from "@/data/products";

import styles from "./HomeHero.module.css";

export function HomeHero() {
  const featuredProduct = products[2];

  return (
    <section className={styles.hero}>
      <div className={styles.copy}>
        <p className="eyebrow">Your cloud. At home.</p>
        <h1>Your digital life,<br />where it belongs.</h1>
        <p className={styles.lead}>
          A personal cloud for photos, files, backups and apps—running on dedicated hardware in your home.
        </p>
        <div className={styles.actions}>
          <ArrowLink href="/#products">Explore {brand.name}</ArrowLink>
          <ArrowLink href="/compare" variant="secondary">Compare models</ArrowLink>
        </div>
      </div>
      <div className={styles.visual}>
        <ProductVisual product={featuredProduct} />
        <p className={styles.conceptNote}>Conceptual industrial design · subject to refinement</p>
      </div>
    </section>
  );
}
