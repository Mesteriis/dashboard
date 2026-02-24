<template>
  <div class="ui-speed-dial" :class="[`dir-${direction}`, { 'is-open': open }]">
    <button
      type="button"
      class="ui-speed-dial__main"
      :aria-expanded="open"
      @click="open = !open"
    >
      <slot name="trigger">+</slot>
    </button>

    <div class="ui-speed-dial__actions">
      <button
        v-for="(item, index) in items"
        :key="item.id"
        type="button"
        class="ui-speed-dial__action"
        :style="actionStyle(index)"
        :title="item.label"
        @click="emitAction(item.id)"
      >
        <span v-if="item.icon" class="ui-speed-dial__action-icon">{{ item.icon }}</span>
        <span class="ui-speed-dial__action-label">{{ item.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface SpeedDialItem {
  id: string;
  label: string;
  icon?: string;
}

const props = withDefaults(
  defineProps<{
    items: SpeedDialItem[];
    direction?: "up" | "down" | "left" | "right";
    distance?: number;
  }>(),
  {
    direction: "up",
    distance: 56,
  },
);

const emit = defineEmits<{
  action: [id: string];
}>();

const open = ref(false);

function actionStyle(index: number): Record<string, string> {
  const offset = `${(index + 1) * props.distance}px`;
  if (!open.value) return { transform: "translate3d(0,0,0)", opacity: "0" };

  if (props.direction === "up") {
    return { transform: `translate3d(0, -${offset}, 0)`, opacity: "1" };
  }
  if (props.direction === "down") {
    return { transform: `translate3d(0, ${offset}, 0)`, opacity: "1" };
  }
  if (props.direction === "left") {
    return { transform: `translate3d(-${offset}, 0, 0)`, opacity: "1" };
  }
  return { transform: `translate3d(${offset}, 0, 0)`, opacity: "1" };
}

function emitAction(id: string): void {
  emit("action", id);
  open.value = false;
}
</script>
