<template>
  <UiSelect
    :id="id"
    :label="label"
    :model-value="modelValue"
    :options="options"
    :placeholder="placeholder"
    :disabled="disabled"
    multiple
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
    modelValue: string[];
    options: UiOption[];
    label?: string;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    id: "",
    label: "",
    placeholder: "Выберите значения",
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

function onUpdate(value: string | string[]): void {
  if (Array.isArray(value)) {
    emit("update:modelValue", value);
    return;
  }
  emit("update:modelValue", value ? [value] : []);
}
</script>
