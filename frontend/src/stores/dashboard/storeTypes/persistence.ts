import type { SelectedNodeState } from "@/stores/dashboard/storeTypes/tree";

export interface PersistedUiState {
  activePageId?: string;
  treeFilter?: string;
  activeIndicatorViewId?: string;
  statsExpanded?: boolean;
  editMode?: boolean;
  serviceCardView?: string;
  serviceGroupingMode?: string;
  siteFilter?: string;
  sidebarView?: string;
  settingsPanelOpen?: boolean;
  selectedNode?: Partial<SelectedNodeState>;
  expandedGroups?: Record<string, boolean>;
  [key: string]: unknown;
}
