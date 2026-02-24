import type { DashboardConfig } from "@/stores/dashboard/storeTypes";

interface AddGroupOptions {
  title?: string;
  id?: string;
  icon?: string;
  description?: string;
}

interface AddSubgroupOptions {
  title?: string;
  id?: string;
}

export function createDashboardCrudGroups(ctx: any) {
  const {
    activePageId,
    allItemIdsInConfig,
    allSubgroupIdsInConfig,
    applyConfigMutation,
    config,
    createEntityEditor,
    editMode,
    ensurePageGroupsReferenceInConfig,
    expandedGroups,
    findGroupInConfig,
    makeUniqueId,
    normalizeId,
    resolveDefaultDashboardId,
    resolveDefaultGroupId,
    resolveDefaultSubgroupId,
    resolveGroupIdsForDashboard,
    selectedNode,
  } = ctx as any;

  async function addGroup(options: AddGroupOptions = {}): Promise<boolean> {
    if (!editMode.value || !config.value) return false;

    let normalizedTitle = String(options.title || "").trim();
    if (!normalizedTitle) {
      const prompted = window.prompt("Название новой группы", "Новая группа");
      if (prompted == null) return false;
      normalizedTitle = prompted.trim();
    }
    if (!normalizedTitle) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "Название группы обязательно";
      return false;
    }

    const rawId = String(options.id || "").trim();
    const icon = String(options.icon || "folder").trim() || "folder";
    const description = String(options.description || "").trim();

    return applyConfigMutation((cfg: DashboardConfig) => {
      const groupIds = new Set((cfg.groups || []).map((group) => group.id));
      const subgroupIds = allSubgroupIdsInConfig(cfg);
      const itemIds = allItemIdsInConfig(cfg);

      const normalizedGroupBase = normalizeId(rawId || normalizedTitle, "group");
      const groupId = rawId
        ? normalizedGroupBase
        : makeUniqueId(normalizedGroupBase, groupIds);
      if (rawId && groupIds.has(groupId)) {
        throw new Error(`ID группы '${groupId}' уже существует`);
      }
      const subgroupId = makeUniqueId(`${groupId}-core`, subgroupIds);
      const itemId = makeUniqueId(`${groupId}-service`, itemIds);

      cfg.groups.push({
        id: groupId,
        title: normalizedTitle,
        icon,
        description,
        layout: "auto",
        subgroups: [
          {
            id: subgroupId,
            title: "Core",
            items: [ctx.buildDefaultItem(itemId, "Новый сервис")],
          },
        ],
      });

      ensurePageGroupsReferenceInConfig(cfg, activePageId.value, groupId);
      expandedGroups[`group:${groupId}`] = true;
      selectedNode.groupKey = `group:${groupId}`;
      selectedNode.subgroupId = subgroupId;
      selectedNode.itemId = itemId;
    });
  }

  async function addSubgroup(
    groupId: string,
    options: AddSubgroupOptions = {},
  ): Promise<boolean> {
    if (!editMode.value || !config.value) return false;

    let normalizedTitle = String(options.title || "").trim();
    if (!normalizedTitle) {
      const prompted = window.prompt("Название подгруппы", "Новая подгруппа");
      if (prompted == null) return false;
      normalizedTitle = prompted.trim();
    }
    if (!normalizedTitle) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "Название подгруппы обязательно";
      return false;
    }
    const rawId = String(options.id || "").trim();

    return applyConfigMutation((cfg: DashboardConfig) => {
      const group = findGroupInConfig(cfg, groupId);
      if (!group) throw new Error(`Группа '${groupId}' не найдена`);

      const subgroupIds = allSubgroupIdsInConfig(cfg);
      const itemIds = allItemIdsInConfig(cfg);
      const normalizedSubgroupBase = normalizeId(
        rawId || `${groupId}-${normalizedTitle}`,
        "subgroup",
      );
      const subgroupId = rawId
        ? normalizedSubgroupBase
        : makeUniqueId(normalizedSubgroupBase, subgroupIds);
      if (rawId && subgroupIds.has(subgroupId)) {
        throw new Error(`ID подгруппы '${subgroupId}' уже существует`);
      }
      const itemId = makeUniqueId(`${subgroupId}-service`, itemIds);

      group.subgroups.push({
        id: subgroupId,
        title: normalizedTitle,
        items: [ctx.buildDefaultItem(itemId, "Новый сервис")],
      });

      expandedGroups[`group:${groupId}`] = true;
      selectedNode.groupKey = `group:${groupId}`;
      selectedNode.subgroupId = subgroupId;
      selectedNode.itemId = itemId;
    });
  }

  async function submitCreateEntityEditor(): Promise<void> {
    if (!createEntityEditor.open || createEntityEditor.submitting) return;

    createEntityEditor.submitting = true;
    createEntityEditor.error = "";

    const form = createEntityEditor.form;
    const normalizedTitle = String(form.title || "").trim();
    const normalizedId = String(form.id || "").trim();
    const normalizedIcon = String(form.icon || "").trim();
    const normalizedDescription = String(form.description || "").trim();
    let success = false;

    if (form.kind === "dashboard") {
      if (!normalizedTitle) {
        createEntityEditor.error = "Название вкладки обязательно";
      } else {
        success = await ctx.createDashboardPage({
          title: normalizedTitle,
          id: normalizedId,
          icon: normalizedIcon || "layout-dashboard",
        });
      }
    } else if (form.kind === "group") {
      if (!normalizedTitle) {
        createEntityEditor.error = "Название группы обязательно";
      } else {
        success = await addGroup({
          title: normalizedTitle,
          id: normalizedId,
          icon: normalizedIcon || "folder",
          description: normalizedDescription,
        });
      }
    } else if (form.kind === "subgroup") {
      if (!normalizedTitle) {
        createEntityEditor.error = "Название подгруппы обязательно";
      } else {
        const parentGroupId = resolveDefaultGroupId(form.parentGroupId);
        if (!parentGroupId) {
          createEntityEditor.error = "Сначала создайте группу";
        } else {
          success = await addSubgroup(parentGroupId, {
            title: normalizedTitle,
            id: normalizedId,
          });
        }
      }
    } else {
      const parentDashboardId = resolveDefaultDashboardId(form.parentDashboardId);
      const allowedGroupIds = resolveGroupIdsForDashboard(parentDashboardId);
      const rawParentGroupId = String(form.parentGroupId || "").trim();
      const parentGroupId = allowedGroupIds.includes(rawParentGroupId)
        ? rawParentGroupId
        : String(allowedGroupIds[0] || "");
      const parentSubgroupId = resolveDefaultSubgroupId(
        parentGroupId,
        form.parentSubgroupId,
      );
      if (!parentGroupId || !parentSubgroupId) {
        createEntityEditor.error =
          "Выберите dashboard, группу и подгруппу для нового элемента";
      } else {
        ctx.openCreateItemEditor(parentGroupId, parentSubgroupId);
        success = true;
      }
    }

    createEntityEditor.submitting = false;
    if (success) {
      ctx.closeCreateEntityEditor(true);
      return;
    }

    if (!createEntityEditor.error && ctx.saveError.value) {
      createEntityEditor.error = ctx.saveError.value;
    }
  }

  return {
    addGroup,
    addSubgroup,
    submitCreateEntityEditor,
  };
}
