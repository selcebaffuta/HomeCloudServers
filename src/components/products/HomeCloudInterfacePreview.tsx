import type { Product } from "@/data/products";
import { brand } from "@/config/brand";

import styles from "./HomeCloudInterfacePreview.module.css";

interface HomeCloudInterfacePreviewProps {
  readonly family: Product["family"];
}

const familyStatus: Record<Product["family"], string> = {
  base: "Web interface",
  plus: "Device display connected",
  pro: "Local controls connected",
};

export function HomeCloudInterfacePreview({ family }: HomeCloudInterfacePreviewProps) {
  return (
    <div className={styles.window} data-family={family} aria-hidden="true">
      <div className={styles.windowBar}>
        <span className={styles.windowControls}><i /><i /><i /></span>
        <span className={styles.address}>{brand.localHostname}</span>
        <span className={styles.connection}><i />Local</span>
      </div>
      <div className={styles.shell}>
        <aside className={styles.sidebar}>
          <strong>HC</strong>
          <span className={styles.activeNav}>Overview</span>
          <span>Storage</span>
          <span>Apps</span>
          <span>Backup</span>
        </aside>
        <div className={styles.content}>
          <div className={styles.heading}>
            <div><small>Good morning</small><strong>Everything looks good.</strong></div>
            <span className={styles.health}><i />Healthy</span>
          </div>
          <div className={styles.metrics}>
            <section className={styles.storage}>
              <span>Storage</span>
              <div><strong>42</strong><small>% used</small></div>
              <i><b /></i>
            </section>
            <section>
              <span>Network</span>
              <strong>Connected</strong>
              <small>Remote access ready</small>
            </section>
            <section>
              <span>Backup</span>
              <strong>Up to date</strong>
              <small>Last checked just now</small>
            </section>
          </div>
          <div className={styles.appsHeading}><strong>Apps</strong><small>4 running</small></div>
          <div className={styles.apps}>
            {["PH", "FS", "ME", "MO"].map((code) => <span key={code}>{code}</span>)}
          </div>
          <div className={styles.familyStatus}><i />{familyStatus[family]}</div>
        </div>
      </div>
    </div>
  );
}
