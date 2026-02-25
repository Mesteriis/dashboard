import type { DashboardItem, DashboardSubgroup } from "@/features/stores/dashboard/storeTypes/config";

export interface TreeGroupNode {
  key: string;
  id: string;
  title: string;
  icon: string | null;
  description: string;
  layout: string;
  subgroups: DashboardSubgroup[];
  __visibleCount?: number;
  [key: string]: unknown;
}

export type ItemWithOrigin = DashboardItem & {
  __originGroupKey: string;
  __originSubgroupId: string;
};

export interface SidebarIconGroupNode {
  key: string;
  type: "group";
  groupKey: string;
  group: TreeGroupNode;
}

export interface SidebarIconSubgroupNode {
  key: string;
  type: "subgroup";
  groupKey: string;
  subgroupId: string;
  subgroup: DashboardSubgroup;
}

export type SidebarIconNode = SidebarIconGroupNode | SidebarIconSubgroupNode;

export interface CommandPaletteEntry {
  id: string;
  type: "action" | "item";
  action: string;
  item: DashboardItem | null;
  title: string;
  titleLower: string;
  host: string;
  ip: string;
  site: string;
  tagsLower: string[];
  groupId: string;
  groupKey: string;
  groupTitle: string;
  subgroupId: string;
  subgroupTitle: string;
  pageId: string;
  searchBlob: string;
}

export interface WidgetRuntimeState {
  loading: boolean;
  error: string;
  payload: unknown;
  lastUpdated: number;
}

export interface WidgetStatListEntry {
  title: string;
  value: string;
}

export interface DragState {
  type: "group" | "subgroup" | "item" | "";
  groupId: string;
  subgroupId: string;
  itemId: string;
}

export interface SelectedNodeState {
  groupKey: string;
  subgroupId: string;
  itemId: string;
}

export interface ParticlesConfig {
  fps_limit: number;
  particles: {
    number: { value: number; density: { enable: boolean; value_area: number } };
    color: { value: string };
    shape: { type: string };
    opacity: { value: number; random: boolean };
    size: { value: number; random: boolean };
    line_linked: {
      enable: boolean;
      distance: number;
      color: string;
      opacity: number;
      width: number;
    };
    move: { enable: boolean; speed: number };
  };
  interactivity: {
    events: {
      onhover: { enable: boolean };
      onclick: { enable: boolean };
      resize: boolean;
    };
  };
  retina_detect: boolean;
}

export interface IconEntity {
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
