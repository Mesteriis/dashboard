<template>
  <button
    class="ghost icon-btn"
    :class="[buttonClass, { active }]"
    :type="type"
    :title="title"
    :aria-label="ariaLabel || title"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<script setup>
defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  type: {
    type: String,
    default: 'button',
  },
  title: {
    type: String,
    default: '',
  },
  ariaLabel: {
    type: String,
    default: '',
  },
  buttonClass: {
    type: String,
    default: '',
  },
})

defineEmits(['click'])
</script>
