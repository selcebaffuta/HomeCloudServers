import Link from "next/link";

import { brand } from "@/config/brand";
import { siteNavigation } from "@/config/site";
import { ArrowLink } from "@/components/ui/ArrowLink";
import { MobileMenu } from "./MobileMenu";

import styles from "./Header.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link className={styles.wordmark} href="/" aria-label={`${brand.name} home`}>
          <span className={styles.mark} aria-hidden="true"><i /></span>
          <span>{brand.name}</span>
        </Link>

        <nav className={styles.desktopNav} aria-label="Primary navigation">
          {siteNavigation.map((item) => (
            <Link key={item.label} href={item.href}>{item.label}</Link>
          ))}
        </nav>

        <div className={styles.desktopCta}>
          <ArrowLink href="/#products">Choose yours</ArrowLink>
        </div>

        <MobileMenu />
      </div>
    </header>
  );
}
