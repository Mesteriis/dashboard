<template>
  <section class="plugin-universal-renderer">
    <section
      v-for="component in manifest.page.components"
      :key="component.id"
      class="plugin-component"
    >
      <header v-if="component.title" class="plugin-component-head">
        <h3>{{ component.title }}</h3>
      </header>

      <p v-if="component.type === 'text'" class="plugin-text">
        {{ component.text }}
      </p>

      <section v-else-if="component.type === 'data-table'" class="plugin-table">
        <header class="plugin-table-toolbar">
          <nav class="plugin-table-tabs" role="tablist" aria-label="Data view mode">
            <button
              v-if="!isCardsOnlyComponent(component)"
              class="plugin-table-tab"
              :class="{ active: resolveComponentView(component.id) === 'table' }"
              type="button"
              @click="setComponentView(component.id, 'table')"
            >
              Table
            </button>
            <button
              class="plugin-table-tab"
              :class="{ active: resolveComponentView(component.id) === 'cards' }"
              type="button"
              @click="setComponentView(component.id, 'cards')"
            >
              Cards
            </button>
            <button
              class="plugin-table-tab"
              :class="{ active: resolveComponentView(component.id) === 'settings' }"
              type="button"
              @click="setComponentView(component.id, 'settings')"
            >
              Settings
            </button>
          </nav>

          <div class="plugin-table-filters">
            <label
              v-if="resolveServiceFilterOptions(component).length"
              class="plugin-table-filter"
            >
              <span>Service</span>
              <select
                class="plugin-table-filter-select"
                :value="resolveServiceFilter(component.id)"
                @change="
                  setServiceFilter(
                    component.id,
                    ($event.target as HTMLSelectElement)?.value || SERVICE_FILTER_ALL,
                  )
                "
              >
                <option
                  v-for="option in resolveServiceFilterOptions(component)"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }} ({{ option.count }})
                </option>
              </select>
            </label>

            <label
              v-if="component.groupBy.length && !isCardsOnlyComponent(component)"
              class="plugin-table-filter plugin-table-filter-checkbox"
            >
              <input
                type="checkbox"
                :checked="isGroupingEnabled(component)"
                @change="
                  setGroupingEnabled(
                    component.id,
                    ($event.target as HTMLInputElement)?.checked ?? false,
                  )
                "
              />
              <span>Group rows</span>
            </label>
          </div>
        </header>

        <section v-if="stateByComponentId[component.id]?.loading" class="plugin-state">
          {{ component.loadingText || "Loading..." }}
        </section>
        <section
          v-else-if="stateByComponentId[component.id]?.error"
          class="plugin-state plugin-state-error"
        >
          {{ component.errorText || "Failed to load data" }}
          <small>{{ stateByComponentId[component.id]?.error }}</small>
        </section>
        <section
          v-else-if="!resolveFilteredIndexedRows(component).length"
          class="plugin-state"
        >
          {{
            resolveServiceFilter(component.id) === SERVICE_FILTER_ALL
              ? component.emptyText || "No data"
              : "No rows for selected service filter"
          }}
        </section>

        <div
          v-else-if="
            !isCardsOnlyComponent(component) &&
            resolveComponentView(component.id) === 'table'
          "
          class="plugin-table-wrap"
        >
          <table>
            <thead>
              <tr>
                <th v-for="column in component.columns" :key="column.key">
                  {{ column.label }}
                </th>
                <th
                  v-if="component.rowActions.length"
                  class="plugin-table-actions-col"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="entry in resolveTableDisplayRows(component)"
                :key="entry.key"
              >
                <tr v-if="entry.kind === 'group'" class="plugin-table-group-row">
                  <td :colspan="component.columns.length + (component.rowActions.length ? 1 : 0)">
                    <button
                      class="plugin-table-group-toggle"
                      type="button"
                      @click="
                        toggleGroupCollapsed(
                          component.id,
                          entry.key,
                          entry.depth,
                          entry.collapsed,
                        )
                      "
                    >
                      <span class="plugin-table-group-caret">
                        {{ entry.collapsed ? "▸" : "▾" }}
                      </span>
                      <span
                        class="plugin-table-group-label"
                        :style="resolveGroupLabelStyle(entry.depth)"
                      >
                        {{ entry.label }}
                      </span>
                      <span class="plugin-table-group-count">
                        {{ entry.count }}
                      </span>
                    </button>
                  </td>
                </tr>
                <tr v-else>
                  <td
                    v-for="(column, columnIndex) in component.columns"
                    :key="column.key"
                    :style="
                      resolveCellStyle(
                        columnIndex,
                        entry.depth,
                        component.groupBy.length,
                        isGroupingEnabled(component),
                      )
                    "
                  >
                    {{ resolveTableCellValue(component, entry.row, column.key) }}
                  </td>
                  <td
                    v-if="component.rowActions.length"
                    class="plugin-table-actions-cell"
                  >
                    <div
                      v-for="action in resolveSupportedRowActions(component.id, entry.row)"
                      :key="action.id"
                      class="plugin-table-action"
                    >
                      <button
                        class="ghost plugin-table-action-btn"
                        type="button"
                        :disabled="
                          isRowActionBusy(component.id, entry.rowIndex, action.id)
                        "
                        @click="
                          runRowAction(
                            component.id,
                            entry.rowIndex,
                            action.id,
                            action,
                            entry.row,
                          )
                        "
                      >
                        {{
                          resolveRowActionLabel(
                            component.id,
                            entry.rowIndex,
                            action.id,
                            action.label,
                          )
                        }}
                      </button>
                      <small
                        v-if="
                          resolveRowActionError(component.id, entry.rowIndex, action.id)
                        "
                        class="plugin-table-action-error"
                      >
                        {{
                          resolveRowActionError(
                            component.id,
                            entry.rowIndex,
                            action.id,
                          )
                        }}
                      </small>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <section
          v-else-if="
            isCardsOnlyComponent(component) ||
            resolveComponentView(component.id) === 'cards'
          "
          class="plugin-cards-grid"
        >
          <UiDataTable
            v-if="isCardsOnlyComponent(component)"
            :rows="resolveHostInventoryRows(component)"
            :columns="AUTODISCOVER_HOST_TABLE_COLUMNS"
            row-key="key"
            :show-search="true"
            :show-filters="true"
            :show-export="false"
            :show-pagination="true"
            :page-size="20"
            :row-clickable="true"
            max-height="min(70vh, 760px)"
            @row-click="openHostDetailsFromInventoryRow(component, $event)"
          />

          <article
            v-else
            v-for="hostCard in resolveHostCards(component)"
            :key="hostCard.key"
            class="plugin-data-card panel"
            role="button"
            tabindex="0"
            @click="openHostDetailsModal(component, hostCard)"
            @keydown.enter.prevent="openHostDetailsModal(component, hostCard)"
            @keydown.space.prevent="openHostDetailsModal(component, hostCard)"
          >
            <header class="plugin-data-card-head">
              <h4>{{ hostCard.hostLabel }}</h4>
              <p class="plugin-data-card-subtitle">
                {{ hostCard.hostname || "Hostname: unknown" }}
              </p>
            </header>

            <dl class="plugin-data-card-meta">
              <div class="plugin-data-card-meta-row">
                <dt>Services</dt>
                <dd>{{ hostCard.services.length }}</dd>
              </div>
              <div class="plugin-data-card-meta-row">
                <dt>Preview</dt>
                <dd>{{ resolveHostServicesPreview(hostCard) }}</dd>
              </div>
            </dl>

            <footer class="plugin-data-card-actions">
              <button class="ghost plugin-table-action-btn" type="button">
                Open services
              </button>
            </footer>
          </article>
        </section>

        <section v-else class="plugin-settings-grid">
          <article class="panel plugin-settings-card">
            <h4>Display settings</h4>
            <p>
              Rows:
              <strong>{{ resolveFilteredIndexedRows(component).length }}</strong>
              /
              <strong>{{ rowsByComponentId[component.id]?.length || 0 }}</strong>
            </p>
            <p>
              Active filter:
              <code>{{ resolveServiceFilter(component.id) }}</code>
            </p>
            <div class="plugin-settings-actions">
              <button
                class="ghost"
                type="button"
                @click="setServiceFilter(component.id, SERVICE_FILTER_ALL)"
              >
                Reset service filter
              </button>
              <button
                class="ghost"
                type="button"
                @click="resetGroupState(component.id)"
              >
                Reset groups
              </button>
            </div>
          </article>

          <article class="panel plugin-settings-card">
            <h4>Plugin settings</h4>
            <p><strong>ID:</strong> {{ manifest.plugin_id }}</p>
            <p><strong>Version:</strong> {{ manifest.version }}</p>
            <p><strong>Capabilities:</strong> {{ manifest.capabilities.length }}</p>
            <p class="plugin-settings-note">
              Runtime plugin settings are managed by plugin backend contracts.
            </p>
          </article>
        </section>
      </section>

      <section v-else class="plugin-state plugin-state-error">
        Unsupported component type: <code>{{ component.originalType }}</code>
      </section>
    </section>

    <BaseModal
      :open="hostDetailsModal.open"
      backdrop-class="plugin-modal-backdrop"
      modal-class="plugin-modal plugin-host-details-modal"
      @backdrop="closeHostDetailsModal"
    >
      <header class="plugin-modal-head">
        <h3>{{ hostDetailsModal.hostLabel }}</h3>
        <button class="ghost" type="button" @click="closeHostDetailsModal">
          Close
        </button>
      </header>
      <p class="plugin-modal-kicker">
        {{ hostDetailsModal.hostname || "Hostname: unknown" }} •
        {{ hostDetailsModal.services.length }} services
      </p>
      <div class="plugin-modal-body plugin-host-details-body">
        <article class="panel plugin-host-summary-card">
          <div class="plugin-host-summary-main">
            <p class="plugin-host-summary-label">Host</p>
            <h4 class="plugin-host-summary-title">
              {{ hostDetailsModal.hostLabel }}
            </h4>
            <p class="plugin-host-summary-subtitle">
              {{ hostDetailsModal.hostname || "Hostname: unknown" }}
            </p>
          </div>
          <div class="plugin-host-summary-aside">
            <span class="plugin-host-summary-pill">
              {{ hostDetailsModal.services.length }} services
            </span>
            <span class="plugin-host-summary-pill plugin-host-summary-pill-muted">
              autodiscover
            </span>
          </div>
        </article>

        <section
          v-if="hostDetailsModal.services.length"
          class="plugin-host-services-grid"
        >
          <article
            v-for="entry in hostDetailsModal.services"
            :key="`${hostDetailsModal.componentId}:host-service:${entry.rowIndex}`"
            class="panel plugin-host-service-card"
          >
            <header class="plugin-host-service-head">
              <div class="plugin-host-service-title-wrap">
                <h4 class="plugin-host-service-title">
                  {{ asCell(entry.row.service) || "Unknown service" }}
                </h4>
                <p
                  class="plugin-host-service-subtitle"
                  :class="{
                    'plugin-host-service-subtitle-muted': !asCell(entry.row.title),
                  }"
                >
                  {{ asCell(entry.row.title) || "No title metadata" }}
                </p>
              </div>
              <span class="plugin-host-service-port">
                {{ resolveServicePortLabel(entry.row.port) }}
              </span>
            </header>

            <div class="plugin-host-service-body">
              <p class="plugin-host-service-field-label">URL</p>
              <p class="plugin-host-service-url">
                {{ asCell(entry.row.url) || "Not available" }}
              </p>
            </div>

            <footer class="plugin-host-service-actions">
              <div class="plugin-host-service-action-list">
                <div
                  v-for="
                    action in resolveSupportedRowActions(
                      hostDetailsModal.componentId,
                      entry.row,
                    )
                  "
                  :key="action.id"
                  class="plugin-table-action plugin-host-service-action"
                >
                  <button
                    class="ghost plugin-table-action-btn"
                    type="button"
                    :disabled="
                      isRowActionBusy(
                        hostDetailsModal.componentId,
                        entry.rowIndex,
                        action.id,
                      )
                    "
                    @click="
                      runRowAction(
                        hostDetailsModal.componentId,
                        entry.rowIndex,
                        action.id,
                        action,
                        entry.row,
                      )
                    "
                  >
                    {{
                      resolveRowActionLabel(
                        hostDetailsModal.componentId,
                        entry.rowIndex,
                        action.id,
                        action.label,
                      )
                    }}
                  </button>
                  <small
                    v-if="
                      resolveRowActionError(
                        hostDetailsModal.componentId,
                        entry.rowIndex,
                        action.id,
                      )
                    "
                    class="plugin-table-action-error"
                  >
                    {{
                      resolveRowActionError(
                        hostDetailsModal.componentId,
                        entry.rowIndex,
                        action.id,
                      )
                    }}
                  </small>
                </div>
                <small
                  v-if="
                    !resolveSupportedRowActions(
                      hostDetailsModal.componentId,
                      entry.row,
                    ).length
                  "
                  class="plugin-table-action-error"
                >
                  No supported link protocol for dashboard item.
                </small>
              </div>
            </footer>
          </article>
        </section>

        <section v-else class="plugin-state">
          No services available for this host.
        </section>
      </div>
    </BaseModal>

    <BaseModal
      :open="addToDashboardForm.open"
      backdrop-class="plugin-modal-backdrop"
      modal-class="plugin-modal plugin-modal-wide"
      @backdrop="closeAddToDashboardForm"
    >
      <header class="plugin-modal-head">
        <h3>Add Service To Dashboard</h3>
        <button class="ghost" type="button" @click="closeAddToDashboardForm">
          Close
        </button>
      </header>

      <section v-if="addToDashboardForm.loading" class="plugin-state">
        Loading dashboard config...
      </section>

      <form v-else class="plugin-add-form" @submit.prevent="submitAddToDashboardForm">
        <section class="plugin-add-form-grid">
          <label class="plugin-add-field">
            <span>Dashboard page</span>
            <select v-model="addToDashboardForm.pageId" class="plugin-add-input">
              <option v-for="page in resolvePageOptions()" :key="page.id" :value="page.id">
                {{ page.title }}
              </option>
            </select>
          </label>

          <label class="plugin-add-field">
            <span>Group</span>
            <select
              v-model="addToDashboardForm.groupChoice"
              class="plugin-add-input"
              @change="handleGroupChoiceChanged"
            >
              <option v-for="group in resolveGroupOptions()" :key="group.id" :value="group.id">
                {{ group.title }}
              </option>
              <option value="__new__">Create new group...</option>
            </select>
          </label>

          <label v-if="addToDashboardForm.groupChoice === '__new__'" class="plugin-add-field">
            <span>New group ID</span>
            <input v-model="addToDashboardForm.newGroupId" class="plugin-add-input" />
          </label>

          <label v-if="addToDashboardForm.groupChoice === '__new__'" class="plugin-add-field">
            <span>New group title</span>
            <input v-model="addToDashboardForm.newGroupTitle" class="plugin-add-input" />
          </label>

          <label class="plugin-add-field">
            <span>Subgroup</span>
            <select v-model="addToDashboardForm.subgroupChoice" class="plugin-add-input">
              <option
                v-for="subgroup in resolveSubgroupOptions(addToDashboardForm.groupChoice)"
                :key="subgroup.id"
                :value="subgroup.id"
              >
                {{ subgroup.title }}
              </option>
              <option value="__new__">Create new subgroup...</option>
            </select>
          </label>

          <label v-if="addToDashboardForm.subgroupChoice === '__new__'" class="plugin-add-field">
            <span>New subgroup ID</span>
            <input v-model="addToDashboardForm.newSubgroupId" class="plugin-add-input" />
          </label>

          <label v-if="addToDashboardForm.subgroupChoice === '__new__'" class="plugin-add-field">
            <span>New subgroup title</span>
            <input v-model="addToDashboardForm.newSubgroupTitle" class="plugin-add-input" />
          </label>

          <label class="plugin-add-field">
            <span>Item title</span>
            <input v-model="addToDashboardForm.itemTitle" class="plugin-add-input" />
          </label>

          <label class="plugin-add-field">
            <span>URL</span>
            <input v-model="addToDashboardForm.itemUrl" class="plugin-add-input" />
          </label>

          <label class="plugin-add-field">
            <span>Tags (comma separated)</span>
            <input v-model="addToDashboardForm.itemTags" class="plugin-add-input" />
          </label>

          <label class="plugin-add-field">
            <span>Open mode</span>
            <select v-model="addToDashboardForm.openMode" class="plugin-add-input">
              <option value="new_tab">New tab</option>
              <option value="same_tab">Same tab</option>
            </select>
          </label>
        </section>

        <p v-if="addToDashboardForm.error" class="plugin-add-error">
          {{ addToDashboardForm.error }}
        </p>

        <footer class="plugin-add-actions">
          <button class="ghost" type="button" @click="closeAddToDashboardForm">
            Cancel
          </button>
          <button
            class="ghost plugin-add-primary"
            type="submit"
            :disabled="addToDashboardForm.submitting"
          >
            {{ addToDashboardForm.submitting ? "Saving..." : "Add to Dashboard" }}
          </button>
        </footer>
      </form>
    </BaseModal>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import {
  fetchDashboardConfig,
  updateDashboardConfig,
} from "@/features/services/dashboardApi";
import { requestJson } from "@/features/services/requestJson";
import BaseModal from "@/ui/overlays/BaseModal.vue";
import {
  resolveResponsePath,
  type PluginDataTableComponentV1,
  type PluginPageManifestV1,
  type PluginRowActionAddToDashboardV1,
} from "@/features/plugins/manifest";

interface DataState {
  loading: boolean;
  error?: string;
}

interface RowActionState {
  busy: boolean;
  added?: boolean;
  message?: string;
  error?: string;
}

interface TableIndexedRow {
  rowIndex: number;
  row: Record<string, unknown>;
}

interface TableGroupRowDisplay {
  kind: "group";
  key: string;
  depth: number;
  label: string;
  count: number;
  collapsed: boolean;
}

interface TableDataRowDisplay {
  kind: "data";
  key: string;
  depth: number;
  rowIndex: number;
  row: Record<string, unknown>;
}

type TableRowDisplay = TableGroupRowDisplay | TableDataRowDisplay;
type ComponentViewMode = "table" | "cards" | "settings";

interface ServiceFilterOption {
  value: string;
  label: string;
  count: number;
}

interface HostCardDisplay {
  key: string;
  hostLabel: string;
  hostname: string;
  services: TableIndexedRow[];
}

interface HostInventoryRow extends HostCardDisplay {
  macAddress: string;
  vendor: string;
  deviceType: string;
  portsLabel: string;
}

interface HostFilterOption {
  value: string;
  label: string;
  count: number;
}

interface AddToDashboardFormState {
  open: boolean;
  loading: boolean;
  submitting: boolean;
  error: string;
  componentId: string;
  rowIndex: number;
  actionId: string;
  action: PluginRowActionAddToDashboardV1 | null;
  row: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  pageId: string;
  groupChoice: string;
  newGroupId: string;
  newGroupTitle: string;
  subgroupChoice: string;
  newSubgroupId: string;
  newSubgroupTitle: string;
  itemTitle: string;
  itemUrl: string;
  itemTags: string;
  openMode: "new_tab" | "same_tab";
}

interface HostDetailsModalState {
  open: boolean;
  componentId: string;
  hostLabel: string;
  hostname: string;
  services: TableIndexedRow[];
}

const props = defineProps<{
  manifest: PluginPageManifestV1;
}>();

const SERVICE_FILTER_ALL = "__all__";
const HOST_FILTER_ALL = "__all__";
const LINKABLE_URL_SCHEMES = new Set([
  "http",
  "https",
  "ssh",
  "ftp",
  "sftp",
  "ftps",
  "rdp",
  "vnc",
  "telnet",
  "smb",
  "nfs",
]);
const stateByComponentId = reactive<Record<string, DataState>>({});
const rowsByComponentId = reactive<Record<string, Array<Record<string, unknown>>>>(
  {},
);
const rowActionStateByKey = reactive<Record<string, RowActionState>>({});
const collapsedGroupStateByKey = reactive<Record<string, boolean>>({});
const componentViewById = reactive<Record<string, ComponentViewMode>>({});
const serviceFilterById = reactive<Record<string, string>>({});
const groupingEnabledById = reactive<Record<string, boolean>>({});
const hostPortFilterById = reactive<Record<string, string>>({});
const hostVendorFilterById = reactive<Record<string, string>>({});
const hostIpMacSearchById = reactive<Record<string, string>>({});
const hostDetailsModal = reactive<HostDetailsModalState>({
  open: false,
  componentId: "",
  hostLabel: "",
  hostname: "",
  services: [],
});
const addToDashboardForm = reactive<AddToDashboardFormState>({
  open: false,
  loading: false,
  submitting: false,
  error: "",
  componentId: "",
  rowIndex: -1,
  actionId: "",
  action: null,
  row: null,
  config: null,
  pageId: "",
  groupChoice: "",
  newGroupId: "",
  newGroupTitle: "",
  subgroupChoice: "",
  newSubgroupId: "",
  newSubgroupTitle: "",
  itemTitle: "",
  itemUrl: "",
  itemTags: "",
  openMode: "new_tab",
});

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

function asNumber(value: unknown): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

function asCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function resolveServicePortLabel(value: unknown): string {
  const normalized = asString(value);
  if (!normalized) return "Port —";
  return `Port ${normalized}`;
}

function resolveComponentView(componentId: string): ComponentViewMode {
  return componentViewById[componentId] || "table";
}

function setComponentView(componentId: string, mode: ComponentViewMode): void {
  componentViewById[componentId] = mode;
}

function isCardsOnlyComponent(component: PluginDataTableComponentV1): boolean {
  return (
    props.manifest.plugin_id === "autodiscover" &&
    component.id === "autodiscover-services-table"
  );
}

function resolveServiceField(component: PluginDataTableComponentV1): string | null {
  const direct = component.columns.find((column) => column.key.toLowerCase() === "service");
  if (direct) return direct.key;
  const fuzzy = component.columns.find((column) => column.key.toLowerCase().includes("service"));
  if (fuzzy) return fuzzy.key;
  const rows = rowsByComponentId[component.id] || [];
  if (rows.some((entry) => asString(entry.service))) return "service";
  return null;
}

function resolveServiceFilter(componentId: string): string {
  return serviceFilterById[componentId] || SERVICE_FILTER_ALL;
}

function setServiceFilter(componentId: string, value: string): void {
  serviceFilterById[componentId] = value || SERVICE_FILTER_ALL;
}

function resolveServiceFilterOptions(
  component: PluginDataTableComponentV1,
): ServiceFilterOption[] {
  const field = resolveServiceField(component);
  if (!field) return [];

  const rows = rowsByComponentId[component.id] || [];
  const counts = new Map<string, number>();
  for (const row of rows) {
    const token = asString(row[field]) || "Unknown";
    counts.set(token, (counts.get(token) || 0) + 1);
  }

  const options: ServiceFilterOption[] = [
    {
      value: SERVICE_FILTER_ALL,
      label: "All",
      count: rows.length,
    },
  ];
  for (const [value, count] of counts.entries()) {
    options.push({ value, label: value, count });
  }
  options.sort((left, right) => {
    if (left.value === SERVICE_FILTER_ALL) return -1;
    if (right.value === SERVICE_FILTER_ALL) return 1;
    return left.label.localeCompare(right.label);
  });
  return options;
}

function resolveIndexedRows(component: PluginDataTableComponentV1): TableIndexedRow[] {
  const rows = rowsByComponentId[component.id] || [];
  return rows.map((row, rowIndex) => ({ row, rowIndex }));
}

function resolveFilteredIndexedRows(
  component: PluginDataTableComponentV1,
): TableIndexedRow[] {
  const indexedRows = resolveIndexedRows(component);
  const selected = resolveServiceFilter(component.id);
  if (selected === SERVICE_FILTER_ALL) return indexedRows;

  const field = resolveServiceField(component);
  if (!field) return indexedRows;
  return indexedRows.filter((entry) => (asString(entry.row[field]) || "Unknown") === selected);
}

function isGroupingEnabled(component: PluginDataTableComponentV1): boolean {
  if (!component.groupBy.length) return false;
  const activeState = groupingEnabledById[component.id];
  if (activeState === undefined) return true;
  return activeState;
}

function setGroupingEnabled(componentId: string, enabled: boolean): void {
  groupingEnabledById[componentId] = enabled;
}

function resolveCellStyle(
  columnIndex: number,
  depth: number,
  groupLevels: number,
  groupingEnabled: boolean,
): Record<string, string> | undefined {
  if (columnIndex !== 0 || !groupingEnabled || groupLevels <= 0 || depth <= 0) return undefined;
  return { paddingLeft: `${10 + depth * 14}px` };
}

function resolveGroupLabelStyle(depth: number): Record<string, string> | undefined {
  if (depth <= 0) return undefined;
  return { paddingLeft: `${depth * 14}px` };
}

function groupPathKey(componentId: string, path: string[]): string {
  if (!path.length) return `${componentId}:group`;
  return `${componentId}:group:${path.join("|")}`;
}

function isGroupCollapsed(groupKey: string, depth: number): boolean {
  const explicit = collapsedGroupStateByKey[groupKey];
  if (explicit !== undefined) return explicit;
  return depth > 0;
}

function toggleGroupCollapsed(
  componentId: string,
  groupKey: string,
  depth: number,
  collapsed: boolean,
): void {
  if (!groupKey.startsWith(`${componentId}:group`)) return;
  const current = collapsed ?? isGroupCollapsed(groupKey, depth);
  collapsedGroupStateByKey[groupKey] = !current;
}

function resetGroupState(componentId: string): void {
  const prefix = `${componentId}:group`;
  for (const key of Object.keys(collapsedGroupStateByKey)) {
    if (!key.startsWith(prefix)) continue;
    delete collapsedGroupStateByKey[key];
  }
}

function formatGroupValue(value: unknown, emptyLabel: string): string {
  const normalized = asString(value);
  if (normalized) return normalized;
  return emptyLabel || "Unknown";
}

function resolveTableCellValue(
  component: PluginDataTableComponentV1,
  row: Record<string, unknown>,
  columnKey: string,
): string {
  if (
    isGroupingEnabled(component) &&
    component.groupBy.some((groupLevel) => groupLevel.field === columnKey)
  ) {
    return "";
  }
  return asCell(row[columnKey]);
}

function resolveHostLabel(row: Record<string, unknown>): string {
  return asString(row.host_ip || row.host || row.ip) || "Unknown host";
}

function compareHostLabels(left: string, right: string): number {
  const parseIpv4 = (value: string): number[] | null => {
    const parts = value.split(".");
    if (parts.length !== 4) return null;
    const parsed = parts.map((part) => Number(part));
    if (
      parsed.some(
        (segment) => !Number.isInteger(segment) || segment < 0 || segment > 255,
      )
    ) {
      return null;
    }
    return parsed;
  };

  const leftIpv4 = parseIpv4(left);
  const rightIpv4 = parseIpv4(right);
  if (leftIpv4 && rightIpv4) {
    for (let index = 0; index < 4; index += 1) {
      if (leftIpv4[index] === rightIpv4[index]) continue;
      return leftIpv4[index] - rightIpv4[index];
    }
    return 0;
  }
  return left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
}

function resolveHostCards(component: PluginDataTableComponentV1): HostCardDisplay[] {
  const grouped = new Map<string, HostCardDisplay>();
  for (const entry of resolveFilteredIndexedRows(component)) {
    const hostLabel = resolveHostLabel(entry.row);
    const key = `${component.id}:host:${hostLabel}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        key,
        hostLabel,
        hostname: asString(entry.row.hostname),
        services: [],
      });
    }
    const hostCard = grouped.get(key);
    if (!hostCard) continue;
    if (!hostCard.hostname) {
      hostCard.hostname = asString(entry.row.hostname);
    }
    hostCard.services.push(entry);
  }
  return Array.from(grouped.values()).sort((left, right) =>
    compareHostLabels(left.hostLabel, right.hostLabel),
  );
}

function resolveHostServicesPreview(card: HostCardDisplay): string {
  const unique = Array.from(
    new Set(card.services.map((entry) => asString(entry.row.service) || "unknown")),
  );
  if (!unique.length) return "No services";
  return unique.slice(0, 4).join(", ");
}

function resolveHostInventoryValue(
  card: HostCardDisplay,
  candidates: string[],
): string {
  for (const entry of card.services) {
    for (const field of candidates) {
      const token = asString(entry.row[field]);
      if (token) return token;
    }
  }
  return "";
}

function resolveHostPortsLabel(services: TableIndexedRow[]): string {
  const ports = Array.from(
    new Set(
      services
        .map((entry) => asString(entry.row.port))
        .filter(Boolean),
    ),
  );
  ports.sort((left, right) => {
    const leftNumber = Number(left);
    const rightNumber = Number(right);
    const leftIsNumber = Number.isFinite(leftNumber);
    const rightIsNumber = Number.isFinite(rightNumber);
    if (leftIsNumber && rightIsNumber) return leftNumber - rightNumber;
    if (leftIsNumber) return -1;
    if (rightIsNumber) return 1;
    return left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
  });
  return ports.length ? ports.join(", ") : "—";
}

function resolveHostInventoryRows(
  component: PluginDataTableComponentV1,
): HostInventoryRow[] {
  return resolveHostCards(component).map((card) => {
    const macAddress =
      resolveHostInventoryValue(card, ["host_mac", "mac_address", "mac"]) || "—";
    const vendor =
      resolveHostInventoryValue(card, ["mac_vendor", "vendor", "manufacturer"]) ||
      "—";
    const deviceType =
      resolveHostInventoryValue(card, ["device_type", "type", "host_type"]) || "—";
    return {
      ...card,
      macAddress,
      vendor,
      deviceType,
      portsLabel: resolveHostPortsLabel(card.services),
    };
  });
}

function resolveHostPortFilter(componentId: string): string {
  return hostPortFilterById[componentId] || HOST_FILTER_ALL;
}

function setHostPortFilter(componentId: string, value: string): void {
  hostPortFilterById[componentId] = value || HOST_FILTER_ALL;
}

function resolveHostVendorFilter(componentId: string): string {
  return hostVendorFilterById[componentId] || HOST_FILTER_ALL;
}

function setHostVendorFilter(componentId: string, value: string): void {
  hostVendorFilterById[componentId] = value || HOST_FILTER_ALL;
}

function resolveHostIpMacSearch(componentId: string): string {
  return hostIpMacSearchById[componentId] || "";
}

function setHostIpMacSearch(componentId: string, value: string): void {
  hostIpMacSearchById[componentId] = asString(value);
}

function resolveHostPortFilterOptions(
  component: PluginDataTableComponentV1,
): HostFilterOption[] {
  const rows = resolveHostInventoryRows(component);
  const counts = new Map<string, number>();
  for (const row of rows) {
    const uniquePorts = new Set(
      row.services
        .map((entry) => asString(entry.row.port))
        .filter(Boolean),
    );
    for (const port of uniquePorts) {
      counts.set(port, (counts.get(port) || 0) + 1);
    }
  }
  const options: HostFilterOption[] = [
    { value: HOST_FILTER_ALL, label: "All ports", count: rows.length },
  ];
  for (const [value, count] of counts.entries()) {
    options.push({ value, label: value, count });
  }
  options.sort((left, right) => {
    if (left.value === HOST_FILTER_ALL) return -1;
    if (right.value === HOST_FILTER_ALL) return 1;
    return Number(left.value) - Number(right.value);
  });
  return options;
}

function resolveHostVendorFilterOptions(
  component: PluginDataTableComponentV1,
): HostFilterOption[] {
  const rows = resolveHostInventoryRows(component);
  const counts = new Map<string, number>();
  for (const row of rows) {
    const token = row.vendor || "—";
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  const options: HostFilterOption[] = [
    { value: HOST_FILTER_ALL, label: "All vendors", count: rows.length },
  ];
  for (const [value, count] of counts.entries()) {
    options.push({ value, label: value, count });
  }
  options.sort((left, right) => {
    if (left.value === HOST_FILTER_ALL) return -1;
    if (right.value === HOST_FILTER_ALL) return 1;
    return left.label.localeCompare(right.label, undefined, {
      sensitivity: "base",
      numeric: true,
    });
  });
  return options;
}

function resolveFilteredHostInventoryRows(
  component: PluginDataTableComponentV1,
): HostInventoryRow[] {
  const rows = resolveHostInventoryRows(component);
  const selectedPort = resolveHostPortFilter(component.id);
  const selectedVendor = resolveHostVendorFilter(component.id);
  const searchToken = resolveHostIpMacSearch(component.id).toLowerCase();

  return rows.filter((row) => {
    if (selectedPort !== HOST_FILTER_ALL) {
      const hasPort = row.services.some(
        (entry) => asString(entry.row.port) === selectedPort,
      );
      if (!hasPort) return false;
    }
    if (selectedVendor !== HOST_FILTER_ALL) {
      const vendor = row.vendor || "—";
      if (vendor !== selectedVendor) return false;
    }
    if (searchToken) {
      const ip = row.hostLabel.toLowerCase();
      const mac = row.macAddress.toLowerCase();
      if (!ip.includes(searchToken) && !mac.includes(searchToken)) return false;
    }
    return true;
  });
}

function openHostDetailsModal(
  component: PluginDataTableComponentV1,
  hostCard: HostCardDisplay,
): void {
  hostDetailsModal.open = true;
  hostDetailsModal.componentId = component.id;
  hostDetailsModal.hostLabel = hostCard.hostLabel;
  hostDetailsModal.hostname = hostCard.hostname;
  hostDetailsModal.services = hostCard.services;
}

function closeHostDetailsModal(): void {
  hostDetailsModal.open = false;
  hostDetailsModal.componentId = "";
  hostDetailsModal.hostLabel = "";
  hostDetailsModal.hostname = "";
  hostDetailsModal.services = [];
}

function resolveComponentRowActions(componentId: string): PluginRowActionAddToDashboardV1[] {
  const component = props.manifest.page.components.find(
    (entry): entry is PluginDataTableComponentV1 =>
      entry.type === "data-table" && entry.id === componentId,
  );
  if (!component) return [];
  return component.rowActions;
}

function resolveTableDisplayRows(
  component: PluginDataTableComponentV1,
): TableRowDisplay[] {
  const indexedRows = resolveFilteredIndexedRows(component);
  if (!component.groupBy.length || !isGroupingEnabled(component)) {
    return indexedRows.map((entry) => ({
      kind: "data",
      key: `${component.id}:row:${entry.rowIndex}`,
      depth: 0,
      rowIndex: entry.rowIndex,
      row: entry.row,
    }));
  }

  const displayRows: TableRowDisplay[] = [];

  const walk = (level: number, chunk: TableIndexedRow[], path: string[]) => {
    if (level >= component.groupBy.length) {
      for (const entry of chunk) {
        displayRows.push({
          kind: "data",
          key: `${component.id}:row:${entry.rowIndex}`,
          depth: level,
          rowIndex: entry.rowIndex,
          row: entry.row,
        });
      }
      return;
    }

    const groupLevel = component.groupBy[level];
    const grouped = new Map<string, TableIndexedRow[]>();
    const order: string[] = [];

    for (const entry of chunk) {
      const key = formatGroupValue(entry.row[groupLevel.field], groupLevel.emptyLabel);
      if (!grouped.has(key)) {
        grouped.set(key, []);
        order.push(key);
      }
      grouped.get(key)?.push(entry);
    }

    for (const groupValue of order) {
      const nestedRows = grouped.get(groupValue) || [];
      const nestedPath = [...path, `${level}:${groupValue}`];
      const key = groupPathKey(component.id, nestedPath);
      const collapsed = isGroupCollapsed(key, level);

      displayRows.push({
        kind: "group",
        key,
        depth: level,
        label: `${groupLevel.label}: ${groupValue}`,
        count: nestedRows.length,
        collapsed,
      });

      if (!collapsed) {
        walk(level + 1, nestedRows, nestedPath);
      }
    }
  };

  walk(0, indexedRows, []);
  return displayRows;
}

function rowActionKey(
  componentId: string,
  rowIndex: number,
  actionId: string,
): string {
  return `${componentId}:${rowIndex}:${actionId}`;
}

function isRowActionBusy(
  componentId: string,
  rowIndex: number,
  actionId: string,
): boolean {
  return Boolean(rowActionStateByKey[rowActionKey(componentId, rowIndex, actionId)]?.busy);
}

function resolveRowActionLabel(
  componentId: string,
  rowIndex: number,
  actionId: string,
  fallbackLabel: string,
): string {
  const state = rowActionStateByKey[rowActionKey(componentId, rowIndex, actionId)];
  if (!state) return fallbackLabel;
  if (state.busy) return "Adding...";
  if (state.added) return state.message || "Added";
  return fallbackLabel;
}

function resolveRowActionError(
  componentId: string,
  rowIndex: number,
  actionId: string,
): string {
  return String(
    rowActionStateByKey[rowActionKey(componentId, rowIndex, actionId)]?.error ||
      "",
  );
}

function cloneConfig<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function normalizeId(raw: string, fallback: string): string {
  const normalized = raw
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+/, "")
    .replace(/-+$/, "");
  if (normalized) return normalized;
  return fallback;
}

function makeUniqueId(base: string, existing: Set<string>): string {
  if (!existing.has(base)) return base;
  let counter = 2;
  while (existing.has(`${base}-${counter}`)) {
    counter += 1;
  }
  return `${base}-${counter}`;
}

function collectItemIds(config: Record<string, unknown>): Set<string> {
  const ids = new Set<string>();
  const groups = Array.isArray(config.groups) ? config.groups : [];
  for (const groupEntry of groups) {
    const group = asRecord(groupEntry);
    if (!group) continue;
    const subgroups = Array.isArray(group.subgroups) ? group.subgroups : [];
    for (const subgroupEntry of subgroups) {
      const subgroup = asRecord(subgroupEntry);
      if (!subgroup) continue;
      const items = Array.isArray(subgroup.items) ? subgroup.items : [];
      for (const itemEntry of items) {
        const item = asRecord(itemEntry);
        if (!item) continue;
        const itemId = asString(item.id);
        if (itemId) ids.add(itemId);
      }
    }
  }
  return ids;
}

function resolveServiceSchemeFromMetadata(
  row: Record<string, unknown>,
  port: number | null,
): string | null {
  const explicitScheme = asString(row.scheme).toLowerCase();
  if (explicitScheme && LINKABLE_URL_SCHEMES.has(explicitScheme)) {
    return explicitScheme;
  }

  const service = asString(row.service).toLowerCase();
  if (service.includes("https")) return "https";
  if (service.includes("http")) return "http";
  if (service.includes("sftp")) return "sftp";
  if (service.includes("ftps")) return "ftps";
  if (service.includes("ftp")) return "ftp";
  if (service.includes("ssh")) return "ssh";
  if (service.includes("rdp")) return "rdp";
  if (service.includes("vnc")) return "vnc";
  if (service.includes("telnet")) return "telnet";
  if (service.includes("smb") || service.includes("cifs")) return "smb";
  if (service.includes("nfs")) return "nfs";

  if (port === null) return null;
  const map = new Map<number, string>([
    [80, "http"],
    [443, "https"],
    [8080, "http"],
    [8443, "https"],
    [9443, "https"],
    [22, "ssh"],
    [21, "ftp"],
    [990, "ftps"],
    [3389, "rdp"],
    [5900, "vnc"],
    [23, "telnet"],
    [445, "smb"],
    [2049, "nfs"],
  ]);
  return map.get(port) || null;
}

function isLinkableScheme(scheme: string): boolean {
  return LINKABLE_URL_SCHEMES.has(scheme.toLowerCase());
}

function resolveServiceUrl(
  row: Record<string, unknown>,
  action: PluginRowActionAddToDashboardV1,
): string {
  const explicitUrl = asString(row[action.urlField]);
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(explicitUrl)) {
    const scheme = explicitUrl.split(":")[0]?.toLowerCase() || "";
    return isLinkableScheme(scheme) ? explicitUrl : "";
  }

  const host = asString(row.host_ip || row.host || row.ip);
  const port = asNumber(row.port);
  const scheme = resolveServiceSchemeFromMetadata(row, port);

  if (explicitUrl && explicitUrl.startsWith("//")) {
    if (!scheme || !["http", "https", "ftp", "ftps"].includes(scheme)) return "";
    return `${scheme}:${explicitUrl}`;
  }
  if (explicitUrl && /^[a-z0-9.-]+(?::\d+)?(?:\/.*)?$/i.test(explicitUrl)) {
    if (!scheme) return "";
    const sanitized = explicitUrl.replace(/^\/+/, "");
    if (["http", "https", "ftp", "ftps"].includes(scheme)) {
      return `${scheme}://${sanitized}`;
    }
    return `${scheme}://${sanitized}`;
  }

  if (!host || !scheme) return "";

  if (scheme === "http") {
    if (!port || port === 80) return `http://${host}/`;
    return `http://${host}:${port}/`;
  }
  if (scheme === "https") {
    if (!port || port === 443) return `https://${host}/`;
    return `https://${host}:${port}/`;
  }
  if (scheme === "ftp") {
    if (!port || port === 21) return `ftp://${host}/`;
    return `ftp://${host}:${port}/`;
  }
  if (scheme === "ftps") {
    if (!port || port === 990) return `ftps://${host}/`;
    return `ftps://${host}:${port}/`;
  }
  if (port) return `${scheme}://${host}:${port}`;
  return `${scheme}://${host}`;
}

function isRowActionSupported(
  action: PluginRowActionAddToDashboardV1,
  row: Record<string, unknown>,
): boolean {
  if (action.type !== "add-to-dashboard") {
    return false;
  }
  return Boolean(resolveServiceUrl(row, action));
}

function resolveSupportedRowActions(
  componentId: string,
  row: Record<string, unknown>,
): PluginRowActionAddToDashboardV1[] {
  const actions = resolveComponentRowActions(componentId);
  if (props.manifest.plugin_id !== "autodiscover") return actions;
  return actions.filter((action) => isRowActionSupported(action, row));
}

function interpolateTemplate(
  template: string,
  row: Record<string, unknown>,
): string {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_chunk, token: string) => {
    return asString(row[token]);
  });
}

function resolveItemTitle(
  row: Record<string, unknown>,
  action: PluginRowActionAddToDashboardV1,
): string {
  if (action.titleTemplate) {
    const fromTemplate = asString(interpolateTemplate(action.titleTemplate, row));
    if (fromTemplate) return fromTemplate;
  }
  if (action.titleField) {
    const fromField = asString(row[action.titleField]);
    if (fromField) return fromField;
  }
  const service = asString(row.service || "service");
  const host = asString(row.host_ip || row.host || row.ip || "host");
  const port = asString(row.port);
  return `${service} ${host}${port ? `:${port}` : ""}`;
}

function resolveItemTags(
  row: Record<string, unknown>,
  action: PluginRowActionAddToDashboardV1,
): string[] {
  const tags: string[] = ["source:plugin-autodiscover"];
  for (const field of action.tagsFromFields) {
    const value = asString(row[field]);
    if (!value) continue;
    tags.push(`${field}:${value}`);
  }
  return Array.from(new Set(tags));
}

interface AddToDashboardMutationOptions {
  pageId?: string;
  groupId?: string;
  groupTitle?: string;
  subgroupId?: string;
  subgroupTitle?: string;
  itemTitle?: string;
  itemUrl?: string;
  itemTags?: string[];
  openMode?: "new_tab" | "same_tab";
}

function ensureLayoutPages(config: Record<string, unknown>): Array<Record<string, unknown>> {
  if (!asRecord(config.layout)) {
    config.layout = {};
  }
  const layout = config.layout as Record<string, unknown>;
  if (!Array.isArray(layout.pages)) {
    layout.pages = [];
  }
  const pages = layout.pages as Array<Record<string, unknown>>;
  if (!pages.length) {
    pages.push({
      id: "home",
      title: "Home",
      blocks: [],
    });
  }
  return pages;
}

function ensureGroupsList(config: Record<string, unknown>): Array<Record<string, unknown>> {
  if (!Array.isArray(config.groups)) {
    config.groups = [];
  }
  return config.groups as Array<Record<string, unknown>>;
}

function resolvePageOptions(): Array<{ id: string; title: string }> {
  const config = addToDashboardForm.config;
  if (!config) return [];
  const pages = ensureLayoutPages(config);
  return pages.map((page, index) => {
    const id = asString(page.id) || `page-${index + 1}`;
    const title = asString(page.title) || id;
    return { id, title };
  });
}

function resolveGroupOptions(): Array<{ id: string; title: string }> {
  const config = addToDashboardForm.config;
  if (!config) return [];
  const groups = ensureGroupsList(config);
  return groups.map((group) => {
    const id = asString(group.id);
    const title = asString(group.title) || id;
    return { id, title };
  });
}

function resolveGroupTitleById(groupId: string): string {
  const match = resolveGroupOptions().find((entry) => entry.id === groupId);
  return match?.title || groupId;
}

function resolveSubgroupOptions(groupId: string): Array<{ id: string; title: string }> {
  if (!groupId || groupId === "__new__") return [];
  const config = addToDashboardForm.config;
  if (!config) return [];
  const groups = ensureGroupsList(config);
  const group = groups.find((entry) => asString(entry.id) === groupId);
  if (!group) return [];
  const subgroups = Array.isArray(group.subgroups) ? group.subgroups : [];
  return subgroups
    .map((subgroup) => asRecord(subgroup))
    .filter((subgroup): subgroup is Record<string, unknown> => !!subgroup)
    .map((subgroup) => {
      const id = asString(subgroup.id);
      const title = asString(subgroup.title) || id;
      return { id, title };
    });
}

function resolveSubgroupTitleById(groupId: string, subgroupId: string): string {
  const match = resolveSubgroupOptions(groupId).find((entry) => entry.id === subgroupId);
  return match?.title || subgroupId;
}

function handleGroupChoiceChanged(): void {
  const options = resolveSubgroupOptions(addToDashboardForm.groupChoice);
  if (!options.length) {
    addToDashboardForm.subgroupChoice = "__new__";
    return;
  }
  const exists = options.some((entry) => entry.id === addToDashboardForm.subgroupChoice);
  if (!exists) {
    addToDashboardForm.subgroupChoice = options[0].id;
  }
}

function parseTagsInput(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean),
    ),
  );
}

function mutateConfigWithRowAction(
  config: Record<string, unknown>,
  row: Record<string, unknown>,
  action: PluginRowActionAddToDashboardV1,
  options: AddToDashboardMutationOptions = {},
): "added" | "exists" {
  const groups = ensureGroupsList(config);
  const pages = ensureLayoutPages(config);
  const targetPageId = asString(options.pageId) || asString(action.targetPageId);
  const page =
    (targetPageId
      ? pages.find((entry) => asString(entry.id) === targetPageId)
      : null) || pages[0];

  if (!Array.isArray(page.blocks)) {
    page.blocks = [];
  }
  const blocks = page.blocks as Array<Record<string, unknown>>;
  let groupsBlock = blocks.find((entry) => asString(entry.type) === "groups");
  if (!groupsBlock) {
    groupsBlock = { type: "groups", group_ids: [] };
    blocks.push(groupsBlock);
  }
  if (!Array.isArray(groupsBlock.group_ids)) {
    groupsBlock.group_ids = [];
  }
  const groupIds = groupsBlock.group_ids as string[];
  const targetGroupId = asString(options.groupId) || action.targetGroupId;
  const targetGroupTitle = asString(options.groupTitle) || action.targetGroupTitle;
  let group = groups.find((entry) => asString(entry.id) === targetGroupId);
  if (!group) {
    group = {
      id: targetGroupId,
      title: targetGroupTitle,
      icon: "radar",
      description: "Added from autodiscover plugin",
      layout: "auto",
      subgroups: [],
    };
    groups.push(group);
  }
  if (!groupIds.includes(targetGroupId)) {
    groupIds.push(targetGroupId);
  }

  if (!Array.isArray(group.subgroups)) {
    group.subgroups = [];
  }
  const subgroups = group.subgroups as Array<Record<string, unknown>>;
  const subgroupTitle =
    asString(options.subgroupTitle) || asString(row[action.subgroupField]) || "Autodiscovered";
  const subgroupId =
    asString(options.subgroupId) ||
    normalizeId(`auto-${subgroupTitle}`, `auto-${targetGroupId}`);
  let subgroup = subgroups.find((entry) => asString(entry.id) === subgroupId);
  if (!subgroup) {
    subgroup = {
      id: subgroupId,
      title: subgroupTitle,
      items: [],
    };
    subgroups.push(subgroup);
  }
  if (!Array.isArray(subgroup.items)) {
    subgroup.items = [];
  }
  const items = subgroup.items as Array<Record<string, unknown>>;

  const nextUrl = asString(options.itemUrl) || resolveServiceUrl(row, action);
  if (!nextUrl) {
    throw new Error("Cannot resolve service URL for dashboard item");
  }
  const existingByUrl = items.find((entry) => asString(entry.url) === nextUrl);
  if (existingByUrl) return "exists";

  const nextTitle = asString(options.itemTitle) || resolveItemTitle(row, action);
  const itemId = makeUniqueId(
    normalizeId(`${subgroupId}-${nextTitle}`, `${subgroupId}-service`),
    collectItemIds(config),
  );
  const nextTags = Array.isArray(options.itemTags) && options.itemTags.length
    ? options.itemTags
    : resolveItemTags(row, action);
  items.push({
    id: itemId,
    type: "link",
    title: nextTitle,
    url: nextUrl,
    icon: null,
    site: null,
    tags: nextTags,
    open: options.openMode || action.openMode,
  });

  return "added";
}

function closeAddToDashboardForm(): void {
  addToDashboardForm.open = false;
  addToDashboardForm.loading = false;
  addToDashboardForm.submitting = false;
  addToDashboardForm.error = "";
  addToDashboardForm.componentId = "";
  addToDashboardForm.rowIndex = -1;
  addToDashboardForm.actionId = "";
  addToDashboardForm.action = null;
  addToDashboardForm.row = null;
  addToDashboardForm.config = null;
  addToDashboardForm.pageId = "";
  addToDashboardForm.groupChoice = "";
  addToDashboardForm.newGroupId = "";
  addToDashboardForm.newGroupTitle = "";
  addToDashboardForm.subgroupChoice = "";
  addToDashboardForm.newSubgroupId = "";
  addToDashboardForm.newSubgroupTitle = "";
  addToDashboardForm.itemTitle = "";
  addToDashboardForm.itemUrl = "";
  addToDashboardForm.itemTags = "";
  addToDashboardForm.openMode = "new_tab";
}

async function openAddToDashboardForm(
  componentId: string,
  rowIndex: number,
  actionId: string,
  action: PluginRowActionAddToDashboardV1,
  row: Record<string, unknown>,
): Promise<void> {
  if (hostDetailsModal.open) {
    closeHostDetailsModal();
  }
  closeAddToDashboardForm();
  addToDashboardForm.open = true;
  addToDashboardForm.loading = true;
  addToDashboardForm.componentId = componentId;
  addToDashboardForm.rowIndex = rowIndex;
  addToDashboardForm.actionId = actionId;
  addToDashboardForm.action = action;
  addToDashboardForm.row = row;

  try {
    const currentConfig = (await fetchDashboardConfig()) as Record<string, unknown>;
    addToDashboardForm.config = cloneConfig(currentConfig);

    const pageOptions = resolvePageOptions();
    const defaultPageId =
      pageOptions.find((page) => page.id === asString(action.targetPageId))?.id ||
      pageOptions[0]?.id ||
      "home";
    addToDashboardForm.pageId = defaultPageId;

    const groupOptions = resolveGroupOptions();
    const defaultGroup = groupOptions.find((group) => group.id === action.targetGroupId);
    addToDashboardForm.groupChoice = defaultGroup ? defaultGroup.id : "__new__";
    addToDashboardForm.newGroupId = action.targetGroupId;
    addToDashboardForm.newGroupTitle = action.targetGroupTitle;

    const subgroupTitle = asString(row[action.subgroupField]) || "Autodiscovered";
    const subgroupId = normalizeId(
      `auto-${subgroupTitle}`,
      `auto-${action.targetGroupId}`,
    );
    const targetGroupIdForSubgroup =
      addToDashboardForm.groupChoice === "__new__"
        ? action.targetGroupId
        : addToDashboardForm.groupChoice;
    const subgroupOptions = resolveSubgroupOptions(targetGroupIdForSubgroup);
    const defaultSubgroup = subgroupOptions.find((subgroup) => subgroup.id === subgroupId);
    addToDashboardForm.subgroupChoice = defaultSubgroup ? defaultSubgroup.id : "__new__";
    addToDashboardForm.newSubgroupId = subgroupId;
    addToDashboardForm.newSubgroupTitle = subgroupTitle;

    addToDashboardForm.itemTitle = resolveItemTitle(row, action);
    addToDashboardForm.itemUrl = resolveServiceUrl(row, action);
    addToDashboardForm.itemTags = resolveItemTags(row, action).join(", ");
    addToDashboardForm.openMode = action.openMode;
    addToDashboardForm.error = "";
  } catch (error: unknown) {
    addToDashboardForm.error = error instanceof Error ? error.message : "Failed to load dashboard config";
  } finally {
    addToDashboardForm.loading = false;
  }
}

async function submitAddToDashboardForm(): Promise<void> {
  const action = addToDashboardForm.action;
  const row = addToDashboardForm.row;
  const config = addToDashboardForm.config;
  if (!action || !row || !config) return;

  const key = rowActionKey(
    addToDashboardForm.componentId,
    addToDashboardForm.rowIndex,
    addToDashboardForm.actionId,
  );
  addToDashboardForm.submitting = true;
  addToDashboardForm.error = "";
  rowActionStateByKey[key] = { busy: true };

  try {
    const nextConfig = cloneConfig(config);
    const groupId =
      addToDashboardForm.groupChoice === "__new__"
        ? asString(addToDashboardForm.newGroupId) || action.targetGroupId
        : addToDashboardForm.groupChoice;
    const groupTitle =
      addToDashboardForm.groupChoice === "__new__"
        ? asString(addToDashboardForm.newGroupTitle) || action.targetGroupTitle
        : resolveGroupTitleById(addToDashboardForm.groupChoice);
    const subgroupId =
      addToDashboardForm.subgroupChoice === "__new__"
        ? asString(addToDashboardForm.newSubgroupId) ||
          normalizeId(
            `auto-${asString(addToDashboardForm.newSubgroupTitle) || "autodiscovered"}`,
            `auto-${groupId}`,
          )
        : addToDashboardForm.subgroupChoice;
    const subgroupTitle =
      addToDashboardForm.subgroupChoice === "__new__"
        ? asString(addToDashboardForm.newSubgroupTitle) || "Autodiscovered"
        : resolveSubgroupTitleById(groupId, addToDashboardForm.subgroupChoice);

    const outcome = mutateConfigWithRowAction(nextConfig, row, action, {
      pageId: addToDashboardForm.pageId,
      groupId,
      groupTitle,
      subgroupId,
      subgroupTitle,
      itemTitle: asString(addToDashboardForm.itemTitle),
      itemUrl: asString(addToDashboardForm.itemUrl),
      itemTags: parseTagsInput(addToDashboardForm.itemTags),
      openMode: addToDashboardForm.openMode,
    });
    if (outcome !== "exists") {
      await updateDashboardConfig(nextConfig);
    }
    rowActionStateByKey[key] = {
      busy: false,
      added: true,
      message: outcome === "exists" ? "Already added" : "Added",
    };
    closeAddToDashboardForm();
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Action failed";
    addToDashboardForm.error = message;
    rowActionStateByKey[key] = {
      busy: false,
      added: false,
      error: message,
    };
  } finally {
    addToDashboardForm.submitting = false;
  }
}

async function runRowAction(
  componentId: string,
  rowIndex: number,
  actionId: string,
  action: PluginRowActionAddToDashboardV1,
  row: Record<string, unknown>,
): Promise<void> {
  const key = rowActionKey(componentId, rowIndex, actionId);
  try {
    if (action.type !== "add-to-dashboard") {
      throw new Error(`Unsupported row action type: ${action.type}`);
    }
    if (props.manifest.plugin_id === "autodiscover" && !isRowActionSupported(action, row)) {
      throw new Error("Service does not expose a supported link protocol");
    }
    await openAddToDashboardForm(componentId, rowIndex, actionId, action, row);
  } catch (error: unknown) {
    rowActionStateByKey[key] = {
      busy: false,
      added: false,
      error: error instanceof Error ? error.message : "Action failed",
    };
  }
}

async function loadTable(component: PluginDataTableComponentV1): Promise<void> {
  stateByComponentId[component.id] = { loading: true };
  rowsByComponentId[component.id] = [];

  try {
    const payload = await requestJson(component.dataSource.endpoint, {
      method: component.dataSource.method,
      ...(component.dataSource.method === "POST"
        ? {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(component.dataSource.body || {}),
          }
        : {}),
    });
    const resolved = resolveResponsePath(payload, component.dataSource.response_path);
    const rows = Array.isArray(resolved) ? resolved : [];
    rowsByComponentId[component.id] = rows
      .map((entry) => asRecord(entry))
      .filter((entry): entry is Record<string, unknown> => !!entry);

    if (!componentViewById[component.id]) {
      componentViewById[component.id] = isCardsOnlyComponent(component)
        ? "cards"
        : "table";
    } else if (
      isCardsOnlyComponent(component) &&
      componentViewById[component.id] === "table"
    ) {
      componentViewById[component.id] = "cards";
    }
    if (serviceFilterById[component.id] === undefined) {
      serviceFilterById[component.id] = SERVICE_FILTER_ALL;
    }
    if (component.groupBy.length && groupingEnabledById[component.id] === undefined) {
      groupingEnabledById[component.id] = true;
    }
    const selectedFilter = resolveServiceFilter(component.id);
    const selectedExists = resolveServiceFilterOptions(component).some(
      (option) => option.value === selectedFilter,
    );
    if (!selectedExists) {
      serviceFilterById[component.id] = SERVICE_FILTER_ALL;
    }
    if (isCardsOnlyComponent(component)) {
      if (hostPortFilterById[component.id] === undefined) {
        hostPortFilterById[component.id] = HOST_FILTER_ALL;
      }
      if (hostVendorFilterById[component.id] === undefined) {
        hostVendorFilterById[component.id] = HOST_FILTER_ALL;
      }
      if (hostIpMacSearchById[component.id] === undefined) {
        hostIpMacSearchById[component.id] = "";
      }
      const selectedPort = resolveHostPortFilter(component.id);
      const selectedPortExists = resolveHostPortFilterOptions(component).some(
        (option) => option.value === selectedPort,
      );
      if (!selectedPortExists) {
        hostPortFilterById[component.id] = HOST_FILTER_ALL;
      }
      const selectedVendor = resolveHostVendorFilter(component.id);
      const selectedVendorExists = resolveHostVendorFilterOptions(component).some(
        (option) => option.value === selectedVendor,
      );
      if (!selectedVendorExists) {
        hostVendorFilterById[component.id] = HOST_FILTER_ALL;
      }
    }

    stateByComponentId[component.id] = { loading: false };
  } catch (error: unknown) {
    stateByComponentId[component.id] = {
      loading: false,
      error: error instanceof Error ? error.message : "Request failed",
    };
  }
}

onMounted(async () => {
  const components = props.manifest.page.components.filter(
    (entry): entry is PluginDataTableComponentV1 => entry.type === "data-table",
  );
  await Promise.all(components.map((component) => loadTable(component)));
});
</script>

<style scoped>
.plugin-universal-renderer {
  display: grid;
  gap: 12px;
}

.plugin-component {
  padding: 0;
  min-width: 0;
}

.plugin-component-head h3 {
  margin: 0 0 10px;
}

.plugin-text {
  margin: 0;
  color: rgba(196, 214, 236, 0.88);
}

.plugin-state {
  color: rgba(183, 202, 224, 0.84);
}

.plugin-state-error {
  color: rgba(250, 173, 173, 0.92);
}

.plugin-state-error small {
  display: block;
  margin-top: 8px;
  opacity: 0.9;
}

.plugin-table {
  display: grid;
  gap: 10px;
}

.plugin-table-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plugin-table-tabs {
  display: inline-flex;
  gap: 6px;
}

.plugin-table-tab {
  min-height: 30px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(81, 116, 149, 0.28);
  background: rgba(6, 17, 30, 0.62);
  color: rgba(188, 209, 233, 0.92);
  cursor: pointer;
}

.plugin-table-tab.active {
  border-color: rgba(110, 181, 230, 0.52);
  background: rgba(23, 58, 89, 0.42);
  color: rgba(226, 240, 255, 0.96);
}

.plugin-table-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-table-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(182, 205, 230, 0.9);
  font-size: 12px;
}

.plugin-table-filter-select {
  min-height: 28px;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid rgba(84, 118, 149, 0.36);
  background: rgba(7, 19, 31, 0.9);
  color: rgba(210, 226, 243, 0.94);
}

.plugin-table-filter-checkbox input {
  margin: 0;
}

.plugin-table-wrap {
  overflow: auto;
  max-height: min(68vh, 720px);
  border-radius: var(--ui-radius);
  scrollbar-gutter: stable both-edges;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

th,
td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(97, 131, 163, 0.18);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

th {
  color: rgba(197, 218, 242, 0.9);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(6, 17, 30, 0.95);
  backdrop-filter: blur(2px);
}

.plugin-table-group-row td {
  padding: 0;
  border-bottom: 1px solid rgba(97, 131, 163, 0.18);
  background: rgba(9, 27, 44, 0.72);
}

.plugin-table-group-toggle {
  width: 100%;
  min-height: 34px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  color: rgba(208, 224, 245, 0.92);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.plugin-table-group-toggle:hover {
  background: rgba(87, 128, 163, 0.12);
}

.plugin-table-group-caret {
  width: 14px;
  color: rgba(159, 192, 226, 0.85);
  flex: 0 0 14px;
}

.plugin-table-group-label {
  flex: 1 1 auto;
}

.plugin-table-group-count {
  min-width: 26px;
  height: 20px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid rgba(88, 124, 158, 0.34);
  color: rgba(194, 214, 236, 0.9);
  font-size: 12px;
  background: rgba(8, 19, 30, 0.72);
}

.plugin-table-actions-col {
  width: 190px;
}

.plugin-table-actions-cell {
  white-space: normal;
  overflow: visible;
  text-overflow: initial;
}

.plugin-table-action-btn {
  min-height: 28px;
  padding: 3px 8px;
  font-size: 12px;
}

.plugin-table-action + .plugin-table-action {
  margin-top: 6px;
}

.plugin-table-action-error {
  display: block;
  margin-top: 4px;
  color: rgba(250, 173, 173, 0.95);
  font-size: 11px;
}

.plugin-cards-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}

.plugin-cards-grid-hosts {
  display: grid;
}

.plugin-hosts-table-wrap {
  padding: 10px;
  overflow: hidden;
  border: 1px solid rgba(84, 124, 156, 0.32);
  background: linear-gradient(160deg, rgba(9, 24, 39, 0.9), rgba(5, 16, 27, 0.9));
  display: grid;
  gap: 8px;
}

.plugin-hosts-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.plugin-hosts-filter {
  display: grid;
  gap: 5px;
  color: rgba(182, 205, 230, 0.9);
  font-size: 12px;
}

.plugin-hosts-filter-search {
  min-width: 0;
}

.plugin-hosts-filter-search .plugin-add-input {
  min-width: 0;
}

.plugin-hosts-table-scroll {
  overflow: auto;
  max-height: min(70vh, 760px);
  scrollbar-gutter: stable both-edges;
  border-radius: 10px;
  border: 1px solid rgba(79, 116, 147, 0.26);
  background: rgba(5, 15, 25, 0.64);
}

.plugin-hosts-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.plugin-hosts-table th,
.plugin-hosts-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(91, 126, 158, 0.2);
  text-align: left;
  vertical-align: top;
}

.plugin-hosts-table th {
  color: rgba(197, 218, 242, 0.9);
  font-weight: 600;
  font-size: 12px;
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(6, 17, 30, 0.95);
  backdrop-filter: blur(2px);
}

.plugin-hosts-row {
  cursor: pointer;
  transition: background 120ms ease;
}

.plugin-hosts-row:hover {
  background: rgba(86, 130, 167, 0.12);
}

.plugin-hosts-ip {
  color: rgba(218, 233, 250, 0.96);
  font-weight: 600;
}

.plugin-hosts-mac,
.plugin-hosts-hostname,
.plugin-hosts-type,
.plugin-hosts-vendor {
  color: rgba(188, 209, 231, 0.92);
}

.plugin-hosts-ports {
  color: rgba(211, 228, 246, 0.95);
  overflow-wrap: anywhere;
}

.plugin-hosts-actions-col {
  width: 150px;
}

.plugin-hosts-actions-cell {
  white-space: nowrap;
}

.plugin-hosts-empty {
  text-align: center;
  color: rgba(176, 198, 223, 0.86);
}

.plugin-data-card {
  padding: 12px;
  display: grid;
  gap: 10px;
  cursor: pointer;
}

.plugin-data-card-head h4 {
  margin: 0;
  font-size: 15px;
}

.plugin-data-card-subtitle {
  margin: 4px 0 0;
  color: rgba(173, 195, 219, 0.86);
  font-size: 12px;
  word-break: break-all;
}

.plugin-data-card-meta {
  margin: 0;
  display: grid;
  gap: 4px;
}

.plugin-data-card-meta-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 8px;
}

.plugin-data-card-meta dt {
  color: rgba(166, 188, 212, 0.82);
  font-size: 12px;
}

.plugin-data-card-meta dd {
  margin: 0;
  color: rgba(214, 229, 245, 0.95);
  overflow-wrap: anywhere;
}

.plugin-data-card-actions {
  margin-top: 4px;
}

.plugin-settings-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.plugin-settings-card {
  padding: 12px;
}

.plugin-settings-card h4 {
  margin: 0 0 10px;
}

.plugin-settings-card p {
  margin: 0 0 8px;
  color: rgba(188, 209, 232, 0.9);
}

.plugin-settings-note {
  color: rgba(164, 188, 215, 0.78);
  font-size: 12px;
}

.plugin-settings-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 120;
  padding: 20px;
  display: grid;
  place-items: center;
  background: rgba(2, 9, 16, 0.72);
  backdrop-filter: blur(4px);
}

.plugin-modal {
  width: min(980px, 100%);
  max-height: min(88vh, 920px);
  overflow: auto;
  border-radius: 14px;
  border: 1px solid rgba(83, 124, 154, 0.34);
  background: linear-gradient(180deg, rgba(8, 21, 34, 0.98), rgba(5, 15, 26, 0.98));
  padding: 14px;
}

.plugin-host-details-modal {
  width: min(1120px, 100%);
  padding: 14px;
  border-color: rgba(104, 166, 214, 0.5);
  background: linear-gradient(165deg, rgba(8, 24, 40, 0.98), rgba(4, 14, 25, 0.98));
  box-shadow:
    0 24px 54px rgba(2, 9, 16, 0.55),
    inset 0 0 0 1px rgba(72, 126, 165, 0.24);
}

.plugin-modal-wide {
  width: min(1040px, 100%);
}

.plugin-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plugin-modal-head h3 {
  margin: 0;
}

.plugin-modal-kicker {
  margin: 8px 0 0;
  color: rgba(176, 198, 222, 0.86);
  font-size: 13px;
}

.plugin-host-details-modal .plugin-modal-kicker {
  margin-top: 6px;
  font-size: 12px;
}

.plugin-modal-body {
  margin-top: 10px;
}

.plugin-host-details-body {
  margin-top: 8px;
  display: grid;
  gap: 10px;
}

.plugin-host-summary-card {
  padding: 12px;
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(88, 139, 177, 0.34);
  background: linear-gradient(154deg, rgba(12, 31, 49, 0.84), rgba(8, 24, 39, 0.84));
}

.plugin-host-summary-main {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.plugin-host-summary-label {
  margin: 0;
  font-size: 12px;
  color: rgba(151, 180, 208, 0.88);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.plugin-host-summary-title {
  margin: 0;
  font-size: 18px;
  color: rgba(229, 241, 255, 0.98);
}

.plugin-host-summary-subtitle {
  margin: 0;
  color: rgba(176, 199, 223, 0.88);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.plugin-host-summary-aside {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.plugin-host-summary-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(101, 158, 201, 0.52);
  background: rgba(16, 56, 86, 0.42);
  color: rgba(217, 234, 252, 0.96);
  font-size: 12px;
}

.plugin-host-summary-pill-muted {
  border-color: rgba(91, 127, 155, 0.34);
  background: rgba(12, 33, 49, 0.62);
  color: rgba(170, 196, 221, 0.9);
}

.plugin-host-services-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  align-items: start;
}

.plugin-host-service-card {
  padding: 12px;
  display: grid;
  gap: 10px;
  min-width: 0;
  border: 1px solid rgba(88, 132, 169, 0.34);
  background: linear-gradient(157deg, rgba(10, 27, 42, 0.9), rgba(6, 19, 31, 0.92));
  transition:
    border-color 150ms ease,
    background 150ms ease;
}

.plugin-host-service-card:hover {
  border-color: rgba(114, 176, 223, 0.54);
  background: linear-gradient(157deg, rgba(12, 33, 51, 0.92), rgba(8, 22, 35, 0.94));
}

.plugin-host-service-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.plugin-host-service-title-wrap {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.plugin-host-service-title {
  margin: 0;
  font-size: 15px;
  color: rgba(226, 240, 255, 0.97);
}

.plugin-host-service-subtitle {
  margin: 0;
  color: rgba(188, 210, 232, 0.9);
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.plugin-host-service-subtitle-muted {
  color: rgba(149, 174, 199, 0.84);
}

.plugin-host-service-port {
  flex: 0 0 auto;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(83, 142, 184, 0.42);
  background: rgba(12, 47, 75, 0.44);
  color: rgba(202, 224, 244, 0.95);
  font-size: 11px;
  line-height: 22px;
}

.plugin-host-service-body {
  display: grid;
  gap: 5px;
}

.plugin-host-service-field-label {
  margin: 0;
  font-size: 11px;
  color: rgba(152, 180, 206, 0.86);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.plugin-host-service-url {
  margin: 0;
  min-height: 32px;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid rgba(84, 120, 149, 0.32);
  background: rgba(8, 23, 36, 0.8);
  color: rgba(202, 223, 243, 0.94);
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.plugin-host-service-actions {
  margin-top: auto;
}

.plugin-host-service-action-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-host-service-action {
  margin: 0;
}

.plugin-host-service-action + .plugin-host-service-action {
  margin-top: 0;
}

.plugin-host-details-modal .plugin-table-action-btn {
  min-height: 26px;
  padding: 3px 9px;
  font-size: 11px;
}

@media (max-width: 760px) {
  .plugin-hosts-filters {
    grid-template-columns: 1fr;
  }

  .plugin-host-services-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plugin-host-summary-card {
    display: grid;
  }

  .plugin-host-summary-aside {
    justify-content: flex-start;
  }
}

@media (max-width: 1200px) {
  .plugin-host-services-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .plugin-hosts-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plugin-host-services-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 540px) {
  .plugin-host-services-grid {
    grid-template-columns: 1fr;
  }
}

.plugin-add-form {
  margin-top: 8px;
  display: grid;
  gap: 12px;
}

.plugin-add-form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
}

.plugin-add-field {
  display: grid;
  gap: 6px;
  color: rgba(182, 205, 228, 0.9);
  font-size: 12px;
}

.plugin-add-input {
  min-height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(84, 120, 150, 0.36);
  background: rgba(7, 19, 31, 0.92);
  color: rgba(219, 233, 247, 0.96);
  padding: 7px 10px;
}

.plugin-add-error {
  margin: 0;
  color: rgba(250, 173, 173, 0.95);
}

.plugin-add-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.plugin-add-primary {
  border-color: rgba(104, 173, 224, 0.56);
}
</style>
