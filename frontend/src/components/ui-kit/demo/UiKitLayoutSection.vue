<template>
  <section class="ui-kit-section">
    <h2>Layout & Containers</h2>

    <article
      v-show="isNodeVisible('ui-node-toolbar')"
      id="ui-node-toolbar"
      class="ui-kit-node"
    >
      <h3>Toolbar</h3>
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
    </article>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-card')"
        id="ui-node-card"
        class="ui-kit-node"
      >
        <h3>Card</h3>
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
      </article>

      <article
        v-show="isNodeVisible('ui-node-divider')"
        id="ui-node-divider"
        class="ui-kit-node ui-kit-stack"
      >
        <h3>Divider</h3>
        <UiDivider label="Divider" />
        <UiDivider orientation="vertical" />
      </article>
    </div>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-fieldset-static')"
        id="ui-node-fieldset-static"
        class="ui-kit-node"
      >
        <h3>Fieldset (static)</h3>
        <UiFieldset legend="Static Fieldset">
          <p>Статический контейнер для группы полей.</p>
        </UiFieldset>
      </article>

      <article
        v-show="isNodeVisible('ui-node-fieldset-collapsible')"
        id="ui-node-fieldset-collapsible"
        class="ui-kit-node"
      >
        <h3>Fieldset (collapsible)</h3>
        <UiFieldset
          v-model="fieldsetOpen"
          legend="Collapsible Fieldset"
          collapsible
        >
          <p>Этот fieldset можно раскрывать и сворачивать.</p>
        </UiFieldset>
      </article>
    </div>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-accordion-vertical')"
        id="ui-node-accordion-vertical"
        class="ui-kit-node"
      >
        <h3>Accordion (vertical)</h3>
        <UiAccordion :items="accordionItems" />
      </article>

      <article
        v-show="isNodeVisible('ui-node-accordion-horizontal')"
        id="ui-node-accordion-horizontal"
        class="ui-kit-node"
      >
        <h3>Accordion (horizontal)</h3>
        <UiAccordion :items="accordionItems" orientation="horizontal" />
      </article>
    </div>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-stepper')"
        id="ui-node-stepper"
        class="ui-kit-node"
      >
        <h3>Stepper</h3>
        <UiStepper v-model="stepIndex" :steps="steps" />
      </article>

      <article
        v-show="isNodeVisible('ui-node-tabs')"
        id="ui-node-tabs"
        class="ui-kit-node"
      >
        <h3>Tabs</h3>
        <UiTabs v-model="tabValue" :tabs="tabs">
          <template #default="{ activeTab }">
            <p>{{ activeTab?.content }}</p>
          </template>
        </UiTabs>
      </article>
    </div>

    <article
      v-show="isNodeVisible('ui-node-sidebar-list-item')"
      id="ui-node-sidebar-list-item"
      class="ui-kit-node ui-kit-stack"
    >
      <h3>Sidebar Tree (Dashboard style)</h3>

      <UiSidebarDemoTree v-model="activeSidebarNode" />
    </article>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiAccordion from "@/components/ui-kit/primitives/UiAccordion.vue";
import UiButton from "@/components/ui-kit/primitives/UiButton.vue";
import UiCard from "@/components/ui-kit/primitives/UiCard.vue";
import UiDivider from "@/components/ui-kit/primitives/UiDivider.vue";
import UiFieldset from "@/components/ui-kit/primitives/UiFieldset.vue";
import UiSidebarDemoTree from "@/components/ui-kit/primitives/UiSidebarDemoTree.vue";
import UiStepper from "@/components/ui-kit/primitives/UiStepper.vue";
import UiTabs from "@/components/ui-kit/primitives/UiTabs.vue";
import UiToolbar from "@/components/ui-kit/primitives/UiToolbar.vue";

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
