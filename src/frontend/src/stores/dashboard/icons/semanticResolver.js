import { BRAND_ICON_BY_KEY } from './brandIcons.js'
import { FALLBACK_ICONS, ICON_BY_KEY, ICON_RULES } from './keywordIcons.js'

export function normalizeIconToken(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9а-яё._-]+/gi, ' ')
    .split(/[\s._-]+/)
    .filter(Boolean)
}

export function fromToken(token) {
  if (BRAND_ICON_BY_KEY[token]) return BRAND_ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(BRAND_ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }

  if (ICON_BY_KEY[token]) return ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }

  return null
}

export function pickSemanticIcon(sources, fallback) {
  for (const source of sources) {
    for (const token of normalizeIconToken(source)) {
      const icon = fromToken(token)
      if (icon) return icon
    }
  }

  const fullText = sources
    .map((source) => String(source || '').toLowerCase())
    .filter(Boolean)
    .join(' ')

  for (const rule of ICON_RULES) {
    if (rule.re.test(fullText)) return rule.icon
  }

  return fallback
}

export function resolvePageIcon(page) {
  return pickSemanticIcon([page?.icon, page?.title, page?.id], FALLBACK_ICONS.page)
}

export function resolveGroupIcon(group) {
  return pickSemanticIcon([group?.icon, group?.title, group?.id, group?.description], FALLBACK_ICONS.group)
}

export function resolveSubgroupIcon(subgroup) {
  return pickSemanticIcon([subgroup?.icon, subgroup?.title, subgroup?.id], FALLBACK_ICONS.subgroup)
}

export function resolveItemIcon(item) {
  return pickSemanticIcon(
    [item?.icon, item?.title, item?.id, item?.type, item?.url, ...(item?.tags || [])],
    item?.type === 'iframe' ? FALLBACK_ICONS.itemIframe : FALLBACK_ICONS.itemLink
  )
}

export function resolveWidgetIcon(widget) {
  return pickSemanticIcon([widget?.icon, widget?.title, widget?.id, widget?.type, widget?.data?.endpoint], FALLBACK_ICONS.widget)
}
