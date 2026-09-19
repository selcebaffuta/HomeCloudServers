import { ArrowLink } from "@/components/ui/ArrowLink";
import { brand } from "@/config/brand";
import { appCategories } from "@/data/features";
import { createMetadata } from "@/lib/metadata";

import styles from "./page.module.css";

export const metadata = createMetadata({
  title: "Apps",
  description: `Explore the kinds of applications that can make ${brand.name} more than storage.`,
  path: "/apps",
});

export default function AppsPage() {
  return (
    <>
      <section className={styles.hero}>
        <div>
          <p className="eyebrow">Apps on your terms</p>
          <h1>More than<br />storage.</h1>
        </div>
        <p>Turn dedicated hardware into a useful home platform. Browse applications in the device Web UI, understand what they need, and decide what belongs on your cloud.</p>
      </section>

      <section className={styles.catalog} aria-labelledby="catalog-title">
        <div className={styles.catalogHeading}>
          <p className="eyebrow">Explore possibilities</p>
          <h2 id="catalog-title">A place for the tools you use.</h2>
        </div>
        <div className={styles.grid}>
          {appCategories.map((app, index) => (
            <article key={app.title}>
              <div className={styles.categoryTop}><span>{app.code}</span><small>{String(index + 1).padStart(2, "0")}</small></div>
              <div><h3>{app.title}</h3><p>{app.description}</p></div>
            </article>
          ))}
        </div>
        <p className={styles.disclaimer}>These are app categories, not announced integrations or partnerships. Specific availability will depend on the supported catalog.</p>
      </section>

      <section className={styles.experience}>
        <div className={styles.experienceCopy}>
          <p className="eyebrow">A guided app experience</p>
          <h2>Install with context, not commands.</h2>
          <p>The future app catalog is designed to show requirements, permissions and device compatibility before installation. Management stays in the local Web UI.</p>
        </div>
        <div className={styles.appWindow} aria-label="Conceptual local app catalog interface">
          <div className={styles.windowTop}><span /><span /><span /><small>Local app catalog</small></div>
          <div className={styles.windowBody}>
            <aside><strong>Apps</strong><span>Installed</span><span>Discover</span><span>Updates</span></aside>
            <div className={styles.windowContent}>
              <div className={styles.windowHeading}><div><small>Discover</small><strong>Useful at home</strong></div><i>Search apps</i></div>
              {["Photo library", "File sync", "Monitoring"].map((name, index) => (
                <div className={styles.appRow} key={name}><span>{appCategories[index].code}</span><div><strong>{name}</strong><small>Ready for your device</small></div><b>View</b></div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className={styles.boundary}>
        <p className="eyebrow">This milestone</p>
        <h2>The public site explains apps. Your device manages them.</h2>
        <p>There is no remote installation from this website, no public account, and no connection to your home device in this version.</p>
      </section>

      <section className={styles.closing}>
        <p className="eyebrow">Choose the hardware experience</p>
        <h2>Every model is built for apps.</h2>
        <ArrowLink href="/compare">Compare models</ArrowLink>
      </section>
    </>
  );
}
