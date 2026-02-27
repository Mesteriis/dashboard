import type {
  DashboardItem,
  DashboardSubgroup,
  ItemWithOrigin,
  TreeGroupNode,
} from "@/features/stores/dashboard/storeTypes";

export function createDashboardGroupingSection(ctx: any) {
  function hasTreeSelection(): boolean {
    return Boolean(
      ctx.selectedNode.groupKey ||
        ctx.selectedNode.subgroupId ||
        ctx.selectedNode.itemId,
    );
  }

  function normalizeTagLabel(rawTag: unknown): string {
    const normalized = String(rawTag || "").trim();
    return normalized || "Без тега";
  }

  function tagsForItem(item: DashboardItem | ItemWithOrigin): string[] {
    const uniqueTags = new Set<string>(
      ctx
        .normalizedItemTags(item)
        .map((tag: string) => normalizeTagLabel(tag))
        .filter(Boolean),
    );
    if (!uniqueTags.size) {
      uniqueTags.add("Без тега");
    }
    return Array.from(uniqueTags);
  }

  function withOrigin(
    item: DashboardItem,
    groupKey: string,
    subgroupId: string,
  ): ItemWithOrigin {
    return {
      ...item,
      __originGroupKey: groupKey,
      __originSubgroupId: subgroupId,
    };
  }

  function filterGroupsBySelectedNode(
    groups: TreeGroupNode[] = [],
  ): TreeGroupNode[] {
    if (!hasTreeSelection()) return groups;

    return groups
      .map((group) => {
        if (
          ctx.selectedNode.groupKey &&
          group.key !== ctx.selectedNode.groupKey
        ) {
          return null;
        }

        let nextSubgroups = group.subgroups || [];

        if (ctx.selectedNode.subgroupId) {
          nextSubgroups = nextSubgroups.filter(
            (subgroup: any) => subgroup.id === ctx.selectedNode.subgroupId,
          );
        }

        if (ctx.selectedNode.itemId) {
          nextSubgroups = nextSubgroups
            .map((subgroup: any) => ({
              ...subgroup,
              items: (subgroup.items || []).filter(
                (item: any) => item.id === ctx.selectedNode.itemId,
              ),
            }))
            .filter((subgroup: any) => subgroup.items.length > 0);
        }

        if (!nextSubgroups.length) return null;
        return {
          ...group,
          subgroups: nextSubgroups,
        };
      })
      .filter((group): group is TreeGroupNode => Boolean(group));
  }

  function groupByTagsInEachGroup(
    groups: TreeGroupNode[] = [],
  ): TreeGroupNode[] {
    const nextGroups: TreeGroupNode[] = [];

    for (const group of groups) {
      const tagsMap = new Map<string, ItemWithOrigin[]>();

      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          for (const tag of tagsForItem(item)) {
            if (!tagsMap.has(tag)) {
              tagsMap.set(tag, []);
            }
            tagsMap.get(tag)?.push(withOrigin(item, group.key, subgroup.id));
          }
        }
      }

      const sortedTagEntries = Array.from(tagsMap.entries()).sort(
        ([left], [right]) =>
          left.localeCompare(right, "ru", { sensitivity: "base" }),
      );
      const tagSubgroups: DashboardSubgroup[] = sortedTagEntries.map(
        ([tag, items]) => ({
          id: `tag-${ctx.normalizeId(`${group.id}-${tag}`, "tag")}`,
          title: `#${tag}`,
          icon: "tag",
          items,
        }),
      );

      if (!tagSubgroups.length) continue;
      nextGroups.push({
        ...group,
        subgroups: tagSubgroups,
      });
    }

    return nextGroups;
  }

  function groupByTagsOnly(groups: TreeGroupNode[] = []): TreeGroupNode[] {
    const tagsMap = new Map<string, ItemWithOrigin[]>();

    for (const group of groups) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          for (const tag of tagsForItem(item)) {
            if (!tagsMap.has(tag)) {
              tagsMap.set(tag, []);
            }
            tagsMap.get(tag)?.push(withOrigin(item, group.key, subgroup.id));
          }
        }
      }
    }

    const sortedTagEntries = Array.from(tagsMap.entries()).sort(
      ([left], [right]) =>
        left.localeCompare(right, "ru", { sensitivity: "base" }),
    );

    return sortedTagEntries.map(([tag, items]) => {
      const tagId = ctx.normalizeId(tag, "tag");
      return {
        key: `tags:${tagId}`,
        id: `tags-${tagId}`,
        title: `#${tag}`,
        icon: "tag",
        description: "Сервисы, сгруппированные только по тегам.",
        layout: "inline",
        subgroups: [
          {
            id: `tags-${tagId}-items`,
            title: "Сервисы",
            items,
          },
        ],
      };
    });
  }

  function toFlatTileGroups(groups: TreeGroupNode[] = []): TreeGroupNode[] {
    const items: ItemWithOrigin[] = [];

    for (const group of groups) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          items.push(withOrigin(item, group.key, subgroup.id));
        }
      }
    }

    if (!items.length) return [];
    return [
      {
        key: "flat:all",
        id: "flat-all",
        title: "Все сервисы",
        icon: "layout-grid",
        description: "Плоское отображение без группировки.",
        layout: "full",
        subgroups: [
          {
            id: "flat-all-items",
            title: "Плитка",
            items,
          },
        ],
      },
    ];
  }

  function applyServiceGroupingMode(
    groups: TreeGroupNode[] = [],
  ): TreeGroupNode[] {
    if (ctx.isSidebarHidden.value) {
      return toFlatTileGroups(groups);
    }

    if (ctx.serviceGroupingMode.value === "tags_in_groups") {
      return groupByTagsInEachGroup(groups);
    }

    if (ctx.serviceGroupingMode.value === "tags") {
      return groupByTagsOnly(groups);
    }

    if (ctx.serviceGroupingMode.value === "flat") {
      return toFlatTileGroups(groups);
    }

    return groups;
  }

  function filteredBlockGroups(
    groupIds: readonly string[] = [],
  ): TreeGroupNode[] {
    const groups = ctx.resolveBlockGroups(groupIds);
    const siteFiltered = ctx.filterGroupsBySite(groups);
    const selectionFiltered = ctx.isSidebarHidden.value
      ? siteFiltered
      : filterGroupsBySelectedNode(siteFiltered);
    const regrouped = applyServiceGroupingMode(selectionFiltered);
    const visibleCount = regrouped.length;
    return regrouped.map((group) => ({
      ...group,
      __visibleCount: visibleCount,
    }));
  }

  function isInlineGroupLayout(group: Record<string, unknown>): boolean {
    const mode = String(group.layout || "auto").toLowerCase();
    if (mode === "inline") return true;
    if (mode === "full") return false;
    return Number(group.__visibleCount || 0) > 1;
  }

  function groupTotalItems(group: {
    subgroups?: Array<{ items?: unknown[] }>;
  }): number {
    return (group.subgroups || []).reduce(
      (acc: number, subgroup) => acc + (subgroup.items || []).length,
      0,
    );
  }

  function subgroupTotalItems(subgroup: { items?: unknown[] }): number {
    return (subgroup?.items || []).length;
  }

  function groupOnlineItems(group: {
    subgroups?: Array<{ items?: Array<{ id?: string }> }>;
  }): number {
    let online = 0;
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        if (ctx.healthState(String(item.id || ""))?.ok) {
          online += 1;
        }
      }
    }
    return online;
  }

  return {
    applyServiceGroupingMode,
    filteredBlockGroups,
    groupOnlineItems,
    groupTotalItems,
    isInlineGroupLayout,
    subgroupTotalItems,
  };
}
