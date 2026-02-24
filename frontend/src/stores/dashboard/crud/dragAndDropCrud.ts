import type { DashboardConfig } from "@/stores/dashboard/storeTypes";

export function createDashboardCrudDragAndDrop(ctx: any) {
  const {
    applyConfigMutation,
    dragState,
    editMode,
    isDirectGroupNode,
    moveGroupInConfig,
    moveItemBeforeInConfig,
    moveItemToSubgroupEndInConfig,
    moveSubgroupInConfig,
  } = ctx as any;

  function clearDragState(): void {
    dragState.type = "";
    dragState.groupId = "";
    dragState.subgroupId = "";
    dragState.itemId = "";
  }

  function onGroupDragStart(
    event: DragEvent,
    group: Record<string, unknown>,
  ): void {
    if (!editMode.value) return;
    if (!isDirectGroupNode(group)) return;
    const groupId = String(group.id || "");
    if (!groupId) return;
    dragState.type = "group";
    dragState.groupId = groupId;
    dragState.subgroupId = "";
    dragState.itemId = "";
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `group:${groupId}`);
    }
  }

  function onSubgroupDragStart(
    event: DragEvent,
    groupId: string,
    subgroupId: string,
  ): void {
    if (!editMode.value) return;
    dragState.type = "subgroup";
    dragState.groupId = groupId;
    dragState.subgroupId = subgroupId;
    dragState.itemId = "";
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `subgroup:${subgroupId}`);
    }
  }

  function onItemDragStart(
    event: DragEvent,
    groupId: string,
    subgroupId: string,
    itemId: string,
  ): void {
    if (!editMode.value) return;
    dragState.type = "item";
    dragState.groupId = groupId;
    dragState.subgroupId = subgroupId;
    dragState.itemId = itemId;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `item:${itemId}`);
    }
  }

  function onGroupDragOver(
    event: DragEvent,
    targetGroup: Record<string, unknown>,
  ): void {
    if (!editMode.value) return;
    if (!isDirectGroupNode(targetGroup)) return;
    const targetGroupId = String(targetGroup.id || "");
    if (!targetGroupId) return;
    if (dragState.type !== "group") return;
    if (dragState.groupId === targetGroupId) return;
    event.preventDefault();
  }

  async function onGroupDrop(
    event: DragEvent,
    targetGroup: Record<string, unknown>,
  ): Promise<void> {
    if (!editMode.value) return;
    if (!isDirectGroupNode(targetGroup)) return;
    const targetGroupId = String(targetGroup.id || "");
    if (!targetGroupId) return;
    if (dragState.type !== "group") return;
    if (!dragState.groupId || dragState.groupId === targetGroupId) return;
    event.preventDefault();

    const sourceGroupId = dragState.groupId;
    clearDragState();

    await applyConfigMutation((cfg: DashboardConfig) =>
      moveGroupInConfig(cfg, sourceGroupId, targetGroupId),
    );
  }

  function onSubgroupDragOver(
    event: DragEvent,
    targetGroupId: string,
    targetSubgroupId: string,
  ): void {
    void targetGroupId;
    if (!editMode.value) return;
    if (dragState.type === "subgroup") {
      if (dragState.subgroupId === targetSubgroupId) return;
      event.preventDefault();
      return;
    }

    if (dragState.type === "item") {
      event.preventDefault();
    }
  }

  async function onSubgroupDrop(
    event: DragEvent,
    targetGroupId: string,
    targetSubgroupId: string,
  ): Promise<void> {
    if (!editMode.value) return;

    if (dragState.type === "subgroup") {
      event.preventDefault();
      const sourceGroupId = dragState.groupId;
      const sourceSubgroupId = dragState.subgroupId;
      clearDragState();

      await applyConfigMutation((cfg: DashboardConfig) =>
        moveSubgroupInConfig(
          cfg,
          sourceGroupId,
          sourceSubgroupId,
          targetGroupId,
          targetSubgroupId,
        ),
      );
      return;
    }

    if (dragState.type === "item") {
      event.preventDefault();
      const sourceGroupId = dragState.groupId;
      const sourceSubgroupId = dragState.subgroupId;
      const sourceItemId = dragState.itemId;
      clearDragState();

      await applyConfigMutation((cfg: DashboardConfig) =>
        moveItemToSubgroupEndInConfig(
          cfg,
          sourceGroupId,
          sourceSubgroupId,
          sourceItemId,
          targetGroupId,
          targetSubgroupId,
        ),
      );
    }
  }

  function onItemDragOver(
    event: DragEvent,
    _targetGroupId: string,
    _targetSubgroupId: string,
    targetItemId: string,
  ): void {
    if (!editMode.value) return;
    if (dragState.type !== "item") return;
    if (dragState.itemId === targetItemId) return;
    event.preventDefault();
  }

  async function onItemDrop(
    event: DragEvent,
    targetGroupId: string,
    targetSubgroupId: string,
    targetItemId: string,
  ): Promise<void> {
    if (!editMode.value) return;
    if (dragState.type !== "item") return;
    if (!dragState.itemId || dragState.itemId === targetItemId) return;
    event.preventDefault();

    const sourceGroupId = dragState.groupId;
    const sourceSubgroupId = dragState.subgroupId;
    const sourceItemId = dragState.itemId;
    clearDragState();

    await applyConfigMutation((cfg: DashboardConfig) =>
      moveItemBeforeInConfig(
        cfg,
        sourceGroupId,
        sourceSubgroupId,
        sourceItemId,
        targetGroupId,
        targetSubgroupId,
        targetItemId,
      ),
    );
  }

  return {
    clearDragState,
    onGroupDragOver,
    onGroupDragStart,
    onGroupDrop,
    onItemDragOver,
    onItemDragStart,
    onItemDrop,
    onSubgroupDragOver,
    onSubgroupDragStart,
    onSubgroupDrop,
  };
}
