import { allSubgroupIds } from './configTreeIds.js'

export function normalizeLayoutBlocks(cfg) {
  const validGroupIds = new Set((cfg.groups || []).map((group) => group.id))
  const validSubgroupIds = allSubgroupIds(cfg)
  const validGroupRefs = new Set([...validGroupIds, ...validSubgroupIds])

  for (const page of cfg.layout?.pages || []) {
    const nextBlocks = []

    for (const block of page.blocks || []) {
      if (block.type === 'groups') {
        block.group_ids = (block.group_ids || []).filter((groupId) => validGroupRefs.has(groupId))
        if (block.group_ids.length) {
          nextBlocks.push(block)
        }
        continue
      }

      if ((block.widgets || []).length) {
        nextBlocks.push(block)
      }
    }

    if (!nextBlocks.length && cfg.groups?.length) {
      nextBlocks.push({
        type: 'groups',
        group_ids: [cfg.groups[0].id],
      })
    }

    page.blocks = nextBlocks
  }
}

export function ensurePageGroupsReference(cfg, pageId, groupId) {
  const pagesList = cfg.layout?.pages || []
  if (!pagesList.length) return

  const page = pagesList.find((entry) => entry.id === pageId) || pagesList[0]
  let groupsBlock = page.blocks.find((block) => block.type === 'groups')

  if (!groupsBlock) {
    groupsBlock = {
      type: 'groups',
      group_ids: [groupId],
    }
    page.blocks.push(groupsBlock)
    return
  }

  if (!groupsBlock.group_ids.includes(groupId)) {
    groupsBlock.group_ids.push(groupId)
  }
}
