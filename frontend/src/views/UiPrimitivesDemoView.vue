<template>
  <section class="ui-kit-page panel">
    <header class="ui-kit-page__head">
      <div>
        <p class="ui-kit-page__kicker">Design System</p>
        <h1>UI Primitive Showcase</h1>
      </div>
      <button type="button" class="ghost" @click="emit('close')">Back to Dashboard</button>
    </header>

    <div class="ui-kit-workspace">
      <aside class="ui-kit-nav">
        <div class="ui-kit-nav__tools">
          <label class="ui-kit-nav__search">
            <span>Search</span>
            <input v-model.trim="searchQuery" type="search" placeholder="Find primitive..." />
          </label>

          <div class="ui-kit-nav__groups" role="tablist" aria-label="Primitive groups">
            <button
              v-for="group in groupFilters"
              :key="group.id"
              type="button"
              class="ui-kit-nav__group-btn"
              :class="{ active: activeGroup === group.id }"
              @click="activeGroup = group.id"
            >
              {{ group.label }}
            </button>
          </div>
        </div>

        <div class="ui-kit-nav__list">
          <section v-for="group in visibleGroups" :key="group.id" class="ui-kit-nav__section">
            <h3>{{ group.label }}</h3>
            <button
              v-for="item in group.items"
              :key="item.id"
              type="button"
              class="ui-kit-nav__item"
              :class="{ active: activeNodeId === item.id }"
              @click="scrollToNode(item.id)"
            >
              {{ item.label }}
            </button>
          </section>

          <p v-if="!visibleGroups.length" class="ui-kit-nav__empty">No matches for search query.</p>
        </div>
      </aside>

      <div ref="contentRef" class="ui-kit-page__content">
        <UiKitFormSection />
        <UiKitDataSection />
        <UiKitLayoutSection />
        <UiKitHtmlSection />
        <UiKitOverlaySection />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import UiKitDataSection from "@/components/ui-kit/demo/UiKitDataSection.vue";
import UiKitFormSection from "@/components/ui-kit/demo/UiKitFormSection.vue";
import UiKitHtmlSection from "@/components/ui-kit/demo/UiKitHtmlSection.vue";
import UiKitLayoutSection from "@/components/ui-kit/demo/UiKitLayoutSection.vue";
import UiKitOverlaySection from "@/components/ui-kit/demo/UiKitOverlaySection.vue";

interface PrimitiveNode {
  id: string;
  label: string;
}

interface PrimitiveGroup {
  id: string;
  label: string;
  items: PrimitiveNode[];
}

const emit = defineEmits<{
  close: [];
}>();

const searchQuery = ref("");
const activeGroup = ref("all");
const activeNodeId = ref("ui-node-inputgroup");
const contentRef = ref<HTMLElement | null>(null);
let observer: IntersectionObserver | null = null;

const groups: PrimitiveGroup[] = [
  {
    id: "forms",
    label: "Forms",
    items: [
      { id: "ui-node-inputgroup", label: "InputGroup" },
      { id: "ui-node-select", label: "Select" },
      { id: "ui-node-multiselect", label: "MultiSelect" },
      { id: "ui-node-select-search", label: "Select with search" },
      { id: "ui-node-select-search-multi", label: "Search + Multi" },
      { id: "ui-node-chips", label: "Chips" },
      { id: "ui-node-label", label: "Label" },
      { id: "ui-node-checkbox", label: "Checkbox" },
      { id: "ui-node-radiobutton", label: "RadioButton" },
      { id: "ui-node-selectbutton", label: "SelectButton" },
      { id: "ui-node-togglebutton", label: "ToggleButton" },
      { id: "ui-node-button", label: "Button" },
    ],
  },
  {
    id: "data",
    label: "Data",
    items: [
      { id: "ui-node-datatable", label: "DataTable" },
      { id: "ui-node-pagination", label: "Pagination" },
      { id: "ui-node-picklist", label: "PickList" },
      { id: "ui-node-tree", label: "Tree" },
    ],
  },
  {
    id: "layout",
    label: "Layout",
    items: [
      { id: "ui-node-toolbar", label: "Toolbar" },
      { id: "ui-node-card", label: "Card" },
      { id: "ui-node-divider", label: "Divider" },
      { id: "ui-node-fieldset-static", label: "Fieldset static" },
      { id: "ui-node-fieldset-collapsible", label: "Fieldset collapsible" },
      { id: "ui-node-accordion-vertical", label: "Accordion vertical" },
      { id: "ui-node-accordion-horizontal", label: "Accordion horizontal" },
      { id: "ui-node-stepper", label: "Stepper" },
      { id: "ui-node-tabs", label: "Tabs" },
    ],
  },
  {
    id: "overlay",
    label: "Overlay",
    items: [
      { id: "ui-node-modal", label: "Modal" },
      { id: "ui-node-speeddial", label: "SpeedDial" },
      { id: "ui-node-dropdown-menu", label: "Dropdown Menu" },
    ],
  },
  {
    id: "html",
    label: "Native HTML",
    items: [
      { id: "ui-node-html-tags", label: "Semantic tags" },
      { id: "ui-node-html-table-lists", label: "Lists & table" },
      { id: "ui-node-html-media", label: "Media & embed" },
      { id: "ui-node-html-form-tags", label: "Form tags" },
    ],
  },
];

const groupFilters = computed(() => [
  { id: "all", label: "All" },
  ...groups.map((group) => ({ id: group.id, label: group.label })),
]);

const visibleGroups = computed<PrimitiveGroup[]>(() => {
  const query = searchQuery.value.trim().toLowerCase();

  return groups
    .filter((group) => activeGroup.value === "all" || group.id === activeGroup.value)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        if (!query) return true;
        return item.label.toLowerCase().includes(query);
      }),
    }))
    .filter((group) => group.items.length > 0);
});

function scrollToNode(id: string): void {
  const target = document.getElementById(id);
  if (!target) return;
  activeNodeId.value = id;
  target.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
}

function setupObserver(): void {
  observer?.disconnect();
  const root = contentRef.value;
  if (!root) return;

  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio);

      if (!visible.length) return;
      const id = (visible[0].target as HTMLElement).id;
      if (!id) return;
      activeNodeId.value = id;
    },
    {
      root,
      rootMargin: "-15% 0px -70% 0px",
      threshold: [0.15, 0.4, 0.7],
    },
  );

  for (const group of groups) {
    for (const item of group.items) {
      const element = document.getElementById(item.id);
      if (!element) continue;
      observer.observe(element);
    }
  }
}

onMounted(() => {
  void nextTick(() => {
    setupObserver();
  });
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});
</script>
