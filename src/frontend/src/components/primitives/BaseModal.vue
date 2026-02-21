<template>
  <div v-if="open" :class="backdropClass" @click.self="$emit('backdrop')">
    <div :class="modalClass">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  backdropClass: {
    type: String,
    required: true,
  },
  modalClass: {
    type: String,
    required: true,
  },
})

defineEmits(['backdrop'])
</script>
