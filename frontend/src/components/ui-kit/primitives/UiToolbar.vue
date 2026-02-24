<template>
  <header class="ui-toolbar">
    <div class="ui-toolbar__start">
      <slot name="start" />
    </div>
    <div class="ui-toolbar__center">
      <h2 v-if="title">{{ title }}</h2>
      <p v-if="subtitle">{{ subtitle }}</p>
      <slot />
    </div>
    <div class="ui-toolbar__end">
      <slot name="end" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  subtitle?: string;
}>();
</script>
