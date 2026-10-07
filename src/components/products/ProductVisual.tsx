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
      aria-hidden="true"
    >
      <div className={styles.stage}>
        <div className={styles.floor} />
        <div className={styles.device}>
          <div className={styles.topEdge} />
          <div className={styles.sideEdge} />
          {hasDisplay ? (
            <div className={styles.screenBezel}>
              <div className={styles.screen}>
                {showInterface && (
                  <div className={styles.screenUi}>
                    <div className={styles.screenTop}>
                      <span className={styles.screenBrand}>{product.shortName}</span>
                      <span className={styles.healthPill}><i />All systems normal</span>
                      <time>10:24</time>
                    </div>
                    <div className={styles.screenContent}>
                      <div className={styles.storageCard}>
                        <span>Storage</span>
                        <strong>42%</strong>
                        <i><span /></i>
                        <small>Space in use</small>
                      </div>
                      <div className={styles.statusStack}>
                        <div><span><i />Network</span><strong>Connected</strong></div>
                        <div><span><i />Backup</span><strong>Up to date</strong></div>
                      </div>
                    </div>
                    <div className={styles.appStrip}>
                      <span>Apps</span>
                      <div><i>PH</i><i>FS</i><i>ME</i></div>
                      <strong>6 active</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className={styles.baseFace}>
              <div className={styles.baseIdentity}>
                <span className={styles.brandGlyph}><i /><i /><b /></span>
                <span><strong>Ready</strong><small>Personal cloud</small></span>
              </div>
              <span className={styles.baseStatus}><i />Online</span>
            </div>
          )}

          {isPro && (
            <div className={styles.controlDeck}>
              <div className={styles.controlBar}>
                <span className={styles.controlActive}><i />Home</span>
                <span><i />Apps</span>
                <span><i />Storage</span>
              </div>
              <div className={styles.rotaryHousing}><div className={styles.rotary}><i /></div></div>
            </div>
          )}

          <span className={styles.familyMark}><i /><i /><b /></span>
          <div className={styles.vents} />
          <div className={styles.productLabel}>{product.displayName}</div>
          <div className={styles.feet}><i /><i /></div>
        </div>
      </div>
    </figure>
  );
}
