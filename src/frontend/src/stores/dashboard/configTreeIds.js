export function normalizeId(value, fallback = 'node') {
  const normalized = String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
  return normalized || fallback
}

export function makeUniqueId(base, existingIds) {
  const normalizedBase = normalizeId(base, 'node')
  let candidate = normalizedBase
  let index = 2

  while (existingIds.has(candidate)) {
    candidate = `${normalizedBase}-${index}`
    index += 1
  }

  return candidate
}

export function allSubgroupIds(cfg) {
  const ids = new Set()
  for (const group of cfg.groups || []) {
    for (const subgroup of group.subgroups || []) {
      ids.add(subgroup.id)
    }
  }
  return ids
}

export function allItemIds(cfg) {
  const ids = new Set()
  for (const group of cfg.groups || []) {
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        ids.add(item.id)
      }
    }
  }
  return ids
}

export function findGroup(cfg, groupId) {
  return (cfg.groups || []).find((group) => group.id === groupId) || null
}

export function findSubgroup(cfg, groupId, subgroupId) {
  const group = findGroup(cfg, groupId)
  if (!group) return null
  return (group.subgroups || []).find((subgroup) => subgroup.id === subgroupId) || null
}

export function isDirectGroupNode(group) {
  return String(group?.key || '').startsWith('group:')
}
