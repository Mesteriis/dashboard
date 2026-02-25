import { createRouter, createWebHistory } from "vue-router";
import BlankPage from "@/pages/blank/BlankPage.vue";
import DashboardPage from "@/pages/dashboard/DashboardPage.vue";
import PluginPage from "@/pages/plugins/plugin/PluginPage.vue";
import PluginsPage from "@/pages/plugins/PluginsPage.vue";
import SettingsPage from "@/pages/settings/SettingsPage.vue";
import UiShowcasePage from "@/pages/ui-showcase/UiShowcasePage.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: DashboardPage,
    },
    {
      path: "/settings",
      name: "settings",
      component: SettingsPage,
    },
    {
      path: "/ui",
      name: "ui-showcase",
      component: UiShowcasePage,
    },
    {
      path: "/plugins",
      name: "plugins",
      component: PluginsPage,
    },
    {
      path: "/plugins/:pluginId",
      name: "plugin",
      component: PluginPage,
    },
    {
      path: "/blank",
      name: "blank",
      component: BlankPage,
    },
  ],
});

export default router;
