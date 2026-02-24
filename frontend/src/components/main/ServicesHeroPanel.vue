<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div class="hero-title-content">
        <HeroPageTabs />
      </div>
    </header>

    <aside
      class="panel hero-control-panel service-hero-controls"
      :class="{ active: editMode }"
    >
      <div class="hero-controls-content">
        <div class="hero-controls-accordion" :class="{ open: controlsOpen }">
          <Transition name="hero-controls-drawer-transition">
            <div
              v-if="controlsOpen"
              id="hero-controls-drawer"
              class="hero-controls-drawer"
            >
              <IconButton
                button-class="hero-icon-btn hero-accordion-action"
                title="Панель настроек"
                aria-label="Открыть панель настроек"
                @click="openSettingsPanel"
              >
                <SlidersHorizontal class="ui-icon hero-action-icon" />
              </IconButton>

              <IconButton
                button-class="hero-icon-btn hero-accordion-action"
                :active="!isSidebarDetailed"
                :title="sidebarViewToggleTitle"
                :aria-label="sidebarViewToggleTitle"
                @click="toggleSidebarView"
              >
                <FolderTree class="ui-icon hero-action-icon" />
              </IconButton>

              <IconButton
                button-class="hero-icon-btn hero-accordion-action editor-toggle"
                :active="editMode"
                :title="
                  editMode
                    ? 'Выключить режим редактирования'
                    : 'Включить режим редактирования'
                "
                :aria-label="
                  editMode
                    ? 'Выключить режим редактирования'
                    : 'Включить режим редактирования'
                "
                @click="toggleEditMode"
              >
                <Pencil class="ui-icon hero-action-icon" />
              </IconButton>

              <IconButton
                button-class="hero-icon-btn hero-accordion-action"
                :disabled="!editMode"
                title="Добавить сущность"
                aria-label="Добавить сущность"
                @click="openCreateChooser()"
              >
                <Plus class="ui-icon hero-action-icon" />
              </IconButton>

              <span
                v-if="editMode"
                class="hero-save-indicator hero-accordion-status"
                :class="saveStatus"
                role="status"
                :title="saveStatusLabel"
                :aria-label="saveStatusLabel"
              >
                <Circle class="ui-icon hero-save-icon" />
              </span>
            </div>
          </Transition>

          <button
            class="hero-controls-trigger"
            type="button"
            :aria-expanded="controlsOpen"
            aria-controls="hero-controls-drawer"
            :title="
              controlsOpen
                ? 'Скрыть панель действий'
                : 'Показать панель действий'
            "
            @click="controlsOpen = !controlsOpen"
          >
            <Wrench class="ui-icon hero-action-icon" />
            <ChevronLeft
              class="ui-icon hero-accordion-caret"
              :class="{ open: controlsOpen }"
            />
          </button>

          <IconButton
            button-class="hero-icon-btn hero-accordion-action hero-plugin-panel-btn"
            title="Открыть панель плагинов"
            aria-label="Открыть панель плагинов"
            @click="openPluginPanel"
          >
            <Puzzle class="ui-icon hero-action-icon" />
          </IconButton>

          <IconButton
            button-class="hero-icon-btn hero-accordion-action hero-pleiad-lock-btn"
            title="Открыть Pleiad"
            aria-label="Открыть Pleiad"
            @click="openPleiad"
          >
            <Lock class="ui-icon hero-action-icon" />
          </IconButton>
        </div>

        <p v-if="editMode && saveError" class="editor-error hero-editor-error">
          {{ saveError }}
        </p>
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import {
  ChevronLeft,
  Circle,
  FolderTree,
  Lock,
  Plus,
  Pencil,
  Puzzle,
  SlidersHorizontal,
  Wrench,
} from "lucide-vue-next";
import HeroPageTabs from "@/components/main/HeroPageTabs.vue";
import IconButton from "@/components/primitives/IconButton.vue";
import {
  goPluginsPanel,
  openPleiadOverlay,
} from "@/core/navigation/nav";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const HERO_CONTROLS_OPEN_STORAGE_KEY = "oko:hero-controls-open:v1";
const controlsOpen = ref(false);

const {
  editMode,
  isSidebarDetailed,
  saveStatus,
  saveStatusLabel,
  saveError,
  sidebarViewToggleTitle,
  toggleEditMode,
  openCreateChooser,
  openSettingsPanel,
  toggleSidebarView,
} = dashboard;

function openPleiad() {
  void openPleiadOverlay("route");
}

function openPluginPanel() {
  void goPluginsPanel();
}

function getLocalStorageSafe() {
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
}

onMounted(() => {
  const storage = getLocalStorageSafe();
  if (!storage) return;
  const raw = storage.getItem(HERO_CONTROLS_OPEN_STORAGE_KEY);
  controlsOpen.value = raw === "1";
});

watch(
  () => controlsOpen.value,
  (value) => {
    const storage = getLocalStorageSafe();
    if (!storage) return;
    storage.setItem(HERO_CONTROLS_OPEN_STORAGE_KEY, value ? "1" : "0");
  },
);
</script>
