import { ImageResponse } from "next/og";

import { brand } from "@/config/brand";

export const alt = `${brand.name} — ${brand.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#f4f5f6",
          color: "#15171a",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "18px", fontSize: "30px", fontWeight: 700 }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "15px", background: "#15171a" }} />
          {brand.name}
        </div>
        <div style={{ display: "flex", maxWidth: "970px", fontSize: "82px", fontWeight: 650, lineHeight: 0.95, letterSpacing: "-5px" }}>
          {brand.tagline}
        </div>
        <div style={{ display: "flex", color: "#6d737d", fontSize: "24px" }}>{brand.descriptor}</div>
      </div>
    ),
    size,
  );
}
