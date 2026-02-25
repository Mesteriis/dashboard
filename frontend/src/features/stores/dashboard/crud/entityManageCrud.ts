import type { DashboardConfig } from "@/features/stores/dashboard/storeTypes";

export function createDashboardCrudEntityManage(ctx: any) {
  const { applyConfigMutation, config, editMode, findGroupInConfig, findSubgroupInConfig } =
    ctx as any;

  async function editGroup(groupId: string): Promise<void> {
    if (!editMode.value || !config.value) return;

    const group = findGroupInConfig(config.value, groupId);
    if (!group) return;

    const nextTitle = window.prompt("Название группы", group.title);
    if (nextTitle == null) return;

    const nextDescription = window.prompt(
      "Описание группы",
      group.description || "",
    );
    if (nextDescription == null) return;

    const nextLayout = window.prompt(
      "Режим группы (auto | full | inline)",
      group.layout || "auto",
    );
    if (nextLayout == null) return;

    await applyConfigMutation((cfg: DashboardConfig) => {
      const target = findGroupInConfig(cfg, groupId);
      if (!target) throw new Error(`Группа '${groupId}' не найдена`);

      const normalizedLayout =
        String(nextLayout || "")
          .trim()
          .toLowerCase() || "auto";
      if (!["auto", "full", "inline"].includes(normalizedLayout)) {
        throw new Error("Режим группы должен быть 'auto', 'full' или 'inline'");
      }

      target.title = nextTitle.trim() || target.title;
      target.description = nextDescription.trim();
      target.layout = normalizedLayout;
    });
  }

  async function editSubgroup(
    groupId: string,
    subgroupId: string,
  ): Promise<void> {
    if (!editMode.value || !config.value) return;

    const subgroup = findSubgroupInConfig(config.value, groupId, subgroupId);
    if (!subgroup) return;

    const nextTitle = window.prompt("Название подгруппы", subgroup.title);
    if (nextTitle == null) return;

    await applyConfigMutation((cfg: DashboardConfig) => {
      const target = findSubgroupInConfig(cfg, groupId, subgroupId);
      if (!target) throw new Error(`Подгруппа '${subgroupId}' не найдена`);

      target.title = nextTitle.trim() || target.title;
    });
  }

  async function editItem(
    groupId: string,
    subgroupId: string,
    itemId: string,
  ): Promise<void> {
    if (!editMode.value || !config.value) return;
    ctx.openEditItemEditor(groupId, subgroupId, itemId);
  }

  async function removeGroup(groupId: string): Promise<void> {
    if (!editMode.value || !config.value) return;

    const group = findGroupInConfig(config.value, groupId);
    if (!group) return;

    if (config.value.groups.length <= 1) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "Нельзя удалить последнюю группу.";
      return;
    }

    if (!window.confirm(`Удалить группу "${group.title}"?`)) return;

    await applyConfigMutation((cfg: DashboardConfig) => {
      const index = (cfg.groups || []).findIndex((entry) => entry.id === groupId);
      if (index < 0) return false;
      cfg.groups.splice(index, 1);

      ctx.selectedNode.groupKey = "";
      ctx.selectedNode.subgroupId = "";
      ctx.selectedNode.itemId = "";
    });
  }

  async function removeSubgroup(
    groupId: string,
    subgroupId: string,
  ): Promise<void> {
    if (!editMode.value || !config.value) return;

    const group = findGroupInConfig(config.value, groupId);
    const subgroup = (group?.subgroups || []).find(
      (entry: any) => entry.id === subgroupId,
    );
    if (!group || !subgroup) return;

    if (group.subgroups.length <= 1) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "В группе должна остаться хотя бы одна подгруппа.";
      return;
    }

    if (!window.confirm(`Удалить подгруппу "${subgroup.title}"?`)) return;

    await applyConfigMutation((cfg: DashboardConfig) => {
      const targetGroup = findGroupInConfig(cfg, groupId);
      if (!targetGroup) return false;

      const index = (targetGroup.subgroups || []).findIndex(
        (entry: any) => entry.id === subgroupId,
      );
      if (index < 0) return false;
      targetGroup.subgroups.splice(index, 1);

      ctx.selectedNode.subgroupId = "";
      ctx.selectedNode.itemId = "";
    });
  }

  async function removeItem(
    groupId: string,
    subgroupId: string,
    itemId: string,
  ): Promise<void> {
    if (!editMode.value || !config.value) return;

    const subgroup = findSubgroupInConfig(config.value, groupId, subgroupId);
    const item = (subgroup?.items || []).find((entry: any) => entry.id === itemId);
    if (!subgroup || !item) return;

    if (subgroup.items.length <= 1) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = "В подгруппе должен остаться хотя бы один элемент.";
      return;
    }

    if (!window.confirm(`Удалить сервис "${item.title}"?`)) return;

    await applyConfigMutation((cfg: DashboardConfig) => {
      const targetSubgroup = findSubgroupInConfig(cfg, groupId, subgroupId);
      if (!targetSubgroup) return false;

      const index = (targetSubgroup.items || []).findIndex(
        (entry: any) => entry.id === itemId,
      );
      if (index < 0) return false;
      targetSubgroup.items.splice(index, 1);

      if (ctx.selectedNode.itemId === itemId) {
        ctx.selectedNode.itemId = "";
      }
    });
  }

  return {
    editGroup,
    editItem,
    editSubgroup,
    removeGroup,
    removeItem,
    removeSubgroup,
  };
}
