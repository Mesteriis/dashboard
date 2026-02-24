import type {
  DashboardConfigTree,
  DashboardGroup,
  DashboardSubgroup,
} from "@/stores/dashboard/types";

export function normalizeId(value: unknown, fallback = "node"): string {
  const normalized = String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return normalized || fallback;
}

export function makeUniqueId(base: unknown, existingIds: ReadonlySet<string>): string {
  const normalizedBase = normalizeId(base, "node");
  let candidate = normalizedBase;
  let index = 2;

  while (existingIds.has(candidate)) {
    candidate = `${normalizedBase}-${index}`;
    index += 1;
  }

  return candidate;
}

export function allSubgroupIds(cfg: DashboardConfigTree): Set<string> {
  const ids = new Set<string>();
  for (const group of cfg.groups ?? []) {
    for (const subgroup of group.subgroups ?? []) {
      const normalized = String(subgroup?.id || "").trim();
      if (normalized) ids.add(normalized);
    }
  }
  return ids;
}

export function allItemIds(cfg: DashboardConfigTree): Set<string> {
  const ids = new Set<string>();
  for (const group of cfg.groups ?? []) {
    for (const subgroup of group.subgroups ?? []) {
      for (const item of subgroup.items ?? []) {
        const normalized = String(item?.id || "").trim();
        if (normalized) ids.add(normalized);
      }
    }
  }
  return ids;
}

export function findGroup(
  cfg: DashboardConfigTree,
  groupId: string,
): DashboardGroup | null {
  const normalizedId = String(groupId || "");
  return (
    (cfg.groups ?? []).find(
      (group) => String(group?.id || "") === normalizedId,
    ) || null
  );
}

export function findSubgroup(
  cfg: DashboardConfigTree,
  groupId: string,
  subgroupId: string,
): DashboardSubgroup | null {
  const group = findGroup(cfg, groupId);
  if (!group) return null;
  const normalizedSubgroupId = String(subgroupId || "");
  return (
    (group.subgroups ?? []).find(
      (subgroup) => String(subgroup?.id || "") === normalizedSubgroupId,
    ) || null
  );
}

export function isDirectGroupNode(group: { key?: unknown } | null | undefined): boolean {
  return String(group?.key || "").startsWith("group:");
}
