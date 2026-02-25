<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="false"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    canvas-aria-label="UI Kit demo"
  >
    <template v-slot:[SLOT_APP_SIDEBAR_TOP]>
      <header class="brand">
        <img :src="EMBLEM_SRC" alt="" aria-hidden="true" />
        <div>
          <p class="brand-title">Oko</p>
          <p class="brand-subtitle">UI Kit primitives showcase</p>
        </div>
      </header>
    </template>

    <template v-slot:[SLOT_APP_SIDEBAR_MIDDLE]>
      <aside
        class="ui-kit-nav ui-kit-showcase-sidebar"
        aria-label="UI kit navigation"
      >
        <div class="ui-kit-nav__tools">
          <label class="ui-kit-nav__search">
            <span>Search</span>
            <input
              v-model.trim="searchQuery"
              type="search"
              placeholder="Find primitive..."
              autocomplete="off"
            />
          </label>

          <div
            class="ui-kit-nav__groups"
            role="tablist"
            aria-label="Primitive groups"
          >
            <button
              v-for="group in groupFilters"
              :key="group.id"
              type="button"
              role="tab"
              class="ui-kit-nav__group-btn"
              :class="{ active: activeGroup === group.id }"
              :aria-selected="activeGroup === group.id"
              @click="handleGroupChange(group.id)"
            >
              {{ group.label }}
            </button>
          </div>

          <div class="ui-kit-showcase-sidebar__actions">
            <button
              type="button"
              class="ui-kit-showcase-sidebar__reset-btn"
              :disabled="!activeNodeId"
              @click="handleSelectionReset"
            >
              Clear selection
            </button>
          </div>
        </div>

        <UiNodeTree
          :groups="visibleGroups"
          :active-group="activeGroup"
          :active-node-id="activeNodeId"
          @group-change="handleGroupChange"
          @node-click="handleNodeTabClick"
        />
      </aside>
    </template>

    <template v-slot:[SLOT_APP_HEADER_TABS]>
      <nav class="hero-page-tabs" role="tablist" aria-label="UI Kit">
        <button
          id="uikit-showcase-tab"
          class="hero-page-tab-btn active"
          type="button"
          role="tab"
          aria-selected="true"
          tabindex="0"
          aria-controls="uikit-showcase-panel"
        >
          <Palette class="ui-icon hero-page-tab-icon" />
          <span class="hero-page-tab-label">UI Kit Showcase</span>
        </button>
      </nav>
    </template>

    <template v-slot:[SLOT_PAGE_CANVAS_MAIN]>
      <section
        id="uikit-showcase-panel"
        class="ui-kit-showcase-panel"
        role="tabpanel"
        aria-labelledby="uikit-showcase-tab"
      >
        <UiPrimitivesDemoView
          :active-group="activeGroup"
          :active-node-id="activeNodeId"
          :has-visible-items="hasVisibleItems"
          @close="handleClose"
          @update:active-node-id="handleActiveNodeUpdate"
        />
      </section>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Palette } from "lucide-vue-next";
import {
  UI_KIT_SHOWCASE_GROUPS,
  type UiKitPrimitiveGroup,
} from "@/components/ui-kit/demo/showcaseRegistry";
import UiBlankLayout from "@/components/ui-kit/primitives/UiBlankLayout.vue";
import UiNodeTree from "@/components/ui-kit/primitives/UiNodeTree.vue";
import { goDashboard } from "@/core/navigation/nav";
import UiPrimitivesDemoView from "@/views/UiPrimitivesDemoView.vue";
import { EMBLEM_SRC, SIDEBAR_PARTICLES_ID } from "@/stores/ui/storeConstants";
import { useUiStore } from "@/stores/uiStore";

const SLOT_APP_SIDEBAR_TOP = "app.sidebar.top";
const SLOT_APP_SIDEBAR_MIDDLE = "app.sidebar.middle";
const SLOT_APP_HEADER_TABS = "app.header.tabs";
const SLOT_PAGE_CANVAS_MAIN = "page.canvas.main";

type GroupFilterId = UiKitPrimitiveGroup["id"];

const uiStore = useUiStore();
const { initSidebarParticles } = uiStore;

const searchQuery = ref("");
const activeGroup = ref<GroupFilterId>(
  UI_KIT_SHOWCASE_GROUPS[0]?.id || "forms",
);
const activeNodeId = ref(
  UI_KIT_SHOWCASE_GROUPS[0]?.items[0]?.id || "ui-node-inputgroup",
);
const isSelectionCleared = ref(false);

const groupFilters = computed(() => [
  ...UI_KIT_SHOWCASE_GROUPS.map((group) => ({
    id: group.id,
    label: group.label,
  })),
]);

const visibleGroups = computed<UiKitPrimitiveGroup[]>(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return UI_KIT_SHOWCASE_GROUPS;
  }

  return UI_KIT_SHOWCASE_GROUPS.map((group) => {
    const sections = group.sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) =>
          item.label.toLowerCase().includes(query),
        ),
      }))
      .filter((section) => section.items.length > 0);
    return {
      ...group,
      sections,
      items: sections.flatMap((section) => section.items),
    };
  }).filter((group) => group.items.length > 0);
});

function handleGroupChange(groupId: GroupFilterId): void {
  activeGroup.value = groupId;
  const filteredGroup = visibleGroups.value.find((group) => group.id === groupId);
  const baseGroup = UI_KIT_SHOWCASE_GROUPS.find((group) => group.id === groupId);
  const firstNodeId = filteredGroup?.items[0]?.id || baseGroup?.items[0]?.id;
  if (!firstNodeId) return;
  activeNodeId.value = firstNodeId;
  isSelectionCleared.value = false;
}

function handleNodeTabClick(nodeId: string, groupId: GroupFilterId): void {
  activeGroup.value = groupId;
  activeNodeId.value = nodeId;
  isSelectionCleared.value = false;
}

function handleSelectionReset(): void {
  activeNodeId.value = "";
  isSelectionCleared.value = true;
}

function handleActiveNodeUpdate(nodeId: string): void {
  if (!nodeId) return;
  activeNodeId.value = nodeId;
  isSelectionCleared.value = false;
}

function handleClose(): void {
  void goDashboard();
}

const hasVisibleItems = computed(() =>
  visibleGroups.value.some((group) => group.items.length > 0),
);

onMounted(() => {
  void initSidebarParticles();
});

watch(
  () => visibleGroups.value,
  (groups) => {
    if (!groups.length) {
      activeNodeId.value = "";
      return;
    }

    if (!groups.some((group) => group.id === activeGroup.value)) {
      activeGroup.value = groups[0]?.id || activeGroup.value;
    }

    if (isSelectionCleared.value) {
      activeNodeId.value = "";
      return;
    }

    const allVisibleItems = groups.flatMap((group) => group.items);
    if (allVisibleItems.some((item) => item.id === activeNodeId.value)) return;

    const activeGroupItems =
      groups.find((group) => group.id === activeGroup.value)?.items || [];
    const fallbackNodeId = activeGroupItems[0]?.id || allVisibleItems[0]?.id;
    if (!fallbackNodeId) return;
    activeNodeId.value = fallbackNodeId;
  },
  { immediate: true },
);
</script>

<style scoped>
.ui-kit-showcase-sidebar {
  inline-size: 100%;
  block-size: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.ui-kit-showcase-sidebar__actions {
  display: flex;
}

.ui-kit-showcase-sidebar__reset-btn {
  inline-size: 100%;
  border: 1px solid rgba(121, 169, 189, 0.26);
  border-radius: var(--ui-radius);
  background: rgba(11, 29, 42, 0.74);
  color: #c8ddec;
  min-height: 28px;
  padding: 5px 10px;
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    color 150ms ease;
}

.ui-kit-showcase-sidebar__reset-btn:hover:not(:disabled) {
  border-color: rgba(116, 247, 224, 0.46);
  background: rgba(17, 52, 62, 0.72);
  color: #e8fbff;
}

.ui-kit-showcase-sidebar__reset-btn:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.ui-kit-showcase-panel {
  inline-size: 100%;
  min-width: 0;
  min-height: 0;
}

.ui-kit-showcase-panel :deep(.ui-kit-page.panel) {
  inline-size: 100%;
  min-width: 0;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  backdrop-filter: none;
  box-shadow: none;
  padding: 0;
}

.ui-kit-showcase-panel :deep(.ui-kit-page__head) {
  padding: 0 2px;
}

.ui-kit-showcase-panel :deep(.ui-kit-page__content) {
  min-height: 0;
  min-width: 0;
  overflow: auto;
  padding-right: 4px;
}

.ui-kit-showcase-panel :deep(.ui-kit-section),
.ui-kit-showcase-panel :deep(.ui-kit-node),
.ui-kit-showcase-panel :deep(.ui-icon-picker__list) {
  min-width: 0;
}

.ui-kit-showcase-panel :deep(.ui-kit-section) {
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
}
</style>
