<template>
  <BaseModal
    :open="itemEditor.open"
    backdrop-class="editor-modal-backdrop"
    modal-class="editor-modal"
    @backdrop="closeItemEditor"
  >
    <header class="editor-modal-header">
      <h3>
        {{
          itemEditor.mode === "create"
            ? "Новый сервис"
            : "Редактирование сервиса"
        }}
      </h3>
      <button
        class="ghost"
        type="button"
        :disabled="itemEditor.submitting"
        @click="closeItemEditor"
      >
        Закрыть
      </button>
    </header>

    <form class="editor-modal-form" @submit.prevent="submitItemEditor">
      <p v-if="itemEditor.error" class="widget-error">{{ itemEditor.error }}</p>

      <div class="editor-modal-tabs" role="tablist" aria-label="Секции редактора">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="editor-modal-tab"
          :class="{ active: activeTab === tab.id }"
          role="tab"
          type="button"
          :aria-selected="activeTab === tab.id"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <div v-show="activeTab === 'basic'" role="tabpanel">
        <ItemEditorBaseFields />
      </div>

      <div v-show="activeTab === 'health'" role="tabpanel">
        <ItemEditorLinkSection />
      </div>

      <div v-show="activeTab === 'iframe' && itemEditor.form.type === 'iframe'" role="tabpanel">
        <ItemEditorIframeSection />
      </div>

      <div class="editor-actions">
        <button
          class="ghost"
          type="button"
          :disabled="itemEditor.submitting"
          @click="closeItemEditor"
        >
          Отмена
        </button>
        <button class="ghost" type="submit" :disabled="itemEditor.submitting">
          {{
            itemEditor.submitting
              ? "Сохранение..."
              : itemEditor.mode === "create"
                ? "Создать"
                : "Сохранить"
          }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import ItemEditorBaseFields from "@/views/dashboard/modals/item-editor/ItemEditorBaseFields.vue";
import ItemEditorIframeSection from "@/views/dashboard/modals/item-editor/ItemEditorIframeSection.vue";
import ItemEditorLinkSection from "@/views/dashboard/modals/item-editor/ItemEditorLinkSection.vue";
import BaseModal from "@/ui/overlays/BaseModal.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const { itemEditor, closeItemEditor, submitItemEditor } = dashboard;

type ItemEditorTabId = "basic" | "health" | "iframe";

const activeTab = ref<ItemEditorTabId>("basic");
const tabs = computed(() => {
  const baseTabs: Array<{ id: ItemEditorTabId; label: string }> = [
    { id: "basic", label: "Основное" },
    { id: "health", label: "Healthcheck" },
  ];
  if (itemEditor.form.type === "iframe") {
    baseTabs.push({ id: "iframe", label: "Iframe" });
  }
  return baseTabs;
});

watch(
  () => itemEditor.open,
  (isOpen) => {
    if (!isOpen) {
      activeTab.value = "basic";
    }
  },
);

watch(
  () => itemEditor.form.type,
  (type) => {
    if (type !== "iframe" && activeTab.value === "iframe") {
      activeTab.value = "basic";
    }
  },
);
</script>
