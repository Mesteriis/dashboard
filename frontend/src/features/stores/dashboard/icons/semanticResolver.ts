import type { Component } from "vue";
import { BRAND_ICON_BY_KEY } from "@/features/stores/dashboard/icons/brandIcons";
import { FALLBACK_ICONS, ICON_BY_KEY, ICON_RULES } from "@/features/stores/dashboard/icons/keywordIcons";

interface IconLikeEntity {
  icon?: unknown;
  title?: unknown;
  id?: unknown;
  type?: unknown;
  url?: unknown;
  description?: unknown;
  tags?: unknown[];
  data?: {
    endpoint?: unknown;
  };
}

export function normalizeIconToken(value: unknown): string[] {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9а-яё._-]+/gi, " ")
    .split(/[\s._-]+/)
    .filter(Boolean);
}

export function fromToken(token: string): Component | null {
  if (BRAND_ICON_BY_KEY[token]) return BRAND_ICON_BY_KEY[token];
  for (const [key, icon] of Object.entries(BRAND_ICON_BY_KEY)) {
    if (token.includes(key)) return icon;
  }

  if (ICON_BY_KEY[token]) return ICON_BY_KEY[token];
  for (const [key, icon] of Object.entries(ICON_BY_KEY)) {
    if (token.includes(key)) return icon;
  }

  return null;
}

export function pickSemanticIcon(
  sources: readonly unknown[],
  fallback: Component,
): Component {
  for (const source of sources) {
    for (const token of normalizeIconToken(source)) {
      const icon = fromToken(token);
      if (icon) return icon;
    }
  }

  const fullText = sources
    .map((source) => String(source || "").toLowerCase())
    .filter(Boolean)
    .join(" ");

  for (const rule of ICON_RULES) {
    if (rule.re.test(fullText)) return rule.icon;
  }

  return fallback;
}

export function resolvePageIcon(page: IconLikeEntity): Component {
  return pickSemanticIcon(
    [page?.icon, page?.title, page?.id],
    FALLBACK_ICONS.page,
  );
}

export function resolveGroupIcon(group: IconLikeEntity): Component {
  return pickSemanticIcon(
    [group?.icon, group?.title, group?.id, group?.description],
    FALLBACK_ICONS.group,
  );
}

export function resolveSubgroupIcon(subgroup: IconLikeEntity): Component {
  return pickSemanticIcon(
    [subgroup?.icon, subgroup?.title, subgroup?.id],
    FALLBACK_ICONS.subgroup,
  );
}

export function resolveItemIcon(item: IconLikeEntity): Component {
  return pickSemanticIcon(
    [
      item?.icon,
      item?.title,
      item?.id,
      item?.type,
      item?.url,
      ...(item?.tags || []),
    ],
    item?.type === "iframe"
      ? FALLBACK_ICONS.itemIframe
      : FALLBACK_ICONS.itemLink,
  );
}

export function resolveWidgetIcon(widget: IconLikeEntity): Component {
  return pickSemanticIcon(
    [
      widget?.icon,
      widget?.title,
      widget?.id,
      widget?.type,
      widget?.data?.endpoint,
    ],
    FALLBACK_ICONS.widget,
  );
}
