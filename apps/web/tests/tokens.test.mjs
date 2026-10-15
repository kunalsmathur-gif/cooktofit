import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tokens = JSON.parse(readFileSync(new URL("../../../assets/brand/tokens.json", import.meta.url)));
const css = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");

const [lightBlock, darkBlock] = css.split("@media (prefers-color-scheme: dark)");
const varsIn = (block) =>
  Object.fromEntries([...block.matchAll(/--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6});/g)].map((m) => [m[1], m[2].toUpperCase()]));

for (const [mode, block] of [["light", lightBlock], ["dark", darkBlock]]) {
  test(`globals.css ${mode} colours match tokens.json`, () => {
    const vars = varsIn(block);
    for (const [key, hex] of Object.entries(tokens.modes[mode])) {
      assert.equal(vars[key.replaceAll("_", "-")], hex.toUpperCase(), `--${key} (${mode})`);
    }
  });
}
