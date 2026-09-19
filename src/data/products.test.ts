import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { comparisonRows } from "@/data/features";
import { getProduct, products } from "@/data/products";

describe("product catalog", () => {
  it("contains exactly one entry for every initial family", () => {
    assert.deepEqual(products.map((product) => product.slug), ["base", "plus", "pro"]);
    assert.equal(new Set(products.map((product) => product.id)).size, products.length);
  });

  it("resolves known products without inventing commerce data", () => {
    const product = getProduct("pro");

    assert.equal(product?.displayName, "HomeCloud Pro");
    assert.equal(product?.basePrice, undefined);
    assert.equal(product?.sku, undefined);
    assert.equal(getProduct("unknown"), undefined);
  });

  it("provides a value for every comparison row and product", () => {
    for (const row of comparisonRows) {
      for (const product of products) {
        assert.ok(row.value(product).trim().length > 0);
      }
    }
  });
});
