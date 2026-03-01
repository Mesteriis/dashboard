import assert from "node:assert/strict";
import test from "node:test";
import {
  getMissingManifestCapabilities,
  loadPluginManifest,
} from "../../frontend/src/features/plugins/manifest.ts";

const originalFetch = globalThis.fetch;
const hadWindow = "window" in globalThis;
const originalWindow = globalThis.window;

function jsonResponse(body = {}, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  if (hadWindow) {
    globalThis.window = originalWindow;
  } else {
    delete globalThis.window;
  }
});

test("loadPluginManifest parses backend envelope v1", async () => {
  globalThis.window = {
    __OKO_CAPABILITIES__: ["read.plugins.manifest", "read.plugins.services"],
  };
  globalThis.fetch = async () =>
    jsonResponse({
      plugin_id: "autodiscover",
      manifest: {
        plugin_id: "autodiscover",
        version: "2.0.0",
        manifest_version: "1.0",
        plugin_api_version: "1.0",
        capabilities: ["read.plugins.services"],
        frontend: {
          renderer: "universal",
          sandbox: true,
          customBundle: {
            enabled: false,
            sandbox: true,
            killSwitchKey: "oko:plugins:bundle:disabled",
          },
        },
        page: {
          enabled: true,
          layout: "content-only",
          components: [
            {
              id: "services",
              type: "data-table",
              columns: [{ key: "host_ip", label: "Host IP" }],
              groupBy: [
                { field: "host_ip", label: "Host", emptyLabel: "Unknown Host" },
                { field: "service", label: "Service", emptyLabel: "Unknown Service" },
              ],
              dataSource: {
                type: "http",
                endpoint: "/api/v1/plugins/autodiscover/services",
                method: "GET",
                capability: "read.plugins.services",
                response_path: "services",
              },
            },
          ],
        },
        schema: {},
      },
      negotiation: {
        accepted: true,
        fallback_used: false,
      },
    });

  const envelope = await loadPluginManifest("autodiscover");
  assert.equal(envelope.manifest.page.layout, "content-only");
  assert.equal(envelope.manifest.page.components[0].type, "data-table");
  assert.deepEqual(envelope.manifest.page.components[0].groupBy, [
    { field: "host_ip", label: "Host", emptyLabel: "Unknown Host" },
    { field: "service", label: "Service", emptyLabel: "Unknown Service" },
  ]);
});

test("unknown component is kept as safe unknown type", async () => {
  globalThis.window = {
    __OKO_CAPABILITIES__: ["read.plugins.manifest"],
  };
  globalThis.fetch = async () =>
    jsonResponse({
      plugin_id: "autodiscover",
      manifest: {
        plugin_id: "autodiscover",
        version: "2.0.0",
        manifest_version: "1.0",
        plugin_api_version: "1.0",
        capabilities: [],
        frontend: {
          renderer: "universal",
          sandbox: true,
          customBundle: { enabled: false, sandbox: true, killSwitchKey: "x" },
        },
        page: {
          enabled: true,
          layout: "content-only",
          components: [{ id: "x", type: "experimental-chart" }],
        },
        schema: {},
      },
      negotiation: { accepted: true, fallback_used: false },
    });

  const envelope = await loadPluginManifest("autodiscover");
  const component = envelope.manifest.page.components[0];
  assert.equal(component.type, "unknown");
  assert.equal(component.originalType, "experimental-chart");
});

test("getMissingManifestCapabilities reports missing component capability", async () => {
  const manifest = {
    plugin_id: "autodiscover",
    version: "2.0.0",
    manifest_version: "1.0",
    plugin_api_version: "1.0",
    capabilities: ["read.plugins.services"],
    frontend: {
      renderer: "universal",
      sandbox: true,
      customBundle: { enabled: false, sandbox: true, killSwitchKey: "x" },
    },
    page: {
      enabled: true,
      layout: "content-only",
      components: [
        {
          id: "services",
          type: "data-table",
          columns: [{ key: "host_ip", label: "Host IP" }],
          dataSource: {
            type: "http",
            endpoint: "/api/v1/plugins/autodiscover/services",
            method: "GET",
            capability: "read.plugins.services",
          },
        },
      ],
    },
    schema: {},
  };

  const missing = getMissingManifestCapabilities(manifest, new Set(["read.plugins.manifest"]));
  assert.deepEqual(missing, ["read.plugins.services"]);
});

test("getMissingManifestCapabilities includes row action capability", async () => {
  const manifest = {
    plugin_id: "autodiscover",
    version: "2.0.0",
    manifest_version: "1.0",
    plugin_api_version: "1.0",
    capabilities: ["read.plugins.services", "write.config.patch"],
    frontend: {
      renderer: "universal",
      sandbox: true,
      customBundle: { enabled: false, sandbox: true, killSwitchKey: "x" },
    },
    page: {
      enabled: true,
      layout: "content-only",
      components: [
        {
          id: "services",
          type: "data-table",
          columns: [{ key: "host_ip", label: "Host IP" }],
          dataSource: {
            type: "http",
            endpoint: "/api/v1/plugins/autodiscover/services",
            method: "GET",
          },
          rowActions: [
            {
              id: "add",
              type: "add-to-dashboard",
              capability: "write.config.patch",
            },
          ],
        },
      ],
    },
    schema: {},
  };

  const missing = getMissingManifestCapabilities(manifest, new Set(["read.plugins.services"]));
  assert.deepEqual(missing, ["write.config.patch"]);
});
