<template>
  <BaseModal
    :open="createChooser.open"
    backdrop-class="create-chooser-backdrop"
    modal-class="create-chooser-modal"
    @backdrop="closeCreateChooser"
  >
    <header class="create-chooser-header">
      <h3>Что создать?</h3>
      <button class="ghost" type="button" @click="closeCreateChooser">
        Закрыть
      </button>
    </header>

    <div class="create-chooser-grid">
      <button
        class="create-chooser-option"
        type="button"
        @click="openCreateOption('dashboard')"
      >
        <span class="create-chooser-title">Dashboard</span>
        <span class="create-chooser-subtitle">Новая вкладка (root/page)</span>
      </button>

      <button
        class="create-chooser-option"
        type="button"
        @click="openCreateOption('group_or_subgroup')"
      >
        <span class="create-chooser-title">Группа / Подгруппа</span>
        <span class="create-chooser-subtitle">Структура дерева сервисов</span>
      </button>

      <button
        class="create-chooser-option"
        type="button"
        @click="openCreateOption('item')"
      >
        <span class="create-chooser-title">Элемент</span>
        <span class="create-chooser-subtitle">Карточка сервиса</span>
      </button>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from "@/components/primitives/BaseModal.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const { createChooser, closeCreateChooser, openCreateOption } = dashboard;
</script>
