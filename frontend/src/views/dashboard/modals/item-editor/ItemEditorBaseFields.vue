<template>
  <div class="editor-grid">
    <label class="editor-field">
      <span>Родительская группа</span>
      <HeroDropdown
        :model-value="itemEditor.form.parentGroupId"
        aria-label="Родительская группа"
        :options="parentGroupOptions"
        :disabled="itemEditor.submitting || !parentGroupOptions.length"
        @update:model-value="setItemEditorParentGroup"
      />
    </label>

    <label class="editor-field">
      <span>Родительская подгруппа</span>
      <HeroDropdown
        v-model="itemEditor.form.parentSubgroupId"
        aria-label="Родительская подгруппа"
        :options="parentSubgroupOptions"
        :disabled="itemEditor.submitting || !parentSubgroupOptions.length"
      />
    </label>

    <label class="editor-field">
      <span>ID</span>
      <input
        v-model.trim="itemEditor.form.id"
        type="text"
        placeholder="auto (из названия)"
        autocomplete="off"
        :disabled="itemEditor.submitting"
      />
    </label>

    <label class="editor-field">
      <span>Название</span>
      <input
        v-model.trim="itemEditor.form.title"
        type="text"
        placeholder="Например: Grafana"
        autocomplete="off"
        :disabled="itemEditor.submitting"
        required
      />
    </label>

    <label class="editor-field">
      <span>Тип</span>
      <HeroDropdown
        v-model="itemEditor.form.type"
        aria-label="Тип сервиса"
        :options="itemTypeOptions"
        :disabled="itemEditor.submitting"
      />
    </label>

    <label class="editor-field">
      <span>URL</span>
      <input
        v-model.trim="itemEditor.form.url"
        type="url"
        placeholder="https://service.example.com"
        autocomplete="off"
        :disabled="itemEditor.submitting"
        required
      />
    </label>

    <label class="editor-field">
      <span>Иконка</span>
      <input
        v-model.trim="itemEditor.form.icon"
        type="text"
        placeholder="proxmox, grafana..."
        autocomplete="off"
        :disabled="itemEditor.submitting"
      />
    </label>

    <label class="editor-field">
      <span>Site</span>
      <input
        v-model.trim="itemEditor.form.siteInput"
        type="text"
        placeholder="Spain, RF"
        autocomplete="off"
        :disabled="itemEditor.submitting"
      />
    </label>

    <label class="editor-field">
      <span>Открытие</span>
      <HeroDropdown
        v-model="itemEditor.form.open"
        aria-label="Режим открытия"
        :options="openModeOptions"
        :disabled="itemEditor.submitting"
      />
    </label>
  </div>

  <label class="editor-field">
    <span>Теги (через запятую)</span>
    <input
      v-model.trim="itemEditor.form.tagsInput"
      type="text"
      placeholder="infra, monitoring"
      autocomplete="off"
      :disabled="itemEditor.submitting"
    />
  </label>
</template>

<script setup lang="ts">
import { computed } from "vue";
import HeroDropdown from "@/primitives/selection/HeroDropdown.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const itemTypeOptions = [
  { value: "link", label: "link" },
  { value: "iframe", label: "iframe" },
];

const openModeOptions = [
  { value: "new_tab", label: "new_tab" },
  { value: "same_tab", label: "same_tab" },
];

const dashboard = useDashboardStore();
const {
  itemEditor,
  createEntityGroupOptions,
  groupById,
  setItemEditorParentGroup,
} = dashboard;

const parentGroupOptions = computed(() =>
  createEntityGroupOptions.value.map((group: any) => ({
    value: String(group.id || ""),
    label: String(group.title || group.id || ""),
  })),
);

const parentSubgroupOptions = computed(() => {
  const group = groupById.value.get(String(itemEditor.form.parentGroupId || ""));
  return (group?.subgroups || []).map((subgroup: any) => ({
    value: String(subgroup.id || ""),
    label: String(subgroup.title || subgroup.id || ""),
  }));
});
</script>
