<template>
  <BaseModal
    :open="createEntityEditor.open"
    backdrop-class="editor-modal-backdrop"
    modal-class="editor-modal create-entity-modal"
    @backdrop="closeCreateEntityEditor"
  >
    <header class="editor-modal-header">
      <h3>{{ modalTitle }}</h3>
      <button
        class="ghost"
        type="button"
        :disabled="createEntityEditor.submitting"
        @click="closeCreateEntityEditor"
      >
        Закрыть
      </button>
    </header>

    <form class="editor-modal-form" @submit.prevent="submitCreateEntityEditor">
      <p v-if="createEntityEditor.error" class="widget-error">
        {{ createEntityEditor.error }}
      </p>

      <section
        v-if="showStructureKindSwitcher"
        class="create-entity-kind-switcher"
      >
        <button
          class="ghost"
          type="button"
          :class="{ active: createEntityEditor.form.kind === 'group' }"
          :disabled="createEntityEditor.submitting"
          @click="setCreateEntityKind('group')"
        >
          Группа
        </button>
        <button
          class="ghost"
          type="button"
          :class="{ active: createEntityEditor.form.kind === 'subgroup' }"
          :disabled="createEntityEditor.submitting"
          @click="setCreateEntityKind('subgroup')"
        >
          Подгруппа
        </button>
      </section>

      <section v-if="createEntityEditor.form.kind === 'dashboard'" class="editor-grid">
        <label class="editor-field">
          <span>Название вкладки</span>
          <input
            v-model.trim="createEntityEditor.form.title"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="Главная"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field">
          <span>ID (optional)</span>
          <input
            v-model.trim="createEntityEditor.form.id"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="home"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field">
          <span>Иконка</span>
          <input
            v-model.trim="createEntityEditor.form.icon"
            type="text"
            maxlength="80"
            autocomplete="off"
            placeholder="layout-dashboard"
            :disabled="createEntityEditor.submitting"
          />
        </label>
      </section>

      <section v-else-if="createEntityEditor.form.kind === 'group'" class="editor-grid">
        <label class="editor-field">
          <span>Название группы</span>
          <input
            v-model.trim="createEntityEditor.form.title"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="Core Services"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field">
          <span>ID (optional)</span>
          <input
            v-model.trim="createEntityEditor.form.id"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="core-services"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field">
          <span>Иконка</span>
          <input
            v-model.trim="createEntityEditor.form.icon"
            type="text"
            maxlength="80"
            autocomplete="off"
            placeholder="folder"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field editor-field--wide">
          <span>Описание</span>
          <input
            v-model.trim="createEntityEditor.form.description"
            type="text"
            maxlength="240"
            autocomplete="off"
            placeholder="Краткое описание"
            :disabled="createEntityEditor.submitting"
          />
        </label>
      </section>

      <section v-else-if="createEntityEditor.form.kind === 'subgroup'" class="editor-grid">
        <label class="editor-field">
          <span>Родительская группа</span>
          <select
            :value="createEntityEditor.form.parentGroupId"
            :disabled="createEntityEditor.submitting || !createEntityGroupOptions.length"
            @change="handleParentGroupChange"
          >
            <option
              v-for="option in createEntityGroupOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.title }}
            </option>
          </select>
        </label>

        <label class="editor-field">
          <span>Название подгруппы</span>
          <input
            v-model.trim="createEntityEditor.form.title"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="Main"
            :disabled="createEntityEditor.submitting"
          />
        </label>

        <label class="editor-field">
          <span>ID (optional)</span>
          <input
            v-model.trim="createEntityEditor.form.id"
            type="text"
            maxlength="120"
            autocomplete="off"
            placeholder="core-main"
            :disabled="createEntityEditor.submitting"
          />
        </label>
      </section>

      <section v-else class="editor-grid">
        <label class="editor-field">
          <span>Dashboard</span>
          <select
            :value="createEntityEditor.form.parentDashboardId"
            :disabled="createEntityEditor.submitting || !createEntityDashboardOptions.length"
            @change="handleParentDashboardChange"
          >
            <option
              v-for="option in createEntityDashboardOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.title }}
            </option>
          </select>
        </label>

        <label class="editor-field">
          <span>Группа</span>
          <select
            :value="createEntityEditor.form.parentGroupId"
            :disabled="createEntityEditor.submitting || !createEntityItemGroupOptions.length"
            @change="handleParentGroupChange"
          >
            <option
              v-for="option in createEntityItemGroupOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.title }}
            </option>
          </select>
        </label>

        <label class="editor-field">
          <span>Подгруппа</span>
          <select
            v-model="createEntityEditor.form.parentSubgroupId"
            :disabled="createEntityEditor.submitting || !createEntitySubgroupOptions.length"
          >
            <option
              v-for="option in createEntitySubgroupOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.title }}
            </option>
          </select>
        </label>

        <p class="create-entity-note">
          Далее откроется форма создания элемента с полями карточки.
        </p>
      </section>

      <div class="editor-actions">
        <button
          class="ghost"
          type="button"
          :disabled="createEntityEditor.submitting"
          @click="closeCreateEntityEditor"
        >
          Отмена
        </button>
        <button class="ghost" type="submit" :disabled="createEntityEditor.submitting">
          {{ submitTitle }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseModal from "@/components/primitives/BaseModal.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const {
  createEntityEditor,
  createEntityDashboardOptions,
  createEntityGroupOptions,
  createEntityItemGroupOptions,
  createEntitySubgroupOptions,
  closeCreateEntityEditor,
  setCreateEntityKind,
  setCreateEntityParentDashboard,
  setCreateEntityParentGroup,
  submitCreateEntityEditor,
} = dashboard;

const showStructureKindSwitcher = computed(
  () =>
    createEntityEditor.form.kind === "group" ||
    createEntityEditor.form.kind === "subgroup",
);

const modalTitle = computed(() => {
  if (createEntityEditor.form.kind === "dashboard") {
    return "Создать dashboard";
  }
  if (createEntityEditor.form.kind === "group") {
    return "Создать группу";
  }
  if (createEntityEditor.form.kind === "subgroup") {
    return "Создать подгруппу";
  }
  return "Создать элемент";
});

const submitTitle = computed(() => {
  if (createEntityEditor.submitting) {
    return "Сохранение...";
  }
  if (createEntityEditor.form.kind === "item") {
    return "Продолжить";
  }
  return "Создать";
});

function handleParentGroupChange(event: Event): void {
  if (!(event.target instanceof HTMLSelectElement)) {
    return;
  }
  setCreateEntityParentGroup(event.target.value);
}

function handleParentDashboardChange(event: Event): void {
  if (!(event.target instanceof HTMLSelectElement)) {
    return;
  }
  setCreateEntityParentDashboard(event.target.value);
}
</script>
