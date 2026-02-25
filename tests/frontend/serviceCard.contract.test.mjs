import assert from "node:assert/strict";
import test from "node:test";
import {
  normalizePluginBlocks,
  normalizeServiceCardCore,
} from "../../frontend/src/shared/contracts/serviceCard.ts";

test("normalizeServiceCardCore keeps mandatory service-card fields", () => {
  const normalized = normalizeServiceCardCore({
    id: "grafana",
    title: "Grafana",
    type: "iframe",
    url: "https://grafana.local",
    tags: ["ops", " metrics ", ""],
    open: "same_tab",
  });

  assert.deepEqual(normalized, {
    id: "grafana",
    title: "Grafana",
    type: "iframe",
    url: "https://grafana.local",
    check_url: "https://grafana.local",
    tags: ["ops", "metrics"],
    open: "same_tab",
    plugin_blocks: [],
  });
});

test("normalizeServiceCardCore resolves explicit check_url first", () => {
  const normalized = normalizeServiceCardCore({
    id: "api",
    title: "API",
    type: "link",
    url: "https://api.local",
    check_url: "https://api.local/readyz",
  });

  assert.equal(normalized.check_url, "https://api.local/readyz");
});

test("normalizeServiceCardCore uses healthcheck.url when check_url not set", () => {
  const normalized = normalizeServiceCardCore({
    id: "web",
    title: "Web",
    type: "link",
    url: "https://web.local",
    healthcheck: {
      url: "https://web.local/healthz",
    },
  });

  assert.equal(normalized.check_url, "https://web.local/healthz");
});

test("normalizePluginBlocks keeps only supported declarative elements", () => {
  const blocks = normalizePluginBlocks([
    {
      plugin_id: "metrics",
      title: "Metrics",
      version: "v1",
      elements: [
        { id: "ok", kind: "text", label: "SLO", value: "99.9%" },
        { id: "badge", kind: "badge", value: "healthy", tone: "success" },
        {
          id: "html",
          kind: "html",
          trust: "server_sanitized_v1",
          html: "<div>safe</div>",
        },
        { id: "skip", kind: "custom", payload: "x" },
      ],
    },
  ]);

  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].plugin_id, "metrics");
  assert.equal(blocks[0].elements.length, 3);
  assert.deepEqual(
    blocks[0].elements.map((element) => element.kind),
    ["text", "badge", "html"],
  );
});
