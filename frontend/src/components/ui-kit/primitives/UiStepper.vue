<template>
  <div class="ui-stepper">
    <button
      v-for="(step, index) in steps"
      :key="step.id"
      type="button"
      class="ui-stepper__step"
      :class="{
        'is-active': index === modelValue,
        'is-complete': index < modelValue,
      }"
      :disabled="linear && index > modelValue + 1"
      @click="emit('update:modelValue', index)"
    >
      <span class="ui-stepper__index">{{ index + 1 }}</span>
      <span class="ui-stepper__meta">
        <strong>{{ step.title }}</strong>
        <small v-if="step.description">{{ step.description }}</small>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
interface StepItem {
  id: string;
  title: string;
  description?: string;
}

withDefaults(
  defineProps<{
    steps: StepItem[];
    modelValue: number;
    linear?: boolean;
  }>(),
  {
    linear: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: number];
}>();
</script>
