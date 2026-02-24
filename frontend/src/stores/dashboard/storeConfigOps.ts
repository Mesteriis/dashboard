import {
  allItemIds,
  allSubgroupIds,
  ensurePageGroupsReference,
  findGroup,
  findSubgroup,
  moveGroup,
  moveItemBefore,
  moveItemToSubgroupEnd,
  moveSubgroup,
  normalizeLayoutBlocks,
} from "@/stores/dashboard/configTreeUtils";
import type {
  DashboardConfig,
  DashboardGroup,
  DashboardSubgroup,
} from "@/stores/dashboard/storeTypes";
import type { DashboardConfigTree } from "@/stores/dashboard/types";

function asConfigTree(cfg: DashboardConfig): DashboardConfigTree {
  return cfg as unknown as DashboardConfigTree;
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function allSubgroupIdsInConfig(cfg: DashboardConfig): Set<string> {
  return allSubgroupIds(asConfigTree(cfg));
}

export function allItemIdsInConfig(cfg: DashboardConfig): Set<string> {
  return allItemIds(asConfigTree(cfg));
}

export function findGroupInConfig(
  cfg: DashboardConfig | null,
  groupId: string,
): DashboardGroup | null {
  if (!cfg) return null;
  return (
    (findGroup(asConfigTree(cfg), groupId) as DashboardGroup | null) || null
  );
}

export function findSubgroupInConfig(
  cfg: DashboardConfig | null,
  groupId: string,
  subgroupId: string,
): DashboardSubgroup | null {
  if (!cfg) return null;
  return (
    (findSubgroup(
      asConfigTree(cfg),
      groupId,
      subgroupId,
    ) as DashboardSubgroup | null) || null
  );
}

export function normalizeLayoutBlocksInConfig(cfg: DashboardConfig): void {
  normalizeLayoutBlocks(asConfigTree(cfg));
}

export function ensurePageGroupsReferenceInConfig(
  cfg: DashboardConfig,
  pageId: string,
  groupId: string,
): void {
  ensurePageGroupsReference(asConfigTree(cfg), pageId, groupId);
}

export function moveGroupInConfig(
  cfg: DashboardConfig,
  sourceGroupId: string,
  targetGroupId: string,
): boolean {
  return moveGroup(asConfigTree(cfg), sourceGroupId, targetGroupId);
}

export function moveSubgroupInConfig(
  cfg: DashboardConfig,
  sourceGroupId: string,
  sourceSubgroupId: string,
  targetGroupId: string,
  targetSubgroupId: string,
): boolean {
  return moveSubgroup(
    asConfigTree(cfg),
    sourceGroupId,
    sourceSubgroupId,
    targetGroupId,
    targetSubgroupId,
  );
}

export function moveItemToSubgroupEndInConfig(
  cfg: DashboardConfig,
  sourceGroupId: string,
  sourceSubgroupId: string,
  sourceItemId: string,
  targetGroupId: string,
  targetSubgroupId: string,
): boolean {
  return moveItemToSubgroupEnd(
    asConfigTree(cfg),
    sourceGroupId,
    sourceSubgroupId,
    sourceItemId,
    targetGroupId,
    targetSubgroupId,
  );
}

export function moveItemBeforeInConfig(
  cfg: DashboardConfig,
  sourceGroupId: string,
  sourceSubgroupId: string,
  sourceItemId: string,
  targetGroupId: string,
  targetSubgroupId: string,
  targetItemId: string,
): boolean {
  return moveItemBefore(
    asConfigTree(cfg),
    sourceGroupId,
    sourceSubgroupId,
    sourceItemId,
    targetGroupId,
    targetSubgroupId,
    targetItemId,
  );
}
