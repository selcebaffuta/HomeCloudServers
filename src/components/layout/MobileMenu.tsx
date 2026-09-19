"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { siteNavigation } from "@/config/site";

import styles from "./Header.module.css";

export function MobileMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  function closeMenu() {
    setIsOpen(false);
  }

  return (
    <div
      className={styles.mobileMenu}
      onKeyDown={(event) => {
        if (event.key === "Escape" && isOpen) {
          closeMenu();
          buttonRef.current?.focus();
        }
      }}
    >
      <button
        ref={buttonRef}
        className={styles.menuButton}
        type="button"
        aria-expanded={isOpen}
        aria-controls="mobile-navigation"
        aria-label={isOpen ? "Close navigation" : "Open navigation"}
        onClick={() => setIsOpen((current) => !current)}
      >
        <span /><span />
      </button>
      {isOpen && (
        <nav id="mobile-navigation" aria-label="Mobile navigation">
          {siteNavigation.map((item) => (
            <Link key={item.label} href={item.href} onClick={closeMenu}>{item.label}</Link>
          ))}
          <Link className={styles.mobileCta} href="/#products" onClick={closeMenu}>
            Choose yours <span aria-hidden="true">↗</span>
          </Link>
        </nav>
      )}
    </div>
  );
}
