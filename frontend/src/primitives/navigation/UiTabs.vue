<template>
  <section class="ui-tabs">
    <header class="ui-tabs__header" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="ui-tabs__tab"
        :class="{ 'is-active': modelValue === tab.id }"
        :disabled="tab.disabled"
        @click="emit('update:modelValue', tab.id)"
      >
        {{ tab.label }}
      </button>
    </header>

    <div class="ui-tabs__panel" role="tabpanel">
      <slot :active-tab="activeTab">
        <p>{{ activeTab?.content || "Нет контента" }}</p>
      </slot>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface TabItem {
  id: string;
  label: string;
  content?: string;
  disabled?: boolean;
}

const props = defineProps<{
  tabs: TabItem[];
  modelValue: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const activeTab = computed(
  () => props.tabs.find((tab) => tab.id === props.modelValue) || null,
);
</script>
