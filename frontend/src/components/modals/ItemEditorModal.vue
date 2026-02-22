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

      <ItemEditorBaseFields />
      <ItemEditorLinkSection v-if="itemEditor.form.type === 'link'" />
      <ItemEditorIframeSection v-else />

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

<script setup>
import ItemEditorBaseFields from "./item-editor/ItemEditorBaseFields.vue";
import ItemEditorIframeSection from "./item-editor/ItemEditorIframeSection.vue";
import ItemEditorLinkSection from "./item-editor/ItemEditorLinkSection.vue";
import BaseModal from "../primitives/BaseModal.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const { itemEditor, closeItemEditor, submitItemEditor } = dashboard;
</script>
