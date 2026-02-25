export type ServiceCardView = "detailed" | "tile" | "icon";
export type ServiceGroupingMode = "groups" | "tags_in_groups" | "tags" | "flat";
export type SidebarViewMode = "detailed" | "hidden";
export type SaveStatus = "idle" | "saving" | "saved" | "error";
export type ItemEditorMode = "create" | "edit";
export type ItemOpenMode = "new_tab" | "same_tab";
export type ItemType = "link" | "iframe";
export type CreateOption = "dashboard" | "group_or_subgroup" | "item";
export type CreateEntityKind = "dashboard" | "group" | "subgroup" | "item";
export type HealthLevel =
  | "online"
  | "recovering"
  | "degraded"
  | "down"
  | "unknown"
  | "indirect_failure";

export type IframeReferrerPolicy =
  | ""
  | "no-referrer"
  | "no-referrer-when-downgrade"
  | "origin"
  | "origin-when-cross-origin"
  | "same-origin"
  | "strict-origin"
  | "strict-origin-when-cross-origin"
  | "unsafe-url";
