<template>
  <UiHeroPanel
    :active="editMode"
    controls-class="hero-control-panel--menu service-hero-controls"
  >
    <template #title>
      <UiHeroPageTabs />
    </template>

    <template #controls>
      <UiHeroControlsAccordion
        drawer-id="hero-controls-drawer"
        :storage-key="heroControlsStorageKey"
      >
        <template #drawer>
          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            title="Панель настроек"
            aria-label="Открыть панель настроек"
            @click="openSettingsPanel"
          >
            <SlidersHorizontal class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            :active="!isSidebarDetailed"
            :title="sidebarViewToggleTitle"
            :aria-label="sidebarViewToggleTitle"
            @click="toggleSidebarView"
          >
            <FolderTree class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiIconButton
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
          </UiIconButton>

          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            :disabled="!editMode"
            title="Добавить сущность"
            aria-label="Добавить сущность"
            @click="openCreateChooser()"
          >
            <Plus class="ui-icon hero-action-icon" />
          </UiIconButton>

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
        </template>

        <template #actions>
          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action hero-plugin-panel-btn"
            title="Открыть панель плагинов"
            aria-label="Открыть панель плагинов"
            @click="openPluginPanel"
          >
            <Puzzle class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiDropdownMenu
            class="hero-action-menu"
            aria-label="Системное меню"
            :items="systemActions"
            :show-caret="false"
            trigger-class="hero-icon-btn hero-accordion-action hero-system-menu-trigger"
            item-class="hero-system-menu-item"
            @action="handleSystemAction"
          >
            <template #trigger>
              <Lock class="ui-icon hero-action-icon" />
            </template>
          </UiDropdownMenu>
        </template>

        <template #footer>
          <p v-if="editMode && saveError" class="editor-error hero-editor-error">
            {{ saveError }}
          </p>
        </template>
      </UiHeroControlsAccordion>
    </template>
  </UiHeroPanel>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import {
  Circle,
  FolderTree,
  Lock,
  Pencil,
  Plus,
  Puzzle,
  SlidersHorizontal,
} from "lucide-vue-next";
import UiHeroPageTabs from "@/components/ui-kit/composites/dashboard/UiHeroPageTabs.vue";
import UiHeroControlsAccordion from "@/components/ui-kit/primitives/UiHeroControlsAccordion.vue";
import UiDropdownMenu from "@/components/ui-kit/primitives/UiDropdownMenu.vue";
import UiHeroPanel from "@/components/ui-kit/primitives/UiHeroPanel.vue";
import UiIconButton from "@/components/ui-kit/primitives/UiIconButton.vue";
import { goPluginsPanel, openPleiadOverlay } from "@/core/navigation/nav";
import { getRuntimeProfile } from "@/services/desktopRuntime";
import { useDashboardStore } from "@/stores/dashboardStore";

const route = useRoute();
const dashboard = useDashboardStore();

const {
  editMode,
  isSidebarDetailed,
  openCreateChooser,
  openSettingsPanel,
  saveError,
  saveStatus,
  saveStatusLabel,
  sidebarViewToggleTitle,
  toggleEditMode,
  toggleSidebarView,
} = dashboard;

type SystemActionId = "kiosk" | "profile" | "pleiad_lock" | "exit";

const systemActions: Array<{
  id: SystemActionId;
  label: string;
  danger?: boolean;
}> = [
  { id: "kiosk", label: "Режим киоска" },
  { id: "profile", label: "Профиль" },
  { id: "pleiad_lock", label: "Блокировка -> Плияды" },
  { id: "exit", label: "Выход", danger: true },
];

const heroControlsStorageKey = computed(() => {
  const rawPath = String(route.path || "/").trim();
  const normalizedPath = rawPath.length > 1 && rawPath.endsWith("/")
    ? rawPath.slice(0, -1)
    : rawPath;
  return `oko:hero-controls-open:${normalizedPath || "/"}`;
});

function openPluginPanel() {
  void goPluginsPanel();
}

async function toggleKioskMode(): Promise<void> {
  if (typeof document === "undefined") return;
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await document.documentElement.requestFullscreen();
  } catch {
    // Keep UI responsive even if fullscreen API is unavailable.
  }
}

async function exitApp(): Promise<void> {
  try {
    if (getRuntimeProfile().desktop) {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      await getCurrentWindow().close();
      return;
    }
  } catch {
    // Fall through to browser close attempt.
  }

  if (typeof window !== "undefined") {
    window.close();
  }
}

function handleSystemAction(actionId: string): void {
  const id = actionId as SystemActionId;

  if (id === "kiosk") {
    void toggleKioskMode();
    return;
  }

  if (id === "profile") {
    openSettingsPanel();
    return;
  }

  if (id === "pleiad_lock") {
    void openPleiadOverlay("route");
    return;
  }

  if (id === "exit") {
    void exitApp();
  }
}
</script>
