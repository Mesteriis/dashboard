import { allSubgroupIds } from "@/stores/dashboard/configTreeIds";
import type {
  DashboardConfigTree,
  DashboardLayoutBlock,
  DashboardLayoutPage,
  DashboardLayoutWidget,
} from "@/stores/dashboard/types";

type GroupBlock = DashboardLayoutBlock & { group_ids: string[] };
type WidgetsBlock = DashboardLayoutBlock & { widgets: DashboardLayoutWidget[] };

function asGroupBlock(block: DashboardLayoutBlock): GroupBlock {
  if (!Array.isArray(block.group_ids)) {
    block.group_ids = [];
  }
  return block as GroupBlock;
}

function asWidgetsBlock(block: DashboardLayoutBlock): WidgetsBlock {
  if (!Array.isArray(block.widgets)) {
    block.widgets = [];
  }
  return block as WidgetsBlock;
}

function ensurePageBlocks(page: DashboardLayoutPage): DashboardLayoutBlock[] {
  if (!Array.isArray(page.blocks)) {
    page.blocks = [];
  }
  return page.blocks;
}

export function normalizeLayoutBlocks(cfg: DashboardConfigTree): void {
  const validGroupIds = new Set(
    (cfg.groups ?? [])
      .map((group) => String(group?.id || "").trim())
      .filter(Boolean),
  );
  const validSubgroupIds = allSubgroupIds(cfg);
  const validGroupRefs = new Set([...validGroupIds, ...validSubgroupIds]);

  for (const page of cfg.layout?.pages ?? []) {
    const nextBlocks: DashboardLayoutBlock[] = [];

    for (const block of ensurePageBlocks(page)) {
      if (block.type === "groups") {
        const groupsBlock = asGroupBlock(block);
        groupsBlock.group_ids = groupsBlock.group_ids
          .map((groupId) => String(groupId || "").trim())
          .filter((groupId) => Boolean(groupId) && validGroupRefs.has(groupId));
        if (groupsBlock.group_ids.length) {
          nextBlocks.push(groupsBlock);
        }
        continue;
      }

      const widgetsBlock = asWidgetsBlock(block);
      if (widgetsBlock.widgets.length) {
        nextBlocks.push(widgetsBlock);
      }
    }

    page.blocks = nextBlocks;
  }
}

export function ensurePageGroupsReference(
  cfg: DashboardConfigTree,
  pageId: string,
  groupId: string,
): void {
  const normalizedPageId = String(pageId || "").trim();
  const normalizedGroupId = String(groupId || "").trim();
  if (!normalizedGroupId) return;

  const pagesList = cfg.layout?.pages ?? [];
  if (!pagesList.length) return;

  const page =
    pagesList.find(
      (entry) => String(entry?.id || "").trim() === normalizedPageId,
    ) || pagesList[0];
  const pageBlocks = ensurePageBlocks(page);
  let groupsBlock = pageBlocks.find((block) => block.type === "groups");

  if (!groupsBlock) {
    groupsBlock = {
      type: "groups",
      group_ids: [normalizedGroupId],
    };
    pageBlocks.push(groupsBlock);
    return;
  }

  const normalizedGroupsBlock = asGroupBlock(groupsBlock);
  const normalizedGroupIds = normalizedGroupsBlock.group_ids.map((id) =>
    String(id || "").trim(),
  );
  if (!normalizedGroupIds.includes(normalizedGroupId)) {
    normalizedGroupsBlock.group_ids.push(normalizedGroupId);
  }
}
