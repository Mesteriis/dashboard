<template>
  <div class="ui-picklist">
    <section class="ui-picklist__list">
      <header>Source</header>
      <label
        v-for="item in sourceItems"
        :key="item.id"
        class="ui-picklist__item"
        :class="{ 'is-selected': sourceSelected.has(item.id) }"
      >
        <input type="checkbox" :checked="sourceSelected.has(item.id)" @change="toggleSource(item.id)" />
        <span>{{ item.label }}</span>
      </label>
    </section>

    <div class="ui-picklist__controls">
      <button type="button" :disabled="!sourceSelected.size" @click="moveToTarget">&gt;</button>
      <button type="button" :disabled="!targetSelected.size" @click="moveToSource">&lt;</button>
    </div>

    <section class="ui-picklist__list">
      <header>Target</header>
      <label
        v-for="item in targetItems"
        :key="item.id"
        class="ui-picklist__item"
        :class="{ 'is-selected': targetSelected.has(item.id) }"
      >
        <input type="checkbox" :checked="targetSelected.has(item.id)" @change="toggleTarget(item.id)" />
        <span>{{ item.label }}</span>
      </label>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface PickItem {
  id: string;
  label: string;
}

const props = defineProps<{
  sourceItems: PickItem[];
  targetItems: PickItem[];
}>();

const emit = defineEmits<{
  "update:sourceItems": [value: PickItem[]];
  "update:targetItems": [value: PickItem[]];
}>();

const sourceSelected = ref<Set<string>>(new Set());
const targetSelected = ref<Set<string>>(new Set());

function toggleSource(id: string): void {
  const next = new Set(sourceSelected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  sourceSelected.value = next;
}

function toggleTarget(id: string): void {
  const next = new Set(targetSelected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  targetSelected.value = next;
}

function moveToTarget(): void {
  if (!sourceSelected.value.size) return;
  const moving = props.sourceItems.filter((item) => sourceSelected.value.has(item.id));
  const source = props.sourceItems.filter((item) => !sourceSelected.value.has(item.id));
  const target = [...props.targetItems, ...moving];
  emit("update:sourceItems", source);
  emit("update:targetItems", target);
  sourceSelected.value = new Set();
}

function moveToSource(): void {
  if (!targetSelected.value.size) return;
  const moving = props.targetItems.filter((item) => targetSelected.value.has(item.id));
  const target = props.targetItems.filter((item) => !targetSelected.value.has(item.id));
  const source = [...props.sourceItems, ...moving];
  emit("update:sourceItems", source);
  emit("update:targetItems", target);
  targetSelected.value = new Set();
}
</script>
