<template>
  <section class="ui-kit-section">
    <UiShowcaseNode
      v-show="isNodeVisible('ui-node-toolbar')"
      id="ui-node-toolbar"
      group-label="Layout & Containers"
      element-label="UiToolbar"
      :value="toolbarMeta"
      :api="SHOWCASE_NODE_API['ui-node-toolbar']"
    >
      <UiToolbar
        title="UI Primitive Demo"
        subtitle="Composable building blocks"
      >
        <template #start>
          <UiButton variant="ghost" size="sm">Back</UiButton>
        </template>
        <template #end>
          <UiButton size="sm">Publish</UiButton>
        </template>
      </UiToolbar>
    </UiShowcaseNode>

    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-card')"
        id="ui-node-card"
        group-label="Layout & Containers"
        element-label="UiCard"
        :value="cardMeta"
        :api="SHOWCASE_NODE_API['ui-node-card']"
      >
        <UiCard
          title="Card Title"
          subtitle="Optional subtitle"
          footer="Card footer text"
        >
          <p>
            Любой контент можно передать через slot: текст, формы, таблицы,
            графики.
          </p>
        </UiCard>
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-divider')"
        id="ui-node-divider"
        class="ui-kit-stack"
        group-label="Layout & Containers"
        element-label="UiDivider"
        :value="dividerMeta"
        :api="SHOWCASE_NODE_API['ui-node-divider']"
      >
        <UiDivider label="Divider" />
        <UiDivider orientation="vertical" />
      </UiShowcaseNode>
    </div>

    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-fieldset-static')"
        id="ui-node-fieldset-static"
        group-label="Layout & Containers"
        element-label="UiFieldset (static)"
        :value="'static'"
        :api="SHOWCASE_NODE_API['ui-node-fieldset-static']"
      >
        <UiFieldset legend="Static Fieldset">
          <p>Статический контейнер для группы полей.</p>
        </UiFieldset>
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-fieldset-collapsible')"
        id="ui-node-fieldset-collapsible"
        group-label="Layout & Containers"
        element-label="UiFieldset (collapsible)"
        :value="fieldsetOpen"
        :api="SHOWCASE_NODE_API['ui-node-fieldset-collapsible']"
      >
        <UiFieldset
          v-model="fieldsetOpen"
          legend="Collapsible Fieldset"
          collapsible
        >
          <p>Этот fieldset можно раскрывать и сворачивать.</p>
        </UiFieldset>
      </UiShowcaseNode>
    </div>

    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-accordion-vertical')"
        id="ui-node-accordion-vertical"
        group-label="Layout & Containers"
        element-label="UiAccordion (vertical)"
        :value="accordionItems.length"
        :api="SHOWCASE_NODE_API['ui-node-accordion-vertical']"
      >
        <UiAccordion :items="accordionItems" />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-accordion-horizontal')"
        id="ui-node-accordion-horizontal"
        group-label="Layout & Containers"
        element-label="UiAccordion (horizontal)"
        :value="accordionItems.length"
        :api="SHOWCASE_NODE_API['ui-node-accordion-horizontal']"
      >
        <UiAccordion :items="accordionItems" orientation="horizontal" />
      </UiShowcaseNode>
    </div>

    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-stepper')"
        id="ui-node-stepper"
        group-label="Layout & Containers"
        element-label="UiStepper"
        :value="stepIndex"
        :api="SHOWCASE_NODE_API['ui-node-stepper']"
      >
        <UiStepper v-model="stepIndex" :steps="steps" />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-tabs')"
        id="ui-node-tabs"
        group-label="Layout & Containers"
        element-label="UiTabs"
        :value="tabValue"
        :api="SHOWCASE_NODE_API['ui-node-tabs']"
      >
        <UiTabs v-model="tabValue" :tabs="tabs">
          <template #default="{ activeTab }">
            <p>{{ activeTab?.content }}</p>
          </template>
        </UiTabs>
      </UiShowcaseNode>
    </div>

    <UiShowcaseNode
      v-show="isNodeVisible('ui-node-sidebar-list-item')"
      id="ui-node-sidebar-list-item"
      class="ui-kit-stack"
      group-label="Layout & Containers"
      element-label="UiSidebarDemoTree"
      :value="activeSidebarNode"
      :api="SHOWCASE_NODE_API['ui-node-sidebar-list-item']"
    >
      <UiSidebarDemoTree v-model="activeSidebarNode" />
    </UiShowcaseNode>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiAccordion from "@/primitives/navigation/UiAccordion.vue";
import UiButton from "@/ui/actions/UiButton.vue";
import UiCard from "@/ui/surfaces/UiCard.vue";
import UiDivider from "@/ui/surfaces/UiDivider.vue";
import UiFieldset from "@/ui/surfaces/UiFieldset.vue";
import UiSidebarDemoTree from "@/views/ui-showcase/components/UiSidebarDemoTree.vue";
import UiShowcaseNode from "@/views/ui-showcase/components/UiShowcaseNode.vue";
import { SHOWCASE_NODE_API } from "@/views/ui-showcase/showcaseNodeApi";
import UiStepper from "@/primitives/navigation/UiStepper.vue";
import UiTabs from "@/primitives/navigation/UiTabs.vue";
import UiToolbar from "@/primitives/navigation/UiToolbar.vue";

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

const toolbarMeta = {
  title: "UI Primitive Demo",
  subtitle: "Composable building blocks",
};

const cardMeta = {
  title: "Card Title",
  subtitle: "Optional subtitle",
  footer: "Card footer text",
};

const dividerMeta = ["horizontal", "vertical"];

const fieldsetOpen = ref(true);
const stepIndex = ref(1);
const tabValue = ref("overview");
const activeSidebarNode = ref<
  "group" | "subgroup" | "new-service" | "proxmox" | "test2"
>("proxmox");

const accordionItems = [
  { id: "acc-1", title: "Section A", content: "Accordion content A" },
  { id: "acc-2", title: "Section B", content: "Accordion content B" },
  { id: "acc-3", title: "Section C", content: "Accordion content C" },
];

const steps = [
  { id: "s1", title: "Start", description: "Init" },
  { id: "s2", title: "Configure", description: "Setup" },
  { id: "s3", title: "Review", description: "Confirm" },
  { id: "s4", title: "Done", description: "Launch" },
];

const tabs = [
  { id: "overview", label: "Overview", content: "Overview tab content" },
  { id: "api", label: "API", content: "API tab content" },
  { id: "design", label: "Design", content: "Design tab content" },
];
</script>
