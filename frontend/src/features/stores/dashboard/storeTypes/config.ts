import type {
  DashboardItem as BaseDashboardItem,
  DashboardSubgroup as BaseDashboardSubgroup,
  DashboardGroup as BaseDashboardGroup,
} from "@/features/stores/dashboard/types";
import type { HealthLevel, ItemOpenMode, ItemType } from "@/features/stores/dashboard/storeTypes/primitives";

export interface DashboardTheme {
  accent?: string;
  background?: string;
  border?: string;
  card?: string;
  glow?: boolean;
  [key: string]: unknown;
}

export interface DashboardGrid {
  gap?: number;
  card_radius?: number;
  columns?: number;
  [key: string]: unknown;
}

export interface DashboardAppInfo {
  title?: string;
  tagline?: string;
  [key: string]: unknown;
}

export interface AuthProfile {
  id: string;
  [key: string]: unknown;
}

export interface DashboardIframeSecurity {
  default_sandbox?: boolean;
  [key: string]: unknown;
}

export interface DashboardSecurity {
  auth_profiles?: AuthProfile[];
  iframe?: DashboardIframeSecurity;
  [key: string]: unknown;
}

export interface DashboardUiConfig {
  theme?: DashboardTheme;
  grid?: DashboardGrid;
  [key: string]: unknown;
}

export interface DashboardItemHealthcheck {
  type?: string;
  url?: string;
  interval_sec?: number;
  timeout_ms?: number;
  tls_verify?: boolean;
  verify_tls?: boolean;
  insecure_skip_verify?: boolean;
  [key: string]: unknown;
}

export interface DashboardItemIframe {
  sandbox?: boolean | null;
  allow?: string[];
  referrer_policy?: string | null;
  [key: string]: unknown;
}

export interface DashboardItem extends BaseDashboardItem {
  id: string;
  title?: string;
  type?: ItemType | string;
  url?: string;
  check_url?: string;
  monitor_health?: boolean;
  icon?: string | null;
  site?: string | null;
  tags?: string[];
  open?: ItemOpenMode | string;
  healthcheck?: DashboardItemHealthcheck;
  iframe?: DashboardItemIframe;
  auth_profile?: string;
  __originGroupKey?: string;
  __originSubgroupId?: string;
  [key: string]: unknown;
}

export interface DashboardSubgroup extends BaseDashboardSubgroup {
  id: string;
  title?: string;
  icon?: string | null;
  items: DashboardItem[];
  [key: string]: unknown;
}

export interface DashboardGroup extends BaseDashboardGroup {
  id: string;
  title?: string;
  icon?: string | null;
  description?: string;
  layout?: string;
  site?: string | null;
  subgroups: DashboardSubgroup[];
  [key: string]: unknown;
}

export interface DashboardLayoutBlock {
  type?: string;
  group_ids?: string[];
  widgets?: string[];
  [key: string]: unknown;
}

export interface DashboardLayoutPage {
  id: string;
  title?: string;
  icon?: string;
  blocks?: DashboardLayoutBlock[];
  [key: string]: unknown;
}

export interface DashboardLayoutConfig {
  pages?: DashboardLayoutPage[];
  [key: string]: unknown;
}

export interface DashboardConfig {
  groups: DashboardGroup[];
  layout?: DashboardLayoutConfig;
  widgets?: DashboardWidget[];
  app?: DashboardAppInfo;
  ui?: DashboardUiConfig;
  security?: DashboardSecurity;
  [key: string]: unknown;
}

export interface DashboardHealthState {
  item_id: string;
  ok: boolean;
  status?: "online" | "degraded" | "down" | "unknown";
  checked_url?: string;
  status_code?: number | null;
  latency_ms?: number | null;
  success_rate?: number | null;
  consecutive_failures?: number | null;
  error?: string | null;
  reason?: string | null;
  level?: HealthLevel | string;
  [key: string]: unknown;
}

export interface DashboardHealthPayload {
  items?: Array<DashboardHealthState | null | undefined>;
  [key: string]: unknown;
}

export interface DashboardWidgetAction {
  id: string;
  title?: string;
  endpoint?: string;
  method?: string;
  [key: string]: unknown;
}

export interface DashboardWidgetColumn {
  key: string;
  title: string;
  [key: string]: unknown;
}

export interface DashboardWidgetMapping {
  value?: string;
  subtitle?: string;
  trend?: string;
  items?: string;
  item_title?: string;
  item_value?: string;
  rows?: string;
  [key: string]: unknown;
}

export interface DashboardWidgetData {
  endpoint?: string;
  refresh_sec?: number;
  mapping?: DashboardWidgetMapping;
  columns?: DashboardWidgetColumn[];
  actions?: DashboardWidgetAction[];
  [key: string]: unknown;
}

export interface DashboardWidget {
  id: string;
  title?: string;
  type?: string;
  data?: DashboardWidgetData;
  actions?: DashboardWidgetAction[];
  [key: string]: unknown;
}

export type DashboardWidgetResolved = DashboardWidget & {
  data: DashboardWidgetData & {
    columns: DashboardWidgetColumn[];
    actions: DashboardWidgetAction[];
  };
};
