<template>
  <teleport to="body">
    <div v-if="open" class="ui-modal__backdrop" @click="onBackdropClick">
      <section class="ui-modal" role="dialog" aria-modal="true" @click.stop>
        <header class="ui-modal__head">
          <h3>{{ title }}</h3>
          <button type="button" class="ui-modal__close" @click="emit('close')">×</button>
        </header>
        <div class="ui-modal__body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="ui-modal__foot">
          <slot name="footer" />
        </footer>
      </section>
    </div>
  </teleport>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean;
    title?: string;
    closeOnBackdrop?: boolean;
  }>(),
  {
    title: "Modal",
    closeOnBackdrop: true,
  },
);

const emit = defineEmits<{
  close: [];
}>();

function onBackdropClick(): void {
  if (!props.closeOnBackdrop) return;
  emit("close");
}
</script>
