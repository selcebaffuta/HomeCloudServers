import { ArrowLink } from "@/components/ui/ArrowLink";

import styles from "./not-found.module.css";

export default function NotFound() {
  return (
    <section className={styles.notFound}>
      <p className="eyebrow">404</p>
      <h1>This page isn’t part of the cloud.</h1>
      <p>The address may have moved, or the page may belong to a future milestone.</p>
      <ArrowLink href="/">Back home</ArrowLink>
    </section>
  );
}
