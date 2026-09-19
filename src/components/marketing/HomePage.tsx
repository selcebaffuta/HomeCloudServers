import Link from "next/link";

import { brand } from "@/config/brand";
import { appCategories, setupSteps } from "@/data/features";
import { getProductHref, products } from "@/data/products";
import { ProductVisual } from "@/components/products/ProductVisual";
import { ArrowLink } from "@/components/ui/ArrowLink";

import styles from "./HomePage.module.css";

export function HomePage() {
  const featuredProduct = products[2];

  return (
    <>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className="eyebrow">Your cloud. At home.</p>
          <h1>Your digital life,<br />where it belongs.</h1>
          <p className={styles.lead}>
            A personal cloud designed for photos, files, backups and apps—running on dedicated hardware in your home.
          </p>
          <div className={styles.actions}>
            <ArrowLink href="#products">Explore {brand.name}</ArrowLink>
            <ArrowLink href="/compare" variant="secondary">Compare models</ArrowLink>
          </div>
        </div>
        <div className={styles.heroVisual}>
          <ProductVisual product={featuredProduct} />
          <p className={styles.conceptNote}>Conceptual product visual · final industrial design may change</p>
        </div>
      </section>

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
            ["02", `${brand.shortName} OS`, "One clear Web UI"],
            ["03", "Apps", "Tools for everyday needs"],
            ["04", "Remote", "Secure access away from home"],
            ["05", "Backup", "Protection you can understand"],
          ].map(([number, title, detail]) => (
            <div key={title}><span>{number}</span><strong>{title}</strong><small>{detail}</small></div>
          ))}
        </div>
      </section>

      <section className={`${styles.section} ${styles.products}`} id="products">
        <div className={styles.sectionHeading}>
          <p className="eyebrow">Three ways to make it yours</p>
          <h2>Meet the family.</h2>
          <p>Start with the same core cloud experience. Choose how present you want the hardware to feel.</p>
        </div>
        <div className={styles.productGrid}>
          {products.map((product) => (
            <article className={styles.productCard} key={product.id}>
              <ProductVisual product={product} size="compact" />
              <div className={styles.productCopy}>
                <p className="eyebrow">{product.eyebrow}</p>
                <h3>{product.displayName}</h3>
                <p>{product.description}</p>
                <ul>{product.features.map((feature) => <li key={feature}>{feature}</li>)}</ul>
                <Link href={getProductHref(product)}>Explore {product.shortName} <span aria-hidden="true">↗</span></Link>
              </div>
            </article>
          ))}
        </div>
        <div className={styles.centerAction}><ArrowLink href="/compare" variant="secondary">Compare models</ArrowLink></div>
      </section>

      <section className={`${styles.section} ${styles.displaySection}`}>
        <div className={styles.displayIntro}>
          <p className="eyebrow">Integrated display</p>
          <h2>You shouldn’t need another device to know what your server is doing.</h2>
          <p>Plus and Pro bring the essential state of your cloud onto the device itself—calmly, clearly and only when useful.</p>
        </div>
        <div className={styles.displayDemo}>
          <div className={styles.oledPanel}>
            <div className={styles.oledHeader}><span><i />All systems normal</span><small>10:24</small></div>
            <div className={styles.oledMain}>
              <div className={styles.oledStorage}><span>Storage</span><strong>1.7 TB</strong><small>of available capacity in use</small><i><b /></i></div>
              <div className={styles.oledStatus}><span>Network</span><strong>Connected</strong><small>Remote access ready</small></div>
              <div className={styles.oledApps}><span>Apps</span><div><i>PH</i><i>FS</i><i>ME</i></div><strong>6 active</strong></div>
              <div className={styles.oledStatus}><span>Backup</span><strong>Up to date</strong><small>Last checked today</small></div>
            </div>
          </div>
          <div className={styles.proControls}>
            <div><span>Control Bar</span><p>Contextual touch controls that complement the main display.</p></div>
            <div><span>Rotary control</span><p>A physical control with haptic feedback for deliberate local interaction.</p></div>
          </div>
        </div>
      </section>

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
        <div className={styles.remoteSignal} aria-hidden="true"><span /><span /><span /><i /></div>
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
