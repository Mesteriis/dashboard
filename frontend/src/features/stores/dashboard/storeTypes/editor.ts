import type {
  CreateEntityKind,
  IframeReferrerPolicy,
  ItemEditorMode,
  ItemOpenMode,
  ItemType,
} from "@/features/stores/dashboard/storeTypes/primitives";

export interface ItemEditorForm {
  id: string;
  title: string;
  type: ItemType;
  url: string;
  icon: string;
  siteInput: string;
  tagsInput: string;
  open: ItemOpenMode;
  healthcheckEnabled: boolean;
  healthcheckUrl: string;
  healthcheckIntervalSec: number;
  healthcheckTimeoutMs: number;
  healthcheckTlsVerify: boolean;
  iframeSandboxMode:
    | "default"
    | "enabled"
    | "enabled_same_origin"
    | "enabled_scripts"
    | "enabled_scripts_same_origin"
    | "disabled";
  iframeSandboxExtraTokens: string[];
  iframeAllow: string[];
  iframeReferrerPolicy: string;
  authProfile: string;
  parentGroupId: string;
  parentSubgroupId: string;
}

export interface ItemEditorState {
  open: boolean;
  mode: ItemEditorMode;
  groupId: string;
  subgroupId: string;
  originalItemId: string;
  submitting: boolean;
  error: string;
  form: ItemEditorForm;
}

export interface CreateChooserState {
  open: boolean;
  groupId: string;
  subgroupId: string;
}

export interface CreateEntityForm {
  kind: CreateEntityKind;
  title: string;
  id: string;
  icon: string;
  description: string;
  parentDashboardId: string;
  parentGroupId: string;
  parentSubgroupId: string;
}

export interface CreateEntityState {
  open: boolean;
  submitting: boolean;
  error: string;
  form: CreateEntityForm;
}

export interface IframeModalState {
  open: boolean;
  title: string;
  src: string;
  allow: string;
  sandbox: boolean;
  sandboxAttribute: string;
  referrerPolicy: IframeReferrerPolicy;
  loading: boolean;
  error: string;
}
