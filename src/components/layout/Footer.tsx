import Link from "next/link";

import { brand } from "@/config/brand";
import { products, getProductHref } from "@/data/products";

import styles from "./Footer.module.css";

const footerGroups = [
  {
    title: "Products",
    items: [
      ...products.map((product) => ({ label: product.shortName, href: getProductHref(product) })),
      { label: "Compare", href: "/compare" },
    ],
  },
  {
    title: "Explore",
    items: [
      { label: "Apps", href: "/apps" },
      { label: `Why ${brand.name}`, href: "/#why" },
    ],
  },
] as const;

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.intro}>
          <Link className={styles.wordmark} href="/">{brand.name}</Link>
          <p>{brand.tagline}</p>
        </div>

        {footerGroups.map((group) => (
          <nav key={group.title} aria-label={`${group.title} links`}>
            <h2>{group.title}</h2>
            {group.items.map((item) => <Link key={item.label} href={item.href}>{item.label}</Link>)}
          </nav>
        ))}

        <nav aria-label="Support links">
          <h2>Support</h2>
          <span>Documentation <small>Later</small></span>
          <a href={`mailto:${brand.contact.supportEmail}`}>Contact</a>
          <span>Shipping <small>Later</small></span>
        </nav>

        <nav aria-label="Legal links">
          <h2>Legal</h2>
          <span>Privacy <small>Draft later</small></span>
          <span>Terms <small>Draft later</small></span>
          <span>Cookies <small>Draft later</small></span>
        </nav>
      </div>
      <div className={styles.bottom}>
        <span>© {new Date().getFullYear()} {brand.name}</span>
        <span>{brand.descriptor}</span>
      </div>
    </footer>
  );
}
