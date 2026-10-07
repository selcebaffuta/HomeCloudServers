import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";

import { getSiteUrl, siteNavigation } from "@/config/site";

const originalSiteUrl = process.env.NEXT_PUBLIC_SITE_URL;

afterEach(() => {
  if (originalSiteUrl === undefined) delete process.env.NEXT_PUBLIC_SITE_URL;
  else process.env.NEXT_PUBLIC_SITE_URL = originalSiteUrl;
});

describe("site navigation", () => {
  it("uses route-safe links and does not expose an unconfigured support destination", () => {
    assert.ok(siteNavigation.some((item) => item.href === "/#products"));
    assert.ok(siteNavigation.some((item) => item.href === "/#why"));
    assert.ok(siteNavigation.some((item) => item.href === "/compare"));
    assert.equal(siteNavigation.find((item) => String(item.label) === "Support"), undefined);
  });
});

describe("site URL", () => {
  it("uses the configured canonical origin", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "https://homecloud.example/";
    assert.equal(getSiteUrl().origin, "https://homecloud.example");
  });

  it("falls back safely for invalid configuration", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "not a url";
    assert.equal(getSiteUrl().toString(), "http://localhost:3000/");
  });
});
