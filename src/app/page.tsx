import { HomePage } from "@/components/marketing/HomePage";
import { JsonLd } from "@/components/ui/JsonLd";
import { brand } from "@/config/brand";
import { getSiteUrl } from "@/config/site";
import { products } from "@/data/products";

export default function Page() {
  const siteUrl = getSiteUrl();

  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: brand.name,
          url: siteUrl.toString(),
          description: brand.metadata.description,
        }}
      />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "ItemList",
          name: `${brand.name} product family`,
          itemListElement: products.map((product, index) => ({
            "@type": "ListItem",
            position: index + 1,
            item: {
              "@type": "Product",
              name: product.displayName,
              description: product.description,
              url: new URL(`/products/${product.slug}`, siteUrl).toString(),
              category: "Personal cloud appliance",
            },
          })),
        }}
      />
      <HomePage />
    </>
  );
}
