import {
  findGroup,
  findSubgroup,
} from "@/features/stores/dashboard/configTreeIds";
import type {
  DashboardConfigTree,
  DashboardSubgroup,
} from "@/features/stores/dashboard/types";

export function moveGroup(
  cfg: DashboardConfigTree,
  sourceGroupId: string,
  targetGroupId: string,
): boolean {
  const groupsList = cfg.groups ?? [];
  const sourceIndex = groupsList.findIndex(
    (group) => group.id === sourceGroupId,
  );
  const targetIndex = groupsList.findIndex(
    (group) => group.id === targetGroupId,
  );

  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex)
    return false;

  const [moved] = groupsList.splice(sourceIndex, 1);
  const insertIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
  groupsList.splice(insertIndex, 0, moved);
  return true;
}

function ensureSubgroupItems(subgroup: DashboardSubgroup): void {
  if (!Array.isArray(subgroup.items)) {
    subgroup.items = [];
  }
}

export function moveSubgroup(
  cfg: DashboardConfigTree,
  sourceGroupId: string,
  sourceSubgroupId: string,
  targetGroupId: string,
  targetSubgroupId: string,
): boolean {
  const sourceGroup = findGroup(cfg, sourceGroupId);
  const targetGroup = findGroup(cfg, targetGroupId);
  if (!sourceGroup || !targetGroup) return false;

  const sourceSubgroups = sourceGroup.subgroups ?? [];
  const targetSubgroups = targetGroup.subgroups ?? [];
  const sourceIndex = sourceSubgroups.findIndex(
    (subgroup) => subgroup.id === sourceSubgroupId,
  );
  const targetIndex = targetSubgroups.findIndex(
    (subgroup) => subgroup.id === targetSubgroupId,
  );
  if (sourceIndex < 0 || targetIndex < 0) return false;

  if (sourceGroupId !== targetGroupId && sourceSubgroups.length <= 1) {
    throw new Error(
      "В исходной группе должна остаться минимум одна подгруппа.",
    );
  }

  const [moved] = sourceSubgroups.splice(sourceIndex, 1);

  if (sourceGroupId === targetGroupId) {
    const insertIndex =
      sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
    sourceSubgroups.splice(insertIndex, 0, moved);
    return true;
  }

  targetSubgroups.splice(targetIndex, 0, moved);
  return true;
}

export function moveItemBefore(
  cfg: DashboardConfigTree,
  sourceGroupId: string,
  sourceSubgroupId: string,
  sourceItemId: string,
  targetGroupId: string,
  targetSubgroupId: string,
  targetItemId: string,
): boolean {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId);
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId);
  if (!sourceSubgroup || !targetSubgroup) return false;
  ensureSubgroupItems(sourceSubgroup);
  ensureSubgroupItems(targetSubgroup);

  const sourceIndex = sourceSubgroup.items.findIndex(
    (item) => item.id === sourceItemId,
  );
  const targetIndex = targetSubgroup.items.findIndex(
    (item) => item.id === targetItemId,
  );
  if (sourceIndex < 0 || targetIndex < 0) return false;

  if (
    sourceSubgroupId !== targetSubgroupId &&
    sourceSubgroup.items.length <= 1
  ) {
    throw new Error(
      "В исходной подгруппе должен остаться минимум один элемент.",
    );
  }

  const [moved] = sourceSubgroup.items.splice(sourceIndex, 1);

  if (sourceSubgroupId === targetSubgroupId) {
    const insertIndex =
      sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
    sourceSubgroup.items.splice(insertIndex, 0, moved);
    return true;
  }

  targetSubgroup.items.splice(targetIndex, 0, moved);
  return true;
}

export function moveItemToSubgroupEnd(
  cfg: DashboardConfigTree,
  sourceGroupId: string,
  sourceSubgroupId: string,
  sourceItemId: string,
  targetGroupId: string,
  targetSubgroupId: string,
): boolean {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId);
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId);
  if (!sourceSubgroup || !targetSubgroup) return false;
  ensureSubgroupItems(sourceSubgroup);
  ensureSubgroupItems(targetSubgroup);

  const sourceIndex = sourceSubgroup.items.findIndex(
    (item) => item.id === sourceItemId,
  );
  if (sourceIndex < 0) return false;

  if (
    sourceSubgroupId !== targetSubgroupId &&
    sourceSubgroup.items.length <= 1
  ) {
    throw new Error(
      "В исходной подгруппе должен остаться минимум один элемент.",
    );
  }

  const [moved] = sourceSubgroup.items.splice(sourceIndex, 1);
  targetSubgroup.items.push(moved);
  return true;
}
