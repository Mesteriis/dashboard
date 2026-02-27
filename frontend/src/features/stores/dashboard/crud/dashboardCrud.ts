import type {
  DashboardConfig,
  DashboardItem,
} from "@/features/stores/dashboard/storeTypes";

interface AddDashboardOptions {
  title?: string;
  id?: string;
  icon?: string;
}

export function createDashboardCrudDashboard(ctx: any) {
  const {
    DEFAULT_ITEM_URL,
    activePageId,
    allItemIdsInConfig,
    allSubgroupIdsInConfig,
    applyConfigMutation,
    clearSelectedNode,
    config,
    editMode,
    makeUniqueId,
    normalizeId,
    selectedNode,
  } = ctx as any;

  function buildDefaultItem(itemId: string, title: string): DashboardItem {
    return {
      id: itemId,
      type: "link",
      title,
      url: DEFAULT_ITEM_URL,
      icon: null,
      site: null,
      tags: [],
      open: "new_tab",
    };
  }

  async function bootstrapInitialDashboard(): Promise<boolean> {
    if (!config.value) return false;

    return applyConfigMutation((cfg: DashboardConfig) => {
      if (!Array.isArray(cfg.groups)) {
        cfg.groups = [];
      }

      if (!cfg.layout || typeof cfg.layout !== "object") {
        cfg.layout = {};
      }

      const existingPages = Array.isArray(cfg.layout.pages)
        ? cfg.layout.pages
        : [];
      cfg.layout.pages = existingPages;

      if (existingPages.length > 0) {
        activePageId.value = String(existingPages[0]?.id || "");
        return false;
      }

      const groupIds = new Set(
        (cfg.groups || [])
          .map((group) => String(group.id || "").trim())
          .filter(Boolean),
      );
      const subgroupIds = allSubgroupIdsInConfig(cfg);
      const itemIds = allItemIdsInConfig(cfg);

      if (!cfg.groups.length) {
        const groupId = makeUniqueId("core", groupIds);
        const subgroupId = makeUniqueId(`${groupId}-main`, subgroupIds);
        const itemId = makeUniqueId(`${subgroupId}-service`, itemIds);

        cfg.groups.push({
          id: groupId,
          title: "Core Services",
          icon: "layout-dashboard",
          description: "Стартовая группа сервисов Oko.",
          layout: "auto",
          subgroups: [
            {
              id: subgroupId,
              title: "Main",
              items: [buildDefaultItem(itemId, "Новый сервис")],
            },
          ],
        });
      }

      const pageIds = new Set(
        existingPages
          .map((page) => String(page.id || "").trim())
          .filter(Boolean),
      );
      const pageId = makeUniqueId("home", pageIds);

      existingPages.push({
        id: pageId,
        title: "Главная",
        icon: "layout-dashboard",
        blocks: [
          {
            type: "groups",
            group_ids: (cfg.groups || []).map((group) =>
              String(group.id || ""),
            ),
          },
        ],
      });

      activePageId.value = pageId;

      const firstGroup = cfg.groups[0];
      const firstSubgroup = firstGroup?.subgroups?.[0];
      const firstItem = firstSubgroup?.items?.[0];

      selectedNode.groupKey = firstGroup ? `group:${firstGroup.id}` : "";
      selectedNode.subgroupId = firstSubgroup?.id || "";
      selectedNode.itemId = firstItem?.id || "";
    });
  }

  async function createDashboardPage(
    options: AddDashboardOptions = {},
  ): Promise<boolean> {
    if (!editMode.value || !config.value) return false;

    let normalizedTitle = String(options.title || "").trim();
    if (!normalizedTitle) {
      const prompted = window.prompt("Название вкладки", "Новая панель");
      if (prompted == null) return false;
      normalizedTitle = prompted.trim();
    }
    if (!normalizedTitle) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "Название вкладки обязательно";
      return false;
    }

    const rawId = String(options.id || "").trim();
    const icon =
      String(options.icon || "layout-dashboard").trim() || "layout-dashboard";

    return applyConfigMutation((cfg: DashboardConfig) => {
      if (!cfg.layout || typeof cfg.layout !== "object") {
        cfg.layout = {};
      }
      const pagesRef = Array.isArray(cfg.layout.pages) ? cfg.layout.pages : [];
      cfg.layout.pages = pagesRef;

      const existingPageIds = new Set(
        pagesRef.map((page) => String(page.id || "").trim()).filter(Boolean),
      );
      const normalizedBase = normalizeId(rawId || normalizedTitle, "dashboard");
      const pageId = rawId
        ? normalizedBase
        : makeUniqueId(normalizedBase, existingPageIds);

      if (rawId && existingPageIds.has(pageId)) {
        throw new Error(`ID вкладки '${pageId}' уже существует`);
      }

      pagesRef.push({
        id: pageId,
        title: normalizedTitle,
        icon,
        blocks: [],
      });

      activePageId.value = pageId;
      clearSelectedNode();
    });
  }

  return {
    bootstrapInitialDashboard,
    buildDefaultItem,
    createDashboardPage,
  };
}
