import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const serviceItemCardPath = path.resolve(
  process.cwd(),
  "src/views/dashboard/components/UiServiceItemCard.vue",
);

test("ServiceItemCard keeps open and copy as core actions", async () => {
  const source = await readFile(serviceItemCardPath, "utf8");

  assert.match(source, /@click="handleCardClick"/);
  assert.match(source, /title="Копировать URL"/);
  assert.doesNotMatch(source, /Recheck health/);
  assert.doesNotMatch(source, /Копировать IP/);
  assert.doesNotMatch(source, /Копировать SSH shortcut/);
});

test("ServiceItemCard includes plugin extension mount and slot", async () => {
  const source = await readFile(serviceItemCardPath, "utf8");

  assert.match(source, /<ServiceItemPluginExtensions/);
  assert.match(source, /<slot name="plugin-content"/);
  assert.match(source, /normalizeServiceCardCore/);
});
