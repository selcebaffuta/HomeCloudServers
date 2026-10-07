import { brand } from "@/config/brand";
import { appCategories, setupSteps } from "@/data/features";
import { getProductHref, products } from "@/data/products";
import { ArrowLink } from "@/components/ui/ArrowLink";
import { HomeHero } from "./HomeHero";
import { IntegratedDisplayShowcase } from "./IntegratedDisplayShowcase";
import { ProductFamilySection } from "./ProductFamilySection";

import styles from "./HomePage.module.css";

export function HomePage() {
  return (
    <>
      <HomeHero />

      <section className={`${styles.section} ${styles.ownership}`} id="why">
        <div className={styles.sectionHeading}>
          <p className="eyebrow">A different relationship with the cloud</p>
          <h2>Your cloud, actually yours.</h2>
        </div>
        <div className={styles.principles}>
          <article><span>01</span><h3>At home</h3><p>The device lives where you do, with your storage physically nearby.</p></article>
          <article><span>02</span><h3>In your control</h3><p>You choose what to install and where your information is kept.</p></article>
          <article><span>03</span><h3>Available anywhere</h3><p>Reach what you need through secure remote access when configured.</p></article>
        </div>
      </section>

      <section className={`${styles.section} ${styles.together}`}>
        <div className={styles.togetherCopy}>
          <p className="eyebrow">Made as one system</p>
          <h2>Hardware and software, together.</h2>
          <p>{brand.name} brings storage, useful apps, remote access and backup into one approachable experience.</p>
        </div>
        <div className={styles.systemLine} aria-label={`${brand.name} combines hardware, operating software, apps, remote access and backup`}>
          {[
            ["01", "Hardware", "A dedicated home device"],
            ["02", `${brand.name} interface`, "One clear Web UI"],
            ["03", "Apps", "Tools for everyday needs"],
            ["04", "Remote", "Secure access away from home"],
            ["05", "Backup", "Protection you can understand"],
          ].map(([number, title, detail]) => (
            <div key={title}><span>{number}</span><strong>{title}</strong><small>{detail}</small></div>
          ))}
        </div>
      </section>

      <ProductFamilySection />

      <IntegratedDisplayShowcase />

      <section className={`${styles.section} ${styles.apps}`} id="apps">
        <div className={styles.appsHeading}>
          <div><p className="eyebrow">A platform for useful things</p><h2>More than storage.</h2></div>
          <ArrowLink href="/apps" variant="text">Discover apps</ArrowLink>
        </div>
        <div className={styles.appRail}>
          {appCategories.map((app) => (
            <article key={app.title}><span>{app.code}</span><h3>{app.title}</h3><p>{app.description}</p></article>
          ))}
        </div>
        <p className={styles.appNote}>Categories shown for illustration; no third-party partnerships are implied.</p>
      </section>

      <section className={`${styles.section} ${styles.setup}`}>
        <div className={styles.setupHeading}>
          <p className="eyebrow">Guided from the start</p>
          <h2>From box to cloud,<br />without the terminal.</h2>
          <p>A browser-based onboarding flow walks through each decision, including network setup and the local administrator account.</p>
        </div>
        <ol className={styles.steps}>
          {setupSteps.map(([number, title, detail]) => <li key={number}><span>{number}</span><div><h3>{title}</h3><p>{detail}</p></div></li>)}
        </ol>
      </section>

      <section className={`${styles.section} ${styles.remote}`}>
        <div className={styles.remotePath} aria-hidden="true">
          <div className={styles.pathNode}><span>At home</span><strong>{brand.name}</strong><i /></div>
          <div className={styles.pathLine}><span>Secure remote access</span></div>
          <div className={styles.pathNode}><span>Away</span><strong>Your devices</strong><i /></div>
        </div>
        <div className={styles.remoteCopy}>
          <p className="eyebrow">Secure remote access</p>
          <h2>Home, even when you’re not.</h2>
          <p>When enabled, integrated remote connectivity helps you reach your files and apps away from home without turning the product into a public hosting service.</p>
          <p className={styles.detail}>Remote access depends on configuration, network conditions and supported connectivity technology.</p>
        </div>
      </section>

      <section className={`${styles.section} ${styles.privacy}`}>
        <div>
          <p className="eyebrow">Ownership by design</p>
          <h2>Cloud without giving up the box.</h2>
        </div>
        <ul>
          <li><span>01</span>Storage stays at home</li>
          <li><span>02</span>Local administrator account</li>
          <li><span>03</span>User-controlled hardware</li>
          <li><span>04</span>Encrypted remote connectivity where supported</li>
        </ul>
      </section>

      <section className={styles.closing}>
        <p className="eyebrow">Find your fit</p>
        <h2>One cloud.<br />Three ways to live with it.</h2>
        <div className={styles.actions}>
          <ArrowLink href="/compare">Compare models</ArrowLink>
          <ArrowLink href={getProductHref(products[0])} variant="secondary">Start with Base</ArrowLink>
        </div>
      </section>
    </>
  );
}
