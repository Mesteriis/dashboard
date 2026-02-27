import type {
  DashboardGroup,
  DashboardItem,
  TreeGroupNode,
} from "@/features/stores/dashboard/storeTypes";

export function createDashboardTreeDataSection(ctx: any) {
  function resolveBlockGroups(
    groupIds: readonly string[] = [],
  ): TreeGroupNode[] {
    const resolved: TreeGroupNode[] = [];

    for (const id of groupIds) {
      const normalizedId = String(id || "");
      const group = ctx.groupById.value.get(normalizedId);
      if (group) {
        resolved.push({
          key: `group:${group.id}`,
          id: group.id,
          title: String(group.title || ""),
          icon: group.icon || null,
          description: group.description || "",
          layout: group.layout || "auto",
          subgroups: group.subgroups || [],
        });
        continue;
      }

      const subgroupRef = ctx.subgroupById.value.get(normalizedId);
      if (subgroupRef) {
        resolved.push({
          key: `subgroup:${subgroupRef.subgroup.id}`,
          id: subgroupRef.group.id,
          title: String(subgroupRef.group.title || ""),
          icon: subgroupRef.group.icon || null,
          description: subgroupRef.group.description || "",
          layout: subgroupRef.group.layout || "auto",
          subgroups: [subgroupRef.subgroup],
        });
      }
    }

    return resolved;
  }

  function syncTreeGroupsState(): void {
    const activeKeys = new Set(
      ctx.treeGroups.value.map((group: any) => group.key),
    );

    for (const key of Object.keys(ctx.expandedGroups)) {
      if (!activeKeys.has(key)) {
        delete ctx.expandedGroups[key];
      }
    }

    for (const group of ctx.treeGroups.value) {
      if (ctx.expandedGroups[group.key] == null) {
        ctx.expandedGroups[group.key] = true;
      }
    }

    if (
      ctx.selectedNode.groupKey &&
      !activeKeys.has(ctx.selectedNode.groupKey)
    ) {
      clearSelectedNode();
    }
  }

  function clearSelectedNode(): void {
    ctx.selectedNode.groupKey = "";
    ctx.selectedNode.subgroupId = "";
    ctx.selectedNode.itemId = "";
  }

  function safeUrlHost(rawValue: unknown): string {
    try {
      return new URL(String(rawValue || "")).hostname || "";
    } catch {
      return "";
    }
  }

  function deriveSiteLabel(
    item: DashboardItem | null | undefined,
    group: Record<string, unknown> | null | undefined,
    tags: readonly string[] = [],
  ): string {
    const itemSite = String(item?.site || "").trim();
    if (itemSite) return itemSite;

    const groupSite = String(group?.site || "").trim();
    if (groupSite) return groupSite;

    const siteTag = tags.find((tag) =>
      String(tag || "")
        .toLowerCase()
        .startsWith("site:"),
    );
    if (!siteTag) return "";
    return String(siteTag).slice(5).trim();
  }

  function normalizedItemTags(
    item: DashboardItem | null | undefined,
  ): string[] {
    return (item?.tags || [])
      .map((tag) => String(tag || "").trim())
      .filter(Boolean);
  }

  function resolveGroupByNodeKey(groupKey: unknown): DashboardGroup | null {
    const key = String(groupKey || "");
    if (!key.startsWith("group:")) return null;
    return ctx.groupById.value.get(key.slice(6)) || null;
  }

  function resolveItemSite(
    item: DashboardItem | null | undefined,
    group: Record<string, unknown> | null = null,
  ): string {
    return deriveSiteLabel(item, group, normalizedItemTags(item));
  }

  function itemSite(item: any, groupKey = ""): string {
    const resolvedGroup = resolveGroupByNodeKey(
      item?.__originGroupKey || groupKey,
    );
    return resolveItemSite(item, resolvedGroup);
  }

  function filterGroupsBySite(groups: TreeGroupNode[] = []): TreeGroupNode[] {
    if (ctx.siteFilter.value === "all") return groups;

    return groups
      .map((group) => {
        const nextSubgroups = (group.subgroups || [])
          .map((subgroup: any) => ({
            ...subgroup,
            items: (subgroup.items || []).filter(
              (item: any) =>
                resolveItemSite(item, group).toLowerCase() ===
                ctx.siteFilter.value,
            ),
          }))
          .filter((subgroup: any) => subgroup.items.length > 0);

        if (!nextSubgroups.length) return null;
        return {
          ...group,
          subgroups: nextSubgroups,
        };
      })
      .filter((group): group is TreeGroupNode => Boolean(group));
  }

  function setSiteFilter(value: unknown): void {
    const normalized = String(value || "all")
      .trim()
      .toLowerCase();
    const allowed = new Set(
      ctx.siteFilterOptions.value.map((option: any) => option.value),
    );
    ctx.siteFilter.value = allowed.has(normalized) ? normalized : "all";
  }

  return {
    clearSelectedNode,
    filterGroupsBySite,
    itemSite,
    normalizedItemTags,
    resolveBlockGroups,
    resolveItemSite,
    safeUrlHost,
    setSiteFilter,
    syncTreeGroupsState,
  };
}
