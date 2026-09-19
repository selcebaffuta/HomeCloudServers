import type { Product } from "@/data/products";

import styles from "./ProductVisual.module.css";

interface ProductVisualProps {
  readonly product: Pick<Product, "displayName" | "shortName" | "visual">;
  readonly size?: "compact" | "hero";
  readonly showInterface?: boolean;
}

export function ProductVisual({ product, size = "hero", showInterface = true }: ProductVisualProps) {
  const hasDisplay = product.visual !== "headless";
  const isPro = product.visual === "control";

  return (
    <figure
      className={`${styles.visual} ${styles[size]} ${styles[product.visual]}`}
      aria-label={`Abstract visual representation of ${product.displayName}`}
    >
      <div className={styles.stage}>
        <div className={styles.shadow} />
        <div className={styles.device}>
          <div className={styles.topEdge} />
          {hasDisplay ? (
            <div className={styles.screen}>
              {showInterface && (
                <div className={styles.screenUi}>
                  <div className={styles.screenTop}>
                    <span className={styles.statusDot} />
                    <b>All systems normal</b>
                    <span className={styles.screenTime}>10:24</span>
                  </div>
                  <div className={styles.screenGrid}>
                    <div className={styles.storageCard}>
                      <span>Storage</span>
                      <strong>42%</strong>
                      <i><span /></i>
                    </div>
                    <div className={styles.appsCard}>
                      <span>Apps</span>
                      <strong>6 active</strong>
                      <div><i /><i /><i /></div>
                    </div>
                    <div className={styles.miniStatus}><span />Network</div>
                    <div className={styles.miniStatus}><span />Backup</div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className={styles.frontMark}><span /><span /><i /></div>
          )}

          {isPro && (
            <>
              <div className={styles.controlBar}>
                <span className={styles.controlActive} />
                <span />
                <span />
                <span />
              </div>
              <div className={styles.rotary}><i /></div>
            </>
          )}

          <div className={styles.vent} />
          <div className={styles.productLabel}>{product.shortName}</div>
        </div>
      </div>
      <figcaption className="sr-only">
        Conceptual hardware mockup. Final industrial design may change.
      </figcaption>
    </figure>
  );
}
