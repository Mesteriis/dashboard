import { goPluginsPanel, type PluginsPanelTab } from "@/core/navigation/nav";

export function dispatchOpenPluginPanel(
  detail: { tab?: PluginsPanelTab } = {},
): void {
  void goPluginsPanel({ tab: detail.tab });
}
