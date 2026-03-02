import assert from "node:assert/strict";
import test from "node:test";
import {
  extractDashboardIndicatorsFromPlugins,
} from "../../frontend/src/features/plugins/dashboardIndicators.ts";

test("extractDashboardIndicatorsFromPlugins parses widgets from page manifest", () => {
  const payload = {
    plugins: [
      {
        id: "external_ip",
        metadata: {
          page_manifest: {
            manifest: {
              dashboard: {
                indicators: [
                  {
                    id: "external_ip_primary",
                    alwaysVisible: true,
                    widget: {
                      id: "plugin.external-ip.current",
                      title: "Внешний IP",
                      type: "stat_card",
                      data: {
                        endpoint: "/api/v1/plugins/external_ip/services",
                        refresh_sec: 120,
                      },
                    },
                  },
                ],
              },
            },
          },
        },
      },
    ],
  };

  const parsed = extractDashboardIndicatorsFromPlugins(payload);
  assert.equal(parsed.widgets.length, 1);
  assert.equal(parsed.widgets[0].id, "plugin.external-ip.current");
  assert.equal(parsed.widgets[0].plugin_id, "external_ip");
  assert.deepEqual(parsed.alwaysVisibleWidgetIds, ["plugin.external-ip.current"]);
});

test("extractDashboardIndicatorsFromPlugins deduplicates widgets and handles invalid payload", () => {
  const payload = {
    plugins: [
      {
        id: "a",
        metadata: {
          page_manifest: {
            manifest: {
              dashboard: {
                indicators: [
                  {
                    id: "x1",
                    widget: { id: "same", title: "one", type: "stat_card" },
                  },
                ],
              },
            },
          },
        },
      },
      {
        id: "b",
        metadata: {
          page_manifest: {
            manifest: {
              dashboard: {
                indicators: [
                  {
                    id: "x2",
                    always_visible: true,
                    widget: { id: "same", title: "two", type: "stat_card" },
                  },
                  {
                    id: "x3",
                    always_visible: true,
                    widget: { title: "fallback id", type: "stat_card" },
                  },
                ],
              },
            },
          },
        },
      },
    ],
  };

  const parsed = extractDashboardIndicatorsFromPlugins(payload);
  assert.equal(parsed.widgets.length, 2);
  assert.equal(parsed.widgets[0].id, "same");
  assert.equal(parsed.widgets[0].title, "one");
  assert.equal(parsed.widgets[1].id, "b.x3");
  assert.deepEqual(parsed.alwaysVisibleWidgetIds, ["same", "b.x3"]);
});

test("extractDashboardIndicatorsFromPlugins returns empty for malformed source", () => {
  assert.deepEqual(extractDashboardIndicatorsFromPlugins(null), {
    widgets: [],
    alwaysVisibleWidgetIds: [],
  });
});
