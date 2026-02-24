<template>
  <div class="ui-accordion" :class="`orientation-${orientation}`">
    <section
      v-for="item in items"
      :key="item.id"
      class="ui-accordion__item"
      :class="{ 'is-open': isOpen(item.id) }"
    >
      <button type="button" class="ui-accordion__header" @click="toggle(item.id)">
        <span>{{ item.title }}</span>
        <span>{{ isOpen(item.id) ? "−" : "+" }}</span>
      </button>
      <div v-if="isOpen(item.id)" class="ui-accordion__content">
        <slot name="item" :item="item">{{ item.content }}</slot>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface AccordionItem {
  id: string;
  title: string;
  content?: string;
}

const props = withDefaults(
  defineProps<{
    items: AccordionItem[];
    multiple?: boolean;
    orientation?: "vertical" | "horizontal";
    defaultOpen?: string[];
  }>(),
  {
    multiple: false,
    orientation: "vertical",
    defaultOpen: () => [],
  },
);

const opened = ref<Set<string>>(new Set(props.defaultOpen));

function isOpen(id: string): boolean {
  return opened.value.has(id);
}

function toggle(id: string): void {
  const next = new Set(opened.value);

  if (next.has(id)) {
    next.delete(id);
    opened.value = next;
    return;
  }

  if (!props.multiple) {
    next.clear();
  }
  next.add(id);
  opened.value = next;
}
</script>
