<template>
  <UiSelect
    :id="id"
    :label="label"
    :model-value="modelValue"
    :options="options"
    :placeholder="placeholder"
    :disabled="disabled"
    :search-placeholder="searchPlaceholder"
    search
    @update:model-value="onUpdate"
  />
</template>

<script setup lang="ts">
import UiSelect from "@/ui/forms/UiSelect.vue";

interface UiOption {
  label: string;
  value: string;
  disabled?: boolean;
}

withDefaults(
  defineProps<{
    id?: string;
    modelValue: string;
    options: UiOption[];
    label?: string;
    placeholder?: string;
    searchPlaceholder?: string;
    disabled?: boolean;
  }>(),
  {
    id: "",
    label: "",
    placeholder: "Выберите",
    searchPlaceholder: "Поиск...",
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

function onUpdate(value: string | string[]): void {
  if (Array.isArray(value)) {
    emit("update:modelValue", String(value[0] || ""));
    return;
  }
  emit("update:modelValue", value);
}
</script>
