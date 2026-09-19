import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import styles from "./ArrowLink.module.css";

type LinkProps = ComponentProps<typeof Link> & {
  readonly children: ReactNode;
  readonly variant?: "primary" | "secondary" | "text";
};

export function ArrowLink({ children, variant = "primary", className, ...props }: LinkProps) {
  const classes = [styles.link, styles[variant], className].filter(Boolean).join(" ");

  return (
    <Link className={classes} {...props}>
      <span>{children}</span>
      <span className={styles.arrow} aria-hidden="true">↗</span>
    </Link>
  );
}
