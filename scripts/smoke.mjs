import assert from "node:assert/strict";
import { spawn } from "node:child_process";

const host = "127.0.0.1";
const port = "3100";
const origin = `http://${host}:${port}`;
const nextBin = "node_modules/next/dist/bin/next";

const server = spawn(process.execPath, [nextBin, "start", "--hostname", host, "--port", port], {
  env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1" },
  stdio: ["ignore", "pipe", "pipe"],
});

let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk; });
server.stderr.on("data", (chunk) => { serverOutput += chunk; });

async function waitForServer() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(origin);
      if (response.ok) return;
    } catch {
      // The server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 125));
  }
  throw new Error(`Production server did not become ready.\n${serverOutput}`);
}

async function checkRoute(path, expectedText) {
  const response = await fetch(`${origin}${path}`);
  assert.equal(response.status, 200, `${path} should return 200`);
  const body = await response.text();
  assert.match(body, expectedText, `${path} should contain its primary content`);
  return body;
}

try {
  await waitForServer();
  const home = await checkRoute("/", /Your digital life/);
  assert.match(home, /aria-expanded="false"/, "homepage should include the accessible mobile menu control");
  assert.match(home, /href="\/compare"/, "homepage should link to comparison");
  assert.match(home, /href="\/products\/base"/, "homepage should link to Base");

  await checkRoute("/apps", /More than/);
  await checkRoute("/compare", /Same cloud/);
  await checkRoute("/products/base", /HomeCloud Base/);
  await checkRoute("/products/plus", /HomeCloud Plus/);
  await checkRoute("/products/pro", /HomeCloud Pro/);
  await checkRoute("/robots.txt", /Sitemap:/);
  await checkRoute("/sitemap.xml", /products\/pro/);

  process.stdout.write("Production smoke test passed for public routes and navigation.\n");
} finally {
  server.kill("SIGTERM");
}
