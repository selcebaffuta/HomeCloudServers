import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProductPage } from "@/components/products/ProductPage";
import { JsonLd } from "@/components/ui/JsonLd";
import { brand } from "@/config/brand";
import { getSiteUrl } from "@/config/site";
import { getProduct, products } from "@/data/products";
import { createMetadata } from "@/lib/metadata";

interface ProductRouteProps {
  readonly params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return products.map((product) => ({ slug: product.slug }));
}

export async function generateMetadata({ params }: ProductRouteProps): Promise<Metadata> {
  const { slug } = await params;
  const product = getProduct(slug);

  if (!product) return {};

  return createMetadata({
    title: product.displayName,
    description: product.longDescription,
    path: `/products/${product.slug}`,
  });
}

export default async function ProductRoute({ params }: ProductRouteProps) {
  const { slug } = await params;
  const product = getProduct(slug);

  if (!product) notFound();

  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "Product",
          name: product.displayName,
          brand: { "@type": "Brand", name: brand.name },
          category: "Personal cloud appliance",
          description: product.longDescription,
          url: new URL(`/products/${product.slug}`, getSiteUrl()).toString(),
        }}
      />
      <ProductPage product={product} />
    </>
  );
}
