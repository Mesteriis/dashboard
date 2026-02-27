<template>
  <section class="ui-kit-section">
    <UiShowcaseNode
      v-show="isNodeVisible('ui-node-datatable')"
      id="ui-node-datatable"
      group-label="Data Components"
      element-label="UiDataTable"
      :value="tableState"
      :api="SHOWCASE_NODE_API['ui-node-datatable']"
    >
      <UiDataTable
        :rows="tableRows"
        :columns="tableColumns"
        :actions="tableActions"
        :show-search="true"
        :show-filters="true"
        :show-export="true"
        :show-pagination="true"
        @action="onTableAction"
        @export="onTableExport"
      />
    </UiShowcaseNode>

    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-pagination')"
        id="ui-node-pagination"
        class="ui-kit-stack"
        group-label="Data Components"
        element-label="UiPagination"
        :value="paginationPage"
        :api="SHOWCASE_NODE_API['ui-node-pagination']"
      >
        <UiPagination
          :total="128"
          :page="paginationPage"
          :page-size="10"
          @update:page="paginationPage = $event"
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-picklist')"
        id="ui-node-picklist"
        class="ui-kit-stack"
        group-label="Data Components"
        element-label="UiPickList"
        :value="pickListState"
        :api="SHOWCASE_NODE_API['ui-node-picklist']"
      >
        <UiPickList
          v-model:source-items="sourceItems"
          v-model:target-items="targetItems"
        />
      </UiShowcaseNode>
    </div>

    <UiShowcaseNode
      v-show="isNodeVisible('ui-node-tree')"
      id="ui-node-tree"
      class="ui-kit-stack"
      group-label="Data Components"
      element-label="UiTree"
      :value="selectedNode"
      :api="SHOWCASE_NODE_API['ui-node-tree']"
    >
      <UiTree
        v-model="selectedNode"
        :nodes="treeNodes"
        :default-expanded="['root-1']"
      />
    </UiShowcaseNode>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import UiDataTable from "@/primitives/data/UiDataTable.vue";
import UiPagination from "@/primitives/data/UiPagination.vue";
import UiPickList from "@/primitives/data/UiPickList.vue";
import UiTree from "@/primitives/data/UiTree.vue";
import UiShowcaseNode from "@/views/ui-showcase/components/UiShowcaseNode.vue";
import { SHOWCASE_NODE_API } from "@/views/ui-showcase/showcaseNodeApi";

const props = withDefaults(
  defineProps<{
    activeNodeId?: string;
  }>(),
  {
    activeNodeId: "",
  },
);

function isNodeVisible(nodeId: string): boolean {
  if (!props.activeNodeId) return true;
  return props.activeNodeId === nodeId;
}

const tableColumns = [
  { key: "name", label: "Name", sortable: true, filterable: true },
  { key: "team", label: "Team", sortable: true, filterable: true },
  { key: "status", label: "Status", sortable: true, filterable: true },
  { key: "latency", label: "Latency", sortable: true },
];

const tableActions = [
  { id: "open", label: "Open" },
  { id: "ping", label: "Ping" },
];

const tableRows = [
  {
    id: "1",
    name: "API Gateway",
    team: "Core",
    status: "online",
    latency: "42ms",
  },
  {
    id: "2",
    name: "Billing",
    team: "Payments",
    status: "degraded",
    latency: "137ms",
  },
  { id: "3", name: "Auth", team: "Core", status: "online", latency: "28ms" },
  {
    id: "4",
    name: "Webhooks",
    team: "Integrations",
    status: "online",
    latency: "51ms",
  },
  {
    id: "5",
    name: "Search",
    team: "Discovery",
    status: "offline",
    latency: "—",
  },
  { id: "6", name: "Storage", team: "Core", status: "online", latency: "33ms" },
  {
    id: "7",
    name: "Analytics",
    team: "Insights",
    status: "degraded",
    latency: "203ms",
  },
  {
    id: "8",
    name: "Scheduler",
    team: "Core",
    status: "online",
    latency: "45ms",
  },
  {
    id: "9",
    name: "Notifications",
    team: "Comms",
    status: "online",
    latency: "39ms",
  },
  {
    id: "10",
    name: "Catalog",
    team: "Commerce",
    status: "online",
    latency: "48ms",
  },
];

const paginationPage = ref(1);

const sourceItems = ref([
  { id: "svc-1", label: "API Gateway" },
  { id: "svc-2", label: "Billing" },
  { id: "svc-3", label: "Search" },
]);

const targetItems = ref([{ id: "svc-4", label: "Auth" }]);

const treeNodes = [
  {
    id: "root-1",
    label: "Platform",
    children: [
      { id: "pl-1", label: "API" },
      { id: "pl-2", label: "Gateway" },
    ],
  },
  {
    id: "root-2",
    label: "Business",
    children: [
      { id: "bs-1", label: "Billing" },
      { id: "bs-2", label: "CRM" },
    ],
  },
];

const selectedNode = ref("pl-1");
const tableLog = ref("");
const exportLog = ref("");

const tableState = computed(() => ({
  rows: tableRows.length,
  lastAction: tableLog.value,
  lastExport: exportLog.value,
}));

const pickListState = computed(() => ({
  sourceCount: sourceItems.value.length,
  targetCount: targetItems.value.length,
}));

function onTableAction(payload: {
  id: string;
  row: Record<string, unknown>;
}): void {
  tableLog.value = `Action: ${payload.id} (${String(payload.row.id || "")})`;
}

function onTableExport(csv: string): void {
  exportLog.value = `CSV exported (${csv.length} chars)`;
}
</script>
