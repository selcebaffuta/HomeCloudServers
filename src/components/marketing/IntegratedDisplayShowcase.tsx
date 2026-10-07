import { brand } from "@/config/brand";

import styles from "./IntegratedDisplayShowcase.module.css";

export function IntegratedDisplayShowcase() {
  return (
    <section className={styles.section}>
      <div className={styles.intro}>
        <p className="eyebrow">Integrated display</p>
        <h2>You shouldn’t need another device to know what your server is doing.</h2>
        <p>Plus and Pro bring essential status onto the hardware itself—calmly, clearly and only when useful.</p>
        <dl>
          <div><dt>Plus</dt><dd>Glanceable local status</dd></div>
          <div><dt>Pro</dt><dd>OLED, Control Bar and rotary input</dd></div>
        </dl>
      </div>
      <div className={styles.hardware} aria-hidden="true">
        <div className={styles.screenFrame}>
          <div className={styles.screen}>
            <header><strong>{brand.name} <small>PLUS</small></strong><span><i />Online</span><time>10:24</time></header>
            <div className={styles.pageHeading}><span>Local display</span><strong>Your {brand.name}</strong><b><i />All systems normal</b></div>
            <div className={styles.statusGrid}>
              <div className={styles.storage}><span>Storage</span><strong>42%</strong><i><b /></i><small>Space in use</small></div>
              <div><span>Network</span><strong>Connected</strong><small>{brand.localHostname}</small></div>
              <div><span>Backup</span><strong>Up to date</strong><small>Checked today</small></div>
              <div><span>Apps</span><strong>6 active</strong><small>All running normally</small></div>
            </div>
            <div className={styles.installedApps}><span>Installed apps</span><div><i>PH</i><i>FS</i><i>ME</i></div></div>
          </div>
          <span className={styles.hardwareLabel}>Integrated Display</span>
          <i className={styles.hardwareVent} />
        </div>
        <div className={styles.controlPreview}>
          <div className={styles.bar}><span className={styles.active}>Home</span><span>Apps</span><span>Storage</span></div>
          <div className={styles.knob}><i /></div>
        </div>
      </div>
    </section>
  );
}
