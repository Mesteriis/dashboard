import type { ServiceCardCoreV1 } from "@/shared/contracts/serviceCard";

export interface DashboardItem {
  id: string;
  title?: ServiceCardCoreV1["title"];
  url?: ServiceCardCoreV1["url"];
  check_url?: ServiceCardCoreV1["check_url"] | string;
  monitor_health?: boolean;
  tags?: ServiceCardCoreV1["tags"];
  open?: ServiceCardCoreV1["open"] | string;
  type?: ServiceCardCoreV1["type"] | string;
  plugin_blocks?: ServiceCardCoreV1["plugin_blocks"];
  [key: string]: unknown;
}

export interface DashboardSubgroup {
  id: string;
  key?: string;
  items: DashboardItem[];
  [key: string]: unknown;
}

export interface DashboardGroup {
  id: string;
  key?: string;
  subgroups: DashboardSubgroup[];
  [key: string]: unknown;
}

export interface DashboardLayoutWidget {
  id?: string;
  [key: string]: unknown;
}

export interface DashboardLayoutBlock {
  type?: string;
  group_ids?: string[];
  widgets?: DashboardLayoutWidget[];
  [key: string]: unknown;
}

export interface DashboardLayoutPage {
  id: string;
  blocks: DashboardLayoutBlock[];
  [key: string]: unknown;
}

export interface DashboardLayout {
  pages?: DashboardLayoutPage[];
  [key: string]: unknown;
}

export interface DashboardConfigTree {
  groups: DashboardGroup[];
  layout?: DashboardLayout;
  [key: string]: unknown;
}
