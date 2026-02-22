import { findGroup, findSubgroup } from "./configTreeIds.js";

export function moveGroup(cfg, sourceGroupId, targetGroupId) {
  const groupsList = cfg.groups || [];
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

export function moveSubgroup(
  cfg,
  sourceGroupId,
  sourceSubgroupId,
  targetGroupId,
  targetSubgroupId,
) {
  const sourceGroup = findGroup(cfg, sourceGroupId);
  const targetGroup = findGroup(cfg, targetGroupId);
  if (!sourceGroup || !targetGroup) return false;

  const sourceIndex = (sourceGroup.subgroups || []).findIndex(
    (subgroup) => subgroup.id === sourceSubgroupId,
  );
  const targetIndex = (targetGroup.subgroups || []).findIndex(
    (subgroup) => subgroup.id === targetSubgroupId,
  );
  if (sourceIndex < 0 || targetIndex < 0) return false;

  if (sourceGroupId !== targetGroupId && sourceGroup.subgroups.length <= 1) {
    throw new Error(
      "В исходной группе должна остаться минимум одна подгруппа.",
    );
  }

  const [moved] = sourceGroup.subgroups.splice(sourceIndex, 1);

  if (sourceGroupId === targetGroupId) {
    const insertIndex =
      sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
    sourceGroup.subgroups.splice(insertIndex, 0, moved);
    return true;
  }

  targetGroup.subgroups.splice(targetIndex, 0, moved);
  return true;
}

export function moveItemBefore(
  cfg,
  sourceGroupId,
  sourceSubgroupId,
  sourceItemId,
  targetGroupId,
  targetSubgroupId,
  targetItemId,
) {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId);
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId);
  if (!sourceSubgroup || !targetSubgroup) return false;

  const sourceIndex = (sourceSubgroup.items || []).findIndex(
    (item) => item.id === sourceItemId,
  );
  const targetIndex = (targetSubgroup.items || []).findIndex(
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
  cfg,
  sourceGroupId,
  sourceSubgroupId,
  sourceItemId,
  targetGroupId,
  targetSubgroupId,
) {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId);
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId);
  if (!sourceSubgroup || !targetSubgroup) return false;

  const sourceIndex = (sourceSubgroup.items || []).findIndex(
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
